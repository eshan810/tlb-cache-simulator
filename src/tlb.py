from src.set_associative_structure import SetAssociativeStructure


class TLBSimulator:
    """
    Caches recent virtual-page -> physical-frame translations.

    num_entries: total TLB capacity (in translations)
    ways: associativity
    """

    def __init__(self, num_entries, ways, policy_name="LRU"):
        self.ways = ways
        self.num_sets = num_entries // ways
        if self.num_sets <= 0:
            raise ValueError("num_entries too small for given ways")

        self.structure = SetAssociativeStructure(
            num_sets=self.num_sets, ways=ways, policy_name=policy_name
        )

    def _split_vpn(self, vpn):
        # Same idea as cache index/tag, just operating on page numbers
        # instead of byte addresses (no offset bits needed here).
        index = vpn % self.num_sets
        tag = vpn // self.num_sets
        return tag, index

    def lookup(self, vpn):
        """Returns (hit, physical_frame_or_None)."""
        tag, index = self._split_vpn(vpn)
        hit, frame = self.structure.lookup(index, tag)
        return hit, frame

    def insert(self, vpn, physical_frame):
        tag, index = self._split_vpn(vpn)
        self.structure.insert(index, tag, data=physical_frame)

    def hit_rate(self):
        return self.structure.hit_rate()