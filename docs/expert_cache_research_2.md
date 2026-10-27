# Expert caching in colibri, part 2: the per-miss overhead and expert-major prefill

**Model:** Qwen3-Coder-30B-A3B (colibri int4 gs64) on the `qwen36` engine.
**Machine:** i9-14900HX, Windows 11 + WSL2 with 12 GB RAM (16 GB host), the same as [part 1](expert_cache_research.md).
**Code:** branch `feature/expert-cache-followup` on top of `a17cc25a` (the part-1 notes commit; the code is in the commits that follow it). Frozen original: `bin/qwen36.baseline` (commit `e0db083c`, sha256 `36ff0d1f…`).
**Reproduction kit and raw data:** [`benchmarks/expert_cache_research/`](../benchmarks/expert_cache_research/README.md) (`phase0/`, `ab2/`, `chunk/`, `grouped/`, `order/`).

## Summary

- **Phase 0: the "per-miss faults" were not per miss.**
  - Of the ~3.0 M minor faults in a short cold run, 2.03 M happen while the model loads, ~1.0 M are the 4 GB slot set being touched once, and decode takes **zero**.
  - The real per-miss overhead is in two places: a second I/O round trip for the scales (~2 ms), and ~3 ms to rewrite an evicted slot that takes 0.25 ms in isolation.
  - The cause of the second is the **Windows host paging the VM out**. During a run the host fell to 4 MB free and trimmed the VM to under 1 GB of working set while the guest held 6 GB, so rewriting the least recently used slot means a host-side page-in the guest can't see.
  - That is outside the engine. A small huge-page slot arena (`COLI_Q36_SLOT_ARENA=1`) removes the one-time faults (−11% to −34%) at +1–3% RSS, with **no significant timing effect** in 17 of 18 cell-metrics.
- **Phase 1: expert-major prefill (`COLI_Q36_PREFILL_WAVES=1`), exact.**
  - Every token of a chunk is routed first. The distinct experts are processed in waves of at most `cap` slots, residents first, and each (token, k) output is kept and summed per token in the original rank order.
  - Against `COLI_Q36_MISS_QD=8` (cold, ABBA, 3 reps):
    - **TTFT −49% to −92%**, significant in all 6 cells; the 514-token prompt goes from **376 s to 30 s** at cap 12 and from 221 s to 47 s at cap 32;
    - **bytes read −54% to −88%** on medium and long prompts (283 → 35 GB);
    - **end-to-end tok/s +72% to +571%**, significant in 4 of 6 cells.
  - Decode tok/s is n.s. in 5 cells and −28% [−48, −1] in one (medium, cap 32).
- **Byte-identical.**
  - Last-token logits and text match the frozen original in **every** run of every arm: 176 cold runs, 0 failures.
  - A unit test checks that every pair is computed exactly once and that no expert is read twice in a layer pass.
- **Follow-ups measured.**
  - **Planning size**: a bigger planning block is strictly better (32 tokens → whole prompt: 86 → 26 GB at cap 32).
  - **Order**: ordering waves by *last* use (now the default) makes decode start from exactly the token path's cache. Decode misses fall 2–26% and equal the token path's in all 6 cells; timing n.s. or mixed.
  - **Grouped kernel**: a 4-token kernel that turned out **exact** (not lossy) cuts the long prompt's prefill expert compute 9–17%, but TTFT is n.s.
- **GLM-5.3.** `glm53.c` is already expert-major but plans 128 tokens at a time, in first-seen order, and sums in block order. The residents-first order, a fixed-order combine and a larger chunk all carry over (§7).

## 1. Before writing code: what `glm53.c` does in the same two places

The real target is GLM-5.3-Flash, so both changes were designed after reading `c/glm53.c`.

| question | `qwen36.c` (before) | `glm53.c` |
|---|---|---|
| Prefill when a chunk routes to more experts than the cache holds | `moe_xf_run` falls back to **one token at a time** (`per = cap >= S*K ? S : 1`), so an expert is looked up, and after the LRU cycles re-read, once per token that routes to it | **already expert-major**: `ffn_layer_ex` takes the union of the chunk's distinct experts and works through it in cache-sized blocks (`expert_block_read`, misses read in parallel); each expert runs all its tokens as one batch (`mlp3_rows`) |
| Block order | — | first-seen order, **not residents-first**: a resident expert needed in a later block can be evicted by an earlier block's misses and read again |
| Chunk | the whole prompt is one `step()` | `GLM53_PREFILL_CHUNK`, default 128 tokens: an expert routed in every chunk is read up to ⌈S/128⌉ times per layer |
| Sum order of the routed experts | rank order per token (`xf_moe_add`) | **block/expert order** (`dst += scale * src` per expert), i.e. a different order from its own decode path |
| Expert read | `pread` into a bounce buffer, int4 repack into the slot, a second `pread` for the scales, `POSIX_FADV_DONTNEED` | `pread` straight into slot memory owned for the slot's life (`slot->own`), one `pread` when the six pieces are contiguous, no repack, page cache left alone |
| Per-page faults | (see §2) | default path: one fault per page on a slot's **first** fill only; the opt-in `COLI_MAP_EXPERTS=1` path serves experts from a shard `mmap`, which faults per page by construction (minor if cached, major if not) |

