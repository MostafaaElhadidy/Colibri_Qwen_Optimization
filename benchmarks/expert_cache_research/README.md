# Expert-cache research: reproducible benchmark kit

This directory is the benchmark harness and raw data behind
[`docs/expert_cache_research.md`](../../docs/expert_cache_research.md). It measures
colibri's `qwen36` engine running Qwen3-Coder-30B-A3B (colibri int4 gs64) with the
routed experts streamed from disk through the per-layer LRU.

Everything here is plain Python 3 and bash, plus one 40-line C helper. Nothing is installed.

## Files

| file | what it does |
|---|---|
| `prepare_model.sh` | Copies the checkpoint to WSL ext4 (rsync; the source is only read). Checks shard sizes against `.colibri-download.json` and writes `env/model_inventory.sha256`. |
| `env_capture.sh` | Records machine, toolchain, git and model state in `env/environment.json`. |
| `evict_cache.py` | `posix_fadvise(DONTNEED)` over every shard, then reports the bytes still resident (via `bin/pagecache_resident`). |
| `pagecache_resident.c` | A `mincore` helper that proves a "cold" run started cold. |
| `expert_iobench.py` | Storage at the engine's exact pattern: whole random experts across all shards, with DONTNEED after each read, at QD 1–16. The headline device number. |
| `thread_sampler.py` | A profiler that needs no perf or gdb: samples every thread's state and syscall from `/proc` every 5 ms. It showed the decode thread is 87% running and only 13% in `pread`. |
| `io_profile.sh` | Storage ceiling at the real expert size: random reads, buffered and O_DIRECT, at QD 1/4/8/16. |
| `run_bench.py` | The matrix runner. Runs each arm cold (fresh CLI process) and warm (one `SERVE=1` process with repeated prompts), interleaved ABBA between arms. |
| `summarize.py` | Turns `runs.jsonl` into `results.json` (raw rows plus per-cell mean, stdev, min and max) and `profiling.log`. |
| `compare.py` | Writes `comparison.md`: per-cell % change with a bootstrap 95% CI. Changes whose CI spans zero are marked n.s. |
| `check_correctness.py` | Gate: greedy output (last-token logits sha256 and text) must be identical to the reference arm in every cell. |
| `prompts/` | Frozen prompts: short / medium / long = 24 / 514 / 1783 tokens after the chat template. `prompts/rendered/` is generated. |
| `ab/` | The before/after experiment: `baseline/` and `optimized/` interleaved, plus `flagoff/` (correctness only). `comparison.md` is computed from here. |
| `baseline/`, `optimized/` | Per arm: `runs.jsonl` (one JSON row per run), `raw/*.log` (full engine stderr), `results.json`, `profiling.log`. |

## Reproduce

```bash
cd benchmarks/expert_cache_research
./prepare_model.sh                                   # ~10 min over the 9p bridge, 19 GB
mkdir -p bin && gcc -O2 -Wall pagecache_resident.c -o bin/pagecache_resident
make -C ../../c qwen36 && cp ../../c/qwen36 bin/qwen36.baseline
./env_capture.sh ~/colibri-models/qwen3-coder-30b
./io_profile.sh  ~/colibri-models/qwen3-coder-30b

# baseline matrix: 3 prompts x caps {32,12} x PILOT {0,1} x 3 reps, cold + warm
python3 run_bench.py --snap ~/colibri-models/qwen3-coder-30b \
    --arm baseline=bin/qwen36.baseline --reps 3 --out . 2>&1 | tee baseline/console.log
python3 summarize.py baseline --profiling-extra env/io_profile.txt env/environment.json
```

To run the before/after experiment, build the modified engine (the feature is
`COLI_Q36_MISS_QD=N`, off by default) and copy it to `bin/qwen36.optimized`. Then
run the arms interleaved, ABBA by repetition. Every condition is the same; the only
difference is the binary and its feature flag:

```bash
make -C ../../c qwen36 && cp ../../c/qwen36 bin/qwen36.optimized
make -C ../../c tests/test_qwen36_cache_index && ../../c/tests/test_qwen36_cache_index

# A/B: original vs feature on (cold, caps 32/12, PILOT=0, short+medium, 3 reps)
python3 run_bench.py --snap ~/colibri-models/qwen3-coder-30b \
    --arm baseline=bin/qwen36.baseline \
    --arm optimized=bin/qwen36.optimized:COLI_Q36_MISS_QD=8 \
    --modes cold --caps 32,12 --pilot 0 --prompts short,medium --reps 3 --n-new 32 --out ab
# the new binary with the feature off must reproduce the original bit for bit
python3 run_bench.py --snap ~/colibri-models/qwen3-coder-30b \
    --arm flagoff=bin/qwen36.optimized \
    --modes cold --caps 32,12 --pilot 0 --prompts short,medium --reps 1 --n-new 32 --out ab
for a in baseline optimized flagoff; do python3 summarize.py ab/$a; done
python3 check_correctness.py ab/baseline ab/optimized ab/flagoff
python3 compare.py ab/baseline ab/optimized --out comparison.md --title "COLI_Q36_MISS_QD=8 vs original"
```

