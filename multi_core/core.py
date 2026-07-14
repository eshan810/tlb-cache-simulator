from multi_core.mesi import MESIState

class Core:
    """
    Simulates a single CPU core with its private L1 cache,
    connected to a shared snooping bus.
    """

    def __init__(self, core_id, cache, bus, memory):
        self.core_id = core_id
        self.cache   = cache
        self.bus     = bus
        self.memory  = memory
        self.clock   = 0

    def _tick(self):
        self.clock += 1
        return self.clock

    # ── READ ────────────────────────────────────────────────
    def read(self, address):
        t = self._tick()
        line = self.cache.find_line(address)

        if line:
            # ── HIT (M / E / S) ────────────────────────────
            self.cache.hits += 1
            line.last_used   = t
            return line.data

        # ── MISS ────────────────────────────────────────────
        self.cache.misses += 1

        # Evict LRU if dirty
        victim = self.cache.get_lru_way(address)
        if victim.state == MESIState.MODIFIED:
            self.bus.writeback(victim.tag, victim.data)

        # Broadcast READ on bus
        found_in_other = self.bus.read(address, self.core_id)

        # Fetch from memory
        data = self.memory.get(address, 0)

        # Install: EXCLUSIVE if only us, SHARED if others had it
        state = MESIState.SHARED if found_in_other \
                else MESIState.EXCLUSIVE
        self.cache.install_line(address, data, state, t)
        return data

    # ── WRITE ───────────────────────────────────────────────
    def write(self, address, data):
        t = self._tick()
        line = self.cache.find_line(address)

        if line:
            if line.state == MESIState.MODIFIED:
                # HIT M — write directly
                self.cache.hits += 1
                line.data      = data
                line.last_used = t

            elif line.state == MESIState.EXCLUSIVE:
                # HIT E — silent upgrade to M
                self.cache.hits += 1
                line.state     = MESIState.MODIFIED
                line.data      = data
                line.last_used = t

            elif line.state == MESIState.SHARED:
                # HIT S — must invalidate other sharers
                self.cache.hits += 1
                self.bus.invalidate(address, self.core_id)
                line.state     = MESIState.MODIFIED
                line.data      = data
                line.last_used = t
        else:
            # MISS — evict, broadcast READ_EXCL, install as M
            self.cache.misses += 1
            victim = self.cache.get_lru_way(address)
            if victim.state == MESIState.MODIFIED:
                self.bus.writeback(victim.tag, victim.data)

            self.bus.read_exclusive(address, self.core_id)
            self.cache.install_line(
                address, data, MESIState.MODIFIED, t)
            self.memory[address] = data