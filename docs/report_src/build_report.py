#!/usr/bin/env python3
"""Build docs/colibri_optimization_results.pdf (for a technical reader new to colibri).

Every number in the report is read here from the result files under
benchmarks/expert_cache_research/ -- nothing is typed in by hand. Steps:
  1. read the comparisons, runs and Phase 0 logs;
  2. write docs/report_src/colibri_optimization_results.html (charts are inline SVG);
  3. print it to PDF with headless Chrome (Windows Chrome through WSL interop if no
     Linux browser is installed): docs/colibri_optimization_results.pdf.

usage: python3 docs/report_src/build_report.py [--html-only]
"""
import html
import json
import os
import re
import statistics as st
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
KIT = REPO / "benchmarks" / "expert_cache_research"
OUT_HTML = HERE / "colibri_optimization_results.html"
OUT_PDF = REPO / "docs" / "colibri_optimization_results.pdf"

CELLS = [("short", 32), ("medium", 32), ("long", 32), ("short", 12), ("medium", 12), ("long", 12)]
PLEN = {"short": 24, "medium": 161, "long": 514}


# ------------------------------------------------------------------ data readers
def rows(arm):
    return [json.loads(l) for l in open(KIT / arm / "runs.jsonl") if l.strip()]


def cell_rows(arm, prompt, cap):
    return [r for r in rows(arm) if r["prompt"] == prompt and r["cap"] == cap]


def compare(path):
    """compare.py markdown -> {(prompt, cap): {metric: dict(a, b, d, lo, hi, verdict)}}"""
    out, cell = {}, None
    for line in open(KIT / path):
        if line.startswith("## "):
            k = line[3:].strip().split("|")
            cell = (k[2], int(k[3][3:])); out[cell] = {}
        elif line.startswith("| ") and cell and "±" in line:
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if c[3] == "–": continue          # baseline mean 0 (e.g. VRAM): no % change
            m = re.match(r"\[([-+\d.]+), ([-+\d.]+)\]", c[4])
            out[cell][c[0]] = dict(a=float(c[1].split("±")[0]), b=float(c[2].split("±")[0]),
                                   d=float(c[3]), lo=float(m.group(1)) if m else None,
                                   hi=float(m.group(2)) if m else None, verdict=c[5])
    return out


def phase0():
    text = (KIT / "phase0" / "qd0.log").read_text(errors="replace")
    phases = {m.group(1): int(m.group(2)) for m in re.finditer(r"\[faultprof\] phase (\w+)\s+minflt\s+(\d+)", text)}
    steps = {}
    for m in re.finditer(r"\[faultprof\]   (.+?)\s{2,}(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", text):
        steps[m.group(1).strip()] = dict(calls=int(m.group(2)), us=float(m.group(3)), minflt=float(m.group(4)))
    total = int(re.search(r"Minor \(reclaiming a frame\) page faults: (\d+)", text).group(1))
    misses = int(re.search(r"hit=\d+ miss=(\d+)", text).group(1))
    host = []
    for line in open(KIT / "phase0" / "host_ws_samples.txt"):
        m = re.search(r"guest_rss_mb=(\d+) .*=(\d+) (\d+) (\d+)", line)
        if m: host.append(tuple(int(x) for x in m.groups()))
    return phases, steps, total, misses, host


def correctness():
    arms = ["ab2/flagoff", "ab2/v3waves", "ab2/qd8", "ab2/arena", "ab2/waves", "ab2/both",
            "chunk/c32", "chunk/c64", "chunk/c128", "chunk/c256", "chunk/call",
            "grouped/gwaves", "grouped/grouped", "order/first", "order/last", "order/token"]
    r = subprocess.run([sys.executable, str(KIT / "check_correctness.py"), str(KIT / "ab2/baseline")]
                       + [str(KIT / a) for a in arms], capture_output=True, text=True)
    fails = int(re.search(r"(\d+) failure\(s\)", r.stdout).group(1))
    fc = subprocess.run([sys.executable, str(KIT / "check_correctness.py"), str(KIT / "final_check/baseline"),
                         str(KIT / "final_check/v5flagoff"), str(KIT / "final_check/v5waves")],
                        capture_output=True, text=True)
    fails_final = int(re.search(r"(\d+) failure\(s\)", fc.stdout).group(1))
    n = sum(len(rows(a)) for a in arms)                       # modified builds compared to the original
    n_all = n + len(rows("ab2/baseline"))                       # every cold run, the original's included
    n_final = sum(len(rows(a)) for a in ("final_check/v5flagoff", "final_check/v5waves"))
    resident = [x["pagecache_resident_before_bytes"] for a in arms + ["ab2/baseline"] for x in rows(a)]
    return dict(fails=fails, runs=n, runs_all=n_all, fails_final=fails_final, runs_final=n_final,
                resident_nz=sum(1 for b in resident if b), resident_max_mb=max(resident) / 1e6)


