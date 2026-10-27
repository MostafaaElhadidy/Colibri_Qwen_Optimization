#!/usr/bin/env python3
"""Compact digest of compare.py outputs: one line per (arm, cell, metric) of interest."""
import re, sys
from pathlib import Path
WANT = ["TTFT (s)", "end-to-end tok/s (engine)", "decode tok/s", "bytes read by engine (GB)",
        "expert misses", "minor page faults", "peak RSS (GB)"]
for f in sys.argv[1:]:
    cell = None
    print(f"### {Path(f).stem}")
    for line in open(f):
        if line.startswith("## "):
            cell = line[3:].strip()
        elif line.startswith("| ") and cell:
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if c[0] in WANT:
                print(f"{cell:<34} {c[0]:<27} {c[1]:>16} -> {c[2]:>16}  {c[3]:>7}%  {c[4]:>16}  {c[5]}")
