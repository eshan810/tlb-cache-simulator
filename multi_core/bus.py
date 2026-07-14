import threading
from multi_core.mesi import BusTransaction

class SharedBus:
    """
    Simulates a shared snooping bus.
    Only one transaction can happen at a time (bus lock).
    """

    def __init__(self, memory):
        self.memory   = memory        # shared dict {address: data}
        self.caches   = []            # registered caches (in order)
        self._lock    = threading.Lock()

        # Stats
        self.total_transactions  = 0
        self.total_invalidations = 0
        self.total_writebacks    = 0

    def register(self, cache):
        self.caches.append(cache)

    def _broadcast(self, transaction, address, requester_id):
        """
        Send transaction to all caches except requester.
        Returns True if any other cache had the line.
        """
        found = False
        for cache in self.caches:
            if cache.core_id == requester_id:
                continue
            if cache.snoop(transaction, address, self.memory):
                found = True
        return found

    # ── public API used by Core ─────────────────────────────

    def read(self, address, requester_id):
        with self._lock:
            self.total_transactions += 1
            return self._broadcast(
                BusTransaction.READ, address, requester_id)

    def read_exclusive(self, address, requester_id):
        with self._lock:
            self.total_transactions  += 1
            self.total_invalidations += 1
            return self._broadcast(
                BusTransaction.READ_EXCL, address, requester_id)

    def invalidate(self, address, requester_id):
        with self._lock:
            self.total_transactions  += 1
            self.total_invalidations += 1
            self._broadcast(
                BusTransaction.INVALIDATE, address, requester_id)

    def writeback(self, address, data):
        with self._lock:
            self.total_writebacks += 1
            self.memory[address]   = data