So neither change is a straight copy. What carries over (§7):

- **Residents-first waves** port to `ffn_layer_ex` as they are. Bit-exactness there needs the same device used here: compute each expert's rows into a per-(token, k) buffer and add them in the **original** union order, because glm53 sums in block order.
- The **chunk-size** result (§6) applies to `GLM53_PREFILL_CHUNK` directly.
- The Phase 0 finding is about the machine, not the loader, and applies to any engine on this WSL setup.

## 2. Phase 0: where the per-miss overhead goes

Part 1 measured ~3.0 M minor faults per short cold run, about 650 per miss, and one expert is 648 pages. The obvious reading was one fault per page of every expert loaded. That reading turned out to be **wrong**.

### 2.1 Instrumentation

`COLI_Q36_FAULT_PROF=1` (diagnostic, off by default, measures only) wraps each step of a miss in `getrusage(RUSAGE_THREAD)` plus a clock: slot pick, read buffer, weight `pread`, int4 repack, scale `pread`, publish. A slot's *first* fill is counted apart from a refill. It also prints process-wide faults at three phase boundaries: model load, prefill and decode.

### 2.2 Result (one short cold run, cap 32, 6,629 misses)

**Faults by phase** (`phase0/qd0.log`, `phase0/qd8.log`):

| phase | MISS_QD off | MISS_QD=8 |
|---|---|---|
| model load | 2,025,231 | 2,025,232 |
| prefill (24 tokens) | 995,289 | 1,016,690 |
| decode (31 tokens) | **0** | 6,870 |
| total (`/usr/bin/time`) | 3,020,521 | 3,048,794 |

**Per miss, MISS_QD off** (main thread, serial):

| step | calls | µs / call | minor faults / call |
|---|---|---|---|
| slot pick (under the lock) | 6,629 | 6.8 | 0.2 |
| read buffer (`malloc`) | 6,629 | 16.9 | 0.2 |
| weight `pread` 2.36 MB (+ DONTNEED) | 6,629 | 8,917 | 133 |
| int4 repack, slot refill | 5,093 | **2,989** | 0 |
| scale `pread` 288 KB, slot refill | 5,093 | **2,023** | 0 |
| int4 repack, slot's first fill | 1,536 | 281 | 0 |
| scale `pread`, slot's first fill | 1,536 | 1,247 | 71 |
| publish | 6,629 | 1.2 | 0 |

### 2.3 What the numbers say

1. **The faults are not per miss.**
   - Two thirds (2.03 M) happen while the model loads, before the first token: the dense trunk and its transient load buffers.
   - The other third (~1.0 M) is the slot set being touched for the first time. That is 48 layers × 32 slots × 648 pages = 995 k, exactly.
   - Decode, which is all misses into reused slots, takes **zero** faults.
   - With MISS_QD=8 the reused read buffer removes the `pread`'s faults (133 → 0.7 per call), but they reappear one-for-one in the slot's first repack (563 per first fill). The total cannot move, because it is the size of memory first touched.
   - Part 1's "650 per miss" was 3.0 M ÷ 4,670 misses: a coincidence of two totals.
2. **The overhead is in two places, and neither is a fault.**
   - The scale `pread` is a **second I/O round trip per miss** (~2 ms). The container stores every expert's scales together in a block at the start of the shard, away from its weights (checked over all 6,144 experts: none adjacent).
   - **Refilling an evicted slot costs ~3 ms of repack, against 0.28 ms for a slot's first fill**, with no guest fault in either case. The same repack in a standalone process costs 0.25 ms (`phase0/slotbench.c`), with 4 KiB or 2 MiB pages alike. One early run of that microbenchmark gave 2.05 ms with 4 KiB pages against 0.25 ms with huge pages, but four later runs gave 0.25 ms for both. It was not a TLB effect.
   - Idle-spinning OpenMP threads are not the cause either: `OMP_WAIT_POLICY=passive` leaves the refill at 2.6 ms (`phase0/qd0_passive.log`).