# ------------------------------------------------------------------ formatting
def f(x, nd=None):
    if nd is not None: return f"{x:,.{nd}f}"
    if abs(x) >= 100: return f"{x:,.0f}"
    if abs(x) >= 10: return f"{x:.1f}"
    return f"{x:.2f}" if abs(x) < 1 else f"{x:.1f}"


def pct(c):
    d = round(c["d"])
    s = "0%" if d == 0 else f"{d:+d}%"
    if c["lo"] is None: return s
    sig = c["verdict"].startswith("sig")
    ci = f"[{c['lo']:+.0f}, {c['hi']:+.0f}]"
    if not sig: return f"{s} <span class=ns>n.s.</span>"
    return f"<b>{s}</b> <span class=ci>{ci}</span>" + (" <span class=worse>worse</span>" if "WORSE" in c["verdict"] else "")


def cell_name(p, cap):
    return f"{p} ({PLEN[p]} tok), cap {cap}"


# ------------------------------------------------------------------ charts (inline SVG)
BEFORE, AFTER = "#2a78d6", "#eb6834"   # dataviz reference palette, slots 1-2 (validated adjacent pair)


def bars(title, items, unit, before_label, after_label, fmt=lambda v: f(v)):
    """Horizontal paired bars, one shared linear axis from 0. items: [(label, before, after)]."""
    W, left, right, bar, gap, group_gap, top = 640, 150, 70, 11, 2, 12, 38
    vmax = max(max(b, a) for _, b, a in items)
    scale = (W - left - right) / vmax
    H = top + len(items) * (2 * bar + gap + group_gap) + 26
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{html.escape(title)}">',
         f'<text x="0" y="14" class="ct">{html.escape(title)}</text>',
         f'<rect x="{left}" y="22" width="10" height="10" rx="2" fill="{BEFORE}"/><text x="{left+14}" y="31" class="lg">{html.escape(before_label)}</text>',
         f'<rect x="{left+190}" y="22" width="10" height="10" rx="2" fill="{AFTER}"/><text x="{left+204}" y="31" class="lg">{html.escape(after_label)}</text>']
    # recessive grid: 4 ticks
    step = [1, 2, 2.5, 5, 10, 20, 25, 50, 100, 200, 250, 500][0]
    for s in [1, 2, 2.5, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000]:
        if vmax / s <= 5: step = s; break
    y0, y1 = top - 2, H - 22
    t = 0
    while t <= vmax * 1.0001:
        x = left + t * scale
        o.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y1}" class="grid"/>')
        o.append(f'<text x="{x:.1f}" y="{H-8}" class="tick" text-anchor="middle">{t:g}</text>')
        t += step
    o.append(f'<text x="{W-right+64}" y="{H-8}" class="tick" text-anchor="end">{html.escape(unit)}</text>')
    y = top
    for label, b, a in items:
        o.append(f'<text x="{left-8}" y="{y+bar+3}" class="lab" text-anchor="end">{html.escape(label)}</text>')
        for v, col, dy in ((b, BEFORE, 0), (a, AFTER, bar + gap)):
            w = max(v * scale, 1.5)
            r = min(4, w / 2)
            # 4px rounded data end, square at the baseline
            o.append(f'<path d="M{left},{y+dy} h{w-r:.1f} a{r},{r} 0 0 1 {r},{r} v{bar-2*r} a{r},{r} 0 0 1 -{r},{r} h-{w-r:.1f} z" fill="{col}"/>')
            o.append(f'<text x="{left+w+4:.1f}" y="{y+dy+bar-2}" class="val">{fmt(v)}</text>')
        y += 2 * bar + gap + group_gap
    o.append(f'<line x1="{left}" y1="{y0}" x2="{left}" y2="{y1}" class="axis"/>')
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ the report
def build():
    p1 = compare("comparison.md")                      # part 1: original vs MISS_QD=8
    wv = compare("ab2/comparison_waves.md")            # A = MISS_QD=8, B = + waves
    ar = compare("ab2/comparison_arena.md")
    gr = compare("grouped/comparison.md")
    phases, steps, total_flt, p0_miss, host = phase0()
    ok = correctness()
    io = json.load(open(KIT / "env" / "expert_iobench.json"))
    ebytes = io["expert_bytes"]
    gbs = {r["qd"]: r["gb_s"] for r in io["rows"]}
    io_gain = (gbs[4] / gbs[1], gbs[8] / gbs[1])
    vocab = json.load(open(Path(os.path.expanduser("~/colibri-models/qwen3-coder-30b")) / "config.json"))["vocab_size"]
    pages = ebytes // 4096
    exp_mib, exp_gib = ebytes / 2**20, 48 * 128 * ebytes / 2**30
    snap = Path(os.path.expanduser("~/colibri-models/qwen3-coder-30b"))
    file_gb = sum(x.stat().st_size for x in snap.glob("*.safetensors")) / 1e9
    rss = {cap: st.mean(r["peak_rss_gb"] for r in rows("ab2/qd8") if r["cap"] == cap) for cap in (32, 12)}
    t = subprocess.run([str(REPO / "c/tests/test_qwen36_cache_index")], capture_output=True, text=True)
    assert t.returncode == 0, t.stderr
    n_wave_cases = t.stdout.count("qwen36 prefill waves")
    dec_halfwidth = max((c["hi"] - c["lo"]) / 2 for c in [wv[x]["decode tok/s"] for x in CELLS])

    # exact miss counts and bytes (deterministic: identical across reps)
    def first(arm, p, c, k): return cell_rows(arm, p, c)[0][k]
    gb = {cell: (st.mean(r["proc_read_bytes"] for r in cell_rows("ab2/qd8", *cell)) / 1e9,
                 st.mean(r["proc_read_bytes"] for r in cell_rows("ab2/waves", *cell)) / 1e9) for cell in CELLS}
    # grouped: prefill expert compute seconds
    gcomp = {}
    for cell in [("medium", 32), ("long", 32), ("medium", 12), ("long", 12)]:
        gcomp[cell] = (st.mean(r["waves_compute_s"] for r in cell_rows("grouped/gwaves", *cell)),
                       st.mean(r["waves_compute_s"] for r in cell_rows("grouped/grouped", *cell)))
    # chunk sweep (514-token prompt)
    chunk = {}
    for a, label in (("c32", 32), ("c64", 64), ("c128", 128), ("c256", 256), ("call", 514)):
        for cap in (32, 12):
            rs = cell_rows(f"chunk/{a}", "long", cap)
            chunk[(label, cap)] = (st.mean(r["proc_read_bytes"] for r in rs) / 1e9, st.mean(r["ttft_s"] for r in rs))
    # wave order: decode misses
    dm = {cell: (first("order/token", *cell, "decode_misses"), first("order/first", *cell, "decode_misses"),
                 first("order/last", *cell, "decode_misses")) for cell in CELLS}
    # arena summary
    ar_timing = [ar[c][m] for c in CELLS for m in ("TTFT (s)", "end-to-end tok/s (engine)", "decode tok/s")]
    ar_ns = sum(1 for c in ar_timing if not c["verdict"].startswith("sig"))
    ar_flt = [ar[c]["minor page faults"]["d"] for c in CELLS]
    ar_rss = [ar[c]["peak RSS (GB)"]["d"] for c in CELLS]
    wv_dec = [wv[c]["decode tok/s"] for c in CELLS]
    wv_dec_ns = sum(1 for c in wv_dec if not c["verdict"].startswith("sig"))
    worst_dec = min(wv_dec, key=lambda c: c["d"])
    worst_dec_cell = [c for c in CELLS if wv[c]["decode tok/s"] is worst_dec][0]
    host_min = min(host, key=lambda h: h[3])
    canary = st.median(r["canary_ms_p50"] for a in ("ab2/qd8", "ab2/waves") for r in rows(a))
    host_free = st.median(r["host_free_mb"] for a in ("ab2/qd8", "ab2/waves") for r in rows(a) if r.get("host_free_mb"))
    L = ("long", 12); L32 = ("long", 32)
    tt = lambda d, c: d[c]["TTFT (s)"]
    e2e = lambda d, c: d[c]["end-to-end tok/s (engine)"]
    ttft_range = (min(tt(wv, c)["d"] for c in CELLS), max(tt(wv, c)["d"] for c in CELLS))
    gb_mlong = [100 * (b - a) / a for (p, _), (a, b) in gb.items() if p != "short"]
    p1_ttft = [tt(p1, c)["d"] for c in p1]; p1_e2e = [e2e(p1, c)["d"] for c in p1]
    ratio128 = {cap: chunk[(128, cap)][0] / chunk[(514, cap)][0] for cap in (32, 12)}
    save128 = {cap: 100 * (1 - chunk[(514, cap)][0] / chunk[(128, cap)][0]) for cap in (32, 12)}
    load_flt, pre_flt, dec_flt = phases.get("load", 0), phases.get("prefill", 0), phases.get("decode", 0)
    refill = steps["int4 repack"]; first_fill = steps["repack, 1st"]; sread = steps["scale pread"]; wread = steps["weight pread"]

    # charts
    c1 = bars("Parallel loading: time to first token (s), original vs. MISS_QD=8",
              [(cell_name(p, c), tt(p1, (p, c))["a"], tt(p1, (p, c))["b"]) for p, c in
               [("short", 32), ("medium", 32), ("short", 12), ("medium", 12)]],
              "seconds", "original (one miss at a time)", "8 misses at a time")
    c2 = bars("Waves: time to first token (s)",
              [(cell_name(*c), tt(wv, c)["a"], tt(wv, c)["b"]) for c in CELLS],
              "seconds", "token at a time (MISS_QD=8)", "waves (MISS_QD=8 + waves)")
    c3 = bars("Waves: expert bytes read from disk per run (GB)",
              [(cell_name(*c), gb[c][0], gb[c][1]) for c in CELLS],
              "GB", "token at a time (MISS_QD=8)", "waves (MISS_QD=8 + waves)")

    # tables
    t_p1 = "".join(f"<tr><td>{cell_name(*c)}</td><td>{f(tt(p1,c)['a'])} → {f(tt(p1,c)['b'])} s</td><td>{pct(tt(p1,c))}</td>"
                   f"<td>{f(e2e(p1,c)['a'])} → {f(e2e(p1,c)['b'])}</td><td>{pct(e2e(p1,c))}</td></tr>"
                   for c in [("short", 32), ("medium", 32), ("short", 12), ("medium", 12)])
    t_wv = "".join(
        f"<tr><td>{cell_name(*c)}</td><td>{f(tt(wv,c)['a'])} → {f(tt(wv,c)['b'])}</td><td>{pct(tt(wv,c))}</td>"
        f"<td>{f(gb[c][0])} → {f(gb[c][1])}</td><td>{first('ab2/qd8',*c,'misses'):,} → {first('ab2/waves',*c,'misses'):,}</td>"
        f"<td>{pct(e2e(wv,c))}</td><td>{pct(wv[c]['decode tok/s'])}</td></tr>" for c in CELLS)
    t_gr = "".join(f"<tr><td>{cell_name(*c)}</td><td>{gcomp[c][0]:.1f} → {gcomp[c][1]:.1f} s</td><td>{pct(tt(gr,c))}</td></tr>"
                   for c in gcomp)
    t_chunk = "".join(f"<tr><td>{n if n != 514 else 'whole prompt (514)'}</td><td>{chunk[(n,32)][0]:.1f}</td><td>{chunk[(n,32)][1]:.0f}</td>"
                      f"<td>{chunk[(n,12)][0]:.1f}</td><td>{chunk[(n,12)][1]:.0f}</td></tr>" for n in (32, 64, 128, 256, 514))

    css = """
@page { size: A4; margin: 15mm 16mm 15mm 16mm; }
:root { --ink:#1b1b1a; --muted:#5a5955; --rule:#d9d8d3; --soft:#f4f3ef; }
html { background:#fff; }
body { font-family: "Segoe UI", system-ui, -apple-system, Arial, sans-serif; font-size: 9.6pt; line-height: 1.42; color: var(--ink); margin:0; background:#fff; }
h1 { font-size: 17pt; margin: 0 0 2px; letter-spacing:-0.2px; }
.sub { color: var(--muted); margin: 0 0 10px; font-size: 9pt; }
h2 { font-size: 11.6pt; margin: 14px 0 4px; padding-top: 4px; border-top: 1px solid var(--rule); break-after: avoid; }
h3 { font-size: 10pt; margin: 9px 0 2px; break-after: avoid; }
p { margin: 4px 0 6px; } ul { margin: 3px 0 6px 0; padding-left: 16px; } li { margin: 1px 0; }
table { border-collapse: collapse; width: 100%; margin: 5px 0 8px; font-size: 8.6pt; break-inside: avoid; }
th, td { text-align: left; padding: 3px 5px; border-bottom: 1px solid var(--rule); vertical-align: top; }
td { white-space: nowrap; } td:first-child { white-space: normal; }
table.wide { font-size: 8.1pt; }
th { color: var(--muted); font-weight: 600; background: var(--soft); }
.summary { background: var(--soft); padding: 8px 10px; border-radius: 4px; }
.ci { color: var(--muted); } .ns { color: var(--muted); font-style: italic; } .worse { color: #9a3412; font-weight: 600; }
.note { color: var(--muted); font-size: 8.4pt; }
.term { font-weight: 600; }
figure { margin: 6px 0 10px; break-inside: avoid; }
figcaption { color: var(--muted); font-size: 8.2pt; margin-top: 2px; }
svg text { font-family: "Segoe UI", system-ui, Arial, sans-serif; fill: var(--ink); }
svg .ct { font-size: 12px; font-weight: 600; } svg .lg, svg .lab { font-size: 10.5px; fill: #3a3936; }
svg .val { font-size: 10px; fill: #3a3936; } svg .tick { font-size: 9.5px; fill: #6b6a65; }
svg .grid { stroke: #e7e6e1; stroke-width: 1; } svg .axis { stroke: #a9a8a2; stroke-width: 1; }
.estimate { border-left: 3px solid #eda100; padding: 4px 10px; background: #fdf8ec; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.pb { break-before: page; }
.keep { break-inside: avoid; }
"""
    H = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Colibri Expert Loading</title><style>{css}</style></head><body>
