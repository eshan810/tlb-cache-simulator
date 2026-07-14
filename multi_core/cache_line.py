from multi_core.mesi import MESIState

class CacheLine:
    def __init__(self):
        self.state    = MESIState.INVALID
        self.tag      = None
        self.data     = None
        self.last_used = 0   # timestamp for LRU

    def is_valid(self):
        return self.state != MESIState.INVALID

    def __repr__(self):
        return (f"CacheLine(state={self.state.value}, "
                f"tag={self.tag}, data={self.data})")