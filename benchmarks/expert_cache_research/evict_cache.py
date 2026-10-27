#!/usr/bin/env python3
"""Evict a model's shards from the Linux page cache with posix_fadvise(DONTNEED).

No root needed: DONTNEED drops clean pages of a file the caller can open, the same
method c/tools/datapoint.py uses. Prints how many shard bytes were still resident
afterwards via bin/pagecache_resident (mincore; build from pagecache_resident.c), so a "cold" label is checked,
not assumed.

usage: evict_cache.py <model_dir> [--check]
"""
import glob
import os
import subprocess
import sys


def evict(model_dir):
    files = sorted(glob.glob(os.path.join(model_dir, "*.safetensors")))
    if not files:
        raise SystemExit(f"no *.safetensors under {model_dir}")
    for path in files:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)
    return files


HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "bin", "pagecache_resident")


def resident_bytes(files):
    """Page-cache-resident bytes over files (mincore helper), or None if not built."""
    if not os.access(CHECKER, os.X_OK):
        return None
    out = subprocess.run([CHECKER, *files], capture_output=True, text=True,
                         check=True).stdout.split()
    return int(out[0])


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    files = evict(sys.argv[1])
    res = resident_bytes(files)
    print(f"evicted {len(files)} shards; resident after eviction: "
          f"{'n/a (pagecache_resident not built)' if res is None else f'{res} bytes'}")
    return res


if __name__ == "__main__":
    main()
