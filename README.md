# tlb-cache-simulator
# Memory Hierarchy Simulator

A cycle-accurate virtual memory pipeline simulator built from scratch in Python — covering the full path from virtual address translation to cache lookup. Built as a curiosity-driven exploration of how modern CPUs bridge the gap between fast processors and slow memory, and how software access patterns dramatically affect hardware performance.

---

## Motivation

Every program I write accesses memory constantly, but I realized I had no concrete understanding of what actually happens between "my code reads a variable" and "the CPU gets that value." This project is my attempt to build that understanding from first principles — implementing the full translation and caching pipeline myself, then running experiments to observe how real software patterns affect hardware performance.

The results were genuinely surprising in places (see Findings below).

---

## What It Simulates

Virtual Address
      │
      ▼
┌─────────────┐   hit   ┌──────────────────┐
│     TLB     │────────▶│  Physical Address │──────────────┐
│ (16 entries)│         └──────────────────┘                |
└─────────────┘                                             ▼
      │ miss                                   ┌──────────────────┐   hit   ┌──────┐
      ▼                                        │      Cache       │────────▶│ Data │
┌─────────────┐  frame  ┌──────────────────┐   │  (4KB, 4-way SA) │         └──────┘
│ Page Table  │────────▶│  Physical Address │─▶└──────────────────┘
│  (2-level)  │  +refill│  (+ TLB refilled)│            │ miss
└─────────────┘  TLB    └──────────────────┘            ▼
      │                                          ┌────────────┐
      │ page fault                               │    RAM     │
      ▼                                          └────────────┘
┌─────────────┐
│  Evict a    │
│ resident pg │
│ free frame  │
└─────────────┘
      │ frame now free
      └──────────────▶ (retry translate, get physical address)
### Components

- **Replacement Policies** — LRU, FIFO, and Random implemented as interchangeable strategy objects, reused across cache eviction, TLB eviction, and page table eviction — the same abstract problem solved once and shared across all three components.
- **Set-Associative Structure** — generic N-way set-associative lookup engine; both the cache and TLB are instances of this with different parameters, not separate implementations.
- **Cache Simulator** — configurable size, block size, and associativity; splits addresses into tag/index/offset fields.
- **TLB Simulator** — caches recent virtual→physical page translations; structurally identical to the cache but operating on page numbers instead of byte addresses.
- **Page Table** — 2-level page table with a fixed physical frame pool; handles page faults and frame eviction transparently.
- **Memory System** — orchestrates the full pipeline: virtual address → TLB lookup → (on miss) page table walk + TLB refill → physical address → cache lookup.

---

## Key Design Decisions

**One generic structure for cache and TLB.** A cache and a TLB solve the same abstract problem — set-associative storage with a replacement policy. Both are instances of `SetAssociativeStructure` with different parameters. The same replacement policy classes also power page table eviction. This meant a bug in the replacement logic would surface across all three components simultaneously, making testing more thorough.

**Physically-indexed, physically-tagged cache.** Translation happens before cache lookup — virtual address → physical address → cache. This is the standard real-world design choice; it avoids aliasing bugs where two processes map different virtual addresses to the same physical location.

**Pluggable replacement policies via a factory function.** LRU, FIFO, and Random are swappable at construction time. This made the policy comparison experiment (Experiment 4) trivial to set up while guaranteeing a fair comparison — identical workload, only the policy changes.

---

## Configuration

Default system configuration used across all experiments:

| Parameter            | Value         |
|----------------------|---------------|
| Page size            | 4096 bytes    |
| Physical frames      | 16            |
| TLB entries          | 16 (4-way)    |
| Cache size           | 4096 bytes    |
| Cache block size     | 64 bytes      |
| Cache associativity  | 4-way         |
| Address width        | 32-bit virtual |

---

## Experiments & Findings

### Experiment 1 — Access Pattern vs Cache Hit Rate

| Pattern        | Cache Hit Rate | TLB Hit Rate | Page Fault Rate | AMAT        |
|----------------|---------------|--------------|-----------------|-------------|
| Sequential     | 93.70%        | 99.90%       | 0.10%           | 17.62 cycles|
| Strided (256B) | 0.00%         | 93.70%       | 6.30%           | 206.26 cycles|
| Random         | 6.60%         | 98.40%       | 1.60%           | 192.12 cycles|

Block size is 64 bytes, element size is 4 bytes — each loaded block holds 16 elements. Sequential access reuses all 16 (15/16 = 93.75% theoretical maximum hit rate). Strided access jumps 256 bytes per step — a completely fresh block every time, loading 64 bytes and using 4 of them before moving on. The result is an **11.7× difference in AMAT** (17.62 vs 206.26 cycles) between sequential and strided access on the same data volume.

---

### Experiment 2 — Matrix Traversal Order

| Traversal                     | Cache Hit Rate | AMAT          |
|-------------------------------|---------------|---------------|
| Row-major (cache-friendly)    | 93.75%        | 17.52 cycles  |
| Column-major (cache-unfriendly)| 0.00%        | 205.02 cycles |

64×64 integer matrix (16384 bytes), 4× larger than the 4096-byte cache. Same data, same number of accesses, zero algorithmic difference — purely loop order. Column-major traversal jumps one full row (64 × 4 = 256 bytes) per step, loading a new cache line on every single access. **An 11.7× AMAT difference from a one-line loop reorder.** This is why cache-aware programming matters in performance-critical code.

---

### Experiment 3 — Temporal Locality

| Workload                            | Cache Hit Rate | AMAT         |
|-------------------------------------|---------------|--------------|
| 10 iterations over 512-byte array   | 99.38%        | 6.27 cycles  |

