#!/usr/bin/env python3
"""Build docs/colibri_story.html: the whole expert-loading story in one page.

Every number is read from the result files under benchmarks/expert_cache_research/
(through build_report.py's readers) and embedded as JSON; the page draws its charts
from that. Open the file in any browser; it needs no server.

    python3 docs/report_src/build_story.py
"""
import json
import os
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_report as R   # noqa: E402

OUT = R.REPO / "docs" / "colibri_story.html"
CELLS, PLEN = R.CELLS, R.PLEN


def data():
    p1 = R.compare("comparison.md")
    wv = R.compare("ab2/comparison_waves.md")
    ar = R.compare("ab2/comparison_arena.md")
    gr = R.compare("grouped/comparison.md")
    phases, steps, total_flt, p0_miss, host = R.phase0()
    ok = R.correctness()
    base = json.load(open(R.KIT / "baseline" / "results.json"))["cells"]
    bm = lambda p, c: base[f"cold|cold-process|{p}|cap{c}|pilot0"]["metrics"]
    io = json.load(open(R.KIT / "env" / "expert_iobench.json"))
    first = lambda arm, p, c, k: R.cell_rows(arm, p, c)[0][k]
    gb = lambda arm, cell: st.mean(r["proc_read_bytes"] for r in R.cell_rows(arm, *cell)) / 1e9
    snap = Path(os.path.expanduser("~/colibri-models/qwen3-coder-30b"))
    D = {
        "model": dict(layers=48, experts=128, topk=8, expert_mib=io["expert_bytes"] / 2**20,
                      experts_gib=48 * 128 * io["expert_bytes"] / 2**30,
                      file_gb=sum(x.stat().st_size for x in snap.glob("*.safetensors")) / 1e9,
                      rss={c: max(r["peak_rss_gb"] for r in R.rows("ab2/qd8") if r["cap"] == c) for c in (32, 12)}),
        "baseline": {f"{p}|{c}": dict(ttft=bm(p, c)["ttft_s"]["mean"], share=100 * bm(p, c)["fetch_share"]["mean"],
                                      gb=bm(p, c)["expert_read_gb"]["mean"], misses=bm(p, c)["misses"]["mean"])
                     for p, c in CELLS},
        "io": [dict(qd=r["qd"], gbs=r["gb_s"], p50=r["lat_ms_p50"]) for r in io["rows"]],
        "p1": {f"{p}|{c}": dict(ttft=p1[(p, c)]["TTFT (s)"], e2e=p1[(p, c)]["end-to-end tok/s (engine)"])
               for p, c in [("short", 32), ("medium", 32), ("short", 12), ("medium", 12)]},
        "wv": {f"{p}|{c}": dict(ttft=wv[(p, c)]["TTFT (s)"], e2e=wv[(p, c)]["end-to-end tok/s (engine)"],
                                dec=wv[(p, c)]["decode tok/s"], gbA=gb("ab2/qd8", (p, c)), gbB=gb("ab2/waves", (p, c)),
                                mA=first("ab2/qd8", p, c, "misses"), mB=first("ab2/waves", p, c, "misses"))
               for p, c in CELLS},
        "arena": dict(ns=sum(1 for c in CELLS for m in ("TTFT (s)", "end-to-end tok/s (engine)", "decode tok/s")
                             if not ar[c][m]["verdict"].startswith("sig")),
                      flt=[ar[c]["minor page faults"]["d"] for c in CELLS],
                      rss=[ar[c]["peak RSS (GB)"]["d"] for c in CELLS]),
        "phase0": dict(load=phases.get("load", 0), prefill=phases.get("prefill", 0), decode=phases.get("decode", 0),
                       total=total_flt, refill_ms=steps["int4 repack"]["us"] / 1e3,
                       first_ms=steps["repack, 1st"]["us"] / 1e3, scale_ms=steps["scale pread"]["us"] / 1e3,
                       weight_ms=steps["weight pread"]["us"] / 1e3,
                       host=[dict(rss=h[0], ws=h[1], commit=h[2], free=h[3]) for h in host],
                       pages=io["expert_bytes"] // 4096),
        "chunk": {},
        "order": {f"{p}|{c}": [first("order/token", p, c, "decode_misses"), first("order/first", p, c, "decode_misses"),
                               first("order/last", p, c, "decode_misses")] for p, c in CELLS},
        "grouped": {f"{p}|{c}": dict(a=st.mean(r["waves_compute_s"] for r in R.cell_rows("grouped/gwaves", p, c)),
                                     b=st.mean(r["waves_compute_s"] for r in R.cell_rows("grouped/grouped", p, c)),
                                     ttft=gr[(p, c)]["TTFT (s)"])
                    for p, c in [("medium", 32), ("long", 32), ("medium", 12), ("long", 12)]},
        "ok": ok,
        "sha": R.cell_rows("final_check/baseline", "short", 32)[0]["logits_sha256"][:16],
        "plen": PLEN,
    }
    for a, n in (("c32", 32), ("c64", 64), ("c128", 128), ("c256", 256), ("call", 514)):
        for cap in (32, 12):
            rs = R.cell_rows(f"chunk/{a}", "long", cap)
            D["chunk"][f"{n}|{cap}"] = dict(gb=st.mean(r["proc_read_bytes"] for r in rs) / 1e9,
                                            ttft=st.mean(r["ttft_s"] for r in rs))
    return D


def page(D):
    W = D["wv"]; L, L32 = W["long|12"], W["long|32"]
    B = D["baseline"]; P0 = D["phase0"]; M = D["model"]; ok = D["ok"]
    f = R.f
    share = [v["share"] for v in B.values()]
    p1t = [v["ttft"]["d"] for v in D["p1"].values()]
    wvt = [v["ttft"]["d"] for v in W.values()]
    gbr = [100 * (1 - v["gbB"] / v["gbA"]) for k, v in W.items() if not k.startswith("short")]
    io = {r["qd"]: r["gbs"] for r in D["io"]}
    hmin = min(P0["host"], key=lambda h: h["free"])
    ch = D["chunk"]
    r128 = {c: ch[f"128|{c}"]["gb"] / ch[f"514|{c}"]["gb"] for c in (32, 12)}
    s128 = {c: 100 * (1 - ch[f"514|{c}"]["gb"] / ch[f"128|{c}"]["gb"]) for c in (32, 12)}
    g32 = D["grouped"]["long|32"]
    n_mod = ok["runs"] + ok["runs_final"]
    om = D["order"]["medium|32"]

    def ci(c):
        d = round(c["d"]); s = "0%" if d == 0 else f"{d:+d}%"
        if c["lo"] is None or not c["verdict"].startswith("sig"):
            return f'{s} <span class="ns">n.s.</span>'
        w = ' <span class="worse">worse</span>' if "WORSE" in c["verdict"] else ""
        return f'<b>{s}</b> <span class="ci">[{c["lo"]:+.0f}, {c["hi"]:+.0f}]</span>{w}'

    name = lambda k: f'{k.split("|")[0]} <span class="dim">({D["plen"][k.split("|")[0]]} tok)</span>, cap {k.split("|")[1]}'
    t_p1 = "".join(f'<tr><td>{name(k)}</td><td class="num">{f(v["ttft"]["a"])} → {f(v["ttft"]["b"])} s</td><td class="num">{ci(v["ttft"])}</td>'
                   f'<td class="num">{f(v["e2e"]["a"])} → {f(v["e2e"]["b"])}</td><td class="num">{ci(v["e2e"])}</td></tr>' for k, v in D["p1"].items())
    t_wv = "".join(f'<tr><td>{name(k)}</td><td class="num">{f(v["ttft"]["a"])} → {f(v["ttft"]["b"])} s</td><td class="num">{ci(v["ttft"])}</td>'
                   f'<td class="num">{f(v["gbA"])} → {f(v["gbB"])}</td><td class="num">{v["mA"]:,} → {v["mB"]:,}</td>'
                   f'<td class="num">{ci(v["e2e"])}</td><td class="num">{ci(v["dec"])}</td></tr>' for k, v in W.items())
    t_io = "".join(f'<tr><td class="num">{r["qd"]}</td><td class="num">{r["gbs"]:.2f}</td><td class="num">{r["p50"]:.1f}</td></tr>' for r in D["io"])
    t_ch = "".join(f'<tr><td>{n if n != 514 else "whole prompt"}</td><td class="num">{ch[f"{n}|32"]["gb"]:.1f}</td><td class="num">{ch[f"{n}|32"]["ttft"]:.0f}</td>'
                   f'<td class="num">{ch[f"{n}|12"]["gb"]:.1f}</td><td class="num">{ch[f"{n}|12"]["ttft"]:.0f}</td></tr>' for n in (32, 64, 128, 256, 514))
    t_or = "".join(f'<tr><td>{name(k)}</td><td class="num">{v[0]:,}</td><td class="num">{v[1]:,}</td><td class="num"><b>{v[2]:,}</b></td></tr>' for k, v in D["order"].items())
    t_gr = "".join(f'<tr><td>{name(k)}</td><td class="num">{v["a"]:.1f} → {v["b"]:.1f} s</td><td class="num">{ci(v["ttft"])}</td></tr>' for k, v in D["grouped"].items())
    t_host = "".join(f'<tr><td class="num">{h["rss"]:,}</td><td class="num">{h["ws"]:,}</td><td class="num">{h["commit"]:,}</td><td class="num">{h["free"]:,}</td></tr>' for h in P0["host"])

    js_data = json.dumps(dict(wv={k: dict(a=v["ttft"]["a"], b=v["ttft"]["b"], gbA=v["gbA"], gbB=v["gbB"], d=v["ttft"]["d"],
                                         lo=v["ttft"]["lo"], hi=v["ttft"]["hi"]) for k, v in W.items()},
                              p1={k: dict(a=v["ttft"]["a"], b=v["ttft"]["b"]) for k, v in D["p1"].items()},
                              plen=D["plen"]))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Colibri Expert Loading</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=IBM+Plex+Sans:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: one reading column (~68ch) with chapter numbers in a left rail on wide screens; figures run wider than the text.
   The numbering is real: the chapters are the order things happened. */
:root {{
  --bg: #f5f7f9;  --surface: #ffffff; --ink: #14202b; --muted: #556270; --rule: #d9e0e7;
  --before: #2a78d6; --after: #eb6834; --accent: #1f5fae; --good: #0f7a3d; --warn: #9a3412; --tint: #e9f0f8;
  --display: "Bricolage Grotesque", "Segoe UI", system-ui, sans-serif;
  --body: "IBM Plex Sans", "Segoe UI", system-ui, -apple-system, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "Cascadia Mono", Consolas, monospace;
  color-scheme: light;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #0e141a; --surface: #151d25; --ink: #e4ebf2; --muted: #9aa8b6; --rule: #283541;
  --before: #3987e5; --after: #d95926; --accent: #79aef0; --good: #4cc27c; --warn: #f0a07a; --tint: #172433; color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #0e141a; --surface: #151d25; --ink: #e4ebf2; --muted: #9aa8b6; --rule: #283541;
  --before: #3987e5; --after: #d95926; --accent: #79aef0; --good: #4cc27c; --warn: #f0a07a; --tint: #172433; color-scheme: dark; }}
* {{ box-sizing: border-box; }}
html {{ -webkit-text-size-adjust: 100%; }}
body {{ margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.62 var(--body);
       padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }}
.wrap {{ max-width: 1040px; margin: 0 auto; padding-block: 40px 72px; }}
h1, h2, h3 {{ font-family: var(--display); text-wrap: balance; line-height: 1.12; margin: 0; }}
h1 {{ font-size: clamp(2.3rem, 6vw, 4.1rem); font-weight: 800; letter-spacing: -0.02em; }}
h2 {{ font-size: clamp(1.45rem, 3vw, 1.9rem); font-weight: 800; letter-spacing: -0.01em; }}
h3 {{ font-size: 1.12rem; font-weight: 600; margin-top: 8px; }}
p {{ margin: 0; max-width: 68ch; }}
a {{ color: var(--accent); }}
a:focus-visible, button:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
code, .mono {{ font-family: var(--mono); font-size: 0.88em; }}
.eyebrow {{ font: 500 0.78rem/1 var(--mono); letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }}
.lede {{ font-size: 1.16rem; color: var(--ink); max-width: 62ch; }}
.dim {{ color: var(--muted); }}
.hero {{ display: grid; gap: 18px; padding-bottom: 36px; border-bottom: 1px solid var(--rule); }}
.hero h1 .from {{ color: var(--before); }} .hero h1 .to {{ color: var(--after); }}
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin-top: 6px; }}
.stat {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 8px; padding: 14px 16px; display: grid; gap: 4px; }}
.stat b {{ font: 800 1.6rem/1.1 var(--display); font-variant-numeric: tabular-nums; }}
.stat span {{ color: var(--muted); font-size: 0.9rem; }}
.chapter {{ display: grid; grid-template-columns: 74px minmax(0, 1fr); gap: 0 20px; padding-top: 44px; }}
.chapter > .no {{ font: 800 2.6rem/1 var(--display); color: var(--rule); text-align: right; padding-top: 2px; font-variant-numeric: tabular-nums; }}
.chapter > .body {{ display: grid; gap: 14px; min-width: 0; }}
@media (max-width: 720px) {{ .chapter {{ grid-template-columns: minmax(0, 1fr); }} .chapter > .no {{ text-align: left; font-size: 1.6rem; }} }}
.box {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 8px; padding: 16px 18px; display: grid; gap: 10px; min-width: 0; }}
.callout {{ background: var(--tint); border-radius: 8px; padding: 14px 18px; display: grid; gap: 8px; }}
.estimate {{ border: 1.5px dashed var(--warn); border-radius: 8px; padding: 14px 18px; display: grid; gap: 8px; }}
.estimate .tag {{ font: 600 0.75rem/1 var(--mono); letter-spacing: 0.1em; text-transform: uppercase; color: var(--warn); }}
ul, ol {{ margin: 0; padding-left: 1.25em; max-width: 66ch; display: grid; gap: 6px; }}
.tablewrap {{ overflow-x: auto; min-width: 0; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
th, td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--rule); vertical-align: top; }}
th {{ font: 600 0.74rem/1.3 var(--mono); letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); }}
td.num {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
.ci, .ns {{ color: var(--muted); }} .ns {{ font-style: italic; }} .worse {{ color: var(--warn); font-weight: 600; }}
.two {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart text {{ fill: var(--ink); font-family: var(--body); }}
.chart .tick {{ fill: var(--muted); font-size: 11px; }} .chart .grid {{ stroke: var(--rule); }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: 0.86rem; color: var(--muted); }}
.legend i {{ display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }}
#tip {{ position: fixed; pointer-events: none; background: var(--ink); color: var(--bg); font: 500 0.82rem/1.35 var(--body);
        padding: 6px 9px; border-radius: 6px; transform: translate(-50%, calc(-100% - 10px)); white-space: nowrap; z-index: 5; }}
