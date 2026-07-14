import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from multi_core.simulator import MultiCoreSimulator

ITERS = 1000  # accesses per core per experiment

# ── Experiment 1: False Sharing ─────────────────────────────
def exp_false_sharing():
    """
    Cores write to DIFFERENT variables that sit on the
    SAME cache line (within 64 bytes of each other).
    They don't logically share data but keep invalidating
    each other — this is false sharing.
    Expected: HIGH invalidation rate.
    """
    print("=" * 50)
    print("Experiment 1: False Sharing")
    print("=" * 50)
    sim = MultiCoreSimulator(num_cores=4)

    # All addresses within 64 bytes → same cache line
    traces = [
        [('W', i * 4, v) for v in range(ITERS)]
        for i in range(4)
    ]
    sim.run(traces, mode='interleaved')
    sim.print_stats()
    return sim.get_stats()

# ── Experiment 2: True Sharing ──────────────────────────────
def exp_true_sharing():
    """
    All cores read and write the SAME address.
    Classic data race / shared counter scenario.
    Expected: HIGH invalidations, ping-pong between cores.
    """
    print("=" * 50)
    print("Experiment 2: True Sharing")
    print("=" * 50)
    sim = MultiCoreSimulator(num_cores=4)
    addr = 500

    traces = []
    for _ in range(4):
        trace = []
        for v in range(ITERS // 2):
            trace.append(('R', addr, 0))
            trace.append(('W', addr, v))
        traces.append(trace)

    sim.run(traces, mode='interleaved')
    sim.print_stats()
    return sim.get_stats()

# ── Experiment 3: Private Data ──────────────────────────────
def exp_private_data():
    """
    Each core accesses its own completely separate
    address space — no sharing at all.
    Expected: LOW invalidations, high hit rate after warmup.
    """
    print("=" * 50)
    print("Experiment 3: Private Data")
    print("=" * 50)
    sim = MultiCoreSimulator(num_cores=4)

    # Each core gets its own 10000-address region
    traces = [
        [('W', i * 10000 + (v % 100), v) for v in range(ITERS)]
        for i in range(4)
    ]
    sim.run(traces, mode='interleaved')
    sim.print_stats()
    return sim.get_stats()

# ── Experiment 4: Producer-Consumer ─────────────────────────
def exp_producer_consumer():
    """
    Core 0 writes every 10 steps (producer).
    Cores 1-3 read every step (consumers).
    Consumers can cache between producer writes.
    """
    print("=" * 50)
    print("Experiment 4: Producer-Consumer")
    print("=" * 50)
    sim = MultiCoreSimulator(num_cores=4)
    shared = 200

    # Producer writes every 10th step, reads otherwise
    producer = []
    for v in range(ITERS):
        if v % 10 == 0:
            producer.append(('W', shared, v))
        else:
            producer.append(('R', shared, 0))

    consumer = [('R', shared, 0) for _ in range(ITERS)]
    traces   = [producer] + [consumer] * 3

    sim.run(traces, mode='interleaved')
    sim.print_stats()
    return sim.get_stats()

# ── Experiment 5: Read-Heavy Sharing ────────────────────────
def exp_read_heavy():
    """
    All cores mostly READ the same addresses with
    occasional writes. Tests SHARED state behaviour.
    Expected: High hit rate, low invalidations
              (most time in SHARED state).
    """
    print("=" * 50)
    print("Experiment 5: Read-Heavy Shared Access")
    print("=" * 50)
    sim = MultiCoreSimulator(num_cores=4)
    addrs = [100, 200, 300, 400]

    traces = []
    for i in range(4):
        trace = []
        for v in range(ITERS):
            addr = addrs[v % len(addrs)]
            if v % 10 == 0:          # 10% writes
                trace.append(('W', addr, v))
            else:                     # 90% reads
                trace.append(('R', addr, 0))
        traces.append(trace)

    sim.run(traces, mode='interleaved')
    sim.print_stats()
    return sim.get_stats()


if __name__ == "__main__":
    results = {}
    results['false_sharing']     = exp_false_sharing()
    results['true_sharing']      = exp_true_sharing()
    results['private_data']      = exp_private_data()
    results['producer_consumer'] = exp_producer_consumer()
    results['read_heavy']        = exp_read_heavy()

    print("\nAll experiments complete.")
    print("Run visualize_multicore.py to generate charts.")