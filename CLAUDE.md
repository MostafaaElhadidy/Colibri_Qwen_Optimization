# Colibri expert-cache research: working notes

**Start here: read `docs/STATUS.md` first** (what is done, every flag and its default, results, open questions, next steps).

Context: `docs/expert_cache_research.md` (report) and `benchmarks/expert_cache_research/README.md` (kit).

## Model
- Qwen3-Coder-30B-A3B, `Justvugg/Qwen3-Coder-30B-A3B-colibri-int4`. It runs on the **qwen36** engine (`c/qwen36.c`), not `colibri.c`.
- 48 layers × 128 experts, top-8. Experts are int4 gs64 (`merged_weight` + f32 `qs`), 2,654,208 B each. The dense trunk is int8. 19 GB in 49 shards.
- Benchmark copy: `~/colibri-models/qwen3-coder-30b` (ext4). The Windows original at `/mnt/c/Users/mosta/colibri-models/qwen3-coder-30b` and the Windows colibri v2.0.0 install are **read-only: never write, move or run `coli` against them** (`coli` writes `.coli_usage` / `.coli_analysis.json` into the model dir). Call `./qwen36` directly.

## Build
- Modified engine: `make -C c qwen36`, then `cp c/qwen36 benchmarks/expert_cache_research/bin/qwen36.optimized`.
- Frozen original (commit `e0db083c`, sha256 `36ff0d1f…`): `benchmarks/expert_cache_research/bin/qwen36.baseline`. Never rebuild over it. To recreate it: `git worktree add /tmp/orig e0db083c && make -C /tmp/orig/c qwen36`.
- Unit test: `make -C c tests/test_qwen36_cache_index && c/tests/test_qwen36_cache_index`.
- `bin/` and `*.logits.f32` are gitignored.

## Benchmarks (run from `benchmarks/expert_cache_research/`)
- A single cold run by hand:
  `python3 evict_cache.py ~/colibri-models/qwen3-coder-30b && SNAP=~/colibri-models/qwen3-coder-30b N_NEW=32 COLI_TIMERS=1 COLI_LOOKUP=0 OMP_NUM_THREADS=16 DUMP=/tmp/l.f32 bin/qwen36.baseline 32 4 prompts/rendered/short.txt`
- A/B (cold, interleaved ABBA, 3 reps):
  `python3 run_bench.py --snap ~/colibri-models/qwen3-coder-30b --arm baseline=bin/qwen36.baseline --arm optimized=bin/qwen36.optimized:FLAG=VAL --modes cold --caps 32,12 --pilot 0 --prompts short,medium --reps 3 --n-new 32 --out ab`
- Flag-off arm: `--arm flagoff=bin/qwen36.optimized --reps 1`.
- Then:
  - `python3 summarize.py ab/<arm>`
  - `python3 check_correctness.py ab/baseline ab/optimized ab/flagoff`, which compares the sha256 of the `DUMP=` last-token logits plus the text
  - `python3 compare.py ab/baseline ab/optimized --out comparison.md`
- Diagnostics:
  - `expert_iobench.py` (device latency at real expert size)
  - `thread_sampler.py -- <cmd>` (per-thread syscall/fault profile; no perf/gdb here)
- Runtime: a cold short run takes ~1–2 min, medium ~2–4 min, the 514-token long prompt ~5–8 min at cap 32. Run long jobs in the background.

## Rules
- No change to routing, expert selection, model math or kernel input order. Placement and timing only. `CACHE_ROUTE`-style lossy levers are out of scope.
- Every change sits behind an env flag, **off by default**. With the flag off, the code takes the original path.
- Logits must be **byte-identical** to the frozen original, with the flag on and off, in every cell (`check_correctness.py` must report 0 failures). With PILOT=0, hit/miss counts should also match exactly.
- Measure as cold runs (page cache evicted), with arms **interleaved ABBA, ≥3 reps**, and identical model/cap/prompts/`N_NEW`/env. Report the bootstrap CI. Call a change "n.s." when its interval spans 0, and never claim it as a win.
- Never benchmark while building or while another engine is running. Check `pgrep -f qwen36` first.
- No commits or pushes unless asked. Author identity is not in git config: use `-c user.name="Mostafa Elhadidy" -c user.email=mostafaelhadidy442@gmail.com`.

## WSL quirks
- **RAM** is 12 GB (`.wslconfig`; the host has 16 GB). `--cap 32` ≈ 6.2 GB RSS, `--cap 12` ≈ 3.8 GB. `--cap 128` does not fit, so the CUDA expert tier (which needs cap = 128) is unusable and everything is CPU expert streaming.
- **Storage** is a VHDX on the host NVMe and very noisy: one expert read ranged 2.7–47.7 ms. Every run records a storage canary (`canary_ms_p50`); compare arms only within one interleaved session.
- **Cold check**: `evict_cache.py` uses `posix_fadvise(DONTNEED)` and then the `bin/pagecache_resident` (mincore) check. A cold row must show `pagecache_resident_before_bytes == 0`. The host's own cache of the VHDX cannot be controlled.
- **Chat template**: the gateway renders Qwen3-Coder with the qwen36 template, which adds an empty `<think></think>`, and the model then returns 0 tokens. Use plain ChatML (`run_bench.CHAT`): `<|im_start|>user\n…<|im_end|>\n<|im_start|>assistant\n`.
- No `perf`, `gdb`, `strace` or `fincore` in this image.
