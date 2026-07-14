import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import unittest
from multi_core.simulator import MultiCoreSimulator
from multi_core.mesi import MESIState

class TestMESIProtocol(unittest.TestCase):

    def _make_sim(self):
        return MultiCoreSimulator(num_cores=2,
                                  num_sets=4,
                                  associativity=2)

    def test_read_miss_gives_exclusive(self):
        """Single core read miss → EXCLUSIVE state."""
        sim = self._make_sim()
        sim.cores[0].read(100)
        line = sim.cores[0].cache.find_line(100)
        self.assertIsNotNone(line)
        self.assertEqual(line.state, MESIState.EXCLUSIVE)

    def test_shared_read(self):
        """Two cores read same address → both SHARED."""
        sim = self._make_sim()
        sim.memory[100] = 42
        sim.cores[0].read(100)
        sim.cores[1].read(100)
        line0 = sim.cores[0].cache.find_line(100)
        line1 = sim.cores[1].cache.find_line(100)
        self.assertEqual(line0.state, MESIState.SHARED)
        self.assertEqual(line1.state, MESIState.SHARED)

    def test_write_invalidates_other(self):
        """Core 0 writes → Core 1's copy becomes INVALID."""
        sim = self._make_sim()
        sim.memory[100] = 0
        sim.cores[0].read(100)
        sim.cores[1].read(100)
        sim.cores[0].write(100, 99)
        line1 = sim.cores[1].cache.find_line(100)
        # line1 should be None or INVALID after invalidation
        self.assertTrue(
            line1 is None or
            line1.state == MESIState.INVALID)

    def test_exclusive_upgrade_to_modified(self):
        """Core reads (EXCLUSIVE) then writes → MODIFIED."""
        sim = self._make_sim()
        sim.cores[0].read(200)
        sim.cores[0].write(200, 55)
        line = sim.cores[0].cache.find_line(200)
        self.assertEqual(line.state, MESIState.MODIFIED)
        self.assertEqual(line.data, 55)

    def test_false_sharing_causes_invalidations(self):
        """
        Two cores write to different addresses on same
        cache line → invalidations should be > 0.
        """
        sim = self._make_sim()
        # Addresses 0 and 4 are on same 64-byte cache line
        traces = [
            [('W', 0, v) for v in range(50)],
            [('W', 4, v) for v in range(50)],
        ]
        sim.run(traces)
        total_inv = sum(
            c.cache.invalidations for c in sim.cores)
        self.assertGreater(total_inv, 0)

    def test_private_data_no_invalidations(self):
        """
        Cores with private address spaces should have
        zero invalidations.
        """
        sim = self._make_sim()
        traces = [
            [('W', 0    + v % 10, v) for v in range(100)],
            [('W', 10000 + v % 10, v) for v in range(100)],
        ]
        sim.run(traces)
        total_inv = sum(
            c.cache.invalidations for c in sim.cores)
        self.assertEqual(total_inv, 0)


if __name__ == '__main__':
    unittest.main()