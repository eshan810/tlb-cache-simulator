from collections import OrderedDict
import random


class LRUPolicy:
    """Least Recently Used — evicts the least recently accessed tag."""

    def __init__(self):
        self.order = OrderedDict()  # tag -> None, order = recency

    def access(self, tag):
        if tag in self.order:
            self.order.move_to_end(tag)
        else:
            self.order[tag] = None

    def evict(self):
        # popitem(last=False) removes the oldest (least recently used) item
        oldest_tag, _ = self.order.popitem(last=False)
        return oldest_tag

    def remove(self, tag):
        # called when a tag is explicitly invalidated, not via eviction
        if tag in self.order:
            del self.order[tag]


class FIFOPolicy:
    """First-In-First-Out — evicts whichever tag was inserted first."""

    def __init__(self):
        self.queue = []  # list acting as insertion-ordered queue

    def access(self, tag):
        if tag not in self.queue:
            self.queue.append(tag)
        # note: FIFO does NOT reorder on hits, only on insertion

    def evict(self):
        return self.queue.pop(0)

    def remove(self, tag):
        if tag in self.queue:
            self.queue.remove(tag)


class RandomPolicy:
    """Evicts a uniformly random tag from the current set."""

    def __init__(self):
        self.tags = []

    def access(self, tag):
        if tag not in self.tags:
            self.tags.append(tag)

    def evict(self):
        idx = random.randrange(len(self.tags))
        return self.tags.pop(idx)

    def remove(self, tag):
        if tag in self.tags:
            self.tags.remove(tag)


def make_policy(policy_name):
    """Factory so the rest of the code can just say make_policy('LRU')."""
    policies = {
        "LRU": LRUPolicy,
        "FIFO": FIFOPolicy,
        "RANDOM": RandomPolicy,
    }
    if policy_name not in policies:
        raise ValueError(f"Unknown policy: {policy_name}")
    return policies[policy_name]()