#!/usr/bin/env python3
"""Build the project README.md and its animated SVGs (assets/optimization/).

Every number comes from the result files under benchmarks/expert_cache_research/,
through the same readers as build_report.py (the PDF). Re-run after new results:

    python3 docs/report_src/build_readme.py
"""
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_report as R   # noqa: E402

REPO = R.REPO
ASSETS = REPO / "assets" / "optimization"
CELLS, PLEN = R.CELLS, R.PLEN
UPSTREAM = "https://github.com/JustVugg/colibri"
ME = "https://github.com/MostafaaElhadidy/Colibri_Qwen_Optimization"
FONT = "Segoe UI, Helvetica Neue, Helvetica, Arial, sans-serif"


def pct(c, bold=True):
    d = round(c["d"]); s = "0%" if d == 0 else f"{d:+d}%"
    if c["lo"] is None or not c["verdict"].startswith("sig"):
        return f"{s} *(n.s.)*"
    ci = f"[{c['lo']:+.0f}, {c['hi']:+.0f}]"
    w = " ⚠️ worse" if "WORSE" in c["verdict"] else ""
    return (f"**{s}** {ci}" if bold else f"{s} {ci}") + w


def f(x): return R.f(x)


# ------------------------------------------------------------------ animated SVGs
def banner():
    W, H = 1280, 300
    blocks = []
    for i in range(10):   # experts streaming from the disk to RAM, staggered
        y = 196 + (i % 3) * 18
        blocks.append(f'<rect class="e" x="0" y="{y}" width="22" height="14" rx="3" style="animation-delay:{i*0.42:.2f}s"/>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Colibri x Qwen: expert-loading optimization">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b1d2a"/><stop offset="1" stop-color="#123a52"/></linearGradient>
  <linearGradient id="acc" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3987e5"/><stop offset="1" stop-color="#1baf7a"/></linearGradient>
</defs>
<style>
  text {{ font-family: {FONT}; }}
  .t {{ fill: #ffffff; font-size: 54px; font-weight: 700; letter-spacing: -0.5px; }}
  .s {{ fill: #c9dceb; font-size: 22px; }}
  .k {{ fill: #8fb3cc; font-size: 15px; letter-spacing: 1.5px; }}
  .e {{ fill: #eb6834; opacity: 0; animation: flow 4.2s linear infinite; }}
  @keyframes flow {{ 0% {{ transform: translateX(205px); opacity: 0; }} 8% {{ opacity: 1; }}
                     88% {{ opacity: 1; }} 100% {{ transform: translateX(1040px); opacity: 0; }} }}
  .pulse {{ animation: pulse 2.1s ease-in-out infinite; transform-origin: 1110px 214px; }}
  @keyframes pulse {{ 0%,100% {{ opacity: .55; }} 50% {{ opacity: 1; }} }}
  .bar {{ animation: grow 1.6s ease-out both; transform-origin: 70px 0; }}
  @keyframes grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
</style>
<rect width="{W}" height="{H}" rx="18" fill="url(#bg)"/>
<text x="70" y="92" class="t">Colibri × Qwen3-Coder</text>
<text x="70" y="132" class="s">Faster expert loading for Mixture-of-Experts inference on small machines</text>
<rect class="bar" x="70" y="150" width="520" height="4" rx="2" fill="url(#acc)"/>
<g transform="translate(70,186)"><rect width="120" height="64" rx="10" fill="#0e2a3c" stroke="#3987e5" stroke-width="2"/>
  <text x="60" y="30" text-anchor="middle" fill="#ffffff" font-size="17" font-weight="600">SSD</text>
  <text x="60" y="50" text-anchor="middle" class="k">EXPERTS</text></g>
<g>{''.join(blocks)}</g>
<g class="pulse" transform="translate(1090,186)"><rect width="120" height="64" rx="10" fill="#0e2a3c" stroke="#1baf7a" stroke-width="2"/>
  <text x="60" y="30" text-anchor="middle" fill="#ffffff" font-size="17" font-weight="600">RAM</text>
  <text x="60" y="50" text-anchor="middle" class="k">CACHE</text></g>
<text x="640" y="282" text-anchor="middle" class="k">BIT-IDENTICAL OUTPUT · COLD-START BENCHMARKED · BUILT ON COLIBRI</text>
</svg>
"""


def results_svg(wv, gb):
    """Two animated panels: TTFT and GB read for the 514-token prompt, before -> after."""
    W, H = 1000, 380
    panels = [("⏱  Time to first token, 514-token prompt", "s",
               [(f"cap {c}", wv[("long", c)]["TTFT (s)"]["a"], wv[("long", c)]["TTFT (s)"]["b"]) for c in (12, 32)]),
              ("💾  Expert bytes read from disk, 514-token prompt", "GB",
               [(f"cap {c}", gb[("long", c)][0], gb[("long", c)][1]) for c in (12, 32)])]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="Waves results: time to first token and bytes read, before and after">',
         f"""<style>
  text {{ font-family: {FONT}; fill: #1b1b1a; }}
  .h {{ font-size: 18px; font-weight: 700; }} .l {{ font-size: 14px; fill: #52514e; }}
  .v {{ font-size: 14px; font-weight: 600; opacity: 0; animation: fade .6s ease-out forwards; }}
  .g {{ font-size: 13px; fill: #52514e; }}
  .b {{ transform-box: fill-box; transform-origin: left center; transform: scaleX(0); animation: grow 1.4s cubic-bezier(.2,.8,.2,1) forwards; }}
  @keyframes grow {{ to {{ transform: scaleX(1); }} }}
  @keyframes fade {{ to {{ opacity: 1; }} }}
</style>""",
         f'<rect width="{W}" height="{H}" rx="16" fill="#fcfcfb" stroke="#e2e1dc"/>',
         f'<rect x="590" y="22" width="14" height="14" rx="3" fill="#2a78d6"/><text x="610" y="34" class="l">token at a time (MISS_QD=8)</text>',
         f'<rect x="800" y="22" width="14" height="14" rx="3" fill="#eb6834"/><text x="820" y="34" class="l">+ waves</text>']
    y = 70; left, maxw = 110, 760
    k = 0
    for title, unit, items in panels:
        vmax = max(max(a, b) for _, a, b in items)
        o.append(f'<text x="30" y="{y}" class="h">{title}</text>')
        y += 18
        for label, a, b in items:
            o.append(f'<text x="{left-14}" y="{y+26}" class="l" text-anchor="end">{label}</text>')
            for v, col, dy in ((a, "#2a78d6", 0), (b, "#eb6834", 22)):
                w = max(v / vmax * maxw, 3)
                delay = 0.25 + 0.35 * k
                o.append(f'<rect class="b" x="{left}" y="{y+dy+6}" width="{w:.1f}" height="18" rx="4" fill="{col}" style="animation-delay:{delay:.2f}s"/>')
                o.append(f'<text class="v" x="{left+w+8:.1f}" y="{y+dy+20}" style="animation-delay:{delay+1.1:.2f}s">{f(v)} {unit}</text>')
                k += 1
            red = 100 * (1 - b / a)
            o.append(f'<text class="v g" x="{W-30}" y="{y+40}" text-anchor="end" style="animation-delay:{0.25+0.35*k+0.8:.2f}s">−{red:.0f}%</text>')
            y += 58
        y += 22
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ README
def build():
    p1 = R.compare("comparison.md")
    wv = R.compare("ab2/comparison_waves.md")
    ar = R.compare("ab2/comparison_arena.md")
    gr = R.compare("grouped/comparison.md")
    phases, steps, total_flt, p0_miss, host = R.phase0()
    ok = R.correctness()
    first = lambda arm, p, c, k: R.cell_rows(arm, p, c)[0][k]
    gb = {cell: (st.mean(r["proc_read_bytes"] for r in R.cell_rows("ab2/qd8", *cell)) / 1e9,
                 st.mean(r["proc_read_bytes"] for r in R.cell_rows("ab2/waves", *cell)) / 1e9) for cell in CELLS}
    gcomp = {cell: (st.mean(r["waves_compute_s"] for r in R.cell_rows("grouped/gwaves", *cell)),
                    st.mean(r["waves_compute_s"] for r in R.cell_rows("grouped/grouped", *cell)))
             for cell in [("medium", 32), ("long", 32), ("medium", 12), ("long", 12)]}
    chunk = {}
    for a, n in (("c32", 32), ("c64", 64), ("c128", 128), ("c256", 256), ("call", 514)):
        for cap in (32, 12):
            rs = R.cell_rows(f"chunk/{a}", "long", cap)
            chunk[(n, cap)] = (st.mean(r["proc_read_bytes"] for r in rs) / 1e9, st.mean(r["ttft_s"] for r in rs))
    dm = {cell: (first("order/token", *cell, "decode_misses"), first("order/first", *cell, "decode_misses"),
                 first("order/last", *cell, "decode_misses")) for cell in CELLS}
    ar_timing = [ar[c][m] for c in CELLS for m in ("TTFT (s)", "end-to-end tok/s (engine)", "decode tok/s")]
    ar_ns = sum(1 for c in ar_timing if not c["verdict"].startswith("sig"))
    ar_flt = [ar[c]["minor page faults"]["d"] for c in CELLS]
    ar_rss = [ar[c]["peak RSS (GB)"]["d"] for c in CELLS]
    tt = lambda d, c: d[c]["TTFT (s)"]
    e2e = lambda d, c: d[c]["end-to-end tok/s (engine)"]
    L, L32 = ("long", 12), ("long", 32)
    p1_ttft = [tt(p1, c)["d"] for c in p1]; p1_e2e = [e2e(p1, c)["d"] for c in p1]
    wv_ttft = [tt(wv, c)["d"] for c in CELLS]
    gb_red = [100 * (1 - b / a) for (p, _), (a, b) in gb.items() if p != "short"]
    host_min = min(host, key=lambda h: h[3])
    load_flt, pre_flt, dec_flt = phases.get("load", 0), phases.get("prefill", 0), phases.get("decode", 0)
    refill, first_fill, sread = steps["int4 repack"], steps["repack, 1st"], steps["scale pread"]
    pages = R.json.load(open(R.KIT / "env" / "expert_iobench.json"))["expert_bytes"] // 4096
    save128 = {cap: 100 * (1 - chunk[(514, cap)][0] / chunk[(128, cap)][0]) for cap in (32, 12)}
    ratio128 = {cap: chunk[(128, cap)][0] / chunk[(514, cap)][0] for cap in (32, 12)}
    n_mod = ok["runs"] + ok["runs_final"]
    import json, os
    io = json.load(open(R.KIT / "env" / "expert_iobench.json"))
    gbs = {r["qd"]: r["gb_s"] for r in io["rows"]}
    io_gain = gbs[8] / gbs[1]
    base = json.load(open(R.KIT / "baseline" / "results.json"))["cells"]
    share = [v["metrics"]["fetch_share"]["mean"] * 100 for k, v in base.items()
             if k.startswith("cold") and "fetch_share" in v["metrics"]]
    snap = Path(os.path.expanduser("~/colibri-models/qwen3-coder-30b"))
    file_gb = sum(x.stat().st_size for x in snap.glob("*.safetensors")) / 1e9
    rss = {cap: max(r["peak_rss_gb"] for r in R.rows("ab2/qd8") if r["cap"] == cap) for cap in (32, 12)}
    comp = [r["waves_compute_s"] for a in ("c32", "c64", "c128", "c256", "call") for r in R.rows(f"chunk/{a}")]

    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "banner.svg").write_text(banner())
    (ASSETS / "results.svg").write_text(results_svg(wv, gb))

    name = lambda p, c: f"{p} ({PLEN[p]} tok), cap {c}"
    t_p1 = "\n".join(f"| {name(*c)} | {f(tt(p1,c)['a'])} → {f(tt(p1,c)['b'])} s | {pct(tt(p1,c))} | "
                     f"{f(e2e(p1,c)['a'])} → {f(e2e(p1,c)['b'])} | {pct(e2e(p1,c))} |"
                     for c in [("short", 32), ("medium", 32), ("short", 12), ("medium", 12)])
    t_wv = "\n".join(f"| {name(*c)} | {f(tt(wv,c)['a'])} → {f(tt(wv,c)['b'])} s | {pct(tt(wv,c))} | "
                     f"{f(gb[c][0])} → {f(gb[c][1])} | {first('ab2/qd8',*c,'misses'):,} → {first('ab2/waves',*c,'misses'):,} | "
                     f"{pct(e2e(wv,c))} | {pct(wv[c]['decode tok/s'], bold=False)} |" for c in CELLS)
    t_chunk = "\n".join(f"| {n if n != 514 else 'whole prompt (514)'} | {chunk[(n,32)][0]:.1f} | {chunk[(n,32)][1]:.0f} | "
                        f"{chunk[(n,12)][0]:.1f} | {chunk[(n,12)][1]:.0f} |" for n in (32, 64, 128, 256, 514))
    t_gr = "\n".join(f"| {name(*c)} | {gcomp[c][0]:.1f} → {gcomp[c][1]:.1f} s | {pct(tt(gr,c))} |" for c in gcomp)
    t_dm = "\n".join(f"| {name(*c)} | {dm[c][0]:,} | {dm[c][1]:,} | **{dm[c][2]:,}** |" for c in CELLS)

    md = f"""<p align="center">
  <img src="assets/optimization/banner.svg" alt="Colibri × Qwen3-Coder: faster expert loading for Mixture-of-Experts inference" width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-2a78d6" alt="License: Apache-2.0"></a>
  <a href="{UPSTREAM}"><img src="https://img.shields.io/badge/built%20on-colibri-1baf7a" alt="Built on colibri"></a>
  <img src="https://img.shields.io/badge/language-C11-555555" alt="Language: C">
  <img src="https://img.shields.io/badge/model-Qwen3--Coder--30B--A3B-eb6834" alt="Model: Qwen3-Coder-30B-A3B">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20WSL2-6250d6" alt="Platform: Linux, WSL2">
  <img src="https://img.shields.io/badge/output-bit--identical-008300" alt="Output: bit-identical">
</p>

<p align="center">
  <b>Time to first token on a 514-token prompt: {f(tt(wv,L)['a'])} s → {f(tt(wv,L)['b'])} s ({tt(wv,L)['d']:+.0f}%) ·
  disk reads {gb[L][0]:.0f} GB → {gb[L][1]:.0f} GB · output bit-for-bit identical</b>
</p>

<p align="center">
  <a href="#-quick-start">🚀 Quick start</a> ·
  <a href="#-talk-to-the-model">💬 Chat</a> ·
  <a href="#-results">📊 Results</a> ·
  <a href="#-how-it-works">🔬 How it works</a> ·
  <a href="docs/colibri_optimization_results.pdf">📄 PDF report</a> ·
  <a href="docs/STATUS.md">🧭 Status</a>
</p>

---

## 💡 What is this?

[**colibri**]({UPSTREAM}) runs very large **Mixture-of-Experts (MoE)** language models on ordinary machines. Each layer of an
MoE model has many small sub-networks, the *experts*, and only a few of them run for each token. colibri keeps a small
**cache** of experts in RAM and streams the rest from the SSD as the model asks for them.

This project is a research fork that measured where that streaming loses time and fixed it. It works on
**Qwen3-Coder-30B-A3B** (48 layers × 128 experts, 8 per token) on colibri's `qwen36` engine, as a stand-in for
**GLM-5.3-Flash**, which does not fit the test machine.

> 🔎 **The finding:** on this machine the time goes to **loading experts from disk**, not to computing with them. Fetching
> experts took {min(share):.0f}–{max(share):.0f}% of every decode step, and processing a prompt re-read the same experts again and again.

### ✨ Highlights

- ⚡ **Parallel miss loading:** a layer's missing experts are read 8 at a time instead of one at a time. Time to first token
  **{-max(p1_ttft):.0f}–{-min(p1_ttft):.0f}% faster**, end-to-end tokens/s **+{min(p1_e2e):.0f}…+{max(p1_e2e):.0f}%**.
- 🌊 **Expert-major prefill ("waves"):** each expert is read **once per prompt** instead of once per token. Time to first token
  **{-max(wv_ttft):.0f}–{-min(wv_ttft):.0f}% faster** on top of parallel loading, and **{min(gb_red):.0f}–{max(gb_red):.0f}% fewer bytes read** on
  medium and long prompts.
- 🎯 **Exact:** last-token logits are **byte-identical** to the frozen original in all **{n_mod}** runs of the modified program
  ({ok['fails'] + ok['fails_final']} differences).
- 🔍 **Phase 0 attribution:** the "3 million page faults" were load-time and first-touch, not per miss. The real per-miss cost is
  the **Windows host paging the WSL VM out** ([details](#-phase-0-what-the-page-faults-really-were)).
- 🧪 Every claim comes from **cold, interleaved (ABBA), 3-rep** benchmarks with **bootstrap 95% confidence intervals**.
  Results that don't clear the bar are reported as *n.s.*, not as wins.

<p align="center">
  <img src="assets/optimization/results.svg" alt="Animated chart: time to first token and bytes read on the 514-token prompt, token at a time vs waves" width="88%">
</p>

---

## 📚 Table of contents

- [💡 What is this?](#-what-is-this)
- [🚀 Quick start](#-quick-start)
- [💬 Talk to the model](#-talk-to-the-model)
- [⚙️ Feature flags](#️-feature-flags)
- [📊 Results](#-results)
- [🔬 How it works](#-how-it-works)
- [🔍 Phase 0: what the page faults really were](#-phase-0-what-the-page-faults-really-were)
- [✅ Correctness](#-correctness)
- [🧪 Reproducing the benchmarks](#-reproducing-the-benchmarks)
- [🗂️ What changed in the code](#️-what-changed-in-the-code)
- [🌐 Does it carry over to GLM-5.3-Flash?](#-does-it-carry-over-to-glm-53-flash)
- [⚠️ Limitations and what didn't help](#️-limitations-and-what-didnt-help)
- [🗺️ Roadmap](#️-roadmap)
- [📖 Documentation](#-documentation)
- [🙏 Acknowledgements and references](#-acknowledgements-and-references)
- [📜 License](#-license)
- [📝 Citation](#-citation)

---

## 🚀 Quick start

### 1. Requirements

| | |
|---|---|
| 🐧 OS | Linux, or Windows with WSL2 |
| 🛠️ Toolchain | `gcc` or `clang` with OpenMP, `make`, Python 3 (benchmarks only) |
| 💾 Disk | ~{file_gb:.0f} GB for the model, an SSD strongly recommended |
| 🧠 RAM | ~{rss[12]:.1f} GB at `--cap 12`, ~{rss[32]:.1f} GB at `--cap 32` (peak RSS measured) |

### 2. Build

```bash
git clone {ME}.git
cd Colibri_Qwen_Optimization
make -C c qwen36                                        # the Qwen3 / Qwen3-Coder engine
make -C c tests/test_qwen36_cache_index && c/tests/test_qwen36_cache_index   # unit tests
```

### 3. Get the model

```bash
pip install -U "huggingface_hub[cli]"
huggingface-cli download Justvugg/Qwen3-Coder-30B-A3B-colibri-int4 --local-dir ~/colibri-models/qwen3-coder-30b
```

### 4. Run it

The engine reads a prompt file. Qwen3-Coder expects plain ChatML:

```bash
printf '<|im_start|>user\\nWrite a Python function that checks whether a string is a valid IPv4 address.<|im_end|>\\n<|im_start|>assistant\\n' > prompt.txt

# usage: qwen36 <cap: experts cached per layer> <bits> <prompt file>
SNAP=~/colibri-models/qwen3-coder-30b N_NEW=64 \\
COLI_Q36_MISS_QD=8 COLI_Q36_PREFILL_WAVES=1 \\
OMP_NUM_THREADS=$(nproc) ./c/qwen36 32 4 prompt.txt
```

> 💡 Every optimization is an **environment flag, off by default**. Without the flags you get the original colibri behaviour,
> bit for bit. `COLI_TIMERS=1` prints a per-phase timing breakdown, and `DUMP=logits.f32` writes the last-token logits for
> comparisons.

> ℹ️ For everyday use, colibri's own launcher (`./coli chat`, `./coli serve`) works as usual; see
> [README.colibri.md](README.colibri.md). This fork passes the flags through the environment.

---

## 💬 Talk to the model

Want to chat with Qwen3-Coder yourself, and feel the difference? [`chat.py`](benchmarks/expert_cache_research/chat.py) loads the
model once and keeps the conversation going. Pick the engine when you start it:

```bash
cd benchmarks/expert_cache_research

python3 chat.py original     # 🐢 the original colibri engine
python3 chat.py modified     # ⚡ this project: parallel loading + waves
```

Wait for **`Ready`** (the model takes 1–3 minutes to load), then type after `you ›` and press **Enter**. The answer streams in
after `model ›`, and a timing line follows it:

```text
you › Write a one-line Python function that reverses a string.
model › def reverse_string(s): return s[::-1]

   ⏱  first token after 24.5 s · 14 tokens in 44.7 s (0.69 tok/s) · prompt 20 tokens
```

| Command / option | What it does |
|---|---|
| `/reset` | start a new conversation |
| `/quit` or **Ctrl + C** | exit |
| `--max-tokens N` | longest answer, default 512 |
| `--cap N` | experts kept in RAM per layer, default 12 (`--cap 32` is faster if you have ~6.5 GB free) |
| `--temp T` | sampling temperature, default 0 (deterministic) |

> 🔬 **Try the same long message in both.** Paste a page of code and ask *"explain this code"*: the longer the message, the
> bigger the gap in *first token after*, because the original re-reads the same experts for every token of your message.
> With the default temperature 0, both engines give the **same answer**; only the waiting changes.

> ℹ️ Why not `coli chat`? colibri's launcher applies the Qwen3.6 template to this model, adding an empty `<think></think>`
> block, and Qwen3-Coder then answers with nothing. `chat.py` sends plain ChatML instead. The engine's own diagnostics go to
> `/tmp/colibri_chat_<engine>.log`, so the chat stays clean. Run one chat at a time.

---

## ⚙️ Feature flags

All flags live in [`c/qwen36.c`](c/qwen36.c). **All are off unless set.**

| Flag | Default | What it does | Verdict |
|---|---|---|---|
| `COLI_Q36_MISS_QD=N` | `0` (off) | Read a layer's cache misses `N` at a time (same cache decisions as the original) | ✅ use `8` |
| `COLI_Q36_PREFILL_WAVES=1` | off | Expert-major prefill: route the whole chunk, then load each distinct expert once, in waves no larger than the cache | ✅ big TTFT win |
| `COLI_Q36_PREFILL_WAVES_CHUNK=N` | `0` = whole chunk | Tokens planned into waves at once (smaller = less memory, more re-reads) | keep `0` |
| `COLI_Q36_PREFILL_WAVES_HEADROOM=H` | `1` with PILOT, else `0` | Cache slots kept out of a wave | default |
| `COLI_Q36_PREFILL_WAVES_ORDER=first` | `last` | `last` (default) leaves decode with exactly the original's cache; `first` = first-seen order | default |
| `COLI_Q36_PREFILL_GROUPED=1` | off | Exact 4-token kernel per weight pass inside waves | ➖ compute −9…−17%, TTFT n.s. |
| `COLI_Q36_SLOT_ARENA=1` | off | Expert cache in 2 MiB huge pages, one mapping per layer | ➖ fewer faults, no speed-up |
| `COLI_Q36_FAULT_PROF=1` | off | Diagnostic: page faults and time for each step of a cache miss | 🔍 diagnostics |

---

## 📊 Results

> 🧪 **Protocol.** Every run is **cold**: a fresh process with the OS page cache emptied, checked with `mincore`. Variants run
> back to back in **ABBA** order, 3 repetitions each, with identical model, cache size, prompts and settings. **Δ** is the
> change of the mean, and the brackets are a **bootstrap 95% CI**. *n.s.* means the interval includes 0. Machine: i9-14900HX
> laptop, NVMe, WSL2 limited to 12 GB of a 16 GB host. Model: Qwen3-Coder-30B-A3B int4 (19 GB).

### ⚡ Parallel miss loading: original vs `COLI_Q36_MISS_QD=8`

| Prompt, cache | Time to first token | Δ | Tokens/s, end to end | Δ |
|---|---|---|---|---|
{t_p1}

### 🌊 Waves: `MISS_QD=8` vs `MISS_QD=8` + `COLI_Q36_PREFILL_WAVES=1`

| Prompt, cache | Time to first token | Δ | GB read | Experts read | Tokens/s, end to end | Decode tokens/s |
|---|---|---|---|---|---|---|
{t_wv}

<details>
<summary>📐 <b>Planning window</b>: how many tokens to plan into waves at once (514-token prompt, 2 cold runs)</summary>

| Tokens planned at once | cap 32: GB read | first token (s) | cap 12: GB read | first token (s) |
|---|---|---|---|---|
{t_chunk}

Bigger is strictly better: fewer re-reads, while expert compute stays at {min(comp):.0f}–{max(comp):.0f} s at every size.
</details>

<details>
<summary>🔁 <b>Wave order</b>: decode misses after prefill (deterministic)</summary>

| Prompt, cache | original path | waves, first-seen order | waves, last-use order (default) |
|---|---|---|---|
{t_dm}

Last-use order leaves decode with exactly the original's cache in every cell.
</details>

<details>
<summary>🧮 <b>Grouped kernel</b> (<code>COLI_Q36_PREFILL_GROUPED=1</code>): exact, but not worth enabling here</summary>

| Prompt, cache | Expert compute in prefill | Δ time to first token |
|---|---|---|
{t_gr}

The kernel shares each weight load across 4 tokens while keeping each token's arithmetic order, so the output is identical.
Compute is only {gcomp[('long',32)][0]:.0f} s of a {f(tt(gr,('long',32))['a'])} s first token on this machine, so it does not move time to first token.
</details>

Full tables with every metric (misses, faults, RSS, CPU time) are in
[`docs/expert_cache_research_2.md`](docs/expert_cache_research_2.md) and in
`benchmarks/expert_cache_research/*/comparison*.md`.

---

## 🔬 How it works

### The original path

```mermaid
flowchart LR
    T[token] --> R[router picks 8 experts]
    R --> H{{in RAM cache?}}
    H -- hit --> C[compute]
    H -- miss --> D[(read from SSD<br/>one at a time)]
    D --> C
```

A prompt of *S* tokens needs *S × 8* experts per layer. When that exceeds the cache (`cap`), colibri processes **one token at
a time**, and each token re-reads experts the previous ones evicted. The 514-token prompt read
**{first('ab2/qd8','long',12,'misses'):,} experts ({gb[L][0]:.0f} GB)** at cap 12 for a model that has only 48 × 128 = 6,144.

### ⚡ Parallel miss loading (`COLI_Q36_MISS_QD`)

```mermaid
sequenceDiagram
    participant L as layer
    participant Cache as LRU cache
    participant SSD
    L->>Cache: decide all hits/misses in one locked pass<br/>(the same decisions as before)
    par 8 reads in flight
        Cache->>SSD: read miss 1
        Cache->>SSD: read miss 2
        Cache->>SSD: … miss N
    end
    SSD-->>Cache: publish all
    Cache-->>L: compute
```

The SSD delivers {io_gain:.1f}× more at 8 reads in flight than at one (`env/expert_iobench.json`). Hits, misses and evictions are identical to the original.

### 🌊 Expert-major prefill ("waves", `COLI_Q36_PREFILL_WAVES`)

```mermaid
flowchart TD
    A[route every token of the chunk] --> B[group the token,k pairs by expert]
    B --> C[order: experts already cached first,<br/>each group by last use]
    C --> D[take a wave of ≤ cap experts]
    D --> E[hold the wave; misses read 8 at a time]
    E --> F[compute every token routed to the wave<br/>into its own row]
    F --> G{{more experts?}}
    G -- yes --> D
    G -- no --> H[sum each token's 8 rows<br/>in the original rank order]
```

**Why the output stays identical.** In colibri's expert kernel (`c/expert_ffn.h`), a (token, expert) output depends only on
that token's row and that expert. So computing it in a different batch gives the same bits. The final per-token sum
(`xf_moe_combine`) is the same statement, in the same order, as the original `xf_moe_add`.

---

## 🔍 Phase 0: what the page faults really were

The first study saw ~{total_flt/1e6:.1f} M minor page faults per short run and suspected a per-miss overhead. Instrumenting every step
of a miss (`COLI_Q36_FAULT_PROF=1`) showed otherwise:

| Phase | Minor faults |
|---|---|
| 🏗️ model load | {load_flt:,} |
| 📝 prompt (first touch of the expert cache's memory: 48 layers × 32 slots × {pages} pages) | {pre_flt:,} |
| 💬 decode (all misses into reused memory) | **{dec_flt:,}** |

The real per-miss costs are:
1. 📖 a **second disk read** per expert for its scales, which the file stores apart from the weights ({sread['us']/1e3:.1f} ms);
2. 🪟 rewriting an evicted slot takes {refill['us']/1e3:.1f} ms, against {first_fill['us']/1e3:.2f} ms for fresh memory. During a run the
   **Windows host fell to {host_min[3]} MB free** and pushed the VM down to {host_min[1]:,} MB of real memory while the engine held
   {host_min[0]:,} MB. The least recently used slot is exactly what the host paged out.

The fix for (2) is in the environment, not the engine: give WSL less RAM than the host can actually back.

---

## ✅ Correctness

- 🔒 **Byte-identical logits.** `DUMP=` writes the last-token logits, and `check_correctness.py` compares their SHA-256 and the
  generated text against the **frozen original binary** (colibri commit `e0db083c`): **{n_mod} runs, {ok['fails'] + ok['fails_final']} differences**,
  across every variant, prompt length and cache size, with every flag off and on.
- 🧩 **Unit tests** (`c/tests/test_qwen36_cache_index`) check:
  - the batched loader makes the same decisions as the serial one;
  - waves are bit-identical to the token path in 13 configurations;
  - every (token, expert) pair is computed exactly once, and no expert is read twice in a layer pass.
- 🎲 **Deterministic cache decisions.** Hit and miss counts are identical across repetitions of each variant.

---

## 🧪 Reproducing the benchmarks

Everything is in [`benchmarks/expert_cache_research/`](benchmarks/expert_cache_research/README.md): the harness, the scripts,
the commands of every session, and the per-run results (`runs.jsonl`).

```bash
cd benchmarks/expert_cache_research
# one cold run by hand
python3 evict_cache.py ~/colibri-models/qwen3-coder-30b && \\
  SNAP=~/colibri-models/qwen3-coder-30b N_NEW=32 COLI_TIMERS=1 COLI_LOOKUP=0 OMP_NUM_THREADS=16 \\
  DUMP=/tmp/l.f32 ../../c/qwen36 32 4 prompts/rendered/short.txt

# the main A/B (cold, ABBA, 3 reps): see ab2/commands.txt
bash -c "$(grep -v '^#' ab2/commands.txt)"
python3 summarize.py ab2/waves && python3 compare.py ab2/qd8 ab2/waves --out ab2/comparison_waves.md
python3 check_correctness.py ab2/baseline ab2/qd8 ab2/waves     # must print 0 failure(s)
```

> ⏱️ A cold short run takes ~1–2 min. The 514-token prompt takes 5–8 min without waves. The full matrix takes a few hours.

---

## 🗂️ What changed in the code

| File | Change |
|---|---|
| [`c/qwen36.c`](c/qwen36.c) | batched miss loading, prefill waves, slot arena, fault profiler; all behind flags |
| [`c/expert_ffn.h`](c/expert_ffn.h) | `xf_moe_combine` (rank-order sum), exact 4-token `xf_dot_i8_x4`, `xf_moe_compute_ex` |
| [`c/tests/test_qwen36_cache_index.c`](c/tests/test_qwen36_cache_index.c) | batch-vs-serial and waves-vs-token-path tests |
| [`benchmarks/expert_cache_research/`](benchmarks/expert_cache_research/) | benchmark kit and all results |
| [`docs/`](docs/) | reports (part 1, part 2), PDF, status, report builders |

---

## 🌐 Does it carry over to GLM-5.3-Flash?

`c/glm53.c` already reads a layer's misses in parallel and processes prompts expert by expert, inside a **128-token window**.
Three pieces would carry over:
- **cached experts first**;
- a **larger planning window**;
- a **fixed-order sum**, so the reordering stays bit-exact (glm53 adds results in block order).

> 📐 **Estimate, not a measurement.** On Qwen, a 128-token window read {ratio128[32]:.1f}× the bytes of whole-prompt planning on the
> 514-token prompt. If GLM-5.3 behaves alike, prefill expert reads would fall by roughly **{min(save128.values()):.0f}–{max(save128.values()):.0f}%** on
> ~500-token prompts. GLM-5.3 has different expert counts, sizes and routing, so this **must be measured on the target machine**.

---

## ⚠️ Limitations and what didn't help

- 🪟 **The machine.** WSL2 on a memory-starved 16 GB host: absolute times drift between sessions, so only interleaved comparisons
  are used.
- 📉 **Decode speed is not proven to change**: 3 repetitions cannot resolve it under this noise.
- 🧱 **Huge-page arena:** faults {max(ar_flt):.0f}…{min(ar_flt):.0f}%, but {ar_ns}/18 timing comparisons n.s., and +{min(ar_rss):.0f}–{max(ar_rss):.0f}% RSS.
- 🧮 **Grouped kernel:** exact and faster at compute, but TTFT n.s. here.
- 🧊 **Cold check:** {ok['resident_nz']} of {ok['runs_all']} runs started with up to {ok['resident_max_mb']:.1f} MB (of {file_gb:.0f} GB) still cached (negligible, but not
  exactly 0).
- 🚫 **Not measured:** server (warm) mode, PILOT prefetch together with waves, and the GPU (CUDA/Vulkan) paths, which keep the
  original code path.

---

## 🗺️ Roadmap

- [x] Parallel miss loading (`COLI_Q36_MISS_QD`)
- [x] Attribute the per-miss overhead (Phase 0)
- [x] Expert-major prefill, bit-exact (`COLI_Q36_PREFILL_WAVES`)
- [x] Last-use wave order as the default
- [x] Exact grouped kernel (`COLI_Q36_PREFILL_GROUPED`)
- [ ] Port cached-first waves, a fixed-order sum and a larger window to `glm53.c`, and measure on the target machine
- [ ] Re-measure decode on a host with spare RAM (≥ 6 repetitions)
- [ ] One disk read per expert (merge or overlap the scale read)
- [ ] Decide whether waves should be on by default

---

## 📖 Documentation

| Document | What's in it |
|---|---|
| 📄 [`docs/colibri_optimization_results.pdf`](docs/colibri_optimization_results.pdf) | 5-page summary for a technical reader new to colibri |
| 🧭 [`docs/STATUS.md`](docs/STATUS.md) | where things stand, every flag, next steps |
| 📘 [`docs/expert_cache_research.md`](docs/expert_cache_research.md) | part 1: architecture, baseline, parallel loading |
| 📗 [`docs/expert_cache_research_2.md`](docs/expert_cache_research_2.md) | part 2: Phase 0, waves, all studies |
| 🧰 [`benchmarks/expert_cache_research/README.md`](benchmarks/expert_cache_research/README.md) | benchmark kit |
| 🐦 [`README.colibri.md`](README.colibri.md) | the upstream colibri README (all engines, the `coli` launcher, the GPU backends) |

The README and the PDF are generated from the result files: `python3 docs/report_src/build_readme.py` and
`python3 docs/report_src/build_report.py`.

---

## 🙏 Acknowledgements and references

- 🐦 **[colibri]({UPSTREAM})** by **Vincenzo Fornaro (JustVugg)**, the engine this work is built on. All credit for the engine, the
  model conversions and the original expert cache goes to colibri and its contributors. Please star and support the
  original project.
- 🤖 **[Qwen3-Coder](https://github.com/QwenLM/Qwen3-Coder)** by the Qwen team; the int4 colibri conversion is
  [`Justvugg/Qwen3-Coder-30B-A3B-colibri-int4`](https://huggingface.co/Justvugg/Qwen3-Coder-30B-A3B-colibri-int4).
- 📚 Related work on MoE expert offloading that informed the design:
  [MoE-Infinity](https://arxiv.org/abs/2401.14361) ·
  [ProMoE](https://arxiv.org/abs/2410.22134) ·
  [HOBBIT](https://arxiv.org/abs/2411.01433) ·
  [Fiddler](https://arxiv.org/abs/2402.07033) ·
  [HybriMoE](https://arxiv.org/abs/2504.05897) ·
  [SpecMD](https://arxiv.org/abs/2602.03921)

---

## 📜 License

Licensed under the **Apache License 2.0**, the same as colibri. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

- colibri is © 2026 Vincenzo Fornaro.
- The modifications in this repository are © 2026 Mostafa Elhadidy, under the same license. They are listed in `NOTICE` and in
  the git history.
- Third-party components bundled with colibri are listed in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

---

## 📝 Citation

If you use this work, please cite it, and cite colibri (see [`CITATION.cff`](CITATION.cff)):

```bibtex
@software{{elhadidy2026colibri_qwen_opt,
  author  = {{Elhadidy, Mostafa}},
  title   = {{Colibri × Qwen3-Coder: faster expert loading for Mixture-of-Experts inference}},
  year    = {{2026}},
  url     = {{{ME}}},
  note    = {{Built on colibri by Vincenzo Fornaro, {UPSTREAM}}}
}}
```

<p align="center">
  Made with ☕ and many cold-cache benchmarks by <a href="https://github.com/MostafaaElhadidy">Mostafa Elhadidy</a> ·
  powered by <a href="{UPSTREAM}">colibri</a> 🐦
</p>
"""
    (REPO / "README.md").write_text(md)
    print("wrote README.md and", ", ".join(p.name for p in ASSETS.iterdir()))


if __name__ == "__main__":
    build()
