from src.tlb import TLBSimulator


def test_tlb_basic_hit_miss():
    t = TLBSimulator(num_entries=4, ways=2, policy_name="LRU")

    hit1, frame1 = t.lookup(vpn=5)
    assert hit1 is False
    assert frame1 is None

    t.insert(vpn=5, physical_frame=42)
    hit2, frame2 = t.lookup(vpn=5)
    assert hit2 is True
    assert frame2 == 42

    print("test_tlb_basic_hit_miss passed")


def test_tlb_eviction():
    # 1 set, 2 ways -> easy to force eviction
    t = TLBSimulator(num_entries=2, ways=2, policy_name="LRU")

    t.insert(vpn=1, physical_frame=10)
    t.insert(vpn=2, physical_frame=20)
    t.lookup(vpn=1)  # touch vpn=1, making vpn=2 the LRU one
    t.insert(vpn=3, physical_frame=30)  # should evict vpn=2

    hit, _ = t.lookup(vpn=2)
    assert hit is False, "vpn=2 should have been evicted"

    hit, frame = t.lookup(vpn=1)
    assert hit is True and frame == 10

    print("test_tlb_eviction passed")


if __name__ == "__main__":
    test_tlb_basic_hit_miss()
    test_tlb_eviction()
    print("All TLB tests passed")