<h1>Faster expert loading in colibri</h1>
<p class="sub">Results report for Mr Shravan · Mostafa Elhadidy · 27 October 2026 · all figures generated from
<code>benchmarks/expert_cache_research/</code> by <code>docs/report_src/build_report.py</code></p>

<div class="summary"><b>Summary.</b> colibri runs large <span class="term">Mixture-of-Experts</span> (MoE) language models
on ordinary computers. Each layer of such a model has many small sub-networks ("experts"), of which only a few run for
each token. The experts do not fit in RAM, so colibri keeps a small cache of them and reads the rest from disk as they
are needed. We measured that on this machine <b>the time goes to loading experts from disk, not to computing with them</b>.
Two changes attack that loading:
<ul>
<li><b>Parallel loading</b> reads a layer's missing experts 8 at a time instead of one at a time.</li>
<li><b>"Waves"</b> process a prompt expert by expert instead of token by token, so each expert is read once instead of once per token.</li>
</ul>
Measured on the 514-token prompt, waves cut the <span class="term">time to first token</span> from {f(tt(wv,L)['a'])} s to
{f(tt(wv,L)['b'])} s ({tt(wv,L)['d']:+.0f}%) with a 12-expert cache, and from {f(tt(wv,L32)['a'])} s to {f(tt(wv,L32)['b'])} s with a
32-expert cache. Disk reads fall from {gb[L][0]:.0f} GB to {gb[L][1]:.0f} GB. Parallel loading had already made the first token
{-max(p1_ttft):.0f}–{-min(p1_ttft):.0f}% faster. The model's output is <b>bit-for-bit identical</b> to the original program in every one of
the {ok['runs'] + ok['runs_final']} runs of the modified program.</div>

