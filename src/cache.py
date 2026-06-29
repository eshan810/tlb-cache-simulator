import math
from src.set_associative_structure import SetAssociativeStructure


class CacheSimulator:
    """
    A configurable set-associative cache.

    cache_size_bytes: total cache capacity
    block_size_bytes: size of one cache line (must be power of 2)
    ways: associativity
    policy_name: 'LRU', 'FIFO', or 'RANDOM'
    """

    def __init__(self, cache_size_bytes, block_size_bytes, ways, policy_name="LRU"):
        self.block_size = block_size_bytes
        self.ways = ways

        num_blocks_total = cache_size_bytes // block_size_bytes
        self.num_sets = num_blocks_total // ways

        if self.num_sets <= 0:
            raise ValueError("cache_size_bytes too small for given block_size/ways")

        self.offset_bits = int(math.log2(block_size_bytes))
        self.index_bits = int(math.log2(self.num_sets))

        self.structure = SetAssociativeStructure(
            num_sets=self.num_sets, ways=ways, policy_name=policy_name
        )

    def _split_address(self, address):
        """
        Address layout (from MSB to LSB): [ tag | index | offset ]
        offset_bits = log2(block_size)   -> byte position within a block
        index_bits  = log2(num_sets)     -> which set this address maps to
        tag         = everything above that -> uniquely identifies the block
        """
        offset = address & (self.block_size - 1)
        index = (address >> self.offset_bits) & (self.num_sets - 1)
        tag = address >> (self.offset_bits + self.index_bits)
        return tag, index, offset

    def access(self, address, mode="R"):
        """
        Simulates one memory access through the cache.
        Returns True if hit, False if miss (and inserts the block on a miss).
        """
        tag, index, _offset = self._split_address(address)
        hit, _data = self.structure.lookup(index, tag)

        if not hit:
            # On a miss, the block gets fetched from lower memory and inserted.
            # 'data' is just a placeholder here — we care about hit/miss timing,
            # not simulating actual byte contents.
            self.structure.insert(index, tag, data=None)

        return hit

    def hit_rate(self):
        return self.structure.hit_rate()