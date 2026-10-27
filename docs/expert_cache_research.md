# Expert caching and prefetching in colibri: research report

**Model:** Qwen3-Coder-30B-A3B (colibri int4 gs64) on the `qwen36` engine.
**Machine:** i9-14900HX, RTX 4060 Laptop 8 GB, Windows 11 + WSL2 with 12 GB RAM.
**Baseline commit:** `e0db083cdc9e563e0766cc6fc661ef23c32298e0`. Branch `feature/smarter-expert-cache`.
**Reproduction kit and raw data:** [`benchmarks/expert_cache_research/`](../benchmarks/expert_cache_research/README.md).

## Summary

- **Bottleneck (measured).** On this machine Qwen3-Coder-30B is limited by expert loading, not compute. Fetching experts takes **81–94% of every decode step**, and prefill at small caches re-reads tens of thousands of experts (up to 283 GB for a 514-token prompt at cap 12). Each miss was fetched one at a time at queue depth 1, while the disk delivers ~4× more at depth 4–8.
- **Change.** `COLI_Q36_MISS_QD=N` (off by default) makes the cache decide a layer's hits and misses in one locked pass, exactly as the original would, and then reads the misses N at a time. It is about 120 lines in `c/qwen36.c` plus a test.
- **Result** (cold, interleaved, 3 reps, N = 8):
  - **TTFT −39% to −68%** (1.6–3.1× faster) and **end-to-end tok/s +59% to +84%**, significant in all four cells;
  - decode-only tok/s +18% to +66%, significant in one of four cells;
  - hit rate and bytes read unchanged; +10–20 MB RAM; no VRAM.
- **Correctness.** Logits are byte-identical to the original in every run, with the flag on or off.
- **Not explained yet.** The reused read buffers did not remove the ~3 M page faults per run; that per-miss overhead is the next target (§9).


## 1. Architecture: where a routed expert comes from

Qwen3-Coder-30B-A3B is a `qwen3_moe` model with 48 layers, all full attention. Each layer has 128 routed experts with top-8 routing and `moe_inter` 768; there is no shared expert. colibri runs it on the **`qwen36` engine** (`c/qwen36.c`), the Qwen3.5/3.6 engine that gained Qwen3-MoE support in #1828, not on `colibri.c`.

Each expert is gate|up|down, int4 with group size 64, stored as one `merged_weight` plus its scales. One expert is **2.53 MiB** on disk (2,359,296 B of int4 plus 294,912 B of f32 scales), so each layer holds 324 MiB of experts and the whole model 15.2 GiB. The dense trunk (attention, router, embeddings and head) is resident, quantized to int8 while loading.

A decode step goes down this path:

```
generate / serve turn
  └─ step() / q36_step_rows()                      c/qwen36.c:4230 / :4405
       ├─ memset(is_queued)  ← cancels last token's PILOT requests (lazily)
       └─ layers_forward_range()                   c/qwen36.c:4132
            for each layer i:
              ├─ attention (dense, resident)
              ├─ PILOT=n: pilot_prefetch(i+1..i+n)  router of the NEXT layer on this layer's
              │                                     hidden state → ring → 1 worker thread
              └─ moe()                              router top-8 (softmax, normalised)
                   └─ moe_xf_run()                  c/qwen36.c:3191   (expert_ffn kernel)
                        for each routed expert, in order:
                          expert_hold()             c/qwen36.c:2890
                            └─ expert_fetch()       c/qwen36.c:2830
                                 hit  → LRU touch, hold, return
                                 miss → slot_victim() (LRU, skip busy/loading/pinned)
                                        load_expert_merged()  pread + int4 repack
                                        (st.h: pread, then posix_fadvise DONTNEED)
                        xf_moe_add()        (compute all 8 once they are resident)
```

Three properties of this path drive everything that follows:

