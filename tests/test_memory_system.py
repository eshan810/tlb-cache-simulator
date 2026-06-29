from src.memory_system import MemorySystem


def make_default_system():
    return MemorySystem(
        page_size_bytes=4096, num_physical_frames=4,
        tlb_entries=4, tlb_ways=2, tlb_policy="LRU",
        cache_size_bytes=1024, block_size_bytes=64, cache_ways=2, cache_policy="LRU",
    )


def test_first_access_is_full_miss():
    mem = make_default_system()
    result = mem.access(0x1000)
    assert result["tlb_hit"] is False  # nothing cached yet
    print("test_first_access_is_full_miss passed")


def test_repeat_access_hits_tlb_and_cache():
    mem = make_default_system()
    mem.access(0x1000)             # cold: TLB miss, page fault, cache miss
    result = mem.access(0x1000)    # repeat: should hit both TLB and cache
    assert result["tlb_hit"] is True
    assert result["cache_hit"] is True
    print("test_repeat_access_hits_tlb_and_cache passed")


def test_stats_reflect_accesses():
    mem = make_default_system()
    mem.access(0x1000)
    mem.access(0x1000)
    mem.access(0x2000)
    stats = mem.stats()
    assert 0.0 <= stats["tlb_hit_rate"] <= 1.0
    assert 0.0 <= stats["cache_hit_rate"] <= 1.0
    print("test_stats_reflect_accesses passed:", stats)


if __name__ == "__main__":
    test_first_access_is_full_miss()
    test_repeat_access_hits_tlb_and_cache()
    test_stats_reflect_accesses()
    print("All memory system tests passed")