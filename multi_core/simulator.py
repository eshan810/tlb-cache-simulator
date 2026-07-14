import threading
import itertools
from multi_core.cache     import MultiCoreCache
from multi_core.bus       import SharedBus
from multi_core.core      import Core

class MultiCoreSimulator:
    def __init__(self, num_cores=4, num_sets=16, associativity=4):
        self.num_cores = num_cores
        self.memory    = {}
        self.bus       = SharedBus(self.memory)

        self.cores = []
        for i in range(num_cores):
            cache = MultiCoreCache(i, num_sets, associativity)
            core  = Core(i, cache, self.bus, self.memory)
            self.bus.register(cache)
            self.cores.append(core)

    def run(self, traces, mode='interleaved'):
        """
        mode='interleaved' : round-robin across cores (recommended)
        mode='sequential'  : one core at a time (shows GIL problem)
        mode='threaded'    : actual Python threads (GIL-limited)
        """
        if mode == 'interleaved':
            self._run_interleaved(traces)
        elif mode == 'sequential':
            self._run_sequential(traces)
        elif mode == 'threaded':
            self._run_threaded(traces)

    def _run_interleaved(self, traces):
        """
        Round-robin: Core 0 does op 0, Core 1 does op 0,
        Core 2 does op 0, Core 3 does op 0,
        Core 0 does op 1, Core 1 does op 1 ...
        This simulates true concurrent interleaving.
        """
        # Pad shorter traces with None
        max_len = max(len(t) for t in traces)
        padded  = [
            t + [None] * (max_len - len(t))
            for t in traces
        ]

        for step in range(max_len):
            for core_idx, core in enumerate(self.cores):
                op = padded[core_idx][step]
                if op is None:
                    continue
                action, address, data = op
                if action == 'R':
                    core.read(address)
                elif action == 'W':
                    core.write(address, data)

    def _run_sequential(self, traces):
        """One core fully completes before next starts."""
        for core, trace in zip(self.cores, traces):
            for op, address, data in trace:
                if op == 'R':
                    core.read(address)
                elif op == 'W':
                    core.write(address, data)

    def _run_threaded(self, traces):
        """Actual Python threads — GIL limits true parallelism."""
        def run_core(core, trace):
            for op, address, data in trace:
                if op == 'R':
                    core.read(address)
                elif op == 'W':
                    core.write(address, data)

        threads = [
            threading.Thread(
                target=run_core,
                args=(self.cores[i], traces[i]))
            for i in range(self.num_cores)
        ]
        for t in threads: t.start()
        for t in threads: t.join()

    def reset(self):
        """Reset all cores and bus for re-use."""
        self.__init__(self.num_cores)

    def print_stats(self):
        sep = "=" * 50
        print(f"\n{sep}")
        print("  MULTI-CORE CACHE COHERENCE SIMULATION")
        print(f"{sep}\n")

        total_hits = total_misses = total_inv = 0

        for core in self.cores:
            c = core.cache
            total = c.hits + c.misses
            print(f"Core {core.core_id}:")
            print(f"  Hits          : {c.hits}")
            print(f"  Misses        : {c.misses}")
            print(f"  Hit Rate      : {c.hit_rate():.2f}%")
            print(f"  Invalidations : {c.invalidations}")
            print(f"  Evictions     : {c.evictions}")
            print()
            total_hits   += c.hits
            total_misses += c.misses
            total_inv    += c.invalidations

        total      = total_hits + total_misses
        overall_hr = (total_hits/total*100) if total else 0

        print(f"Bus Statistics:")
        print(f"  Total Transactions  : {self.bus.total_transactions}")
        print(f"  Total Invalidations : {self.bus.total_invalidations}")
        print(f"  Total Writebacks    : {self.bus.total_writebacks}")
        print(f"\nOverall Hit Rate    : {overall_hr:.2f}%")
        print(f"Total Invalidations : {total_inv}")
        print(f"{sep}\n")

    def get_stats(self):
        return {
            'cores': [
                {
                    'id':            c.cache.core_id,
                    'hits':          c.cache.hits,
                    'misses':        c.cache.misses,
                    'hit_rate':      c.cache.hit_rate(),
                    'invalidations': c.cache.invalidations,
                    'evictions':     c.cache.evictions,
                }
                for c in self.cores
            ],
            'bus': {
                'transactions':  self.bus.total_transactions,
                'invalidations': self.bus.total_invalidations,
                'writebacks':    self.bus.total_writebacks,
            }
        }