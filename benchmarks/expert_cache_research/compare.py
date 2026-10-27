#!/usr/bin/env python3
"""Before/after comparison of two arms' results.json -> comparison.md.

For every cell present in both arms: mean ± stdev of each arm, the % change of
B against A, and a bootstrap 95% confidence interval of that % change (10 000
resamples of the per-run values, fixed seed). A change whose interval spans zero
is reported as not significant -- it is not claimed as an improvement.

usage: compare.py <arm_A_dir> <arm_B_dir> [--out comparison.md] [--title TEXT]
"""
import argparse
import json
import random
import statistics
from pathlib import Path

# metric, label, direction (+1 higher is better, -1 lower is better, 0 neutral)
ROWS = [
    ("ttft_s", "TTFT (s)", -1),
    ("decode_tok_s", "decode tok/s", +1),
    ("engine_tok_s", "end-to-end tok/s (engine)", +1),
    ("hit_rate_pct", "expert hit rate (%)", +1),
    ("misses", "expert misses", -1),
    ("est_misses", "expert misses (from bytes read)", -1),
    ("fetch_ms_tok", "decode expert fetch (ms/token)", -1),
    ("expert_read_gb", "bytes read by engine (GB)", -1),
    ("load_ms_per_miss", "expert load latency (ms/miss)", -1),
    ("peak_rss_gb", "peak RSS (GB)", -1),
    ("gpu_mem_delta_mib", "peak VRAM above idle (MiB)", -1),
]


def boot_ci(a, b, n=10000, seed=1234):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        ma = statistics.fmean(rng.choice(a) for _ in a)
        mb = statistics.fmean(rng.choice(b) for _ in b)
        if ma:
            out.append(100.0 * (mb - ma) / ma)
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out)) - 1]


def fmt(s):
    return f"{s['mean']:.3g} ± {s['stdev']:.2g}" if s else "–"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--out", default=None)
    ap.add_argument("--title", default="Before/after comparison")
    args = ap.parse_args()
    A = json.load(open(Path(args.a) / "results.json"))
    B = json.load(open(Path(args.b) / "results.json"))
    na, nb = Path(args.a).name, Path(args.b).name
    lines = [f"# {args.title}", "",
             f"A = `{na}`, B = `{nb}`. Values are mean ± stdev over repetitions; Δ is (B − A) / A.",
             "95% CI: bootstrap over runs. **sig** = the interval excludes 0.", ""]
    for key in sorted(set(A["cells"]) & set(B["cells"])):
        ma, mb = A["cells"][key]["metrics"], B["cells"][key]["metrics"]
        lines += [f"## {key}", "", f"| metric | {na} | {nb} | Δ % | 95% CI | verdict |",
                  "|---|---|---|---|---|---|"]
        for metric, label, direction in ROWS:
            sa, sb = ma.get(metric), mb.get(metric)
            if not sa or not sb:
                continue
            if sa["mean"] == 0:
                lines.append(f"| {label} | {fmt(sa)} | {fmt(sb)} | – | – | – |")
                continue
            d = 100.0 * (sb["mean"] - sa["mean"]) / sa["mean"]
            lo, hi = boot_ci(sa["values"], sb["values"]) if sa["n"] > 1 and sb["n"] > 1 else (None, None)
            sig = lo is not None and (lo > 0 or hi < 0)
            if not sig:
                verdict = "n.s."
            elif direction == 0:
                verdict = "sig"
            else:
                verdict = "sig better" if (d > 0) == (direction > 0) else "sig WORSE"
            ci = f"[{lo:+.1f}, {hi:+.1f}]" if lo is not None else "–"
            lines.append(f"| {label} | {fmt(sa)} | {fmt(sb)} | {d:+.1f} | {ci} | {verdict} |")
        lines.append("")
    text = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(text)
        print("wrote", args.out)
    else:
        print(text)


if __name__ == "__main__":
    main()
