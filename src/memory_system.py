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