1. **The expert cache is the only cache.** `st.h` drops every expert's pages from the OS page cache straight after reading them (`POSIX_FADV_DONTNEED`, `c/st.h:1091,1192`). This keeps RSS at "dense + cache" rather than "whole model". It also means a miss always goes to storage, and the OS page cache never serves as a second cache level.
2. **Demand misses are serial.** `moe_xf_run` fetches the routed experts one after another, and each miss is one blocking `pread` of 2.53 MiB, at queue depth 1.
3. **Placement never changes routing.** Every mechanism below except `CACHE_ROUTE` only decides where an expert's bytes live. The router's top-8 and their weights are computed the same way regardless, which is what keeps output bit-identical.

## 2. What already exists: the caching and prefetching inventory

### 2.1 Qwen path (`c/qwen36.c`), the engine that ran every measurement here

| mechanism | code | behaviour | default |
|---|---|---|---|
| Per-layer expert LRU | `Slot`/`LCache` :851, `expert_fetch` :2830, `slot_victim` :1051, index `slot_by_expert` :999-1031 | `cap` slots per layer. The victim is the least recently used slot that is not busy, not loading and not pinned; pinned slots go only as a last resort. An O(1) expert→slot index validates both sides, so stale bookkeeping can only cause a miss, never a wrong hit. | on, `cap` = argv[1] (0 = from RAM) |
| Hold/busy refcount | `slot_hold/release` :1037 | A slot a kernel is reading is never evicted. | on |
| Cache sizing | `qwen36_cap_for_ram` :2459, :989 | One static cap for every layer, chosen once at start (`--cap`, `RAM_GB`). | auto |
| **PILOT predictive prefetch** | `pilot_prefetch` :4482, `pilot_worker` :4469, `pilot_realload` :4445, call sites :4150-4161 | Runs layer L+1's router (int8 gate) on layer L's post-attention hidden state, blended with an EMA of past logits (`SMOOTH`=0.3). It takes the top candidates until their softmax mass reaches `CONF_LIMIT`=0.92 (at least top-k, at most top-k×`WIDE`) and queues the non-resident ones into a 4096-entry ring that **one** worker thread drains with plain LRU eviction. `PILOT=2/3` also looks 2–3 layers ahead. Decode only (S ≤ 8). | **off** (`PILOT=0`) |
| Prefetch cancellation | `memset(is_queued)` :4234, :4407; check in `pilot_realload` :4448 | At each token's start every queued request is invalidated. A queued entry is skipped when it reaches the worker; one that has already started a read runs to completion. | with PILOT |
| Hot-expert pinning | `pin_hot_experts` :2892 | After `WARMUP` tokens (default 5), pins the top-`HOT` experts per layer by routing frequency, once, and queues the missing ones through PILOT. | off (`HOT=0`) |
| Prompt-resident pinning | `COLIBRI_RESIDENT` :2946 | Pins the experts the prompt routed to, up to the cap. Meant to feed a GPU tier. | off |
| Cache-aware routing | `CACHE_ROUTE` :3226 | Lets a resident expert stand in for a non-resident one inside the top-M window. **Lossy: it changes routing**, so it is outside this study's rules. | off |
| CUDA VRAM expert tier | `c/qwen36_tier.c`, `tier_offer_slot` :1287, `QT_PREFILL_REPLAN` :2786 | An LFRU-managed VRAM tier with async uploads and a prefill-time re-plan. **Requires `cap == n_experts`** (every expert also in RAM) outside the fp8-stream mode. | off (`COLI_CUDA=1`) |
| Vulkan routed-expert tier | `c/vk_tier.c`, `vkt_ram_first` | A VRAM tier that can run with cap < E (RAM evicts device-resident experts first). | off |

### 2.2 GLM-5.3-Flash path (`c/glm53.c`)