.diagram {{ width: 100%; height: auto; display: block; }}
.diagram text {{ fill: var(--ink); font-family: var(--body); font-size: 13px; }}
.diagram .lane {{ fill: var(--surface); stroke: var(--rule); }}
.diagram .tok {{ fill: var(--before); }} .diagram .exp {{ fill: var(--after); }} .diagram .ln {{ stroke: var(--muted); }}
.diagram .lab {{ fill: var(--muted); font-size: 12px; }}
.timeline {{ display: grid; gap: 0; border-left: 2px solid var(--rule); margin-left: 6px; }}
.timeline > div {{ position: relative; padding: 0 0 14px 18px; }}
.timeline > div::before {{ content: ""; position: absolute; left: -7px; top: 7px; width: 12px; height: 12px; border-radius: 50%; background: var(--surface); border: 2px solid var(--accent); }}
footer {{ margin-top: 56px; padding-top: 18px; border-top: 1px solid var(--rule); color: var(--muted); font-size: 0.88rem; display: grid; gap: 6px; }}
@media (prefers-reduced-motion: no-preference) {{ .bar {{ transition: width .5s ease, x .5s ease; }} }}
</style>
</head>
<body>
<div class="wrap">

<header class="hero">
  <span class="eyebrow">colibri · qwen36 engine · Qwen3-Coder-30B-A3B · cold-cache benchmarks</span>
  <h1>From <span class="from">{f(L["ttft"]["a"])}</span> seconds to <span class="to">{f(L["ttft"]["b"])}</span></h1>
  <p class="lede">How we made colibri's Qwen engine answer a 514-token prompt {L["ttft"]["a"]/L["ttft"]["b"]:.0f}× sooner without changing a single
  output bit. This is the story from the first measurement to the last check, what changed inside the engine, and what it means for
  GLM-5.3-Flash.</p>
  <div class="stats">
    <div class="stat"><b>{f(L["ttft"]["a"])} → {f(L["ttft"]["b"])} s</b><span>time to first token, 514-token prompt, 12-expert cache ({L["ttft"]["d"]:+.0f}%)</span></div>
    <div class="stat"><b>{L["gbA"]:.0f} → {L["gbB"]:.0f} GB</b><span>expert bytes read from the SSD for the same prompt</span></div>
    <div class="stat"><b>{n_mod} / {n_mod}</b><span>runs with logits byte-identical to the original engine</span></div>
  </div>
