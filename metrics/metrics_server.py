"""
metrics_server.py

Wraps BOTH single-core and multi-core cache simulators
in a Flask web server.

Endpoints:
  GET /health          — Kubernetes liveness probe
  GET /run/singlecore  — Run single-core experiments
  GET /run/multicore   — Run multi-core experiments
  GET /run/all         — Run everything
  GET /metrics         — Prometheus metrics
  GET /               — Info
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, Response
from prometheus_client import (
    Gauge, Counter, generate_latest, CONTENT_TYPE_LATEST
)

# Single-core imports — using actual function names from trace_generator.py
from src.trace_generator import (
    generate_sequential,
    generate_strided,
    generate_random,
    generate_repeated_loop,
    generate_matrix_row_major,
    generate_matrix_col_major,
)
from src.memory_system import MemorySystem

# Multi-core imports
from multi_core.simulator import MultiCoreSimulator

app = Flask(__name__)

# ── Prometheus Gauges ──────────────────────────────────────

# Single-core metrics
sc_amat_gauge = Gauge(
    'singlecore_amat_cycles',
    'Average Memory Access Time in cycles',
    ['experiment']
)
sc_cache_hit_rate_gauge = Gauge(
    'singlecore_cache_hit_rate_percent',
    'Cache hit rate percentage',
    ['experiment']
)
sc_tlb_hit_rate_gauge = Gauge(
    'singlecore_tlb_hit_rate_percent',
    'TLB hit rate percentage',
    ['experiment']
)
sc_page_fault_rate_gauge = Gauge(
    'singlecore_page_fault_rate',
    'Page fault rate',
    ['experiment']
)

# Multi-core metrics
mc_hit_rate_gauge = Gauge(
    'multicore_hit_rate_percent',
    'Per-core cache hit rate',
    ['experiment', 'core']
)
mc_invalidations_gauge = Gauge(
    'multicore_invalidations_total',
    'Per-core cache invalidations',
    ['experiment', 'core']
)
mc_bus_transactions_gauge = Gauge(
    'multicore_bus_transactions_total',
    'Total bus transactions',
    ['experiment']
)

runs_counter = Counter(
    'experiment_runs_total',
    'Total experiment runs',
    ['type']
)

# ── Single-core Config ─────────────────────────────────────
# These match MemorySystem.__init__ signature exactly:
# __init__(self, page_size_bytes, num_physical_frames,
#          tlb_entries, tlb_ways, tlb_policy,
#          cache_size_bytes, block_size_bytes, cache_ways, cache_policy,
#          page_replacement_policy="LRU")

def make_memory_system():
    """Create a fresh MemorySystem with standard config."""
    return MemorySystem(
        page_size_bytes=4096,
        num_physical_frames=64,
        tlb_entries=16,
        tlb_ways=4,
        tlb_policy="LRU",
        cache_size_bytes=4096,
        block_size_bytes=64,
        cache_ways=4,
        cache_policy="LRU",
        page_replacement_policy="LRU"
    )

# ── Single-core Experiments ────────────────────────────────
# Using exact function signatures from trace_generator.py

SINGLE_CORE_EXPERIMENTS = {
    'sequential': lambda: generate_sequential(1000),
    'strided':    lambda: generate_strided(1000),
    'random':     lambda: generate_random(1000),
    'repeated_loop': lambda: generate_repeated_loop(
        num_iterations=10, array_size_bytes=512),
    'matrix_row_major': lambda: generate_matrix_row_major(32, 32),
    'matrix_col_major': lambda: generate_matrix_col_major(32, 32),
}

def run_singlecore_experiments():
    """
    Runs all single-core experiments.
    Uses actual MemorySystem.access(), .stats(), and .amat() methods.
    """
    results = {}

    for exp_name, trace_fn in SINGLE_CORE_EXPERIMENTS.items():
        try:
            ms = make_memory_system()
            trace = trace_fn()

            # MemorySystem.access() takes (virtual_address, mode="R")
            # trace_generator returns list of ("R", address) tuples
            for mode, address in trace:
                ms.access(address, mode)

            # .stats() returns dict with keys:
            # tlb_hit_rate, page_fault_rate, cache_hit_rate
            stats = ms.stats()

            # .amat() returns float (cycles)
            amat_value = ms.amat()

            results[exp_name] = {
                'cache_hit_rate': round(stats['cache_hit_rate'] * 100, 2),
                'tlb_hit_rate':   round(stats['tlb_hit_rate'] * 100, 2),
                'page_fault_rate': round(stats['page_fault_rate'] * 100, 4),
                'amat_cycles':    round(amat_value, 3),
                'num_accesses':   len(trace),
            }

            # Update Prometheus gauges
            sc_amat_gauge.labels(
                experiment=exp_name
            ).set(amat_value)

            sc_cache_hit_rate_gauge.labels(
                experiment=exp_name
            ).set(stats['cache_hit_rate'] * 100)

            sc_tlb_hit_rate_gauge.labels(
                experiment=exp_name
            ).set(stats['tlb_hit_rate'] * 100)

            sc_page_fault_rate_gauge.labels(
                experiment=exp_name
            ).set(stats['page_fault_rate'])

            runs_counter.labels(type='singlecore').inc()

        except Exception as e:
            results[exp_name] = {'error': str(e)}

    return results

# ── Multi-core Traces ──────────────────────────────────────

ITERS = 1000

def build_multicore_traces():
    return {
        'false_sharing': [
            [('W', i * 4, v) for v in range(ITERS)]
            for i in range(4)
        ],
        'true_sharing': [
            [item
             for v in range(ITERS // 2)
             for item in [('R', 500, 0), ('W', 500, v)]]
            for _ in range(4)
        ],
        'private_data': [
            [('W', i * 10000 + (v % 100), v)
             for v in range(ITERS)]
            for i in range(4)
        ],
        'producer_consumer': (
            [[('W' if v % 10 == 0 else 'R', 200, v)
              for v in range(ITERS)]] +
            [[('R', 200, 0) for _ in range(ITERS)]] * 3
        ),
        'read_heavy': [
            [('W' if v % 10 == 0 else 'R',
              [100, 200, 300, 400][v % 4], v)
             for v in range(ITERS)]
            for _ in range(4)
        ],
    }

def run_multicore_experiments():
    """Runs all 5 multi-core coherence experiments."""
    results = {}
    all_traces = build_multicore_traces()

    for name, traces in all_traces.items():
        sim = MultiCoreSimulator(num_cores=4)
        sim.run(traces, mode='interleaved')
        stats = sim.get_stats()
        results[name] = stats

        # Update Prometheus
        for core_stats in stats['cores']:
            core_id = str(core_stats['id'])
            mc_hit_rate_gauge.labels(
                experiment=name,
                core=core_id
            ).set(core_stats['hit_rate'])

            mc_invalidations_gauge.labels(
                experiment=name,
                core=core_id
            ).set(core_stats['invalidations'])

        mc_bus_transactions_gauge.labels(
            experiment=name
        ).set(stats['bus']['transactions'])

        runs_counter.labels(type='multicore').inc()

    return results

# ── Routes ─────────────────────────────────────────────────

@app.route('/')
def index():
    return jsonify({
        'name': 'Cache Simulator — Single & Multi Core',
        'description': (
            'Cycle-accurate cache/TLB simulator with '
            'MESI coherence protocol'
        ),
        'endpoints': {
            '/health':         'Kubernetes liveness probe',
            '/run/singlecore': 'Single-core experiments (JSON)',
            '/run/multicore':  'Multi-core MESI experiments (JSON)',
            '/run/all':        'Both experiments (JSON)',
            '/metrics':        'Prometheus metrics endpoint'
        }
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time()
    }), 200

@app.route('/run/singlecore')
def run_sc():
    start = time.time()
    results = run_singlecore_experiments()
    return jsonify({
        'type': 'singlecore',
        'elapsed_seconds': round(time.time() - start, 3),
        'experiments': results
    })

@app.route('/run/multicore')
def run_mc():
    start = time.time()
    results = run_multicore_experiments()

    formatted = {}
    for name, stats in results.items():
        formatted[name] = {
            'overall_hit_rate': round(
                sum(c['hit_rate'] for c in stats['cores']) / 4, 2),
            'total_invalidations': sum(
                c['invalidations'] for c in stats['cores']),
            'bus_transactions': stats['bus']['transactions'],
            'cores': stats['cores']
        }

    return jsonify({
        'type': 'multicore',
        'elapsed_seconds': round(time.time() - start, 3),
        'experiments': formatted
    })

@app.route('/run/all')
def run_all():
    start = time.time()
    sc = run_singlecore_experiments()
    mc = run_multicore_experiments()

    mc_formatted = {}
    for name, stats in mc.items():
        mc_formatted[name] = {
            'overall_hit_rate': round(
                sum(c['hit_rate'] for c in stats['cores']) / 4, 2),
            'total_invalidations': sum(
                c['invalidations'] for c in stats['cores']),
            'bus_transactions': stats['bus']['transactions'],
        }

    return jsonify({
        'elapsed_seconds': round(time.time() - start, 3),
        'singlecore': sc,
        'multicore':  mc_formatted
    })

@app.route('/metrics')
def metrics():
    return Response(
        generate_latest(),
        mimetype=CONTENT_TYPE_LATEST
    )

# ── Entry Point ────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"\nCache Simulator Metrics Server")
    print(f"  http://localhost:{port}/")
    print(f"  http://localhost:{port}/health")
    print(f"  http://localhost:{port}/run/singlecore")
    print(f"  http://localhost:{port}/run/multicore")
    print(f"  http://localhost:{port}/run/all")
    print(f"  http://localhost:{port}/metrics\n")
    app.run(host='0.0.0.0', port=port, debug=False)