## Controlled conditions (identical across arms)

- **Model**: `Justvugg/Qwen3-Coder-30B-A3B-colibri-int4` (int4 gs64 experts, int8 dense trunk). It is read from an ext4 copy, so no reads go over the `/mnt/c` 9p bridge. The Windows original is never written.
- **Engine invocation**: `qwen36 <cap> 4 <prompt>`, called directly, never through `coli`, because `coli` writes `.coli_analysis.json`/`.coli_usage` into the model directory.
- **Fixed environment**: `COLI_TIMERS=1`, `COLI_LOOKUP=0`, `COLI_KV_PREFIX=0`, `OMP_NUM_THREADS=16`, `OMP_PROC_BIND=close`, `OMP_PLACES=cores`. Prompt-lookup speculation is off so every decode step is one row; the decode timers would otherwise count draft-verify steps as prefill. The CLI is always greedy, and serve requests use temperature 0.
- **`N_NEW=64`**. Cache capacity is `--cap 32` (standard, about 6.5 GB RSS) and `--cap 12` (restricted; simulates a machine with about 8 GB).
- **Cold**: shards evicted from the page cache before each run, checked with `mincore` (`pagecache_resident_before_bytes`), in a fresh process with an empty LRU.
- **Warm**: one serve process per (cap, PILOT, rep). Each prompt is sent twice: `first` and `repeat`. The repeat is the warm upper bound.

## Where each metric comes from

| metric | source |
|---|---|
| TTFT | cold: the engine's `TTFT:` line (time from generate() to first token, so prefill included). warm: client time to the first streamed text |
| tok/s | the engine's `Speed:` line (prefill and decode together). `decode_tok_s` = (n − 1) / (gen time − TTFT) |
| hit/miss | cold: the engine's `Expert cache hit rate` line, covering prefill and decode lookups. warm: misses = bytes read from storage ÷ bytes per expert (2,654,208 B = 2.53 MiB in this checkpoint: 2,359,296 B int4 merged gate|up|down + 294,912 B f32 group scales), because the serve DONE frame does not report a hit rate |
| expert-load latency | `[timers] expert kernel: fetch` (decode ms/token spent in the miss path), the PROF frame's `expert_disk_s` ÷ misses (warm), and `io_profile.txt` for the device |
| disk I/O | `read_bytes` from `/proc/<pid>/io`, `ru_inblock` from `wait4`, and the change in `/proc/diskstats` sectors for the volume |
| RAM / VRAM | the engine's `PEAK RSS`, `ru_maxrss` from `wait4`, and `VmHWM` (warm). nvidia-smi is sampled every 200 ms; values are peak minus idle |
| correctness | the sha256 of the `DUMP=` last-token float32 logits, plus the decoded text |

## Part 2 (docs/expert_cache_research_2.md)

| dir | what | commands |
|---|---|---|
| `phase0/` | per-miss fault/time profile (`COLI_Q36_FAULT_PROF=1`), slot microbenchmark, host working-set samples | `phase0/run_profile.sh`, `run_smoke.sh`, `host_ws_sample.sh`, `slotbench.c` |
| `ab2/` | main A/B (A = `COLI_Q36_MISS_QD=8` vs +arena, +waves, +both) and correctness (frozen original, flag-off) | `ab2/commands.txt`, `ab2/commands_followup.txt` |
| `chunk/` | waves planning size 32…whole, 514-token prompt | `ab2/commands_followup.txt` §2 |
| `grouped/` | `COLI_Q36_PREFILL_GROUPED=1` vs waves alone | `ab2/commands_followup.txt` §3 |
| `order/` | `COLI_Q36_PREFILL_WAVES_ORDER=last` vs first-seen; token path's decode misses | `order/commands.txt` |

Rows now also carry `ru_minflt`/`ru_majflt`, the host canary (`host_free_mb`, `host_vm_ws_mb`, WSL only), the `[waves]` counters and timers, and `prefill_misses`/`decode_misses` (from the `[timers] prefill cache:` line of `qwen36.v4`+). `ab2/report_tables.py` turns `compare.py` outputs into the report's tables.