</header>

<section class="chapter" id="setup"><div class="no">1</div><div class="body">
  <span class="eyebrow">The setting</span>
  <h2>A model bigger than the machine</h2>
  <p><a href="https://github.com/JustVugg/colibri">colibri</a> runs <b>Mixture-of-Experts</b> (MoE) models on ordinary computers.
  Each layer of an MoE model holds many small feed-forward networks, the <b>experts</b>. A small <b>router</b> picks a few of them
  for each token. Only those few run, so the model can be huge while each token stays cheap. colibri keeps a fixed number of experts
  per layer in RAM (the <b>cap</b>) and reads any other expert from the SSD the moment the router asks for it.</p>
  <div class="two">
    <div class="box"><h3>The model</h3><p class="dim">Qwen3-Coder-30B-A3B on colibri's <code>qwen36</code> engine:
    {M["layers"]} layers × {M["experts"]} experts, {M["topk"]} chosen per token. Each expert is {M["expert_mib"]:.2f} MiB of 4-bit weights,
    {M["experts_gib"]:.1f} GiB of experts in all ({M["file_gb"]:.0f} GB on disk).</p></div>
    <div class="box"><h3>The machine</h3><p class="dim">i9-14900HX laptop, NVMe SSD, Windows 11 with WSL2 limited to 12 GB of the 16 GB.
    The experts cannot all be in RAM, so we test cap 32 (peak {M["rss"][32]:.1f} GB) and cap 12 (peak {M["rss"][12]:.1f} GB,
    a small machine).</p></div>
  </div>
  <p>The real target is <b>GLM-5.3-Flash</b>, a 321-billion-parameter MoE whose container is 195 GB. It does not fit here.
  Qwen3-Coder has the same structure (routed experts streamed from disk through a per-layer cache) and does fit, so it is the
  stand-in where every idea is measured before it is ported.</p>
  <p class="dim">Every number on this page comes from <b>cold</b> runs: a fresh process, with the operating system's file cache emptied
  first, so each expert really comes from the SSD. Variants run back to back in alternating order (A B B A), 3 repetitions each. A
  change counts only when its <b>bootstrap 95% confidence interval</b> excludes zero; otherwise it is marked <span class="ns">n.s.</span></p>