512 bytes ÷ 64 bytes per block = 8 cold misses on the first pass. All 9 subsequent passes find everything resident (working set fits entirely in the 4096-byte cache). 8 misses out of 1280 total accesses = 99.375% hit rate — matching theoretical prediction exactly. At 6.27 cycles AMAT, this is the fastest result in the project and demonstrates that once a working set fits in cache, repeated access costs almost nothing.

---

### Experiment 4 — Replacement Policy Comparison

8192-byte working set (2× cache size), scanned 5 times — forces constant eviction.

| Policy | Cache Hit Rate | AMAT          |
|--------|---------------|---------------|
| LRU    | 93.75%        | 17.50 cycles  |
| FIFO   | 93.75%        | 17.50 cycles  |
| Random | 94.54%        | 15.92 cycles  |

**The counterintuitive result: LRU and FIFO perform identically, and Random outperforms both.**

For a sequential scan larger than cache, LRU is adversarial — it evicts the least recently used block, but in a forward sequential scan the oldest block is also the one you'll need first on the next pass. FIFO has the same problem for the same reason. Random occasionally preserves a block that happens to be useful on the next iteration, edging them both out. This is **LRU's sequential flooding problem** — a well-documented phenomenon that modern CPUs address with dedicated streaming prefetch modes. Finding it independently by running the experiment was the most interesting result of this project.

---

### Experiment 5 — TLB Pressure

| Working Set                  | TLB Hit Rate | Page Fault Rate | AMAT          |
|------------------------------|-------------|-----------------|---------------|
| 2 pages — 8192 bytes         | 99.96%      | 0.04%           | 105.49 cycles |
| 128 pages — 524288 bytes     | 12.00%      | 85.78%          | 211.08 cycles |

With only 2 distinct pages, the TLB (16 entries) caches both translations after the first two accesses and they stay resident forever. With 128 pages and random access, translations are constantly evicted before reuse — almost every access requires a full page table walk, and with only 16 physical frames for 128 pages, most walks also trigger a page fault. **AMAT reaches 211 cycles** — the highest in the project — because TLB pressure and cache pressure are independent bottlenecks that compound simultaneously. This is why OS memory managers, JVM garbage collectors, and database buffer pools work to keep working sets spatially compact: spreading across too many pages destroys TLB performance independently of cache behavior.

---

## Project Structure

cache-tlb-simulator/
├── src/
│   ├── replacement_policies.py       # LRU, FIFO, Random as strategy objects
│   ├── set_associative_structure.py  # Generic N-way set-associative engine
│   ├── cache.py                      # Cache simulator (address splitting)
│   ├── tlb.py                        # TLB simulator (VPN translation cache)
│   ├── page_table.py                 # Page table + page fault handling
│   ├── memory_system.py              # Full pipeline orchestration + AMAT
│   ├── trace_generator.py            # Access pattern trace generation
│   └── main.py                       # CLI entry point
├── tests/
│   ├── test_replacement_policies.py
│   ├── test_set_associative_structure.py
│   ├── test_cache.py
│   ├── test_tlb.py
│   ├── test_page_table.py
│   └── test_memory_system.py
├── traces/                           # Generated memory access trace files
├── experiments/
│   ├── run_experiments.py            # All 5 experiments with AMAT
│   ├── visualize.py                  # Matplotlib charts for all experiments
│   └── charts/                       # Generated PNG charts
└── README.md

---

## How to Run

**Generate traces:**
```bash
python3 -m src.trace_generator
```

**Run all experiments:**
```bash
python3 experiments/run_experiments.py
```

**Run tests:**
```bash
python3 -m tests.test_replacement_policies
python3 -m tests.test_set_associative_structure
python3 -m tests.test_cache
python3 -m tests.test_tlb
python3 -m tests.test_page_table
python3 -m tests.test_memory_system
```

**Generate charts:**
```bash
python3 experiments/visualize.py
```

**CLI — run any pattern or trace file with custom config:**
```bash
# built-in pattern with AMAT breakdown
python3 -m src.main --pattern sequential --amat

# custom cache size
python3 -m src.main --pattern matrix_col_major --cache-size 8192 --amat

# load a trace file
python3 -m src.main --trace traces/sequential.trace --amat

# see every individual access
python3 -m src.main --pattern random --verbose

# compare policies
python3 -m src.main --pattern sequential --cache-policy FIFO --amat
python3 -m src.main --pattern sequential --cache-policy RANDOM --amat
```

---

## What I Learned

- **A cache and a TLB are the same problem.** Realizing this early meant one generic engine powered both, and the same replacement policy code ran across cache, TLB, and page table eviction. Shared abstractions found bugs faster than isolated implementations would have.
- **LRU is not always optimal.** For working sets larger than cache with sequential access, LRU and FIFO perform identically — and Random can outperform both. The sequential flooding problem is real and measurable, not just theoretical.
- **TLB pressure and cache pressure are independent bottlenecks.** A program can have poor TLB performance and good cache performance, or vice versa. When both compound simultaneously, AMAT reaches its worst point in the project (211 cycles) — higher than any pure cache-miss workload alone.
- **AMAT makes findings concrete.** Hit rate percentages are useful but abstract. Translating them to cycles (17.5 vs 205 cycles) makes the cost of a bad access pattern immediately tangible — the kind of number you can reason about when writing performance-critical code.
- **Building beats reading.** Writing the address-splitting logic (tag/index/offset) forced a precision that reading about caches never did. Every concept that was fuzzy from textbooks became exact once I had to implement and test it against known expected outputs.