<h2>1. Setup</h2>
<ul>
<li><b>Model:</b> Qwen3-Coder-30B-A3B: 48 layers × 128 experts, 8 experts per token per layer. Experts are 4-bit, {exp_mib:.2f} MiB each,
{exp_gib:.1f} GiB in total ({file_gb:.0f} GB on disk). It runs on colibri's <code>qwen36</code> engine.</li>
<li><b>Machine:</b> Intel i9-14900HX laptop, NVMe SSD, Windows 11 with WSL2 (a Linux virtual machine) limited to 12 GB of the
host's 16 GB RAM. The experts alone are {exp_gib:.1f} GiB, more than the VM can hold next to everything else, so they cannot all be in RAM. The GPU tier needs every expert
in RAM and is therefore unusable, so everything runs on the CPU.</li>
<li><b>Cache size ("cap"):</b> the number of experts kept in RAM per layer. We test <b>cap 32</b> (peak memory {rss[32]:.1f} GB) and <b>cap 12</b> ({rss[12]:.1f} GB,
simulating a small machine).</li>
<li><b>Why Qwen3-Coder stands in for GLM-5.3-Flash.</b> GLM-5.3-Flash, the real target, is a 321-billion-parameter MoE (195 GB)
that cannot run in 12 GB. Qwen3-Coder has the same structure (routed experts streamed from disk through a per-layer cache) and
fits, so the mechanisms can be measured here and then ported (§7).</li>
<li><b>How it was measured:</b> every run is <span class="term">cold</span>: a fresh process, with the operating system's file cache
emptied first, so every expert really comes from disk. The variants run back to back and alternate their order (A B B A), 3
repetitions each. A difference counts only if its 95% <span class="term">bootstrap confidence interval</span> (an interval
estimated by resampling the measured runs) excludes zero; otherwise it is marked <span class="ns">n.s.</span> (not
significant). The disk is a virtual disk on the laptop and is noisy: the per-run probe (median {canary:.1f} ms per
expert read) varied several-fold, which is why only back-to-back comparisons are used.</li>
</ul>

