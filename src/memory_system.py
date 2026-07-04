import math
from src.cache import CacheSimulator
from src.tlb import TLBSimulator
from src.page_table import PageTable


class MemorySystem:
    """
    Full pipeline: virtual address -> TLB/page-table translation
    -> physical address -> cache lookup.

    page_size_bytes: size of one page (must be power of 2), used to
        split a virtual address into (VPN, page_offset).
    """

    def __init__(self, page_size_bytes, num_physical_frames,
                 tlb_entries, tlb_ways, tlb_policy,
                 cache_size_bytes, block_size_bytes, cache_ways, cache_policy,
                 page_replacement_policy="LRU"):

        self.page_size = page_size_bytes
        self.page_offset_bits = int(math.log2(page_size_bytes))

        self.tlb = TLBSimulator(tlb_entries, tlb_ways, tlb_policy)
        self.page_table = PageTable(num_physical_frames, page_replacement_policy)
        self.cache = CacheSimulator(cache_size_bytes, block_size_bytes, cache_ways, cache_policy)

        self.tlb_hits = 0
        self.tlb_misses = 0
        self.total_accesses = 0
        self.system_page_faults = 0

    def _virtual_to_vpn_offset(self, virtual_address):
        page_offset = virtual_address & (self.page_size - 1)
        vpn = virtual_address >> self.page_offset_bits
        return vpn, page_offset

    def access(self, virtual_address, mode="R"):
        """
        Simulates one full memory access. Returns a dict of what happened,
        useful for logging/analysis later.
        """
        self.total_accesses += 1
        vpn, page_offset = self._virtual_to_vpn_offset(virtual_address)

        # Step 1: try the TLB first (the fast path).
        tlb_hit, frame = self.tlb.lookup(vpn)

        if tlb_hit:
            self.tlb_hits += 1
        else:
            self.tlb_misses += 1
            # Step 2: TLB miss -> walk the page table (the slow path).
            faults_before = self.page_table.page_faults
            frame = self.page_table.translate(vpn)
            # if translate() caused a new fault, record it at system level too
            if self.page_table.page_faults > faults_before:
                self.system_page_faults += 1
            # Refill the TLB so next time this page is a TLB hit.
            self.tlb.insert(vpn, frame)

        # Step 3: reconstruct physical address from frame + page_offset.
        physical_address = (frame << self.page_offset_bits) | page_offset

        # Step 4: access the cache using the physical address
        # (physically-indexed, physically-tagged cache — simpler, more
        # common real-world design: translate first, then access cache).
        cache_hit = self.cache.access(physical_address, mode)

        return {
            "virtual_address": virtual_address,
            "physical_address": physical_address,
            "tlb_hit": tlb_hit,
            "cache_hit": cache_hit,
        }

    def stats(self):
        total_tlb = self.tlb_hits + self.tlb_misses
        return {
            "tlb_hit_rate": self.tlb_hits / total_tlb if total_tlb else 0.0,
            "page_fault_rate": self.system_page_faults / self.total_accesses if self.total_accesses else 0.0,
            "cache_hit_rate": self.cache.hit_rate(),
        }
    
    def amat(self,
         l1_hit_cycles=4,
         l2_hit_cycles=12,
         mem_cycles=200,
         tlb_hit_cycles=1,
         tlb_miss_penalty=20):
        """
        Average Memory Access Time in CPU cycles.

        Realistic latency model:
        L1 cache hit   :   4 cycles  (fast SRAM)
        L2 cache hit   :  12 cycles  (slower SRAM)
        RAM access     : 200 cycles  (DRAM)
        TLB hit        :   1 cycle   (parallel with cache in real HW,
                                        modelled as small adder here)
        TLB miss       :  20 cycles  (page table walk penalty)

        Formula:
        AMAT = translation_cost
            + L1_hit_time
            + L1_miss_rate × (L2_hit_time + L2_miss_rate × mem_time)

        We don't simulate L2 explicitly, so we treat an L1 miss as going
        straight to RAM — a conservative (pessimistic) model that makes
        the cache miss penalty very visible.
        """
        cache_miss_rate = 1.0 - self.cache.hit_rate()
        total_tlb       = self.tlb_hits + self.tlb_misses
        tlb_miss_rate   = self.tlb_misses / total_tlb if total_tlb else 0.0

        translation_cost = tlb_hit_cycles + tlb_miss_rate * tlb_miss_penalty
        memory_cost      = l1_hit_cycles + cache_miss_rate * mem_cycles

        return translation_cost + memory_cost

    def amat_report(self):
        """Print a human-readable AMAT breakdown."""
        cache_miss_rate = 1.0 - self.cache.hit_rate()
        total_tlb       = self.tlb_hits + self.tlb_misses
        tlb_miss_rate   = self.tlb_misses / total_tlb if total_tlb else 0.0
        value           = self.amat()

        print(f"  AMAT breakdown:")
        print(f"    Cache miss rate : {cache_miss_rate:.2%}")
        print(f"    TLB miss rate   : {tlb_miss_rate:.2%}")
        print(f"    AMAT            : {value:.2f} cycles")
        return value