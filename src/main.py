import argparse
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.memory_system import MemorySystem
from src.trace_generator import load_trace, save_trace
from src.trace_generator import (
    generate_sequential,
    generate_strided,
    generate_random,
    generate_repeated_loop,
    generate_matrix_row_major,
    generate_matrix_col_major,
)


PATTERNS = {
    "sequential"      : lambda: generate_sequential(1000),
    "strided"         : lambda: generate_strided(1000),
    "random"          : lambda: generate_random(1000),
    "repeated_loop"   : lambda: generate_repeated_loop(10),
    "matrix_row_major": lambda: generate_matrix_row_major(64, 64),
    "matrix_col_major": lambda: generate_matrix_col_major(64, 64),
}


def build_parser():
    p = argparse.ArgumentParser(
        description="Cache & TLB Simulator — explore memory hierarchy performance.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # input
    input_group = p.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--trace", metavar="FILE",
        help="Path to a .trace file (one 'R|W 0xADDR' per line)."
    )
    input_group.add_argument(
        "--pattern",
        choices=PATTERNS.keys(),
        help="Generate a built-in access pattern instead of loading a file."
    )

    # cache config
    p.add_argument("--cache-size",  type=int, default=4096,
                   help="Total cache size in bytes.")
    p.add_argument("--block-size",  type=int, default=64,
                   help="Cache block/line size in bytes.")
    p.add_argument("--cache-ways",  type=int, default=4,
                   help="Cache associativity (ways per set).")
    p.add_argument("--cache-policy",
                   choices=["LRU", "FIFO", "RANDOM"], default="LRU",
                   help="Cache replacement policy.")

    # TLB config
    p.add_argument("--tlb-entries", type=int, default=16,
                   help="Number of TLB entries.")
    p.add_argument("--tlb-ways",    type=int, default=4,
                   help="TLB associativity.")
    p.add_argument("--tlb-policy",
                   choices=["LRU", "FIFO", "RANDOM"], default="LRU",
                   help="TLB replacement policy.")

    # page table config
    p.add_argument("--page-size",    type=int, default=4096,
                   help="Page size in bytes.")
    p.add_argument("--num-frames",   type=int, default=16,
                   help="Number of physical frames.")
    p.add_argument("--page-policy",
                   choices=["LRU", "FIFO", "RANDOM"], default="LRU",
                   help="Page replacement policy.")

    # output
    p.add_argument("--amat", action="store_true",
                   help="Print AMAT (Average Memory Access Time) breakdown.")
    p.add_argument("--save-trace", metavar="FILE",
                   help="Save generated pattern to this .trace file.")
    p.add_argument("--verbose", action="store_true",
                   help="Print result of every individual access.")

    return p


def main():
    args = build_parser().parse_args()

    # ── build memory system ───────────────────────────────────────────────
    mem = MemorySystem(
        page_size_bytes       = args.page_size,
        num_physical_frames   = args.num_frames,
        tlb_entries           = args.tlb_entries,
        tlb_ways              = args.tlb_ways,
        tlb_policy            = args.tlb_policy,
        cache_size_bytes      = args.cache_size,
        block_size_bytes      = args.block_size,
        cache_ways            = args.cache_ways,
        cache_policy          = args.cache_policy,
        page_replacement_policy = args.page_policy,
    )

    # ── load or generate trace ────────────────────────────────────────────
    if args.trace:
        print(f"Loading trace: {args.trace}")
        traces = load_trace(args.trace)
    else:
        print(f"Generating pattern: {args.pattern}")
        traces = PATTERNS[args.pattern]()
        if args.save_trace:
            save_trace(traces, args.save_trace)

    # ── run simulation ────────────────────────────────────────────────────
    print(f"Running {len(traces)} accesses...\n")

    for mode, addr in traces:
        result = mem.access(addr, mode)
        if args.verbose:
            status = (
                f"{'HIT ' if result['cache_hit'] else 'MISS'} | "
                f"TLB {'HIT ' if result['tlb_hit'] else 'MISS'} | "
                f"vaddr={hex(result['virtual_address'])} "
                f"paddr={hex(result['physical_address'])}"
            )
            print(status)

    # ── print results ─────────────────────────────────────────────────────
    stats = mem.stats()

    print("=" * 45)
    print("  Configuration")
    print("=" * 45)
    print(f"  Cache : {args.cache_size}B, {args.block_size}B blocks, "
          f"{args.cache_ways}-way, {args.cache_policy}")
    print(f"  TLB   : {args.tlb_entries} entries, "
          f"{args.tlb_ways}-way, {args.tlb_policy}")
    print(f"  Pages : {args.page_size}B pages, "
          f"{args.num_frames} frames, {args.page_policy}")
    print()
    print("=" * 45)
    print("  Results")
    print("=" * 45)
    print(f"  Total accesses  : {len(traces)}")
    print(f"  Cache hit rate  : {stats['cache_hit_rate']:.2%}")
    print(f"  TLB hit rate    : {stats['tlb_hit_rate']:.2%}")
    print(f"  Page fault rate : {stats['page_fault_rate']:.2%}")

    if args.amat:
        print()
        mem.amat_report()

    print("=" * 45)


if __name__ == "__main__":
    main()