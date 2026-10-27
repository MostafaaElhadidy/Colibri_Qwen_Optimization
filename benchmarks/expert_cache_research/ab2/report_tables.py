#!/usr/bin/env python3
"""Markdown tables for docs/expert_cache_research_2.md from compare.py outputs."""
import re, sys
from pathlib import Path
COLS = [("TTFT (s)", "TTFT A → B (s)"), ("end-to-end tok/s (engine)", "end-to-end tok/s"),
        ("decode tok/s", "decode tok/s"), ("bytes read by engine (GB)", "GB read"),
        ("expert misses", "misses"), ("minor page faults", "minor faults"), ("peak RSS (GB)", "peak RSS (GB)")]
ORDER = ["short|cap32", "medium|cap32", "long|cap32", "short|cap12", "medium|cap12", "long|cap12"]
NAME = {"short": "short (24)", "medium": "medium (161)", "long": "long (514)"}
def mean(x): return x.split("±")[0].strip()
def num(x):
    v = float(mean(x))
    if v >= 1e6: return f"{v/1e6:.2f} M"
    if v >= 1000: return f"{v:,.0f}"
    return f"{v:.3g}"
def load(f):
    cells, cell = {}, None
    for line in open(f):
        if line.startswith("## "):
            k = line[3:].strip().split("|"); cell = f"{k[2]}|{k[3]}"; cells[cell] = {}
        elif line.startswith("| ") and cell:
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            cells[cell][c[0]] = c
    return cells
for f in sys.argv[1:]:
    cells = load(f)
    print(f"\n<!-- {Path(f)} -->")
    print("| cell | " + " | ".join(h for _, h in COLS) + " |")
    print("|---|" + "---|" * len(COLS))
    for k in ORDER:
        if k not in cells: continue
        p, cap = k.split("|")
        out = []
        for key, _ in COLS:
            c = cells[k].get(key)
            if not c: out.append("–"); continue
            a, b, d, ci, v = num(c[1]), num(c[2]), c[3], c[4], c[5]
            star = "**" if v.startswith("sig") else ""
            tag = "" if v.startswith("sig") else " n.s."
            if v == "sig WORSE": tag = " (worse)"
            out.append(f"{a} → {b}, {star}{d}%{star} {ci}{tag}" if ci != "–" else f"{a} → {b}")
        print(f"| {NAME[p]}, {cap.replace('cap', 'cap ')} | " + " | ".join(out) + " |")
