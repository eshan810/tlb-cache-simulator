import random
import os


def generate_sequential(num_accesses, base_address=0x10000, stride=4):
    """
    Sequential access: each access is exactly `stride` bytes after the last.
    Best-case pattern for cache performance — maximum spatial locality.
    Real-world example: iterating through an array forward, element by element.
    """
    traces = []
    addr = base_address
    for _ in range(num_accesses):
        traces.append(("R", addr))
        addr += stride
    return traces


def generate_strided(num_accesses, base_address=0x10000, stride=256):
    """
    Strided access: jumps by a large stride each time, skipping most of
    each cache line. Worse cache performance than sequential since you
    load a full block but only use one element before moving far away.
    Real-world example: accessing every Nth element of an array,
    or traversing a 2D array in the wrong dimension (column-major in C).
    """
    traces = []
    addr = base_address
    for _ in range(num_accesses):
        traces.append(("R", addr))
        addr += stride
    return traces


def generate_random(num_accesses, base_address=0x10000, memory_range=0x10000):
    """
    Random access: no locality at all.
    Worst-case pattern — almost every access is a cache miss.
    Real-world example: hash table lookups, pointer chasing in linked lists.
    """
    traces = []
    for _ in range(num_accesses):
        offset = random.randint(0, memory_range - 1) & ~3  # align to 4 bytes
        traces.append(("R", base_address + offset))
    return traces


def generate_repeated_loop(num_iterations, array_size_bytes=512, base_address=0x10000, element_size=4):
    """
    Simulates a loop that repeatedly scans a small array.
    First pass: all misses. Subsequent passes: all hits (if array fits in cache).
    Real-world example: inner loop of matrix multiply or convolution
    that repeatedly reads the same row/column.
    This is the pattern that shows temporal locality most clearly.
    """
    traces = []
    num_elements = array_size_bytes // element_size
    for _ in range(num_iterations):
        for i in range(num_elements):
            traces.append(("R", base_address + i * element_size))
    return traces


def generate_matrix_row_major(rows, cols, base_address=0x10000, element_size=4):
    """
    Row-major traversal of a 2D matrix (how C stores arrays in memory).
    Cache-friendly: accesses consecutive memory locations.
    """
    traces = []
    for r in range(rows):
        for c in range(cols):
            addr = base_address + (r * cols + c) * element_size
            traces.append(("R", addr))
    return traces


def generate_matrix_col_major(rows, cols, base_address=0x10000, element_size=4):
    """
    Column-major traversal of the SAME matrix layout (still stored row-major in memory).
    Cache-unfriendly: jumps by `cols * element_size` bytes each step,
    loading a new cache line on nearly every access.
    Comparing this vs row-major is your key experiment.
    """
    traces = []
    for c in range(cols):
        for r in range(rows):
            addr = base_address + (r * cols + c) * element_size
            traces.append(("R", addr))
    return traces


def save_trace(traces, filename):
    """Save a trace list to a file in traces/ directory."""
    os.makedirs("traces", exist_ok=True)
    filepath = os.path.join("traces", filename)
    with open(filepath, "w") as f:
        for mode, addr in traces:
            f.write(f"{mode} {hex(addr)}\n")
    print(f"Saved {len(traces)} accesses to {filepath}")


def load_trace(filename):
    """
    Load a trace file back into a list of (mode, address) tuples.
    Accepts either a plain filename (looks in traces/ folder automatically)
    or a full/relative path (used as-is).
    """
    # if the path already exists as given, use it directly
    # otherwise fall back to looking inside traces/
    if os.path.exists(filename):
        filepath = filename
    else:
        filepath = os.path.join("traces", filename)

    with open(filepath, "r") as f:
        traces = []
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                mode = parts[0]
                addr = int(parts[1], 16)
                traces.append((mode, addr))
    return traces


if __name__ == "__main__":
    # Generate and save all trace files
    save_trace(generate_sequential(1000),         "sequential.trace")
    save_trace(generate_strided(1000),             "strided.trace")
    save_trace(generate_random(1000),              "random.trace")
    save_trace(generate_repeated_loop(10),         "repeated_loop.trace")
    save_trace(generate_matrix_row_major(32, 32),  "matrix_row_major.trace")
    save_trace(generate_matrix_col_major(32, 32),  "matrix_col_major.trace")

    print("\nAll traces generated successfully.")