</div></section>

<section class="chapter" id="baseline"><div class="no">2</div><div class="body">
  <span class="eyebrow">Measuring the original</span>
  <h2>The time goes to loading, not computing</h2>
  <p>We first measured the untouched engine on three prompts (24, 161 and 514 tokens) at both caps. Two things stood out.</p>
  <ul>
    <li><b>Generating a token is mostly waiting for experts.</b> Fetching experts took {min(share):.0f}–{max(share):.0f}% of every decode
    step. Each missing expert was read on its own, one after another, while the SSD sat mostly idle.</li>
    <li><b>Reading a prompt re-reads the same experts again and again.</b> A prompt of S tokens needs S × 8 experts per layer. When that
    is more than the cap, the engine falls back to processing <i>one token at a time</i>, and each token evicts experts that later tokens
    need again. The 514-token prompt read {B["long|12"]["misses"]:,.0f} experts ({B["long|12"]["gb"]:.0f} GB) at cap 12, for a model that has
    only {M["layers"] * M["experts"]:,} experts in total. Its first token took {B["long|12"]["ttft"]:.0f} s.</li>
  </ul>
  <div class="box"><h3>The SSD was not the limit, the queue was</h3>
  <p class="dim">Reading random whole experts at different queue depths (reads in flight at once):</p>
  <div class="tablewrap"><table><tr><th>reads in flight</th><th>GB/s</th><th>median latency (ms)</th></tr>{t_io}</table></div>
  <p class="dim">Eight reads in flight deliver {io[8]/io[1]:.1f}× what one does.</p></div>
</div></section>

