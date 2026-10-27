#!/usr/bin/env python3
"""Storage benchmark at the engine's exact access pattern: whole routed experts.

Reads N randomly chosen (layer, expert) pairs -- merged_weight + qs, the two preads
load_expert_merged issues -- from their real offsets across all shards, buffered,
each followed by posix_fadvise(DONTNEED) like st.h, with `qd` reader threads.
Experts are sampled WITHOUT replacement across the whole 15 GB of experts, with a
different seed per row, so neither the guest page cache nor the Windows host's cache
of the WSL VHDX can serve a read that an earlier row already made warm.
(os.pread releases the GIL, so threads give real queue depth.)

usage: expert_iobench.py <model_dir> [--n 192] [--qd 1,2,4,8,16] [--out FILE]
"""
import argparse
import json
import os
import random
import statistics
import struct
import threading
import time
from pathlib import Path


def expert_index(snap):
    idx = {}
    for shard in sorted(Path(snap).glob("*.safetensors")):
        with open(shard, "rb") as f:
            n = struct.unpack("<Q", f.read(8))[0]
            hdr = json.loads(f.read(n))
        base = 8 + n
        for k, v in hdr.items():
            if ".mlp.experts." not in k:
                continue
            parts = k.split(".")
            layer, eid = int(parts[2]), int(parts[5])
            a, b = v["data_offsets"]
            idx.setdefault((layer, eid), []).append((str(shard), base + a, b - a))
    return idx


def run_row(idx, keys, qd):
    fds = {}
    lock = threading.Lock()
    lat = []
    it = iter(keys)

    def fd_of(path):
        with lock:
            if path not in fds:
                fds[path] = os.open(path, os.O_RDONLY)
            return fds[path]

    def worker():
        while True:
            with lock:
                k = next(it, None)
            if k is None:
                return
            t0 = time.perf_counter()
            for path, off, n in idx[k]:
                fd = fd_of(path)
                got = 0
                while got < n:
                    got += len(os.pread(fd, n - got, off + got))
                os.posix_fadvise(fd, off, n, os.POSIX_FADV_DONTNEED)
            dt = time.perf_counter() - t0
            with lock:
                lat.append(dt)

    t0 = time.perf_counter()
    th = [threading.Thread(target=worker) for _ in range(qd)]
    for t in th:
        t.start()
    for t in th:
        t.join()
    wall = time.perf_counter() - t0
    for fd in fds.values():
        os.close(fd)
    nbytes = sum(n for k in keys for _, _, n in idx[k])
    lat.sort()
    return {"qd": qd, "n": len(keys), "bytes": nbytes, "wall_s": wall,
            "gb_s": nbytes / wall / 1e9, "experts_per_s": len(keys) / wall,
            "lat_ms_p50": 1e3 * lat[len(lat) // 2], "lat_ms_p90": 1e3 * lat[int(len(lat) * 0.9)],
            "lat_ms_mean": 1e3 * statistics.fmean(lat)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snap")
    ap.add_argument("--n", type=int, default=192)
    ap.add_argument("--qd", default="1,2,4,8,16")
    ap.add_argument("--out")
    a = ap.parse_args()
    idx = expert_index(a.snap)
    pool = sorted(idx)
    random.Random(20261026).shuffle(pool)   # fixed: rows never share an expert
    rows, pos = [], 0
    for qd in [int(x) for x in a.qd.split(",")]:
        keys = pool[pos:pos + a.n]
        pos += a.n
        r = run_row(idx, keys, qd)
        rows.append(r)
        print(f"QD{qd:>2}: {r['gb_s']:.2f} GB/s  {r['experts_per_s']:.0f} experts/s  "
              f"latency p50 {r['lat_ms_p50']:.1f} ms  p90 {r['lat_ms_p90']:.1f} ms  "
              f"mean {r['lat_ms_mean']:.1f} ms", flush=True)
    if a.out:
        json.dump({"snap": a.snap, "expert_bytes": rows[0]["bytes"] // rows[0]["n"],
                   "rows": rows}, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
