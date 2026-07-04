import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.memory_system import MemorySystem
from src.trace_generator import (
    load_trace,
    generate_matrix_row_major,
    generate_matrix_col_major,
    generate_repeated_loop,
    save_trace,
)


def make_system(cache_policy="LRU", tlb_policy="LRU"):
    """Standard config used across all experiments for fair comparison."""
    return MemorySystem(
        page_size_bytes=4096,
        num_physical_frames=16,
        tlb_entries=16,
        tlb_ways=4,
        tlb_policy=tlb_policy,
        cache_size_bytes=4096,
        block_size_bytes=64,
        cache_ways=4,
        cache_policy=cache_policy,
    )


def run_trace(trace_file, label, cache_policy="LRU", tlb_policy="LRU"):
    mem = make_system(cache_policy, tlb_policy)
    traces = load_trace(trace_file)
    for mode, addr in traces:
        mem.access(addr, mode)
    stats = mem.stats()
    print(f"  {label}:")
    print(f"    Cache hit rate  : {stats['cache_hit_rate']:.2%}")
    print(f"    TLB hit rate    : {stats['tlb_hit_rate']:.2%}")
    print(f"    Page fault rate : {stats['page_fault_rate']:.2%}")
    print(f"    AMAT            : {mem.amat():.2f} cycles")
    return stats, mem


def experiment_access_patterns():
    """
    Experiment 1: how does access pattern affect cache performance?
    Compares sequential, strided, and random — the fundamental locality test.
    Sequential has maximum spatial locality (consecutive elements share
    a cache block), strided skips most of each loaded block, random
    has no locality at all.
    """
    print("\n=== Experiment 1: Access Pattern vs Cache Hit Rate ===")
    run_trace("sequential.trace", "Sequential (best case — maximum spatial locality)")
    run_trace("strided.trace",    "Strided    (medium stride — wastes loaded blocks)")
    run_trace("random.trace",     "Random     (worst case — no locality)")


def experiment_matrix_traversal():
    """
    Experiment 2: row-major vs column-major matrix traversal.
    Same data, same number of accesses, different order only.
    Matrix is 64x64 ints = 16384 bytes, which is 4x larger than
    the 4096-byte cache — so column-major will thrash it badly.
    Row-major accesses consecutive memory (cache-friendly).
    Column-major jumps by one full row (256 bytes) each step,
    blowing through cache lines without reusing them.
    """
    print("\n=== Experiment 2: Matrix Traversal Order ===")
    print("  (64x64 matrix = 16384 bytes, cache = 4096 bytes)")

    save_trace(generate_matrix_row_major(64, 64), "matrix_row_major_large.trace")
    save_trace(generate_matrix_col_major(64, 64), "matrix_col_major_large.trace")

    run_trace("matrix_row_major_large.trace", "Row-major    (cache-friendly)")
    run_trace("matrix_col_major_large.trace", "Column-major (cache-unfriendly)")


def experiment_temporal_locality():
    """
    Experiment 3: repeated loop scan — shows temporal locality.
    512-byte working set fits in cache (cache = 4096 bytes).
    First pass: 8 cold misses (512/64 = 8 blocks to load).
    All 9 subsequent passes: nearly 100% hits.
    Shows that if your working set fits in cache, repeated
    access costs almost nothing after the first pass.
    """
    print("\n=== Experiment 3: Repeated Loop (Temporal Locality) ===")
    print("  (512-byte array, 10 iterations — working set fits in cache)")
    run_trace("repeated_loop.trace",
              "Repeated loop (10x over 512B array)")


def experiment_replacement_policies():
    """
    Experiment 4: LRU vs FIFO vs RANDOM on a working set
    larger than the cache, so evictions actually happen.
    8192-byte array repeated 5 times through a 4096-byte cache.
    LRU should win on this workload because it retains the most
    recently used blocks — the ones most likely to be needed again
    in the next loop iteration. FIFO evicts by insertion order
    regardless of recency, so it can evict something right before
    it's needed again. RANDOM is unpredictable but surprisingly
    competitive on some workloads (interesting to discuss).
    """
    print("\n=== Experiment 4: Replacement Policy Comparison ===")
    print("  (8192-byte array, 5 iterations — working set EXCEEDS cache)")

    save_trace(
        generate_repeated_loop(num_iterations=5, array_size_bytes=8192),
        "repeated_loop_large.trace"
    )

    for policy in ["LRU", "FIFO", "RANDOM"]:
        run_trace("repeated_loop_large.trace",
                  f"Policy: {policy}",
                  cache_policy=policy)


def experiment_tlb_pressure():
    """
    Experiment 5: TLB pressure.
    TLB has 16 entries, page size = 4096 bytes.
    To stress the TLB, we need random accesses across many pages —
    so each access likely lands on a different page, forcing a new
    TLB lookup each time.
    Small range: accesses stay within 2 pages -> TLB almost never misses.
    Large range: accesses spread across 128 pages -> TLB thrashes
    (only 16 entries, so most accesses evict a translation before reuse).
    """
    print("\n=== Experiment 5: TLB Pressure ===")
    print("  (TLB has 16 entries, page size = 4096 bytes)")

    from src.trace_generator import generate_random, save_trace

    # small range: 8192 bytes = 2 pages, random within them
    # TLB only needs to cache 2 translations -> near 100% hit rate
    save_trace(
        generate_random(num_accesses=5000, base_address=0x10000,
                        memory_range=8192),
        "tlb_small_random.trace"
    )

    # large range: 524288 bytes = 128 pages, random within them
    # TLB can only hold 16 translations at once -> constant eviction
    save_trace(
        generate_random(num_accesses=5000, base_address=0x10000,
                        memory_range=524288),
        "tlb_large_random.trace"
    )

    run_trace("tlb_small_random.trace",
              "Small range  (2 pages   — TLB easily covers working set)")
    run_trace("tlb_large_random.trace",
              "Large range  (128 pages — TLB thrashes, constant page walks)")


if __name__ == "__main__":
    experiment_access_patterns()
    experiment_matrix_traversal()
    experiment_temporal_locality()
    experiment_replacement_policies()
    experiment_tlb_pressure()