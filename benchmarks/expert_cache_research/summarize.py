#!/usr/bin/env python3
"""Aggregate one arm's runs.jsonl into results.json (raw rows + per-cell statistics).

A cell is (mode, kind, prompt, cap, pilot). Failed runs stay in the raw rows with
ok=false and are excluded from the statistics, and the exclusion is counted.

Derived per-run metrics:
  fetch_share           decode expert fetch / decode step time (COLI_TIMERS, cold mode)
  expert_read_gb        bytes the engine process read from storage (/proc/<pid>/io)
  load_ms_per_miss      warm mode: engine's expert load time (t_disk: pread + unpack,
                        summed over loader threads) / misses derived from bytes read

usage: summarize.py <arm_dir> [--profiling-extra FILE ...]
"""
import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

METRICS = [
    "ttft_s", "engine_tok_s", "decode_tok_s", "wall_s", "hit_rate_pct", "hits", "misses",
    "est_misses", "fetch_ms_tok", "compute_ms_tok", "step_ms_tok", "moe_ms_tok",
    "attn_ms_tok", "router_ms_tok", "fetch_share", "expert_read_gb", "disk_read_gb",
    "load_ms_per_miss", "peak_rss_gb", "ru_maxrss_gb", "gpu_mem_peak_mib",
    "gpu_mem_delta_mib", "prompt_tokens", "gen_tokens", "prefill_moe_ms",
]


def derive(r):
    if r.get("fetch_ms_tok") is not None and r.get("step_ms_tok"):
        r["fetch_share"] = r["fetch_ms_tok"] / r["step_ms_tok"]
    if r.get("proc_read_bytes") is not None:
        r["expert_read_gb"] = r["proc_read_bytes"] / 1e9
    if r.get("disk_read_bytes") is not None:
        r["disk_read_gb"] = r["disk_read_bytes"] / 1e9
    prof = r.get("prof")
    if prof and r.get("est_misses"):
        r["load_ms_per_miss"] = 1e3 * prof["expert_disk_s"] / r["est_misses"]
    if r.get("gpu_mem_peak_mib") is not None and r.get("gpu_mem_idle_mib") is not None:
        r["gpu_mem_delta_mib"] = r["gpu_mem_peak_mib"] - r["gpu_mem_idle_mib"]
    return r


def stats(values):
    v = [x for x in values if x is not None]
    if not v:
        return None
    return {"n": len(v), "mean": statistics.fmean(v),
            "stdev": statistics.stdev(v) if len(v) > 1 else 0.0,
            "min": min(v), "max": max(v), "values": v}


def cell_key(r):
    return f"{r['mode']}|{r['kind']}|{r['prompt']}|cap{r['cap']}|pilot{r['pilot']}"


def summarize(arm_dir):
    rows = [derive(json.loads(line)) for line in open(arm_dir / "runs.jsonl") if line.strip()]
    cells = defaultdict(list)
    for r in rows:
        cells[cell_key(r)].append(r)
    out = {}
    for key, rs in sorted(cells.items()):
        ok = [r for r in rs if r.get("ok")]
        out[key] = {
            "runs": len(rs), "excluded_failed": len(rs) - len(ok),
            "metrics": {m: s for m in METRICS if (s := stats([r.get(m) for r in ok]))},
            "output_hashes": sorted({r.get("logits_sha256") or r.get("text_sha256") or "" for r in ok}),
        }
    return rows, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arm_dir")
    ap.add_argument("--profiling-extra", nargs="*", default=[],
                    help="files appended to profiling.log (iobench, environment)")
    a = ap.parse_args()
    arm_dir = Path(a.arm_dir).resolve()
    rows, cells = summarize(arm_dir)
    inv = [json.loads(line) for line in open(arm_dir / "invocation.json") if line.strip()]
    json.dump({"invocations": inv, "cells": cells, "raw_runs": rows},
              open(arm_dir / "results.json", "w"), indent=1)

    # profiling.log: every run's timer block, plus the extra files, in one readable place
    with open(arm_dir / "profiling.log", "w") as f:
        f.write(f"# profiling log for arm {arm_dir.name}\n")
        for extra in a.profiling_extra:
            f.write(f"\n===== {extra} =====\n{Path(extra).read_text()}\n")
        for r in rows:
            f.write(f"\n===== {r['run_id']} ({r['arm']}) ok={r.get('ok')} =====\n")
            f.write(f"cmd: {r.get('cmd')}\nenv: {json.dumps(r.get('env'))}\n")
            if r.get("log"):
                text = (arm_dir.parent / r["log"]).read_text(errors="replace")
                keep = [ln for ln in text.splitlines()
                        if ln.startswith(("[timers]", "TTFT", "PEAK", "Expert cache", "Speed",
                                          "[enc]", "== qwen36", "[dense", "[HOT]", "[RESIDENT]"))]
                f.write("\n".join(keep) + "\n")
            if r.get("prof"):
                f.write(f"PROF {json.dumps(r['prof'])}\n")
            f.write(f"io: read_bytes={r.get('proc_read_bytes')} disk_read_bytes={r.get('disk_read_bytes')} "
                    f"est_misses={r.get('est_misses')} gpu_peak_mib={r.get('gpu_mem_peak_mib')}\n")

    # a compact console table
    print(f"{'cell':<44} {'n':>2} {'TTFT s':>14} {'decode tok/s':>14} {'hit %':>7} {'fetch%':>7} {'read GB':>8} {'RSS GB':>7}")
    for key, c in cells.items():
        m = c["metrics"]
        def f(name, scale=1.0, d=2):
            s = m.get(name)
            return f"{s['mean']*scale:.{d}f}±{s['stdev']*scale:.{d}f}" if s else "-"
        def g(name, scale=1.0, d=1):
            s = m.get(name)
            return f"{s['mean']*scale:.{d}f}" if s else "-"
        print(f"{key:<44} {c['runs']-c['excluded_failed']:>2} {f('ttft_s'):>14} {f('decode_tok_s'):>14} "
              f"{g('hit_rate_pct'):>7} {g('fetch_share', 100):>7} {g('expert_read_gb', 1, 2):>8} {g('peak_rss_gb', 1, 2):>7}")


if __name__ == "__main__":
    main()