3. **The cause is the host paging the VM out.** The Windows host was sampled during one cold run (`phase0/host_ws_samples.txt`, read-only PowerShell queries):

   | time | engine RSS (guest) | VM working set on the host | VM commit | host free RAM |
   |---|---|---|---|---|
   | +0 s | 0.5 GB | 3.4 GB | 9.2 GB | 3.0 GB |
   | +13 s | 2.1 GB | 6.2 GB | 10.5 GB | 1.4 GB |
   | +29 s | 4.2 GB | **0.9 GB** | 11.3 GB | **4 MB** |
   | +43 s | 6.0 GB | 1.0 GB | 12.3 GB | 36 MB |
   | +58 s | 6.3 GB | 4.5 GB | 12.3 GB | 1.1 GB |

   The VM is given 12 GB of a 16 GB host, and the host runs out. Windows then trims the VM's working set to under 1 GB while the guest holds 6 GB of anonymous memory, so most guest pages live in the host's pagefile or compression store. Touching such a page is a host-side fault: the guest sees neither a fault nor any time in a system call, only a slow instruction. This explains everything above:
   - the **least recently used** slot, which an eviction rewrites, is by definition the guest memory the host is most likely to have trimmed, so a refill is slow while a first fill into freshly recycled memory is fast;
   - part 1 saw the decode thread "87% running, 12% in `pread`" with an unexplained ~6 ms per miss;
   - the microbenchmark was slow only right after two engine runs.
4. **What the engine can and cannot do about it.**
   - It cannot make cold guest memory warm on the host. The fix is outside the engine: give WSL less than the host can back (for example `memory=8GB` in `.wslconfig` with `--cap 12`), or close host applications.
   - It *can* stop paying a fault per 4 KiB page for the one-time first touch, which is the small, clear fix the plan allowed for.

### 2.4 `COLI_Q36_SLOT_ARENA=1`

