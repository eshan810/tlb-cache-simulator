from src.set_associative_structure import SetAssociativeStructure


def test_lru_basic():
    s = SetAssociativeStructure(num_sets=1, ways=2, policy_name="LRU")
    s.insert(0, "A", "data_A")
    s.insert(0, "B", "data_B")

    hit, _ = s.lookup(0, "A")  # touch A so B becomes LRU
    assert hit is True

    evicted = s.insert(0, "C", "data_C")
    assert evicted == "B", f"expected B evicted, got {evicted}"

    hit, _ = s.lookup(0, "A")
    assert hit is True
    hit, _ = s.lookup(0, "B")
    assert hit is False

    print("test_lru_basic passed")


def test_separate_sets_dont_interfere():
    s = SetAssociativeStructure(num_sets=2, ways=1, policy_name="LRU")
    s.insert(0, "X", "data_X")
    s.insert(1, "Y", "data_Y")

    # inserting into set 0 again should not evict anything from set 1
    s.insert(0, "Z", "data_Z")
    hit, _ = s.lookup(1, "Y")
    assert hit is True, "set 1 should be untouched by activity in set 0"

    print("test_separate_sets_dont_interfere passed")


def test_hit_rate_calculation():
    s = SetAssociativeStructure(num_sets=1, ways=2, policy_name="LRU")
    s.insert(0, "A", "data_A")
    s.lookup(0, "A")   # hit
    s.lookup(0, "B")   # miss
    assert s.hit_rate() == 0.5, f"expected 0.5, got {s.hit_rate()}"
    print("test_hit_rate_calculation passed")


if __name__ == "__main__":
    test_lru_basic()
    test_separate_sets_dont_interfere()
    test_hit_rate_calculation()
    print("All set-associative structure tests passed")