| mechanism | code | behaviour |
|---|---|---|
| Per-layer LRU | `expert_cache_init` :1537, `slot_find` :1599, `expert_slot` :1977 | The budget is sized from RAM after leaving the model room in the page cache (`GLM53_EXPERT_GB`). Lookup is a linear scan; the victim is plain LRU. |
| Parallel block read | `expert_block_read` :2014 | A layer's missing experts get slots up front and are read **in parallel**. |
| Multi-SSD mirror | :1611 | Picks a replica deterministically per expert. |
| Prefetch / pinning / PILOT | none | GLM-5.3 has **no predictive prefetch**. |

GLM-5.3-Flash is 321B parameters, a 195 GB container with about 18 GB of dense BF16. It cannot run in 12 GB of RAM plus 8 GB of VRAM, so it was analysed from code only and not downloaded.

### 2.3 Prior art inside colibri (`c/colibri.c`, the GLM-5.2 engine)

The most mature versions of these ideas live here: `PILOT_REAL` (real loads into layer L+1's cache), `PILOT_TWO` (two-step lookahead), `PILOT_WORKERS` (several prefetch threads), io_uring batching (`URING`), the WILLNEED cross-layer hint (`PREFETCH`), and **`PILOT_EVICT_GUARD`**. That guard lets a speculative load evict a resident expert only if the predicted expert is historically hotter. None of these were ported to `qwen36`.

### 2.4 Mapping the four requested directions onto what exists

| direction | already in qwen36 | already elsewhere in colibri | not implemented anywhere |
|---|---|---|---|
| A. Cost-aware replacement | plain LRU + pin | LFRU in the CUDA tier; `PILOT_EVICT_GUARD` in colibri.c | reuse × reload-cost scoring for RAM slots |
| B. Router-predictive prefetch | PILOT (1 worker, off by default) | PILOT_REAL/TWO/WORKERS, URING (colibri.c) | in-flight dedup between PILOT and demand misses in qwen36 |
| C. Adaptive sizing / hot placement | static cap, HOT, RESIDENT | GLM-5.3 page-cache-aware budget | per-layer cap rebalancing at runtime |
| D. CPU/GPU residency | CUDA/Vulkan tiers (blocked here) | CUDA tier LFRU + re-plan | — (the hardware blocks it, see §3) |

## 3. Environment and what it allows

| item | value | consequence |
|---|---|---|
| CPU | i9-14900HX; WSL2 exposes 16 cores / 32 threads | `OMP_NUM_THREADS=16` |
| RAM | 16 GB host, **12 GB for WSL** (`.wslconfig`) | every expert in RAM (`--cap 128`) needs 15–17 GB, so it **cannot fit** |
| GPU | RTX 4060 Laptop, 8 GB, driver 610.62, CUDA 12.6 | the qwen36 CUDA expert tier requires `cap == 128` (`qt_init`), so it is **unusable** for this model on this machine; every run is CPU expert streaming (VRAM above idle ≈ 0 MiB in every run) |
| model | `Justvugg/Qwen3-Coder-30B-A3B-colibri-int4`: int4 gs64 experts, int8 dense trunk, 19 GB in 49 shards, sha256 inventory in `env/model_inventory.sha256` | compatible with `qwen36` (Qwen3-MoE support from #1828); loads in about 20 s; 2.96 GB RSS after load |
| model location | read-only ext4 copy at `~/colibri-models/qwen3-coder-30b`, on a WSL VHDX on the laptop NVMe | the Windows original and the Windows colibri v2.0.0 install were never written to |
| disk | 906 GB free | — |

**Storage behaves differently here than on bare metal.** `env/expert_iobench.json` read random whole experts (2.53 MiB each) across all shards, buffered, with `DONTNEED` after each read, just as the engine does:

| queue depth | GB/s | experts/s | p50 latency |
|---|---|---|---|
| 1 | 0.93 | 350 | 2.7 ms |
| 2 | 1.73 | 652 | 2.9 ms |
| 4 | 2.59 | 977 | 3.8 ms |
| 8 | 3.72 | 1,402 | 5.2 ms |
| 16 | 4.25 | 1,602 | 8.3 ms |

QD1 leaves about 4× the throughput unused. The VHDX also sits behind the Windows host's own cache and disk activity. A pass right after the 19 GB copy saw 14–28 ms per expert, and the per-run **storage canary** (16 random experts at QD1, read just before each run) ranged from **5.2 to 47.7 ms (median 14.0 ms)** during the baseline. Absolute numbers on this machine therefore carry host noise. Comparisons are only valid when the arms are interleaved in the same session, and the A/B in §7 was run that way.

**"Cold" is verified, not assumed.** Before every cold run all shards are evicted with `posix_fadvise(DONTNEED)`, and `mincore` confirmed **0 bytes resident** in all 36 cold runs. This proves the guest page cache was empty; the Windows host cache of the VHDX cannot be controlled from inside WSL.

**The gateway prompt template does not fit this model.** `openai_server.render_chat_for_arch` resolves Qwen3-Coder to the `qwen36` family and appends an empty `<think>\n\n</think>` block. Qwen3-Coder has no thinking mode, and it answers that prompt with an immediate end of turn (0 tokens). Both benchmark modes therefore send the same plain ChatML text. This is worth a separate issue upstream.


## 4. Baseline (original code, commit `e0db083c`)

The matrix was 108 runs with no failures. It covered 3 prompts (24 / 161 / 514 tokens) × `--cap` 32 (6.2 GB RSS) and 12 (3.8 GB RSS, simulating a small machine) × `PILOT` 0/1 × 3 reps, in two modes:
- **cold**: fresh process, page cache evicted;
- **warm**: one serve process, each prompt sent twice.

Greedy decoding, `N_NEW=32`, `COLI_LOOKUP=0`, `COLI_KV_PREFIX=0`. Raw rows are in `benchmarks/expert_cache_research/baseline/runs.jsonl`, statistics in `results.json`, and the timers of every run in `profiling.log`. Greedy output was identical across all 3 reps in all 36 cells.

**Cold, mean ± stdev of 3 runs**

| prompt | cap | PILOT | TTFT (s) | decode tok/s | hit % | decode expert fetch (ms/tok) | compute (ms/tok) | fetch share | bytes read (GB) |
|---|---|---|---|---|---|---|---|---|---|
| short | 32 | 0 | 47.6 ± 7.3 | 0.54 ± 0.03 | 68.6 | 1,707 | 78 | 92% | 21.0 |
| short | 32 | 1 | 58.7 ± 21.0 | 0.63 ± 0.04 | 71.2 | 1,439 | 76 | 90% | 23.6 |
| medium | 32 | 0 | 144.1 ± 13.6 | 1.32 ± 0.55 | 74.4 | 717 | 64 | 85% | 50.5 |
| medium | 32 | 1 | 138.7 ± 15.7 | 0.99 ± 0.31 | 74.7 | 874 | 91 | 81% | 52.2 |
| long | 32 | 0 | 308.4 ± 50.5 | 0.32 ± 0.06 | 72.9 | 2,847 | 136 | 90% | 140.7 |
| long | 32 | 1 | 291.9 ± 28.8 | 0.67 ± 0.16 | 73.0 | 1,258 | 131 | 81% | 142.6 |
| short | 12 | 0 | 44.5 ± 8.4 | 0.70 ± 0.20 | 44.8 | 1,395 | 39 | 93% | 33.0 |
| short | 12 | 1 | 49.0 ± 7.7 | 1.36 ± 0.20 | 52.9 | 669 | 27 | 90% | 37.5 |
| medium | 12 | 0 | 149.4 ± 8.5 | 0.81 ± 0.19 | 45.1 | 1,166 | 42 | 92% | 101.7 |
| medium | 12 | 1 | 154.5 ± 15.5 | 0.76 ± 0.22 | 47.2 | 1,249 | 38 | 91% | 105.3 |
| long | 12 | 0 | 483.0 ± 32.3 | 0.40 ± 0.18 | 44.2 | 2,666 | 54 | 94% | 282.9 |
| long | 12 | 1 | 491.8 ± 47.7 | 0.44 ± 0.15 | 44.9 | 2,312 | 60 | 92% | 287.0 |

Peak VRAM above idle was ≈ 0 MiB in every cell (CPU build, tier off).

**What the baseline says**

1. **Decode is almost entirely expert fetch.** Fetching experts takes **81–94% of the decode step** in every cell; the expert matmul is 27–136 ms of a 743–3,146 ms step. Compute is not the bottleneck. Getting experts into RAM is.
2. **A miss costs far more than the read.** In a controlled short run with the host quiet, each miss cost about **11 ms** in the engine (87.5 decode misses per token, 991 ms of fetch per token). The same read+repack sequence in a standalone process costs 3.2–3.7 ms, and the device needs 2.7–5 ms at QD1. Thread sampling showed the decode thread was **87% running and only 12–13% blocked in `pread`**, and the process took ~3.0 M minor page faults (about 650 per miss). Isolated tests ruled out OpenMP spinning (+0.5 ms) and the per-miss `malloc` (removing it did not change the fault count, §7). The remaining per-miss overhead is real, but its source is not fully attributed.
3. **Prefill is the worst case for TTFT.** At cap 32 a prompt chunk needs S × 8 expert slots, so `moe_xf_run` falls back to one token at a time. The 514-token prompt re-reads **~57 k experts (141 GB)** at cap 32 and **~117 k experts (283 GB)** at cap 12 before the first token. That is why TTFT reaches 300–480 s, and why a warm repeat of the long prompt is no faster than the first request (the prefill cycles the whole LRU).
4. **The warm upper bound is large where the LRU survives.** The short prompt repeated in the same process drops TTFT from 56 s to 20 s at cap 32 (49 s → 19 s at cap 12).
5. **PILOT, the existing predictive prefetch, is not a reliable win here.** It reads 1–14% more bytes in every cell. It helps decode in a few cold cells (short and long at cap 32, short at cap 12) and hurts in others (medium at cap 32). In warm sessions it makes TTFT clearly worse: medium at cap 32 goes from 106 to 183 s, medium at cap 12 from 144 to 186 s. That is consistent with queued speculative loads from one request still running during the next request's prefill, since PILOT is cancelled only at decode-step boundaries. Its single FIFO worker cannot overlap enough reads to hide a miss, and the spread across reps is wide. This is why the first experiment does not build on PILOT.


## 5. Research comparison

| work | core idea | relation to colibri |
|---|---|---|
| MoE-Infinity, Xue et al., [arXiv:2401.14361](https://arxiv.org/abs/2401.14361) | Traces activation per request or sequence; uses the trace to drive prefetching and caching of offloaded experts | colibri's `.coli_usage` history and the CUDA tier's LFRU heat are the same idea at the tier level; the RAM LRU does not use a trace |
| SpecPrefetch, [arXiv:2607.24787](https://arxiv.org/pdf/2607.24787) | A small learned predictor, fused with LoRA, for layer l+1's top-K; the prefetch budget adapts to the overlap window between compute and transfer; keeps the router's decisions; reports up to 20% decode speed-up on a mobile SoC | PILOT already predicts l+1 by reusing the next layer's real router on the current hidden state, a training-free counterpart. The budget-to-overlap idea is what PILOT lacks: it queues up to `WIDE`×k candidates with no regard to how much I/O time is left. *(Verified from the abstract and model card only.)* |
| APEX, Lin et al., [arXiv:2411.17651](https://arxiv.org/abs/2411.17651) | A simulator that searches parallel execution plans for LLM serving (dynamism-aware, iteration-level batching) | Not an expert-cache method: it plans multi-GPU parallelism. Useful only as a methodology for choosing placement offline. *(A different "APEX", [arXiv:2506.03296](https://arxiv.org/abs/2506.03296), schedules hybrid CPU-GPU decoding for dense models.)* |
| ProMoE, [arXiv:2410.22134](https://arxiv.org/abs/2410.22134) | Proactive caching: predicts and prefetches experts ahead of use, scored by "GoodPred" | The same family as PILOT |
| HOBBIT, [arXiv:2411.01433](https://arxiv.org/abs/2411.01433) | Swaps less critical missed experts for low-precision copies | Lossy; outside this study's rules |
| Fiddler, [arXiv:2402.07033](https://arxiv.org/abs/2402.07033) | Computes missed experts on the CPU instead of copying them over PCIe | colibri's CUDA tier already does this (`qt_take` + CPU misses) |
| HybriMoE, [arXiv:2504.05897](https://arxiv.org/abs/2504.05897) | CPU-GPU intra-layer scheduling, inter-layer prefetch, score-based caching | Direction D; blocked on this machine |
| SpecMD, [arXiv:2602.03921](https://arxiv.org/abs/2602.03921) | Expert accesses break LRU/LFU locality assumptions; proposes "Least-Stale" eviction | Supports direction A |

## 6. The first experiment: parallel demand-miss loading (`COLI_Q36_MISS_QD=N`)

### Why this one

The candidates were the four directions in §2.4 and §5. The baseline points at one bottleneck: **a layer's expert misses are fetched one after another, at queue depth 1, by the thread that then sits idle waiting for them**. The other directions either do not touch that path or cannot work on this machine:

- **A. Cost-aware replacement** changes which experts get evicted. The hit rate is already 69–75% at cap 32, and the time goes into each miss rather than their number.
- **B. Smarter PILOT** speculates on misses. Its measured effect is mixed and it already reads 1–14% extra bytes. It is a good second step once a miss itself is cheap.
- **C. Adaptive sizing** needs more RAM than 12 GB has to give.
- **D. CPU/GPU residency** is blocked: the tier requires every expert to be in RAM.

### Algorithm

`expert_hold_batch` (`c/qwen36.c`) replaces the per-expert `expert_hold` loop in `moe_xf_run` when `COLI_Q36_MISS_QD=N` (N ≥ 2):

```
under g_pilot_mx, for each routed (token, expert) pair of this run, in order:
    resident                      -> hit: LRU touch, hold
    reserved earlier in this pass -> hit (what the serial path sees once that load publishes)
    otherwise                     -> miss: victim = slot_victim()  (same LRU rule: not busy,
                                     not loading, unpinned first), hide it, hold it, LRU touch
    no victim at all              -> stop; the rest goes through expert_hold (waits, as before)
unlock
read the reserved misses N at a time (OpenMP), each into its thread's reused buffer
under g_pilot_mx: publish all of them (index + pinned flag + t_disk)
```

**Same decisions as the original.** The pass makes the decisions the serial loop makes, in the same order, against the same state. A hidden, held slot is excluded from later victim picks exactly like a slot the serial path just loaded and holds. Reservation clocks follow the serial order. The result: with PILOT off, the batched path evicts the same experts, fills the same slots and counts the same hits and misses. The unit test checks this over 500 randomized runs, and the engine smoke run confirms it (hit=10,306 / miss=4,670 in both arms).

**Output is unchanged.** Routing, the experts computed and the kernel's input order are untouched.

**Thread safety.**
- Reservations and publishes happen under the existing `g_pilot_mx`.
- A slot being read is hidden (`eid = -1`) **and** held, so neither another reservation nor the PILOT worker can take it.
- `load_expert_merged` was already called from parallel code (`tier_rebuild_evicted`).

**Prefetch cancellation and eviction.**
- No speculative work is added: everything read was routed and is used.
- PILOT's per-token cancellation is unchanged.
- If PILOT holds every free slot in flight, the batch stops reserving and the remainder waits on the existing path, which waits for a publish and never steals a loading slot.

**Memory.** One reused read buffer per loader thread: N × 2.36 MB (19 MB at N = 8). No VRAM. The scales are read straight into the slot, so the 288 KB bounce buffer per miss is gone too.

**Flag off.** With the flag unset (the default), `moe_xf_run` calls `expert_hold` exactly as before, and `load_expert_merged` keeps its `malloc`/`free`.

**Files.** `c/qwen36.c` (+118/−5) and `c/tests/test_qwen36_cache_index.c` (+94): the batch-vs-serial equivalence test and a concurrency check.

## 7. Before/after: `COLI_Q36_MISS_QD=8` vs. the original

**Protocol.** Two arms in the same session:
- **A**: the frozen original binary (`bin/qwen36.baseline`, sha256 `36ff0d1f…`).
- **B**: the modified binary (`bin/qwen36.optimized`, sha256 `06184142…`) with `COLI_Q36_MISS_QD=8`.

Each run was a fresh cold process: page cache evicted, 0 bytes resident (checked). The arms were interleaved run by run, with their order alternated ABBA by repetition. The model, container, `--cap`, prompts, `N_NEW=32`, greedy decoding, threads and environment were identical; only the flag differs. There were 3 repetitions per cell and 24 timed runs. The storage canary medians were similar in both arms (A 9.4 ms, B 8.6 ms). Exact commands are in `benchmarks/expert_cache_research/env/ab_commands.txt`, raw rows in `ab/{baseline,optimized}/runs.jsonl`, and the full table with bootstrap CIs in [`comparison.md`](../benchmarks/expert_cache_research/comparison.md).

| cell | TTFT A → B (s) | Δ TTFT | end-to-end tok/s A → B | Δ | decode tok/s A → B | Δ |
|---|---|---|---|---|---|---|
| short, cap 32 | 59.8 → 29.3 | **−51%** [−58, −42] | 0.31 → 0.52 | **+66%** [+32, +111] | 0.86 → 1.01 | +18% (n.s.) |
| medium, cap 32 | 131 → 80 | **−39%** [−49, −26] | 0.20 → 0.31 | **+59%** [+25, +96] | 1.03 → 1.61 | +56% (n.s.) |
| short, cap 12 | 52.6 → 17.0 | **−68%** [−82, −37] | 0.46 → 0.85 | **+84%** [+32, +210] | 1.13 → 1.57 | +38% (n.s.) |
| medium, cap 12 | 135 → 75 | **−45%** [−46, −43] | 0.18 → 0.32 | **+80%** [+70, +90] | 0.78 → 1.30 | **+66%** [+23, +124] |

Brackets are the bootstrap 95% CI of the % change; n.s. means the interval includes 0. End-to-end tok/s is the engine's own `Speed:` line: 32 tokens over prefill plus decode.

| other metric | change |
|---|---|
| expert hit rate, misses | **identical** in every run (68.6 / 74.4 / 44.8 / 45.1%); the same decisions, as designed |
| bytes read by the engine | unchanged (−0.1 to −0.4%) |
| decode expert fetch (ms/token) | −27% to −49% (significant only for medium, cap 12) |
| peak RSS | +0.2–0.5% (+10–20 MB: the per-thread read buffers) |
| peak VRAM | 0 MiB above idle in both arms (CPU build) |
| CPU time | user −55% (1,150 → 512 s per run: shorter runs, less OpenMP spin), system +56% (88 → 138 s: page faults and reads now overlap) |

**Reading the result honestly**

- **TTFT is where it pays: 1.6–3.1× faster in every cell.** Prefill at these caps runs one token at a time with 8 experts per run, several of them misses, and those misses now load together.
- **Decode gains are real but smaller and noisier.** At cap 32 a decode token has only ~1.8 misses per layer, so there is little to overlap. The one cell with significant decode gain is the restricted cap 12, which has more misses per layer. The per-token decode rate also swings with the host's disk: the canary ranged 3.7–13.5 ms within the session. Three repetitions cannot resolve a ±50% effect under that noise.
- **The page-fault hypothesis from §4 was wrong.** The reused buffers did not reduce the ~3.0 M minor faults per short run (3.02 M → 3.05 M), so those faults come from elsewhere in the process. The measured gain is the overlap of reads, not removed faults. The fault source is still unexplained and is the next thing to profile (needs `perf`, which this WSL image lacks).

## 8. Correctness verification

| check | result |
|---|---|
| Last-token logits (raw float32 from `DUMP=`), original vs. flag on | **byte-identical** (sha256 equal) in all 4 cells × 3 reps |
| New binary with the flag **off** vs. original | **byte-identical** logits and text in all 4 cells |
| Both arms vs. the 108-run baseline from §4 | identical |
| Determinism of the original | every one of the 36 baseline cells gave one output across 3 reps |
| Generated text | identical, compared after removing engine notes that land at timing-dependent places in stderr |
| Cache decisions | hit/miss counts identical between arms in every run |
| Unit test (`tests/test_qwen36_cache_index`) | passes: over 500 randomized runs (1,597 hits, 418 misses) the batch matched the serial path's slot choice, LRU order and counters exactly; 4 reads in flight at qd=4 |
| ThreadSanitizer (unit test, `-fsanitize=thread`) | 25 reports, **all** pairs of one access inside the OpenMP loop body and one in the main thread before the loop's fork or after its join (slot setup, `load_t`, `cache_publish`). This is the known libgomp false positive (libgomp is not TSan-instrumented, so its fork/join barriers are invisible). **No worker-against-worker access was reported.** An LLVM/Archer build would be needed to make this check clean. |

The model is unchanged and routing is unchanged, so perplexity and quality are those of the original. The teacher-forced comparison against BF16 in the model card still applies.

## 9. Limitations and next steps

**Limitations of this study**

- **Machine.** A laptop under WSL2 with 12 GB and a VHDX in front of the NVMe. Host disk activity moved the per-expert read cost from 2.7 to 47.7 ms. Gains are relative and interleaved; absolute tok/s will differ on bare-metal Linux or native Windows, likely in the engine's favour.
- **Workload.** Prompts were 24–514 tokens with 32 new tokens. The 1,783-token prompt is kept in `prompts/long_full.txt` but was not run: one cold run takes ~40 min at cap 32. The A/B covered the cold, `PILOT=0` cells. Warm sessions, the 514-token prompt and `PILOT=1` were measured for the original only.
- **Repetitions.** Three repetitions per cell, as specified. That is enough for TTFT and end-to-end throughput, not for decode-only rates under this noise.
- **Untested here.** GLM-5.3-Flash (195 GB) and the GPU tier could not run on this machine.
- **Unmeasured paths.** The flag only covers the `expert_ffn` (planar int4) path, the default for this container. The int8-unpack path (`QWEN_EXPERT_KERNEL=0`) and the CUDA/Vulkan tier paths still use the serial loop.

**Next steps, in order of the evidence**

1. **Find the ~6 ms of per-miss overhead** that is not the read: the 3 M minor faults. A `perf` profile on bare-metal Linux is the right tool.
2. **Overlap misses across layers.** Decode has too few misses per layer to overlap. The next lever is to start layer L+1's predicted misses during layer L (a PILOT that reuses this batched loader and its N-way reads instead of one FIFO worker), with cancellation when the token's route diverges.
3. **Prefill.** At caps below S×8 prefill runs token by token and re-reads ~57 k experts for 514 tokens. Grouping prompt tokens by shared experts, which changes the run shape but not the math, would cut both bytes read and TTFT.
4. **Port to GLM-5.3-Flash.** `glm53.c` already reads a layer's misses in parallel but has no prefetch at all, so step 2 is the transferable part.