- **What it does.** Each layer's planar slots (weights and scales) are carved from one anonymous mapping, 2 MiB aligned and `madvise(MADV_HUGEPAGE)`. Slot *i* of a layer always sits at offset *i* × 2,654,208 B, so slot memory is never freed, reallocated or moved. The per-thread miss buffers become huge-page mappings too.
- **What the code did before** (the plan's checklist):
  - slot memory is allocated once (`slot_ensure_allocated`, `malloc`) and never freed, reallocated or `madvise`d during a run;
  - the 2.36 MB slot and the 288 KB scale block are above glibc's mmap threshold, so each was its own 4 KiB-page `mmap`;
  - no path touches shards through `mmap` (`COLI_MAP_EXPERTS` is not used by qwen36).
- **Effect** (smoke run): the arena is entirely on huge pages (`AnonHugePages` 3.99 GB of 6.56 GB RSS). Minor faults drop from 3.04 M to 2.05 M, which removes the slot-population third. A slot's first fill now costs one huge-page fault, but under this host's memory pressure that fault waits on direct compaction (`compact_stall` 2,635): 30 ms per first fill against 3.8 ms. Its net effect on TTFT is measured in §5.
- **Safety.** Off by default, and the bytes in a slot are unchanged. The segment adapter's teardown skips `free` for arena slots (`Slot.in_arena`), and the Vulkan warm start's temporary slots are not cache slots, so they still get `malloc`.

## 3. Phase 1: expert-major prefill (`COLI_Q36_PREFILL_WAVES=1`)

### Algorithm

`moe_ex` already routes every token of the chunk before any expert runs (`xidx`/`xval`). With the flag on, when the chunk's S × 8 pairs do not fit the layer cache and S > 1, `moe_xf_run` calls `moe_xf_waves` instead of going token by token:

```
for each block of B tokens (COLI_Q36_PREFILL_WAVES_CHUNK, default: the whole chunk):
    group the block's (token, k) pairs by expert, experts in first-seen order
    under g_pilot_mx: which of them are resident now?
    order = resident experts, then the misses (both in first-seen order)
    for each wave of at most W = cap − headroom experts in that order:
        hold the wave: expert_hold_batch (MISS_QD on: misses read N at a time) or expert_hold
        hits += (pairs of each expert − 1)       # hits+miss stay = routed pairs, as before
        compute every pair of the wave, 256 pairs per kernel call, grouped by expert:
            ctb[token][k] = expert(x[token])     # xf_moe_compute, one pair per row, K = 1
        release the wave
    out[token] += Σ_k val[token][k] · ctb[token][k]   # xf_moe_combine, rank order
```

**Why the output is byte-identical.** In `expert_ffn.h` a pair's output depends only on its token's row and its expert: the activation quantisation is per row, every dot product is per output row, and the row chunking only splits rows. So computing a pair in another batch gives the same bits. The token path ends in `xf_moe_add`'s rank-order loop `os[d] += w * c[d]`. `xf_moe_combine` is that same statement, in the same translation unit, so it contracts to the same FMA.

**Cache rules kept.**
- Every slot of the current wave is held (`busy`), so neither a later miss nor the PILOT worker can evict it.
- Victims come from the existing `slot_victim` (LRU, not busy, not loading, unpinned first).
- If every slot is taken, the batch falls back to `expert_hold`, which waits, as before.
- Headroom defaults to 1 slot under PILOT (its worker may hold one slot mid-load) and 0 otherwise.
- Residents-first means a chunk starts from what the previous chunk, or the previous request, left in the cache.

**Memory.** One per-thread buffer of B × 8 × hidden floats for the block's outputs (33.7 MB at B = 514), plus 256-pair kernel scratch (~5 MB). Both are kept for the thread's life, so a layer pass reuses the pages the previous one faulted in.

**Flag off.** `moe_xf_run` takes the original path. The only code shared with it is `q36_miss_qd`, whose cached value moved from a function-local static to a file-scope one so the unit test can set it.

### Tests

`c/tests/test_qwen36_cache_index` gains `check_waves`, which uses real `expert_ffn` kernels on synthetic int4 experts written from the expert id. It covers 13 configurations:
- S = 9…300, cap 5…12, including cap < top-k, where the token path goes pair by pair;
- block size whole or 5/64 tokens, headroom 0/1, serial loads and MISS_QD = 4/8;
- the grouped kernel and ORDER=last of §6 (2 and 3 cases).

In each one it checks four things:
1. the waves output is **bit-identical** (`memcmp`) to the token path;
2. every routed (token, k) pair is computed **exactly once**;
3. **no expert is read twice** in one layer pass (whole-chunk blocks);
4. hits + misses equals the number of routed pairs, and no slot is left held;
5. with ORDER=last on a cold cache, the final token's experts are resident afterwards.

All pass. For example, S = 300 at cap 12 reads 20 experts where the token path reads 1,048.

## 4. Protocol

Every comparison is within one interleaved session. Each run is a fresh cold process: all 49 shards evicted with `posix_fadvise(DONTNEED)`, then checked with `mincore`. The arms of a cell run back to back and their order flips every repetition (ABBA). Model, `--cap`, prompts (24 / 161 / 514 tokens, plain ChatML), `N_NEW=32`, greedy decoding, `OMP_NUM_THREADS=16`, `COLI_TIMERS=1` and `COLI_LOOKUP=0` are the same in every arm. Only the flags differ.

**Arm A** is `COLI_Q36_MISS_QD=8`, the change from part 1, and every other arm is A plus its flag. All arms run the same binary, so a difference can only come from a flag. Statistics: mean ± stdev over 3 repetitions, Δ = (B − A)/A, and a bootstrap 95% CI of Δ (10,000 resamples, `compare.py`). **n.s.** = the interval spans 0, and such a change is never claimed.

| session | arms | runs | binary |
|---|---|---|---|
| main matrix (`ab2/commands.txt`) | A, A+arena, A+waves, A+both; 6 cells × 3 reps | 72 | `qwen36.v2` (`6af414ac…`) |
| correctness (`ab2/commands_followup.txt` §1) | frozen original, final binary flag-off, final binary A+waves; 6 cells × 1 | 18 | `qwen36.baseline`, `qwen36.v3` (`562a03d6…`) |
| planning size (§2 of the same file) | A+waves with chunk 32/64/128/256/whole; long × 2 caps × 2 reps | 20 | `qwen36.v3` |
| grouped kernel (§3) | A+waves vs A+waves+grouped; medium, long × 2 caps × 3 reps | 24 | `qwen36.v3` |
| wave order (`order/commands.txt`) | A+waves vs A+waves+ORDER=last, 6 cells × 3; token path × 1 | 42 | `qwen36.v4` (`fad0bf33…`) |

`v3` is `v2` plus the grouped kernel (off unless set) and the `[waves]` timers; `v4` adds ORDER=last (off unless set) and the `[timers] prefill cache:` line. The kit records two new values per row:
- `host_free_mb` / `host_vm_ws_mb`: the Windows host's free RAM and the VM's host working set, read before the run (§2.3);
- `ru_minflt` / `ru_majflt`: from `wait4`.

**Noise.** The host had a median of about 1.1 GB free RAM before runs in every session, and the storage canary's median was 7.7–10.3 ms. Absolute times therefore drift between sessions: the same configuration, A+waves on the long prompt at cap 32, averaged 47 s in the main matrix, 50 s in the grouped session and 63 s in the order session. Only compare within a table.

**Cold check.** `pagecache_resident_before_bytes` was 0 in 150 of 176 runs. In the other 26, spread over 13 arms, 0.03–4.3 MB of the 19 GB stayed resident after eviction, i.e. at most 1.6 experts' worth against 6,000–117,000 misses per run. Part 1 had 0 everywhere. The cause is not known, and the impact is below anything these tables can resolve, but the cold check did not pass strictly in those 26 rows.

## 5. Results: main matrix (A = `COLI_Q36_MISS_QD=8`)

### 5.1 `COLI_Q36_PREFILL_WAVES=1`

| cell | TTFT A → B (s) | Δ TTFT | end-to-end tok/s | Δ | decode tok/s | Δ |
|---|---|---|---|---|---|---|
| short, cap 32 | 40.8 → 20.9 | **−48.8%** [−67.7, −6.6] | 0.383 → 0.430 | +12.2% (n.s.) | 0.684 → 0.583 | −14.8% (n.s.) |
| medium, cap 32 | 82.8 → 27.2 | **−67.2%** [−74.3, −57.6] | 0.290 → 0.500 | **+72.4%** [+35.4, +109.9] | 1.17 → 0.839 | **−28.4%** [−48.4, −0.8] (worse) |
| long, cap 32 | 221 → 47.0 | **−78.7%** [−84.8, −70.8] | 0.117 → 0.333 | **+185.7%** [+131.4, +250.0] | 0.672 → 0.619 | −7.9% (n.s.) |
| short, cap 12 | 24.3 → 8.98 | **−63.0%** [−75.4, −43.9] | 0.683 → 1.08 | +57.6% (n.s.) | 1.28 → 1.53 | +19.7% (n.s.) |
| medium, cap 12 | 117 → 18.0 | **−84.6%** [−89.2, −77.3] | 0.223 → 0.787 | **+252.2%** [+101.5, +452.1] | 0.928 → 1.40 | +50.6% (n.s.) |
| long, cap 12 | 376 → 30.0 | **−92.0%** [−94.0, −89.7] | 0.080 → 0.537 | **+570.8%** [+407.4, +794.4] | 0.728 → 1.08 | +47.7% (n.s.) |

| cell | GB read A → B | misses A → B | of which decode (B) | minor faults | peak RSS (GB) |
|---|---|---|---|---|---|
| short, cap 32 | 21.0 → 20.3 (**−3.5%**) | 6,629 → 6,289 | 3,441 | 3.05 M → 3.05 M (−0.1%) | 6.20 → 6.20 |
| medium, cap 32 | 50.5 → 23.3 (**−53.8%**) | 18,843 → 7,432 | 2,532 | 3.18 M → 3.16 M (−0.8%) | 6.22 → 6.24 (+0.3%) |
| long, cap 32 | 141 → 25.8 (**−81.7%**) | 56,703 → 8,363 | 2,756 | 3.96 M → 3.87 M (−2.3%) | 6.30 → 6.34 (+0.6%) |
| short, cap 12 | 32.9 → 27.6 (**−16.2%**) | 11,658 → 9,377 | 6,529 | 2.44 M → 2.43 M (−0.3%) | 3.82 → 3.83 (+0.3%) |
| medium, cap 12 | 102 → 32.2 (**−68.3%**) | 40,440 → 11,203 | 6,303 | 2.60 M → 2.55 M (−1.8%) | 3.85 → 3.87 (+0.5%) |
| long, cap 12 | 283 → 34.8 (**−87.7%**) | 116,777 → 12,261 | 6,654 | 3.43 M → 3.28 M (−4.3%) | 3.92 → 3.96 (+1.1%) |

Misses and bytes have zero spread across repetitions: with PILOT off, the cache decisions are deterministic. Peak VRAM was 0 MiB above idle in every run (CPU build).

**Reading it.**
- **Prefill now reads each expert about once per layer.** The 514-token prompt at cap 12 reads 35 GB where it read 283 GB. That is 5,607 prefill loads (each layer's distinct experts, once) plus 6,654 decode misses, instead of 117 k re-reads.
- **What is left of TTFT is loading, not compute.** With the `[waves]` timers (§6), prefill spent 13–57 s holding (loading) and about 10 s computing experts on the long prompt at cap 32.
- **Decode is unchanged in 5 of 6 cells**, and the one significant cell (medium, cap 32, −28%) has a mechanism. A waves prefill ends with the *last wave* resident: experts in first-seen order, not the ones the final tokens used, while the token path ends with exactly those. At cap 32 this cost 5–35% more decode misses than the token path (1,870 → 2,532 on medium; §6.2). ORDER=last removes that difference exactly. Its own timing A/B, though, is mixed (§6.2).
- **The short prompt gains least**: 24 tokens touch 59 distinct experts per layer on average. The waves still read 3.5–16% fewer bytes, and the TTFT gain is significant in both caps.

### 5.2 `COLI_Q36_SLOT_ARENA=1`

| cell | Δ TTFT | Δ end-to-end tok/s | Δ decode tok/s | minor faults | peak RSS |
|---|---|---|---|---|---|
| short, cap 32 | −8.1% (n.s.) | +17.4% (n.s.) | +35.7% (n.s.) | 3.05 M → 2.06 M (**−32.5%**) | +1.0% |
| medium, cap 32 | −0.2% (n.s.) | −1.1% (n.s.) | −15.1% (n.s.) | 3.18 M → 2.11 M (**−33.6%**) | +1.2% |
| long, cap 32 | +7.6% (n.s.) | +0.0% (n.s.) | +6.5% (n.s.) | 3.96 M → 3.07 M (**−22.4%**) | +0.8% |
| short, cap 12 | **−33.2%** [−54.3, −0.8] | +13.2% (n.s.) | −1.0% (n.s.) | 2.44 M → 2.05 M (**−16.1%**) | +2.6% |
| medium, cap 12 | −8.0% (n.s.) | +11.9% (n.s.) | +42.4% (n.s.) | 2.60 M → 2.11 M (**−18.8%**) | +2.8% |
| long, cap 12 | −1.8% (n.s.) | −4.2% (n.s.) | +5.7% (n.s.) | 3.43 M → 3.06 M (**−10.9%**) | +2.4% |

- **What it does:** it removes the slot-population faults it was built for, at the cost of 50–110 MB of RSS (huge pages are backed whole).
- **Timing:** 17 of 18 timing cells are n.s. The one significant cell has an upper bound of −0.8%, and I do not count it as a win.
- **Why it doesn't help:** the per-miss cost it could not reach is the host paging of §2.3, and a huge-page first touch costs direct compaction on this host.
- **Verdict:** keep it off. It may be worth re-measuring on a host that is not short of memory.

### 5.3 Both flags

The same TTFT gains as waves alone: −45% to −92%, significant in 5 of 6 cells (short cap 32: −45.2% [−61.9, +3.6], n.s.). End-to-end tok/s improves +45% to +654%, significant in 5 of 6, and the arena's fault reduction carries over (−16% to −35%). Long cap 12 decode is +84.2% [+10.2, +182.1], but the arena alone does not move decode and waves alone is n.s. there. I do not attribute that cell to the combination; it needs more repetitions.

## 6. Follow-ups

### 6.1 Prefill planning size (`COLI_Q36_PREFILL_WAVES_CHUNK`)

The engine prefills the whole prompt as one `step()`, so the "chunk" here is how many tokens a layer plans into waves at once. That is also the knob glm53 exposes as `GLM53_PREFILL_CHUNK`. The bits are the same at every size (`chunk/`, all byte-identical). 514-token prompt, cold, 2 reps (individual runs shown):

| tokens planned at once | cap 32: TTFT (s) | GB read | misses | hold / compute (s) | cap 12: TTFT (s) | GB read | misses |
|---|---|---|---|---|---|---|---|
| 32 | 201, 277 | 86.3 | 32,377 | 172 / 17, 249 / 13 | 209, 232 | 121.0 | 46,935 |
| 64 | 178, 285 | 64.8 | 23,845 | 148 / 17, 256 / 13 | 150, 158 | 87.5 | 33,216 |
| 128 | 116, 199 | 47.0 | 16,561 | 91 / 11, 146 / 12 | 114, 115 | 62.3 | 23,069 |
| 256 | 106, 124 | 33.8 | 11,392 | 68 / 11, 94 / 14 | 54, 57 | 45.9 | 16,689 |
| whole prompt | 46, 89 | 25.9 | 8,363 | 13 / 10, 57 / 11 | 55, 51 | 35.1 | 12,261 |

- **Bigger is better.** Bytes and misses fall at every step, and TTFT follows.
- **Large chunks cost nothing extra now.** The token path paid for a large chunk in re-reads; the waves path pays only one 8-row output buffer per token (33.7 MB at 514 tokens).
- **Compute doesn't grow with chunk size.** Expert compute stays at 10–17 s, so planning more tokens costs no time.
- **Compared with glm53's default of 128 tokens**, planning the whole prompt reads 1.8× fewer bytes at both caps here.

### 6.2 Wave order (`COLI_Q36_PREFILL_WAVES_ORDER=last`)

First-seen order (the matrix above) vs ordering each group by last use, so that the experts the final tokens routed to are loaded last and remain resident when decode starts. Each expert is still read once, and the bits are the same.

| cell | decode misses: token path / first-seen / last | Δ TTFT | Δ decode tok/s | Δ end-to-end tok/s |
|---|---|---|---|---|
| short, cap 32 | 3,271 / 3,441 / **3,271** | **+100.5%** [+2.0, +180.3] (worse) | +11.9% (n.s.) | −17.1% (n.s.) |
| medium, cap 32 | 1,870 / 2,532 / **1,870** | +8.5% (n.s.) | −12.2% (n.s.) | −9.2% (n.s.) |
| long, cap 32 | 2,164 / 2,756 / **2,164** | **−35.8%** [−47.5, −19.3] | **−40.2%** [−61.7, −1.7] (worse) | +11.3% (n.s.) |
| short, cap 12 | 6,383 / 6,529 / **6,383** | −14.9% (n.s.) | −10.3% (n.s.) | −5.0% (n.s.) |
| medium, cap 12 | 6,053 / 6,303 / **6,053** | +25.7% (n.s.) | **+48.7%** [+9.2, +115.1] | +10.5% (n.s.) |
| long, cap 12 | 6,410 / 6,654 / **6,410** | +7.0% (n.s.) | +36.0% (n.s.) | +6.2% (n.s.) |

The deterministic part is clear. With last-use order, decode misses equal the token path's **exactly** in all six cells: the LRU ends holding the experts with the latest last use either way. That is 2–26% fewer decode misses than first-seen order, and total bytes drop 1.3–7.4%.

The timing part is not clear:
- Two cells came out significant and *contradict* the miss counts: long cap 32 decode −40% despite 21% fewer misses, and short cap 32 TTFT doubled with identical prefill reads.
- One significant cell agrees with them: medium cap 12 decode +49%.

Out of 18 timing comparisons under this session's host noise, I read these as noise and **claim no timing effect**. **Done after this report's measurements: last-use is now the default order** (`COLI_Q36_PREFILL_WAVES_ORDER=first` restores first-seen). It costs nothing, and it is the only order that leaves decode with the cache the original path leaves. Re-checked with the final binary `qwen36.v5` (`final_check/`, short prompt, cap 32, cold): logits byte-identical to the frozen original with the flag off and with waves on, and 3,271 decode misses, equal to the token path.

### 6.3 Grouped kernel (`COLI_Q36_PREFILL_GROUPED=1`)

The plan allowed for a lossy grouped GEMM. Reading `xf_dot_i8_avx2` showed that a multi-token kernel can be **exact**. `xf_dot_i8_x4` loads each 32-byte weight block and splits its nibbles once, then runs four tokens' integer dot products, lane FMAs, correction chains and 8→1 trees, each in the single-token order. So the output bits are the same; the unit test and all 24 runs are byte-identical. Max |Δlogit| is 0 and the greedy text is identical.

| cell | prefill expert compute (s) | Δ compute | Δ TTFT | Δ end-to-end tok/s |
|---|---|---|---|---|
| medium, cap 32 | 4.73 → 4.90 | +3.5% (n.s.) | −0.0% (n.s.) | +13.5% (n.s.) |
| long, cap 32 | 10.10 → 8.43 | **−16.5%** [−21.0, −11.2] | +0.1% (n.s.) | +1.1% (n.s.) |
| medium, cap 12 | 3.70 → 3.30 | −10.8% (n.s.) | **+58.4%** [+11.4, +126.3] (worse) | −16.9% (n.s.) |
| long, cap 12 | 8.53 → 7.80 | **−8.6%** [−10.1, −7.1] | −2.8% (n.s.) | −7.5% (n.s.) |

- **Compute:** the kernel does what it should on the long prompt, 9–17% less expert compute.
- **TTFT:** too small a slice of TTFT to show. The one sig-worse cell, medium cap 12, comes from the loading side: hold time 16–31 s vs 9–17 s, while compute was lower in the same runs. The kernel doesn't touch loading, so I read that cell as I/O noise, but it is reported as measured.
- **Verdict:** not worth enabling on this machine. On a machine where loading is cheap, for example cap = 128 or a fast disk, compute would dominate prefill and this is the lever to re-measure.

## 7. Porting to GLM-5.3-Flash (`c/glm53.c`)

**Prefill.** `ffn_layer_ex` already builds the chunk's expert union and runs each expert's tokens as one batch. Three pieces of this work carry over:

1. **Residents first.** Partition `union_ids` into the experts `slot_find` already holds and the rest, before the `for (base …; base += block)` loop. Today a resident needed in a late block can be evicted by an earlier block's misses and read again.
2. **A fixed-order combine.** glm53 adds each expert's rows into `out` in block order (`dst[d] += scale * src[d]` inside the block loop). Reordering the blocks would change the float sum, so the results must go to a per-(token, k) buffer and be added in the *current* union order (or in rank order, which is then a deliberate numerics change). This is the `xf_moe_combine` device; the buffer is tokens × top-k × hidden floats.
3. **A larger chunk.** §6.1 measured `GLM53_PREFILL_CHUNK`'s default of 128 tokens at 1.8× the bytes of whole-prompt planning here. With (1) and (2) a larger chunk costs only the output buffer, and the chunk also bounds the dense chain's memory (`g53c_prefill_rows`), so the default should be re-measured there.

ORDER=last (§6.2) carries over unchanged. glm53 has no hold/busy refcount and no PILOT, so the wave bookkeeping is simpler: its `expert_block_read` already reserves victims by clock.

**Loader.** glm53 reads straight into slot memory it owns, without a repack or a bounce buffer, and makes one `pread` when the six pieces are contiguous. qwen36's second round trip for the scales (§2.3) does not exist there when `contig` holds. It is worth checking `ref->contig` on the real GLM-5.3 container, because convert scripts that write every scale block first, as this Qwen container does, would make it false. The slot arena is not worth porting (§5.2). The host-paging finding applies to any engine on this WSL setup, glm53 included: its slot budget should leave the *host* room, not only the guest.

## 8. Correctness verification

| check | result |
|---|---|
| Last-token logits (`DUMP=`, sha256) vs the frozen original, all arms of all five sessions | **byte-identical** in all 176 cold runs (6 cells; waves, arena, both, grouped, ORDER=last, every planning size) |
| Final binary with every flag off vs the frozen original | byte-identical logits and text in all 6 cells (`ab2/flagoff`, `qwen36.v3`). `v4`'s only change on the flag-off path is the `[timers] prefill cache:` stderr line (printed only under `COLI_TIMERS=1`); its token-path arm (`order/token`) is byte-identical too |
| Generated text | identical in every run (after the parser fix below) |
| Determinism | every cell of every arm gave one output across its repetitions |
| Cache decisions | with PILOT off: misses identical across repetitions within each arm; arena and grouped make the same decisions as A (identical misses) |
| Unit test (`c/tests/test_qwen36_cache_index`) | passes: 13 waves configurations (grouped, ORDER=last, cap < top-k, headroom, 5/64-token blocks, serial and batched loads) bit-identical to the token path; every routed pair computed exactly once; no expert read twice per layer pass; hits+misses = routed pairs; no slot left held; ORDER=last leaves the final token's experts resident |

**A harness bug found and fixed on the way.** In the `order/` session, `check_correctness.py` first reported 18 text failures. In every case the logits were identical, but the captured text was empty. v4's new `[timers] prefill cache:` line prints between `Text :` and the streamed text, and the text regex ends its capture at the first `[timers]`. `parse_cli_log` now drops that line before matching, and `order/reparse.py` re-parsed the 42 rows from their raw logs. All 42 now match.

## 9. Limitations and next steps

**Limitations**
- **The machine.** The host is short of memory during every run (median ~1.1 GB free), and §2.3 shows that this, rather than the engine, sets the per-miss cost. Absolute times drift by up to a third between sessions for the same configuration (47 vs 63 s, §4). Every claim here is relative and within one interleaved session.
- **Repetitions.** Three per cell, enough for TTFT and bytes, not for decode tok/s: decode CIs span ±50%.
- **Scope.**
  - PILOT stayed 0 everywhere and warm (serve) mode was not measured. The waves path supports PILOT (headroom 1, held slots are never evicted), but its effect there is unmeasured.
  - Only the `expert_ffn` path has waves; the int8-unpack, CUDA and Vulkan tier paths keep the token path.
  - Raw logs and logit dumps stay local (gitignored); `runs.jsonl`/`results.json` and the comparisons are in the kit.

**Next steps, by evidence**
1. ~~Make ORDER=last the waves default~~ (done, §6.2). Then consider waves on by default. It reads 54–88% fewer bytes on any prompt over ~100 tokens with byte-identical output.
2. **Port residents-first waves plus a fixed-order combine to `glm53.c`, then re-measure `GLM53_PREFILL_CHUNK`** (§7).
3. **Fix the environment, not the engine, for the per-miss cost.** Give WSL less than the host can back (for example 8 GB with `--cap 12`) and repeat a decode A/B: that is where the 5–6 ms per miss that is not I/O should go away.
4. **The scale read.** Overlapping the scale `pread` with the weight `pread` (a `WILLNEED` on the scale range, or both in one batch) saves one round trip per miss. Alternatively, a container that stores each expert's scales next to its weights makes it one read.

## 10. Reproduction

All from `benchmarks/expert_cache_research/`, model at `~/colibri-models/qwen3-coder-30b`:

```bash
make -C ../../c qwen36 && cp ../../c/qwen36 bin/qwen36.v4
make -C ../../c tests/test_qwen36_cache_index && ../../c/tests/test_qwen36_cache_index
phase0/run_profile.sh && phase0/run_smoke.sh      # §2: fault profile (COLI_Q36_FAULT_PROF=1)
phase0/host_ws_sample.sh                          # §2.3: host-side view of one run
bash -c "$(grep -v '^#' ab2/commands.txt)"        # §5 (v2 = this tree minus GROUPED/ORDER/timers)
bash -c "$(grep -v '^#' ab2/commands_followup.txt)"   # §6.1, §6.3, §8
bash -c "$(grep -v '^#' order/commands.txt)"      # §6.2
for d in ab2/* chunk/* grouped/* order/*; do [ -f $d/runs.jsonl ] && python3 summarize.py $d; done
python3 check_correctness.py ab2/baseline ab2/{flagoff,v3waves,qd8,arena,waves,both} chunk/* grouped/{gwaves,grouped} order/{first,last,token}
python3 compare.py ab2/qd8 ab2/waves --out ab2/comparison_waves.md      # and _arena, _both; grouped/, order/
python3 ab2/report_tables.py ab2/comparison_*.md order/comparison.md grouped/comparison.md
```

**Flags (all off by default, all in `c/qwen36.c`):** `COLI_Q36_PREFILL_WAVES=1` (+ `_CHUNK=N`, `_HEADROOM=H`, `_ORDER=first`; last-use order is the default), `COLI_Q36_PREFILL_GROUPED=1` (needs waves), `COLI_Q36_SLOT_ARENA=1`, `COLI_Q36_FAULT_PROF=1` (diagnostic).