<h2>2. Parallel loading (MISS_QD=8)</h2>
<p><b>What it does.</b> When a layer needs experts that are not in the cache (<span class="term">cache misses</span>), the original
code read them one after another. Each read waits for the disk, and the disk was mostly idle: it delivers about {io_gain[0]:.1f}–{io_gain[1]:.1f}× more at 4–8
reads in flight than at one. The change first decides all of a layer's hits and misses in one pass (exactly the decisions the
original makes), then reads the misses 8 at a time.</p>
<p><b>Why it helps.</b> The waiting overlaps. Nothing about which experts run changes.</p>
<table><tr><th>prompt, cache</th><th>time to first token</th><th>change [95% CI]</th><th>tokens/s, end to end</th><th>change</th></tr>{t_p1}</table>
<figure>{c1}<figcaption>Mean of 3 cold runs per bar. The medium prompt is {PLEN['medium']} tokens and the short one {PLEN['short']}; the 514-token prompt was not part of this comparison.</figcaption></figure>

<h2>3. Waves: reading each expert once per prompt</h2>
<p><b>The problem.</b> A prompt of S tokens needs S × 8 experts per layer. That is far more than the cache holds, so the original
falls back to processing <i>one token at a time</i>. Every token re-reads experts the previous tokens evicted, even though a layer
only has 128 distinct experts. The 514-token prompt read {first('ab2/qd8','long',12,'misses'):,} experts ({gb[L][0]:.0f} GB) before
its first output token at cap 12.</p>
<p><b>What it does.</b>
<ol style="margin:3px 0 6px; padding-left:18px">
<li>The router (the small network that picks each token's 8 experts) runs for every prompt token first.</li>
<li>The distinct experts are processed in "waves" no larger than the cache, starting with the ones already in RAM.</li>
<li>While a wave is in RAM, every token that needs those experts is computed.</li>
<li>Each token's 8 results are added in the original order with the original weights, so the output is bit-identical.</li>
</ol></p>
<table class=wide><tr><th>prompt, cache</th><th>first token, s</th><th>change [95% CI]</th><th>GB read</th><th>experts read</th><th>tokens/s, end to end</th><th>decode tokens/s</th></tr>{t_wv}</table>
<figure>{c2}</figure>
<figure>{c3}</figure>
<p class="note">Baseline here is MISS_QD=8 (§2), so these gains come on top of parallel loading. "Decode" is generating the 31
tokens after the first: it reads only a few experts per token and is unchanged within the noise in {wv_dec_ns} of 6 cells
({pct(worst_dec)} in the sixth, {cell_name(*worst_dec_cell)}; see §7).</p>
<p><b>Planning window.</b> How many tokens are planned into waves at once matters: a bigger window means fewer re-reads.
514-token prompt, mean of 2 cold runs:</p>
<table><tr><th>tokens planned at once</th><th>cap 32: GB read</th><th>first token, s</th><th>cap 12: GB read</th><th>first token, s</th></tr>{t_chunk}</table>

<h2>4. Phase 0: what the "page faults" were</h2>
<p>The first study counted ~{total_flt/1e6:.1f} million <span class="term">minor page faults</span> per short run, of the same order
as one fault per 4 KiB page of every expert loaded. A page fault is the operating system mapping a fresh 4 KiB page of memory the
first time a program touches it. That looked like a per-miss overhead. We timed every step of a miss and counted its faults. They are
<b>not per miss</b>:</p>
<ul>
<li>{load_flt/1e6:.2f} M happen while the model loads, before any token;</li>
<li>{pre_flt/1e6:.2f} M are the expert cache's memory being touched for the first time, i.e. 48 layers × 32 slots × {pages} pages per expert;</li>
<li>decode, which is all misses into reused memory, takes <b>{dec_flt:,}</b>.</li>
</ul>
<p>The real per-miss costs are:</p>
<ul>
<li>a <b>second disk read</b> for each expert's scale factors, which the file stores apart from its weights ({sread['us']/1e3:.1f} ms);</li>
<li>rewriting an evicted cache slot takes {refill['us']/1e3:.1f} ms, against {first_fill['us']/1e3:.2f} ms for fresh memory, with no fault at all.</li>
</ul>
<p>The cause of the second is outside the program. During a run the Windows host fell to {host_min[3]} MB of free RAM and
pushed the virtual machine down to {host_min[1]:,} MB of real memory while the program held {host_min[0]:,} MB. The least recently
used cache slot is exactly the memory the host has paged out, so rewriting it waits for the host. A huge-page memory arena
(<code>COLI_Q36_SLOT_ARENA</code>) removes the first-touch faults ({max(ar_flt):.0f}% to {min(ar_flt):.0f}%), but {ar_ns} of 18 timing
comparisons are not significant, so it stays off.</p>

<div class="keep"><h2>5. Grouped kernel: correct but not worth enabling</h2>
<p>With waves, each expert computes many tokens at once. The grouped kernel processes 4 tokens per pass over the expert's weights
(each weight block is loaded and unpacked once instead of four times). Each token's arithmetic keeps its exact order, so this
turned out <b>exact</b>, not approximate: identical output, maximum logit difference 0.</p>
<table><tr><th>prompt, cache</th><th>expert compute time in prefill</th><th>change in first-token time</th></tr>{t_gr}</table>
<p>It saves {100*(1-gcomp[('long',32)][1]/gcomp[('long',32)][0]):.0f}% of compute on the long prompt at cap 32. But compute is only
~{gcomp[('long',32)][0]:.0f} s of a {f(tt(gr,('long',32))['a'])} s first token, so the first token does not measurably change. The one
"worse" cell traces to disk time, which the kernel does not touch. It is worth re-testing on a machine where loading is fast.</p></div>

<h2>6. Correctness</h2>
<ul>
<li><b>Identical output.</b> In every run the program wrote its final scores over the whole vocabulary (the
<span class="term">logits</span>, {vocab:,} numbers) to a file. We compared their SHA-256 hash and the generated text against the
<b>frozen original program</b>.
{ok['runs']} runs of the modified program across all variants, prompt lengths and cache sizes: <b>{ok['fails']} differences</b>. After the final change
(last-use wave order made the default) {ok['runs_final']} more runs: <b>{ok['fails_final']} differences</b>.</li>
<li><b>Unit test.</b> {n_wave_cases} configurations of waves vs. token-at-a-time give bit-identical results, every (token, expert) pair is
computed exactly once, and no expert is read twice in a layer pass.</li>
<li><b>Same cache decisions.</b> The cache decisions are deterministic: hit and miss counts are identical across repetitions of
each variant.</li>
</ul>

<h2>7. What didn't help or isn't proven</h2>
<ul>
<li><b>Huge-page arena</b> (§4): fewer faults, no measurable speed-up, +{min(ar_rss):.0f}–{max(ar_rss):.0f}% memory.</li>
<li><b>Decode speed</b> is not proven to change: 3 repetitions cannot resolve it under this host's noise (decode confidence intervals up to ±{dec_halfwidth:.0f} percentage points wide).</li>
<li><b>Wave order.</b> In first-seen order, waves leave a slightly worse set of experts cached for decode at cap 32
(decode misses {dm[('medium',32)][1]:,} vs {dm[('medium',32)][0]:,} on the medium prompt). Ordering by last use makes them equal to the original in
all 6 cells (now the default), but its timing effect was mixed and is not claimed.</li>
<li><b>Imperfect cold start.</b> {ok['resident_nz']} of {ok['runs_all']} cold runs started with up to {ok['resident_max_mb']:.1f} MB (of {file_gb:.0f} GB) still cached
(the rule is exactly 0): at most ~{ok['resident_max_mb']*1e6/ebytes:.1f} experts' worth, which is negligible.</li>
<li><b>Not measured:</b> server (warm) mode, the predictive prefetch (PILOT) with waves, the GPU paths.</li>
</ul>

<h2>8. Can this apply to GLM-5.3-Flash?</h2>
<p><b>What <code>glm53.c</code> already does</b> (from reading the code): it reads a layer's missing experts in parallel, and its
prompt processing is already expert by expert, inside a <b>128-token window</b> (<code>GLM53_PREFILL_CHUNK</code>).</p>
<p><b>What would carry over:</b></p>
<ol style="margin:3px 0 6px; padding-left:18px">
<li><b>Cached experts first.</b> Today it walks a window's experts in first-seen order, so an expert already in RAM can be evicted
before its turn and read again.</li>
<li><b>A larger planning window.</b> 128 tokens means an expert used throughout a long prompt is re-read in every window.</li>
<li><b>A fixed-order sum.</b> glm53 adds expert results in processing order, so reordering would change the last bits of the output.
Keeping per-(token, expert) results and adding them in a fixed order keeps it exact, as done here.</li>
<li><b>Last-use order</b>, so generation starts with the right experts cached.</li>
</ol>
<div class="estimate keep"><b>Expected effect: an estimate from code analysis and the Qwen measurement, not a GLM measurement.</b>
On Qwen with waves, a 128-token window read {ratio128[32]:.1f}× (cap 32) and {ratio128[12]:.1f}× (cap 12) the bytes of whole-prompt
planning for the 514-token prompt. If GLM behaves alike, a larger window should cut its prefill expert reads by roughly
{save128[12]:.0f}–{save128[32]:.0f}% on prompts of ~500 tokens, more on longer prompts, and nothing on prompts under 128 tokens. Cached-first
mainly helps when windows or requests share experts. GLM-5.3 has different expert counts, sizes and routing, so these
numbers <b>must be measured on the cloud instance</b> before any claim.</div>

<h2>9. Next steps</h2>
<ol style="margin:3px 0 6px; padding-left:18px">
<li>Port cached-first waves, the fixed-order sum and a larger window to <code>glm53.c</code>; measure on the cloud instance with the
same cold, alternating protocol and the same bit-exactness check.</li>
<li>Re-measure decode on a host that is not short of memory (WSL limited to what the host can back), with ≥ 6 repetitions.</li>
<li>Merge or overlap the scale read with the weight read: one disk read per expert instead of two.</li>
<li>Then decide whether waves should be on by default (it is off, as the project's rules require).</li>
</ol>
<p class="note">Full reports: <code>docs/expert_cache_research.md</code> (part 1), <code>docs/expert_cache_research_2.md</code> (part 2),
<code>docs/STATUS.md</code>. Raw rows: <code>benchmarks/expert_cache_research/{{ab2,chunk,grouped,order,phase0,final_check}}/</code>.
Median host free RAM before runs: {host_free:.0f} MB.</p>
</body></html>"""
    OUT_HTML.write_text(H)
    return H


def to_pdf():
    chrome = None
    for c in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        p = subprocess.run(["bash", "-lc", f"command -v {c}"], capture_output=True, text=True).stdout.strip()
        if p: chrome = p; break
    if chrome:
        src, dst = OUT_HTML.as_uri(), str(OUT_PDF)
        prof = "/tmp/colibri_report_chrome"
    else:   # Windows Chrome through WSL interop: paths as Windows sees them
        chrome = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
        distro = os.environ.get("WSL_DISTRO_NAME", "Ubuntu")
        win = lambda p: "\\\\wsl.localhost\\" + distro + str(p).replace("/", "\\")
        src = "file:" + win(OUT_HTML).replace("\\", "/")
        dst = win(OUT_PDF)
        prof = subprocess.run(["cmd.exe", "/c", "echo %TEMP%"], capture_output=True, text=True,
                              cwd="/mnt/c").stdout.strip() + "\\colibri_report_chrome"
    subprocess.run([chrome, "--headless=new", "--disable-gpu", f"--user-data-dir={prof}", "--no-pdf-header-footer",
                    f"--print-to-pdf={dst}", src], check=True, capture_output=True, timeout=180)
    print("wrote", OUT_PDF)


if __name__ == "__main__":
    build()
    print("wrote", OUT_HTML)
    if "--html-only" not in sys.argv:
        to_pdf()
