from src.replacement_policies import make_policy


class SetAssociativeStructure:
    """
    Generic set-associative lookup structure.
    Used as the base for both the cache and the TLB.

    num_sets: how many sets the structure is divided into
    ways: associativity (how many entries per set)
    policy_name: 'LRU', 'FIFO', or 'RANDOM'
    """

    def __init__(self, num_sets, ways, policy_name="LRU"):
        self.num_sets = num_sets
        self.ways = ways
        self.policy_name = policy_name

        # each set holds: { tag -> data }, plus its own replacement policy instance
        self.sets = [dict() for _ in range(num_sets)]
        self.policies = [make_policy(policy_name) for _ in range(num_sets)]

        # stats
        self.hits = 0
        self.misses = 0

    def lookup(self, set_index, tag):
        """
        Returns (hit: bool, data or None).
        Updates replacement policy state on a hit.
        """
        current_set = self.sets[set_index]
        if tag in current_set:
            self.hits += 1
            self.policies[set_index].access(tag)
            return True, current_set[tag]
        else:
            self.misses += 1
            return False, None

    def insert(self, set_index, tag, data):
        """
        Inserts a new (tag, data) into the given set.
        Evicts something first if the set is full.
        Returns the evicted tag, or None if no eviction was needed.
        """
        current_set = self.sets[set_index]
        evicted_tag = None

        if len(current_set) >= self.ways and tag not in current_set:
            evicted_tag = self.policies[set_index].evict()
            del current_set[evicted_tag]

        current_set[tag] = data
        self.policies[set_index].access(tag)
        return evicted_tag

    def invalidate(self, set_index, tag):
        """Explicitly remove an entry (not via eviction) — useful later for coherence/flush scenarios."""
        current_set = self.sets[set_index]
        if tag in current_set:
            del current_set[tag]
            self.policies[set_index].remove(tag)

    def hit_rate(self):
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0