<section class="chapter" id="parallel"><div class="no">3</div><div class="body">
  <span class="eyebrow">First change · <code>COLI_Q36_MISS_QD=8</code></span>
  <h2>Read a layer's missing experts together</h2>
  <p>When a layer needs experts that are not cached, the engine now first makes every hit/miss decision in one pass, the exact
  decisions the original makes in the same order, and then reads the misses 8 at a time. Which experts run, and which get evicted,
  is unchanged. Only the waiting overlaps.</p>
  <div class="box">
    <div class="legend"><span><i style="background:var(--before)"></i>original, one read at a time</span><span><i style="background:var(--after)"></i>8 reads at a time</span></div>
    <svg class="chart" id="chart-p1" viewBox="0 0 760 250" role="img" aria-label="Time to first token, original vs parallel loading"></svg>
  </div>
  <div class="tablewrap"><table><tr><th>prompt, cap</th><th>first token</th><th>change [95% CI]</th><th>tokens/s, end to end</th><th>change</th></tr>{t_p1}</table></div>
</div></section>

<section class="chapter" id="faults"><div class="no">4</div><div class="body">
  <span class="eyebrow">An investigation · <code>COLI_Q36_FAULT_PROF=1</code></span>
  <h2>The page faults were a red herring</h2>
  <p>Each cache miss still cost about twice what the disk needs. The process took ~{P0["total"]/1e6:.1f} million <b>minor page faults</b> per short
  run (the operating system mapping a fresh 4 KiB page the first time it is touched), so faults looked like the culprit. We timed
  every step of a miss and counted its faults:</p>
  <div class="two">
    <div class="box"><h3>Where the faults are</h3>
      <div class="tablewrap"><table><tr><th>phase</th><th>minor faults</th></tr>
      <tr><td>model load</td><td class="num">{P0["load"]:,}</td></tr>
      <tr><td>prompt: first touch of the expert cache (48 × 32 slots × {P0["pages"]} pages)</td><td class="num">{P0["prefill"]:,}</td></tr>
      <tr><td>decode: every miss lands in reused memory</td><td class="num"><b>{P0["decode"]:,}</b></td></tr></table></div></div>
    <div class="box"><h3>Where a miss really spends time</h3>
      <ul><li>Weight read, 2.36 MB: {P0["weight_ms"]:.1f} ms</li>
      <li>A <b>second read</b> for the expert's scales, which the file stores apart from its weights: {P0["scale_ms"]:.1f} ms</li>
      <li>Rewriting an evicted cache slot: {P0["refill_ms"]:.1f} ms, against {P0["first_ms"]:.2f} ms for fresh memory, with no fault at all</li></ul></div>
  </div>
  <p>The slow rewrite comes from outside the program. We read the Windows host's view of the virtual machine during one run:</p>
  <div class="tablewrap"><table><tr><th>engine memory in the VM (MB)</th><th>VM memory the host keeps in RAM (MB)</th><th>VM commit (MB)</th><th>host free RAM (MB)</th></tr>{t_host}</table></div>
  <div class="callout"><p><b>What this means.</b> The host ran out of memory ({hmin["free"]} MB free) and paged most of the VM out, keeping
  {hmin["ws"]:,} MB of it in RAM while the engine held {hmin["rss"]:,} MB. The least recently used cache slot is exactly the memory the host
  had pushed out, so rewriting it waits for the host. The guest cannot see that wait. The fix is in the environment (give WSL less RAM
  than the host can back), not in the engine.</p></div>
  <p>A huge-page memory arena (<code>COLI_Q36_SLOT_ARENA=1</code>) removes the first-touch faults
  ({max(D["arena"]["flt"]):.0f}% to {min(D["arena"]["flt"]):.0f}%), but {D["arena"]["ns"]} of 18 timing comparisons were not significant.
  It stays off.</p>
</div></section>

