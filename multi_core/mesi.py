from enum import Enum

class MESIState(Enum):
    MODIFIED  = 'M'  # dirty, exclusive owner
    EXCLUSIVE = 'E'  # clean, exclusive owner
    SHARED    = 'S'  # clean, multiple owners
    INVALID   = 'I'  # not present / stale

class BusTransaction(Enum):
    READ       = 'READ'       # want to read
    READ_EXCL  = 'READ_EXCL'  # want to write (exclusive)
    INVALIDATE = 'INVALIDATE' # force others to invalidate
    WRITEBACK  = 'WRITEBACK'  # dirty eviction