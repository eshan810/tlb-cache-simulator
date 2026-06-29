from src.cache import CacheSimulator


def test_cache_basic_hit_miss():
    # 1024 bytes total, 64-byte blocks, 2-way -> 8 blocks total -> 4 sets
    c = CacheSimulator(cache_size_bytes=1024, block_size_bytes=64, ways=2, policy_name="LRU")

    hit1 = c.access(0x100)  # first touch -> must be a miss
    assert hit1 is False

    hit2 = c.access(0x100)  # same address again -> should now be a hit
    assert hit2 is True

    print("test_cache_basic_hit_miss passed")


def test_cache_address_splitting_consistency():
    c = CacheSimulator(cache_size_bytes=1024, block_size_bytes=64, ways=2, policy_name="LRU")

    # two addresses within the SAME block (block size 64, so within 0x40 of each other)
    # should be treated as the same block -> second access is a hit
    c.access(0x200)
    hit = c.access(0x210)  # still within the same 64-byte block as 0x200
    assert hit is True, "addresses within the same block should hit after first access"

    print("test_cache_address_splitting_consistency passed")


def test_cache_eviction_under_pressure():
    # tiny cache: 1 set, 2 ways -> forces eviction quickly
    c = CacheSimulator(cache_size_bytes=128, block_size_bytes=64, ways=2, policy_name="LRU")

    c.access(0x000)
    c.access(0x040)
    c.access(0x080)  # should evict 0x000's block (least recently used)

    hit = c.access(0x000)  # should be a miss again, since it was evicted
    assert hit is False

    print("test_cache_eviction_under_pressure passed")


if __name__ == "__main__":
    test_cache_basic_hit_miss()
    test_cache_address_splitting_consistency()
    test_cache_eviction_under_pressure()
    print("All cache tests passed")