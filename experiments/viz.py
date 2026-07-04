import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from src.memory_system import MemorySystem
from src.trace_generator import (
    load_trace,
    generate_matrix_row_major,
    generate_matrix_col_major,
    generate_repeated_loop,
    generate_random,
    save_trace,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def make_system(cache_policy="LRU", tlb_policy="LRU",
                cache_size=4096, num_frames=16):
    return MemorySystem(
        page_size_bytes=4096,
        num_physical_frames=num_frames,
        tlb_entries=16,
        tlb_ways=4,
        tlb_policy=tlb_policy,
        cache_size_bytes=cache_size,
        block_size_bytes=64,
        cache_ways=4,
        cache_policy=cache_policy,
    )


def run_trace(trace_file, cache_policy="LRU", tlb_policy="LRU",
              cache_size=4096, num_frames=16):
    mem = make_system(cache_policy, tlb_policy, cache_size, num_frames)
    for mode, addr in load_trace(trace_file):
        mem.access(addr, mode)
    return mem.stats()


COLORS = {
    "blue":   "#4C72B0",
    "orange": "#DD8452",
    "green":  "#55A868",
    "red":    "#C44E52",
    "purple": "#8172B3",
    "grey":   "#8C8C8C",
}

os.makedirs("experiments/charts", exist_ok=True)


def save_fig(filename, title):
    plt.suptitle(title, fontsize=13, fontweight="bold", y=1.01)
    plt.tight_layout()
    path = f"experiments/charts/{filename}"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"Saved {path}")
    plt.close()


# ── chart 1: access patterns ──────────────────────────────────────────────

