from src.page_table import PageTable


def test_page_table_fault_on_first_access():
    pt = PageTable(num_physical_frames=2, page_replacement_policy="LRU")

    frame = pt.translate(vpn=1)
    assert pt.page_faults == 1
    assert frame in (0, 1)  # one of the 2 available frames

    print("test_page_table_fault_on_first_access passed")


def test_page_table_no_fault_on_repeat():
    pt = PageTable(num_physical_frames=2, page_replacement_policy="LRU")

    frame1 = pt.translate(vpn=1)
    frame2 = pt.translate(vpn=1)  # same page again, should NOT fault
    assert pt.page_faults == 1
    assert frame1 == frame2

    print("test_page_table_no_fault_on_repeat passed")


def test_page_table_eviction_when_full():
    pt = PageTable(num_physical_frames=2, page_replacement_policy="LRU")

    pt.translate(vpn=1)
    pt.translate(vpn=2)
    pt.translate(vpn=1)  # touch vpn=1, vpn=2 becomes LRU
    pt.translate(vpn=3)  # no free frames -> must evict vpn=2

    assert pt.page_faults == 3

    # vpn=2 should fault again since it was evicted
    faults_before = pt.page_faults
    pt.translate(vpn=2)
    assert pt.page_faults == faults_before + 1

    print("test_page_table_eviction_when_full passed")


if __name__ == "__main__":
    test_page_table_fault_on_first_access()
    test_page_table_no_fault_on_repeat()
    test_page_table_eviction_when_full()
    print("All page table tests passed")