<section class="chapter" id="waves"><div class="no">5</div><div class="body">
  <span class="eyebrow">Second change · <code>COLI_Q36_PREFILL_WAVES=1</code></span>
  <h2>Waves: read each expert once per prompt</h2>
  <p>The bigger loss was the prompt re-reading experts. Waves turn the loop inside out. Instead of walking token by token, the engine
  walks expert by expert:</p>
  <svg class="diagram" viewBox="0 0 760 236" role="img" aria-label="Token at a time versus waves">
    <rect class="lane" x="0" y="0" width="372" height="236" rx="8"/><rect class="lane" x="388" y="0" width="372" height="236" rx="8"/>
    <text x="16" y="26" font-weight="600">Token at a time (original)</text>
    <text x="404" y="26" font-weight="600">Waves</text>
    {''.join(f'<rect class="tok" x="{24+i*44}" y="52" width="30" height="18" rx="3"/>' for i in range(8))}
    {''.join(f'<rect class="exp" x="{24+i*44}" y="{108+(i%3)*30}" width="30" height="18" rx="3"/><line class="ln" x1="{39+i*44}" y1="70" x2="{39+i*44}" y2="{108+(i%3)*30}"/>' for i in range(8))}
    <text class="lab" x="16" y="204">each token loads its own experts, and the cache</text><text class="lab" x="16" y="221">evicts them before the next token needs them</text>
    {''.join(f'<rect class="tok" x="{412+i*40}" y="52" width="28" height="18" rx="3"/>' for i in range(8))}
    {''.join(f'<rect class="exp" x="{440+i*90}" y="140" width="40" height="22" rx="3"/>' for i in range(3))}
    {''.join(f'<line class="ln" x1="{426+i*40}" y1="70" x2="{460+(i%3)*90}" y2="140"/>' for i in range(8))}
    <text class="lab" x="404" y="204">route every token first, load each expert once,</text><text class="lab" x="404" y="221">and run all the tokens that use it</text>
  </svg>
  <ol>
    <li>The router runs for every token in the prompt first.</li>
    <li>The distinct experts are grouped into <b>waves</b> no larger than the cache. Experts already in RAM go first, so nothing cached is
    evicted before its turn.</li>
    <li>While a wave is in RAM, every token routed to those experts is computed. Each result lands in its own (token, expert) slot.</li>
    <li>At the end, each token adds up its 8 results <b>in the original order with the original weights</b>.</li>
  </ol>
  <div class="callout"><p><b>Why the output does not change by a single bit.</b> In colibri's expert kernel a token's result from one
  expert depends only on that token and that expert. Computing it in a different batch gives the same bits, and the final sum is the
  same statement in the same order as the original. So the model's output is identical, not merely close.</p></div>
  <div class="box">
    <div class="legend"><span><i style="background:var(--before)"></i>token at a time (with parallel loading)</span><span><i style="background:var(--after)"></i>with waves</span></div>
    <h3>Time to first token</h3>
    <svg class="chart" id="chart-wv-t" viewBox="0 0 760 300" role="img" aria-label="Time to first token, before and after waves, six prompt and cache combinations"></svg>
    <h3>Expert bytes read from the SSD</h3>
    <svg class="chart" id="chart-wv-gb" viewBox="0 0 760 300" role="img" aria-label="Gigabytes read, before and after waves, six prompt and cache combinations"></svg>
  </div>
  <div class="tablewrap"><table><tr><th>prompt, cap</th><th>first token</th><th>change [95% CI]</th><th>GB read</th><th>experts read</th><th>tokens/s end to end</th><th>decode tokens/s</th></tr>{t_wv}</table></div>
  <p class="dim">The baseline here already has parallel loading, so these gains stack on chapter 3. Reading the prompt now costs about one read per
  distinct expert per layer. Decode (generating the tokens after the first) reads only a few experts per token and is unchanged within the noise.</p>

  <h3>Three follow-up questions</h3>
  <div class="box"><p><b>How many tokens should be planned at once?</b> All of them. 514-token prompt, mean of 2 cold runs:</p>
  <div class="tablewrap"><table><tr><th>tokens planned at once</th><th>cap 32: GB read</th><th>first token (s)</th><th>cap 12: GB read</th><th>first token (s)</th></tr>{t_ch}</table></div></div>
  <div class="box"><p><b>Which experts should be left in RAM for generating the answer?</b> The ones the last prompt tokens used, the
  same ones the original leaves behind. Ordering waves by each expert's last use does exactly that, and it is now the default.
  Decode misses (counts are deterministic):</p>
  <div class="tablewrap"><table><tr><th>prompt, cap</th><th>original</th><th>waves, first-seen order</th><th>waves, last-use order</th></tr>{t_or}</table></div></div>
  <div class="box"><p><b>Can the compute part get faster too?</b> A grouped kernel (<code>COLI_Q36_PREFILL_GROUPED=1</code>) passes over an
  expert's weights once for 4 tokens. Each token keeps its exact arithmetic order, so it is exact as well. It cuts compute by
  {100*(1-g32["b"]/g32["a"]):.0f}% on the long prompt at cap 32, but compute is only {g32["a"]:.0f} s of a {f(g32["ttft"]["a"])} s first token here,
  so the first token does not measurably move:</p>
  <div class="tablewrap"><table><tr><th>prompt, cap</th><th>expert compute in prefill</th><th>first token change</th></tr>{t_gr}</table></div></div>
</div></section>

<section class="chapter" id="correct"><div class="no">6</div><div class="body">
  <span class="eyebrow">Proof</span>
  <h2>Same model, same answers</h2>
  <ul>
    <li>Every run wrote the model's final scores over the whole vocabulary (the <b>logits</b>) to a file. We compared their SHA-256 and the
    generated text with the <b>frozen original binary</b>: <b>{n_mod} runs of the modified engine, {ok["fails"] + ok["fails_final"]} differences</b>,
    across every variant, prompt and cache size, with every flag off and on. The short prompt at cap 32 gives <code>{D["sha"]}…</code> every time.</li>
    <li>Unit tests run real expert kernels on synthetic experts. They check that waves are bit-identical to token-at-a-time, that every
    (token, expert) pair is computed exactly once, and that no expert is read twice in a layer.</li>
    <li>Cache decisions are deterministic: hit and miss counts are identical across the repetitions of each variant.</li>
  </ul>
</div></section>