def chart_access_patterns():
    labels   = ["Sequential", "Strided", "Random"]
    files    = ["sequential.trace", "strided.trace", "random.trace"]
    colors   = [COLORS["blue"], COLORS["orange"], COLORS["red"]]

    cache_rates = []
    tlb_rates   = []
    pf_rates    = []

    for f in files:
        s = run_trace(f)
        cache_rates.append(s["cache_hit_rate"] * 100)
        tlb_rates.append(s["tlb_hit_rate"] * 100)
        pf_rates.append(s["page_fault_rate"] * 100)

    x     = np.arange(len(labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - width, cache_rates, width, label="Cache Hit Rate",  color=COLORS["blue"])
    ax.bar(x,         tlb_rates,   width, label="TLB Hit Rate",    color=COLORS["green"])
    ax.bar(x + width, pf_rates,    width, label="Page Fault Rate", color=COLORS["red"])

    ax.set_ylabel("Rate (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 110)
    ax.legend()
    ax.bar_label(ax.containers[0], fmt="%.1f%%", padding=3, fontsize=8)
    ax.bar_label(ax.containers[1], fmt="%.1f%%", padding=3, fontsize=8)
    ax.bar_label(ax.containers[2], fmt="%.1f%%", padding=3, fontsize=8)

    save_fig("01_access_patterns.png",
             "Experiment 1 — Access Pattern vs Memory Hierarchy Performance")


# ── chart 2: matrix traversal ─────────────────────────────────────────────

def chart_matrix_traversal():
    save_trace(generate_matrix_row_major(64, 64), "matrix_row_major_large.trace")
    save_trace(generate_matrix_col_major(64, 64), "matrix_col_major_large.trace")

    labels = ["Row-major\n(cache-friendly)", "Column-major\n(cache-unfriendly)"]
    files  = ["matrix_row_major_large.trace", "matrix_col_major_large.trace"]
    colors = [COLORS["blue"], COLORS["red"]]

    rates = [run_trace(f)["cache_hit_rate"] * 100 for f in files]

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(labels, rates, color=colors, width=0.4)
    ax.set_ylabel("Cache Hit Rate (%)")
    ax.set_ylim(0, 110)
    ax.bar_label(bars, fmt="%.2f%%", padding=5, fontweight="bold", fontsize=11)

    ax.annotate("Same data.\nSame number of accesses.\nDifferent loop order only.",
                xy=(0.5, 0.6), xycoords="axes fraction",
                ha="center", fontsize=10,
                bbox=dict(boxstyle="round,pad=0.4", fc="#FFF9C4", ec="#CCBB00"))

    save_fig("02_matrix_traversal.png",
             "Experiment 2 — Matrix Traversal Order: Row-major vs Column-major")


# ── chart 3: temporal locality ────────────────────────────────────────────

def chart_temporal_locality():
    """Show hit rate per pass for a repeated loop."""
    array_size   = 512
    element_size = 4
    num_elements = array_size // element_size
    base_address = 0x10000
    num_iters    = 10

    mem = make_system()
    pass_hit_rates = []

    for iteration in range(num_iters):
        hits_this_pass = 0
        for i in range(num_elements):
            addr   = base_address + i * element_size
            result = mem.access(addr)
            if result["cache_hit"]:
                hits_this_pass += 1
        pass_hit_rates.append(hits_this_pass / num_elements * 100)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(range(1, num_iters + 1), pass_hit_rates,
            marker="o", color=COLORS["blue"], linewidth=2, markersize=7)
    ax.fill_between(range(1, num_iters + 1), pass_hit_rates,
                    alpha=0.15, color=COLORS["blue"])

    ax.set_xlabel("Loop Iteration (Pass Number)")
    ax.set_ylabel("Cache Hit Rate per Pass (%)")
    ax.set_xticks(range(1, num_iters + 1))
    ax.set_ylim(0, 110)
    ax.axhline(y=100, color=COLORS["grey"], linestyle="--", alpha=0.5,
               label="100% (theoretical max)")
    ax.legend()

    for i, v in enumerate(pass_hit_rates):
        ax.annotate(f"{v:.1f}%", (i + 1, v),
                    textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=8)

    save_fig("03_temporal_locality.png",
             "Experiment 3 — Temporal Locality: Cache Hit Rate per Loop Pass")


# ── chart 4: replacement policies ────────────────────────────────────────

def chart_replacement_policies():
    save_trace(
        generate_repeated_loop(num_iterations=5, array_size_bytes=8192),
        "repeated_loop_large.trace"
    )

    policies = ["LRU", "FIFO", "RANDOM"]
    colors   = [COLORS["blue"], COLORS["orange"], COLORS["green"]]
    rates    = [
        run_trace("repeated_loop_large.trace", cache_policy=p)["cache_hit_rate"] * 100
        for p in policies
    ]

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(policies, rates, color=colors, width=0.4)
    ax.set_ylabel("Cache Hit Rate (%)")
    ax.set_ylim(88, 100)   # zoom in — differences are subtle
    ax.bar_label(bars, fmt="%.2f%%", padding=5, fontweight="bold", fontsize=11)

    ax.annotate(
        "LRU's sequential flooding problem:\nfor scans larger than cache,\n"
        "LRU ≡ FIFO. Random wins by luck.",
        xy=(0.5, 0.3), xycoords="axes fraction",
        ha="center", fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", fc="#FFE0E0", ec="#CC0000")
    )

    save_fig("04_replacement_policies.png",
             "Experiment 4 — Replacement Policy Comparison (working set > cache)")


# ── chart 5: TLB pressure ────────────────────────────────────────────────

def chart_tlb_pressure():
    save_trace(
        generate_random(5000, base_address=0x10000, memory_range=8192),
        "tlb_small_random.trace"
    )
    save_trace(
        generate_random(5000, base_address=0x10000, memory_range=524288),
        "tlb_large_random.trace"
    )

    labels = ["2 pages\n(TLB fits)", "128 pages\n(TLB thrashes)"]
    files  = ["tlb_small_random.trace", "tlb_large_random.trace"]
    colors = [COLORS["blue"], COLORS["red"]]

    tlb_rates = [run_trace(f)["tlb_hit_rate"] * 100 for f in files]
    pf_rates  = [run_trace(f)["page_fault_rate"] * 100 for f in files]

    x     = np.arange(len(labels))
    width = 0.3

    fig, ax = plt.subplots(figsize=(8, 5))
    b1 = ax.bar(x - width / 2, tlb_rates, width,
                label="TLB Hit Rate",    color=COLORS["blue"])
    b2 = ax.bar(x + width / 2, pf_rates,  width,
                label="Page Fault Rate", color=COLORS["red"])

    ax.set_ylabel("Rate (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 115)
    ax.legend()
    ax.bar_label(b1, fmt="%.1f%%", padding=3, fontsize=9)
    ax.bar_label(b2, fmt="%.1f%%", padding=3, fontsize=9)

    save_fig("05_tlb_pressure.png",
             "Experiment 5 — TLB Pressure: Small vs Large Working Set")


# ── run all ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating charts...")
    chart_access_patterns()
    chart_matrix_traversal()
    chart_temporal_locality()
    chart_replacement_policies()
    chart_tlb_pressure()
    print("\nAll charts saved to experiments/charts/")