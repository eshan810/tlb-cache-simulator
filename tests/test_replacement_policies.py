from src.replacement_policies import make_policy


def test_lru_eviction_order():
    p = make_policy("LRU")
    p.access("A")
    p.access("B")
    p.access("C")
    # touch A again -> A becomes freshest, B is now oldest
    p.access("A")
    evicted = p.evict()
    assert evicted == "B", f"expected B, got {evicted}"
    print("test_lru_eviction_order passed")


def test_fifo_ignores_reaccess():
    p = make_policy("FIFO")
    p.access("A")
    p.access("B")
    p.access("C")
    # touching A again should NOT change FIFO order
    p.access("A")
    evicted = p.evict()
    assert evicted == "A", f"expected A, got {evicted}"
    print("test_fifo_ignores_reaccess passed")


def test_random_evicts_existing_tag():
    p = make_policy("RANDOM")
    p.access("A")
    p.access("B")
    evicted = p.evict()
    assert evicted in ("A", "B")
    print("test_random_evicts_existing_tag passed")


if __name__ == "__main__":
    test_lru_eviction_order()
    test_fifo_ignores_reaccess()
    test_random_evicts_existing_tag()
    print("All replacement policy tests passed")