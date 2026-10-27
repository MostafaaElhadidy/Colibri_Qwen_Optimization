# Expert-cache work: status (read this first)

Engine `c/qwen36.c`, model Qwen3-Coder-30B-A3B int4 on WSL2 (12 GB). It stands in for GLM-5.3-Flash (`c/glm53.c`), which does not fit this machine. Rules and commands: `CLAUDE.md`. Reports: [part 1](expert_cache_research.md), [part 2](expert_cache_research_2.md), and for a non-specialist [colibri_optimization_results.pdf](colibri_optimization_results.pdf). Kit and raw data: `benchmarks/expert_cache_research/`.

## Done
1. **Parallel miss loading** (part 1). A layer's cache misses are decided in one locked pass (the same decisions as before) and read 8 at a time. TTFT −39…−68%, end-to-end tok/s +59…+84% vs the original.
2. **Phase 0: the "page faults per miss"** (part 2 §2). They were not per miss: 2.0 M happen at model load, 1.0 M are the first touch of the slot memory, and decode has 0. The real per-miss cost is (a) a second I/O for the scales, which the container stores away from the weights, and (b) the **Windows host paging the VM out**: the host had 4 MB free, the VM's working set was under 1 GB while the guest held 6 GB. That is not fixable in the engine.
3. **Expert-major prefill, "waves"** (part 2 §3, §5.1). Route the whole chunk first, then load each distinct expert once, cached ones first, in waves of at most `cap` slots. Every (token, k) output is kept and summed per token in rank order, so the result is byte-identical. TTFT −49…−92% and bytes read −54…−88% on medium and long prompts, vs MISS_QD=8.
4. **Studies** (part 2 §6):
   - planning size: bigger is strictly better (32 tokens → whole prompt: 86 → 26 GB);
   - wave order: last-use order gives exactly the original path's decode cache, and is now the default;
   - an **exact** 4-token grouped kernel cuts expert compute 9–17%, but TTFT is n.s.
5. **Correctness.** Logits are byte-identical to the frozen original (`bin/qwen36.baseline`, commit `e0db083c`) in every run of every arm (176 + 3 cold runs, 0 failures). Unit test: `make -C c tests/test_qwen36_cache_index && c/tests/test_qwen36_cache_index`.

## Flags (all in `c/qwen36.c`, all OFF unless set)
| flag | default | what it does |
|---|---|---|
| `COLI_Q36_MISS_QD=N` | 0 (off) | read a layer's misses N at a time; 8 is the measured setting |
| `COLI_Q36_PREFILL_WAVES=1` | off | expert-major prefill when a chunk's S×8 pairs exceed the cache |
| `COLI_Q36_PREFILL_WAVES_CHUNK=N` | 0 = whole chunk | tokens planned at once (smaller = less memory, more reads) |
| `COLI_Q36_PREFILL_WAVES_HEADROOM=H` | 1 under PILOT, else 0 | slots kept out of a wave |
| `COLI_Q36_PREFILL_WAVES_ORDER=first` | last | `first` restores first-seen order (the order of the main matrix) |
| `COLI_Q36_PREFILL_GROUPED=1` | off | waves compute 4 tokens per weight pass; exact, same bits |
| `COLI_Q36_SLOT_ARENA=1` | off | slot memory in 2 MiB pages from one mapping per layer |
| `COLI_Q36_FAULT_PROF=1` | off | diagnostic: per-step faults/µs of a miss, faults per phase |

## Headline (cold, ABBA, 3 reps, bootstrap 95% CI; part 2 §5.1)
- 514-token prompt, cap 12: TTFT **376 → 30 s** (−92% [−94, −90]), GB read 283 → 35, end-to-end tok/s +571%.
- 514-token prompt, cap 32: TTFT **221 → 47 s** (−79%), GB read 141 → 26, end-to-end tok/s +186%.
- 161-token prompt: TTFT −67% (cap 32) / −85% (cap 12). 24-token prompt: −49% / −63%.
- Comparison tables: `benchmarks/expert_cache_research/ab2/comparison_*.md`, `chunk/`, `grouped/comparison.md`, `order/comparison.md`.

## Did not work / not significant
- `COLI_Q36_SLOT_ARENA`: faults −11…−34%, but 17 of 18 timing cells n.s.; +1–3% RSS. Leave it off.
- Grouped kernel: compute −9…−17% (long prompt), TTFT n.s.; one cell (medium, cap 12) sig worse, from I/O noise.
- Decode tok/s: n.s. almost everywhere (3 reps, ±50% host noise). One waves cell −28% [−48, −1] (medium, cap 32), explained by first-seen order; last-use order removes the miss gap, but its own timing A/B is mixed.
- 26 of 176 runs had 0.03–4.3 MB (of 19 GB) still in page cache after eviction; the rule is exactly 0. Cause unknown; negligible impact.
- Part 1: PILOT (the existing predictive prefetch) helped only some cells and hurt warm TTFT.

## Open questions
- Is waves safe as the default? Untested: PILOT=1, warm/serve mode, and the CUDA/Vulkan/int8 paths (they keep the token path).
- What decode does on a host that is *not* short of RAM (for example WSL `memory=8GB` with `--cap 12`)?
- Why a few MB survive `posix_fadvise(DONTNEED)` in some cold runs.

## Next steps (in order)
1. **Port to GLM-5.3 (`c/glm53.c`, `ffn_layer_ex`).** It already reads misses in parallel and prefills expert-major over a 128-token window (`GLM53_PREFILL_CHUNK`), in first-seen order, summing in block order. Add three things:
   - cached experts first;
   - a per-(token, k) buffer with a fixed-order sum, to stay exact;
   - a larger window.

   Check `ERef.contig` on the real container (one read per expert or six). Measure on the cloud instance, since GLM-5.3 does not fit here.
2. Fix the environment, then re-measure decode with WSL memory below what the host can back.
3. Overlap or merge the scale read with the weight read (one I/O per miss instead of two).
4. More reps for decode (≥ 6), then decide on waves on by default.
