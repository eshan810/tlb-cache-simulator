from multi_core.cache_line import CacheLine
from multi_core.mesi import MESIState, BusTransaction

CACHE_LINE_SIZE = 64  # bytes

class MultiCoreCache:
    def __init__(self, core_id, num_sets=16, associativity=4):
        self.core_id      = core_id
        self.num_sets     = num_sets
        self.associativity = associativity

        # sets[set_index] = list of CacheLines (ways)
        self.sets = [
            [CacheLine() for _ in range(associativity)]
            for _ in range(num_sets)
        ]

        # Stats
        self.hits         = 0
        self.misses       = 0
        self.invalidations = 0
        self.evictions    = 0
        self.clock        = 0

    # ── address decomposition ──────────────────────────────
    def _set_index(self, address):
        return (address // CACHE_LINE_SIZE) % self.num_sets

    def _tag(self, address):
        return address // (CACHE_LINE_SIZE * self.num_sets)

    # ── lookup ─────────────────────────────────────────────
    def find_line(self, address):
        idx = self._set_index(address)
        tag = self._tag(address)
        for way in self.sets[idx]:
            if way.tag == tag and way.is_valid():
                return way
        return None

    # ── LRU eviction ───────────────────────────────────────
    def get_lru_way(self, address):
        idx = self._set_index(address)
        return min(self.sets[idx], key=lambda w: w.last_used)

    # ── install a fetched line ──────────────────────────────
    def install_line(self, address, data, state, clock):
        way = self.get_lru_way(address)
        if way.state == MESIState.MODIFIED:
            # caller must handle writeback before calling this
            self.evictions += 1
        way.tag       = self._tag(address)
        way.data      = data
        way.state     = state
        way.last_used = clock
        return way

    # ── snoop handler (called by bus) ──────────────────────
    def snoop(self, transaction, address, memory):
        """
        React to another core's bus transaction.
        Returns True if this cache had the line.
        """
        line = self.find_line(address)
        if line is None:
            return False

        if transaction == BusTransaction.READ:
            if line.state == MESIState.MODIFIED:
                # Write dirty data back to memory, downgrade to S
                memory[address] = line.data
                line.state = MESIState.SHARED
                self.invalidations += 1
            elif line.state == MESIState.EXCLUSIVE:
                line.state = MESIState.SHARED
            # SHARED stays SHARED
            return True

        elif transaction in (BusTransaction.READ_EXCL,
                             BusTransaction.INVALIDATE):
            if line.state == MESIState.MODIFIED:
                memory[address] = line.data
            line.state = MESIState.INVALID
            self.invalidations += 1
            return True

        return False

    # ── stats helper ───────────────────────────────────────
    def hit_rate(self):
        total = self.hits + self.misses
        return (self.hits / total * 100) if total else 0.0