<section class="chapter" id="changes"><div class="no">7</div><div class="body">
  <span class="eyebrow">What changed in the engine</span>
  <h2>Everything sits behind a switch</h2>
  <p>All changes are environment flags that are off by default. With every flag off, the engine is the original, bit for bit.</p>
  <div class="tablewrap"><table>
    <tr><th>flag</th><th>what it does</th><th>verdict</th></tr>
    <tr><td><code>COLI_Q36_MISS_QD=8</code></td><td>read a layer's missing experts 8 at a time</td><td>use it</td></tr>
    <tr><td><code>COLI_Q36_PREFILL_WAVES=1</code></td><td>expert-major prompt processing, cached experts first, last-use order</td><td>use it</td></tr>
    <tr><td><code>COLI_Q36_PREFILL_WAVES_CHUNK=N</code></td><td>plan N tokens at once (0 = whole prompt)</td><td>keep 0</td></tr>
    <tr><td><code>COLI_Q36_PREFILL_GROUPED=1</code></td><td>exact 4-token kernel inside waves</td><td>no gain here</td></tr>
    <tr><td><code>COLI_Q36_SLOT_ARENA=1</code></td><td>expert cache in 2 MiB huge pages</td><td>no gain here</td></tr>
    <tr><td><code>COLI_Q36_FAULT_PROF=1</code></td><td>diagnostic: faults and time per step of a miss</td><td>diagnostics</td></tr>
  </table></div>
  <p class="dim">Code: <code>c/qwen36.c</code> (loading, waves, flags), <code>c/expert_ffn.h</code> (the fixed-order sum and the 4-token kernel),
  <code>c/tests/test_qwen36_cache_index.c</code> (tests).</p>
</div></section>

<section class="chapter" id="glm"><div class="no">8</div><div class="body">
  <span class="eyebrow">The real target</span>
  <h2>Will it help GLM-5.3-Flash?</h2>
  <p>We read GLM-5.3's engine (<code>c/glm53.c</code>) before writing any code, so the design could be ported. It already does part of the job:</p>
  <div class="two">
    <div class="box"><h3>Already there</h3><ul>
      <li>A layer's missing experts are read in parallel.</li>
      <li>Prompt processing is already expert by expert, but only inside a <b>128-token window</b> (<code>GLM53_PREFILL_CHUNK</code>).</li>
      <li>Experts are read straight into their cache slot, with no repacking.</li></ul></div>
    <div class="box"><h3>What would carry over</h3><ul>
      <li><b>Cached experts first.</b> Today a window's experts go in first-seen order, so an expert already in RAM can be evicted before its turn.</li>
      <li><b>A larger planning window.</b> 128 tokens means an expert used across a long prompt is re-read in every window.</li>
      <li><b>A fixed-order sum.</b> GLM-5.3 adds expert results in processing order, so reordering would shift the last bits; per-(token, expert) results summed in a fixed order keep it exact.</li>
      <li><b>Last-use order</b>, so the answer starts with the right experts cached.</li></ul></div>
  </div>
  <div class="estimate"><span class="tag">Estimate, not a measurement</span>
    <p>On Qwen with waves, planning 128 tokens at a time read {r128[32]:.1f}× (cap 32) and {r128[12]:.1f}× (cap 12) the bytes of planning the
    whole 514-token prompt. If GLM-5.3 behaves the same way, a larger window would cut its prompt-time expert reads by roughly
    {min(s128.values()):.0f}–{max(s128.values()):.0f}% on ~500-token prompts, more on longer ones, and not at all on prompts under 128 tokens.
    Cached-first ordering helps most when consecutive windows or requests share experts.</p>
    <p><b>This must be measured on the cloud instance.</b> GLM-5.3 has different expert counts and sizes, different routing and a different
    memory budget; none of these numbers transfer automatically.</p></div>
</div></section>

