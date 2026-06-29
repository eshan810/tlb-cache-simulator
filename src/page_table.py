from src.replacement_policies import make_policy


class PageTable:
    """
    Simulates page-table-based address translation with a limited pool
    of physical frames, so page faults actually occur and need handling.

    num_physical_frames: how many physical frames exist (kept small on
        purpose so faults happen and your experiments show something).
    page_replacement_policy: which policy decides which resident page
        gets evicted when a new page needs a frame and none are free.
    """

    def __init__(self, num_physical_frames, page_replacement_policy="LRU"):
        self.num_physical_frames = num_physical_frames
        self.vpn_to_frame = {}       # virtual page number -> physical frame number
        self.frame_to_vpn = {}       # reverse mapping, needed on eviction
        self.free_frames = list(range(num_physical_frames))

        self.policy = make_policy(page_replacement_policy)

        self.page_faults = 0
        self.accesses = 0

    def translate(self, vpn):
        """
        Returns the physical frame for a given virtual page number.
        Handles page faults (assigning a free frame, or evicting a
        resident page if none are free) transparently.
        """
        self.accesses += 1

        if vpn in self.vpn_to_frame:
            # Page already resident — still counts as an "access" for LRU purposes.
            self.policy.access(vpn)
            return self.vpn_to_frame[vpn]

        # Page fault: this page isn't currently in any physical frame.
        self.page_faults += 1

        if self.free_frames:
            frame = self.free_frames.pop()
        else:
            # No free frames — evict a resident page to make room.
            evicted_vpn = self.policy.evict()
            frame = self.vpn_to_frame.pop(evicted_vpn)
            del self.frame_to_vpn[frame]

        self.vpn_to_frame[vpn] = frame
        self.frame_to_vpn[frame] = vpn
        self.policy.access(vpn)

        return frame

    def fault_rate(self):
        return self.page_faults / self.accesses if self.accesses > 0 else 0.0