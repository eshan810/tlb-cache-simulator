import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from multi_core.simulator import MultiCoreSimulator

OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), "charts", "multicore")
os.makedirs(OUTPUT_DIR, exist_ok=True)

ITERS = 1000

def get_results(exp_fn):
    sim_result = exp_fn()
    return sim_result

def build_traces_false_sharing():
    return [
        [('W', i * 4, v) for v in range(ITERS)]
        for i in range(4)
    ]

def build_traces_true_sharing():
    traces = []
    addr = 500
    for _ in range(4):
        trace = []
        for v in range(ITERS // 2):
            trace.extend([('R', addr, 0), ('W', addr, v)])
        traces.append(trace)
    return traces

def build_traces_private():
    return [
        [('W', i*10000 + (v%100), v) for v in range(ITERS)]
        for i in range(4)
    ]

def build_traces_producer_consumer():
    shared = 200
    return [[('W', shared, v) for v in range(ITERS)]] + \
           [[('R', shared, 0) for _ in range(ITERS)]] * 3

def build_traces_read_heavy():
    addrs = [100, 200, 300, 400]
    traces = []
    for i in range(4):
        trace = []
        for v in range(ITERS):
            addr = addrs[v % len(addrs)]
            if v % 10 == 0:
                trace.append(('W', addr, v))
            else:
                trace.append(('R', addr, 0))
        traces.append(trace)
    return traces

def run_sim(traces):
    sim = MultiCoreSimulator(num_cores=4)
    sim.run(traces)
    return sim.get_stats()

def chart_hit_rates(all_results):
    """Bar chart: hit rate per core per experiment."""
    experiments = list(all_results.keys())
    x = np.arange(4)
    width = 0.15
    colors = ['#2196F3','#4CAF50','#FF9800','#E91E63','#9C27B0']

    fig, ax = plt.subplots(figsize=(12, 6))
    for i, (exp, stats) in enumerate(all_results.items()):
        rates = [c['hit_rate'] for c in stats['cores']]
        ax.bar(x + i*width, rates, width,
               label=exp.replace('_', ' ').title(),
               color=colors[i], alpha=0.85)

    ax.set_xlabel('Core ID')
    ax.set_ylabel('Hit Rate (%)')
    ax.set_title('Cache Hit Rate per Core — All Experiments')
    ax.set_xticks(x + width*2)
    ax.set_xticklabels([f'Core {i}' for i in range(4)])
    ax.legend()
    ax.set_ylim(0, 105)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'hit_rates.png'), dpi=150)
    plt.close()
    print("Saved: hit_rates.png")

def chart_invalidations(all_results):
    """Bar chart: total invalidations per experiment."""
    experiments = list(all_results.keys())
    totals = [
        sum(c['invalidations'] for c in stats['cores'])
        for stats in all_results.values()
    ]
    colors = ['#F44336','#2196F3','#4CAF50','#FF9800','#9C27B0']

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(range(len(experiments)), totals,
                  color=colors, alpha=0.85)

    ax.set_xticks(range(len(experiments)))
    ax.set_xticklabels(
        [e.replace('_', ' ').title() for e in experiments],
        rotation=15, ha='right')
    ax.set_ylabel('Total Invalidations')
    ax.set_title('Cache Invalidations by Experiment')

    for bar, val in zip(bars, totals):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + 0.5,
                str(val), ha='center', va='bottom',
                fontweight='bold')

    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'invalidations.png'), dpi=150)
    plt.close()
    print("Saved: invalidations.png")

def chart_bus_transactions(all_results):
    """Grouped bar: bus transactions vs invalidations."""
    experiments = list(all_results.keys())
    transactions = [s['bus']['transactions'] for s in all_results.values()]
    invalidations = [s['bus']['invalidations'] for s in all_results.values()]
    writebacks    = [s['bus']['writebacks']    for s in all_results.values()]

    x = np.arange(len(experiments))
    w = 0.25

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x - w,   transactions, w, label='Transactions', color='#2196F3', alpha=0.85)
    ax.bar(x,       invalidations, w, label='Invalidations', color='#F44336', alpha=0.85)
    ax.bar(x + w,   writebacks,    w, label='Writebacks',    color='#FF9800', alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(
        [e.replace('_', ' ').title() for e in experiments],
        rotation=15, ha='right')
    ax.set_ylabel('Count')
    ax.set_title('Bus Activity by Experiment')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'bus_activity.png'), dpi=150)
    plt.close()
    print("Saved: bus_activity.png")

def chart_mesi_state_distribution(all_results):
    """
    Pie-style comparison of sharing patterns
    inferred from invalidation count.
    """
    experiments = list(all_results.keys())
    fig, axes = plt.subplots(1, len(experiments),
                              figsize=(15, 4))

    for ax, (exp, stats) in zip(axes, all_results.items()):
        inv   = sum(c['invalidations'] for c in stats['cores'])
        hits  = sum(c['hits']          for c in stats['cores'])
        miss  = sum(c['misses']        for c in stats['cores'])

        values = [hits, miss, inv]
        labels = ['Hits', 'Misses', 'Invalidations']
        colors = ['#4CAF50', '#F44336', '#FF9800']

        # Filter zeros
        filtered = [(v,l,c) for v,l,c
                    in zip(values, labels, colors) if v > 0]
        if filtered:
            v, l, c = zip(*filtered)
            ax.pie(v, labels=l, colors=c,
                   autopct='%1.0f%%', startangle=90)
        ax.set_title(exp.replace('_', '\n').title(),
                     fontsize=9)

    plt.suptitle('Cache Event Distribution per Experiment',
                 fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'distributions.png'),
                dpi=150)
    plt.close()
    print("Saved: distributions.png")


if __name__ == "__main__":
    print("Running all experiments for visualization...\n")

    all_results = {
        'false_sharing':     run_sim(build_traces_false_sharing()),
        'true_sharing':      run_sim(build_traces_true_sharing()),
        'private_data':      run_sim(build_traces_private()),
        'producer_consumer': run_sim(build_traces_producer_consumer()),
        'read_heavy':        run_sim(build_traces_read_heavy()),
    }

    print("\nGenerating charts...\n")
    chart_hit_rates(all_results)
    chart_invalidations(all_results)
    chart_bus_transactions(all_results)
    chart_mesi_state_distribution(all_results)

    print(f"\nAll charts saved to: {OUTPUT_DIR}")