<section class="chapter" id="open"><div class="no">9</div><div class="body">
  <span class="eyebrow">Honest limits</span>
  <h2>What isn't proven yet</h2>
  <ul>
    <li><b>Decode speed.</b> Three repetitions cannot resolve it under this host's noise. One waves cell measured −28% (medium prompt, cap 32)
    with first-seen order. The last-use order that is now the default makes its decode cache identical to the original's
    ({om[1]:,} → {om[2]:,} misses), but its own timing test was mixed.</li>
    <li><b>The machine.</b> The host was short of memory in nearly every run, so absolute times drift between sessions. Only back-to-back
    comparisons are claimed.</li>
    <li><b>Not measured.</b> Server (warm) mode, colibri's predictive prefetch (PILOT) together with waves, and the GPU paths, which keep the original code.</li>
    <li><b>Cold start.</b> {ok["resident_nz"]} of {ok["runs_all"]} runs began with up to {ok["resident_max_mb"]:.1f} MB of the model still cached
    (the rule is exactly 0), about one expert's worth.</li>
  </ul>
  <h3>Next steps</h3>
  <div class="timeline">
    <div><b>Port to GLM-5.3:</b> cached-first waves, the fixed-order sum and a larger window in <code>glm53.c</code>, then measure on the cloud
    instance with the same cold, alternating protocol and the same bit-exact check.</div>
    <div><b>Re-measure decode</b> on a host with spare RAM, with 6 or more repetitions.</div>
    <div><b>One disk read per expert:</b> merge or overlap the scale read with the weight read.</div>
    <div><b>Decide on defaults:</b> whether waves should be on by default (today it is off, as the project's rules require).</div>
  </div>
</div></section>

<footer>
  <span>Built on <a href="https://github.com/JustVugg/colibri">colibri</a> by Vincenzo Fornaro (Apache-2.0). Work and measurements:
  Mostafa Elhadidy · <a href="https://github.com/MostafaaElhadidy/Colibri_Qwen_Optimization">github.com/MostafaaElhadidy/Colibri_Qwen_Optimization</a></span>
  <span>Generated by <code>docs/report_src/build_story.py</code> from <code>benchmarks/expert_cache_research/</code>. Full reports:
  <code>docs/expert_cache_research.md</code>, <code>docs/expert_cache_research_2.md</code>, <code>docs/colibri_optimization_results.pdf</code>.</span>
</footer>
</div>
<div id="tip" hidden></div>
<script>
const DATA = {js_data};
const tip = document.getElementById('tip');
function showTip(e, html) {{ tip.innerHTML = html; tip.hidden = false; tip.style.left = e.clientX + 'px'; tip.style.top = e.clientY + 'px'; }}
function hideTip() {{ tip.hidden = true; }}
const NS = 'http://www.w3.org/2000/svg';
function el(tag, attrs, parent) {{ const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; }}
const fmt = v => v >= 100 ? Math.round(v).toLocaleString() : v >= 10 ? v.toFixed(1) : v.toFixed(2);
function niceStep(max) {{ for (const s of [1,2,5,10,20,25,50,100,200,250,500,1000]) if (max / s <= 5) return s; return 1000; }}
/* paired horizontal bars on one shared linear scale from 0; hover shows the values */
function bars(svg, rows, unit, opts) {{
  svg.innerHTML = '';
  /* draw at the on-screen width so text stays at its real size on a phone */
  const W = Math.max(300, Math.round(svg.getBoundingClientRect().width) || 760);
  const narrow = W < 520, left = narrow ? Math.min(132, W * 0.42) : (opts.left || 170), right = narrow ? 58 : 70;
  const bar = 13, gap = 3, gg = 16, top = 8;
  const H = top + rows.length * (2 * bar + gap + gg) + 24;
  svg.setAttribute('viewBox', `0 0 ${{W}} ${{H}}`);
  const vmax = Math.max(...rows.flatMap(r => [r.a, r.b])), sc = (W - left - right) / vmax, step = niceStep(vmax);
  for (let t = 0; t <= vmax * 1.0001; t += step) {{
    const x = left + t * sc;
    el('line', {{x1: x, y1: top - 4, x2: x, y2: H - 20, class: 'grid'}}, svg);
    el('text', {{x, y: H - 6, class: 'tick', 'text-anchor': 'middle'}}, svg).textContent = t;
  }}
  el('text', {{x: W - 4, y: H - 6, class: 'tick', 'text-anchor': 'end'}}, svg).textContent = unit;
  let y = top;
  rows.forEach(r => {{
    el('text', {{x: left - 10, y: y + bar + 4, 'text-anchor': 'end', 'font-size': narrow ? 11.5 : 13}}, svg).textContent = narrow ? r.short : r.label;
    [[r.a, 'var(--before)', 0, r.la], [r.b, 'var(--after)', bar + gap, r.lb]].forEach(([v, col, dy, who]) => {{
      const w = Math.max(v * sc, 2), rr = Math.min(4, w / 2);
      const p = el('path', {{d: `M${{left}},${{y+dy}} h${{w-rr}} a${{rr}},${{rr}} 0 0 1 ${{rr}},${{rr}} v${{bar-2*rr}} a${{rr}},${{rr}} 0 0 1 -${{rr}},${{rr}} h-${{w-rr}} z`, fill: col}}, svg);
      el('text', {{x: left + w + 6, y: y + dy + bar - 2, 'font-size': 12}}, svg).textContent = fmt(v) + ' ' + unit;
      const hit = el('rect', {{x: left, y: y + dy - 1, width: W - left - right + 60, height: bar + 2, fill: 'transparent'}}, svg);
      hit.addEventListener('mousemove', e => showTip(e, `${{r.label}} · ${{who}}: <b>${{fmt(v)}} ${{unit}}</b>`));
      hit.addEventListener('mouseleave', hideTip);
    }});
    y += 2 * bar + gap + gg;
  }});
}}
const nm = k => {{ const [p, c] = k.split('|'); return `${{p}} (${{DATA.plen[p]}} tok), cap ${{c}}`; }};
const sn = k => {{ const [p, c] = k.split('|'); return `${{DATA.plen[p]}} tok, cap ${{c}}`; }};
bars(document.getElementById('chart-p1'), Object.entries(DATA.p1).map(([k, v]) => ({{label: nm(k), short: sn(k), a: v.a, b: v.b, la: 'original', lb: '8 at a time'}})), 's', {{left: 190}});
const wvRows = (fa, fb) => Object.entries(DATA.wv).map(([k, v]) => ({{label: nm(k), short: sn(k), a: v[fa], b: v[fb], la: 'token at a time', lb: 'waves'}}));
bars(document.getElementById('chart-wv-t'), wvRows('a', 'b'), 's', {{left: 190}});
bars(document.getElementById('chart-wv-gb'), wvRows('gbA', 'gbB'), 'GB', {{left: 190}});
function drawAll() {{
  bars(document.getElementById('chart-p1'), Object.entries(DATA.p1).map(([k, v]) => ({{label: nm(k), short: sn(k), a: v.a, b: v.b, la: 'original', lb: '8 at a time'}})), 's', {{left: 190}});
  bars(document.getElementById('chart-wv-t'), wvRows('a', 'b'), 's', {{left: 190}});
  bars(document.getElementById('chart-wv-gb'), wvRows('gbA', 'gbB'), 'GB', {{left: 190}});
}}
let rz; window.addEventListener('resize', () => {{ clearTimeout(rz); rz = setTimeout(drawAll, 120); }});
</script>
</body>
</html>
"""


if __name__ == "__main__":
    OUT.write_text(page(data()))
    print("wrote", OUT)
