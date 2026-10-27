#!/usr/bin/env python3
"""Poor man's profiler without perf/gdb: sample every thread of a process from /proc.

Every 5 ms reads /proc/<pid>/task/<tid>/stat (state, utime) and .../syscall (the
syscall a thread is blocked in, or "running"). At exit prints, per thread, the
share of samples spent running user code, blocked in pread64 / fadvise / futex /
other syscalls, plus CPU seconds. Used here to find where the main (decode) thread
spends a cache miss: in the storage read, or elsewhere.

usage: thread_sampler.py --start-after-regex 'resident weights loaded' -- <cmd ...>
       (samples only after a log line matches, so model loading is excluded)
"""
import argparse
import collections
import os
import re
import subprocess
import sys
import threading
import time

SYSCALLS = {"17": "pread64", "221": "fadvise64", "202": "futex", "0": "read",
            "35": "nanosleep", "230": "clock_nanosleep", "24": "sched_yield",
            "9": "mmap", "11": "munmap", "28": "madvise", "1": "write"}


def sample(pid, counts, stop, gate):
    while not stop.is_set():
        if gate.is_set():
            try:
                tids = os.listdir(f"/proc/{pid}/task")
            except FileNotFoundError:
                return
            for tid in tids:
                try:
                    try:
                        with open(f"/proc/{pid}/task/{tid}/syscall") as f:
                            sc = f.read().split()
                    except PermissionError:   # thread exiting
                        continue
                    with open(f"/proc/{pid}/task/{tid}/stat") as f:
                        st = f.read().rsplit(")", 1)[1].split()
                except (FileNotFoundError, ProcessLookupError):
                    continue
                state = st[0]
                flt = int(st[7])  # minflt (field 10 of stat; index 7 after the comm)
                counts[tid].setdefault("_minflt_first", flt)
                counts[tid]["_minflt_last"] = flt
                if sc and sc[0] == "running":
                    what = "running"
                elif sc:
                    what = SYSCALLS.get(sc[0], f"sys{sc[0]}")
                else:
                    what = "?"
                counts[tid][what] += 1
                counts[tid]["_state_" + state] += 1
        time.sleep(0.005)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-after-regex", default=None)
    ap.add_argument("--log", default=None, help="write the command's output here")
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    counts = collections.defaultdict(collections.Counter)
    stop, gate = threading.Event(), threading.Event()
    if not a.start_after_regex:
        gate.set()
    t = threading.Thread(target=sample, args=(p.pid, counts, stop, gate), daemon=True)
    t.start()
    rx = re.compile(a.start_after_regex) if a.start_after_regex else None
    log = open(a.log, "w") if a.log else None
    for line in p.stdout:
        if log:
            log.write(line)
        if rx and rx.search(line):
            gate.set()
    p.wait()
    stop.set()
    t.join()
    main_tid = str(p.pid)
    print(f"{'thread':>8} {'samples':>8}  top states (share of samples)")
    for tid, c in sorted(counts.items(), key=lambda kv: (kv[0] != main_tid, -sum(v for k, v in kv[1].items() if not k.startswith('_')))):
        tot = sum(v for k, v in c.items() if not k.startswith("_"))
        if not tot:
            continue
        top = ", ".join(f"{k} {100*v/tot:.0f}%" for k, v in c.most_common() if not k.startswith("_") and v / tot >= 0.02)
        tag = " (main)" if tid == main_tid else ""
        flt = c.get("_minflt_last", 0) - c.get("_minflt_first", 0)
        print(f"{tid:>8} {tot:>8}  minflt {flt:>8}  {top}{tag}")
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
