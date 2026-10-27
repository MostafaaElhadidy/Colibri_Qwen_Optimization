#!/usr/bin/env bash
# Storage ceiling at the engine's real access pattern: random reads of one expert's
# size from the model volume, buffered and O_DIRECT, at queue depth (threads) 1/4/8.
# The page cache is evicted before every measurement (rule 1 of docs/benchmarking.md).
# usage: io_profile.sh <model_dir> [out.txt]
set -euo pipefail
SNAP="${1:?model dir}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${2:-$HERE/env/io_profile.txt}"
IOB="$HERE/bin/iobench"
[ -x "$IOB" ] || gcc -O2 -fopenmp -I"$HERE/../../c" "$HERE/../../c/iobench.c" -o "$IOB"
EB=$(python3 -I -c "import sys; sys.path.insert(0, '$HERE'); import run_bench; print(run_bench.expert_bytes('$SNAP'))")
MB=$(python3 -I -c "print($EB / 1048576)")
SHARD="$SNAP/model-00020.safetensors"
{
  echo "# io_profile $(date -Is)  model=$SNAP  device=$(df --output=source "$SNAP" | tail -1)"
  echo "# expert size: $EB bytes ($MB MiB); file: $SHARD; 120 random reads per row (buffered rows may re-hit overlapping blocks; the O_DIRECT rows are the device number)"
  for direct in 0 1; do
    for qd in 1 4 8 16; do
      python3 -I "$HERE/evict_cache.py" "$SNAP" >/dev/null
      echo "## direct=$direct threads(QD)=$qd"
      "$IOB" "$SHARD" "$MB" 120 "$qd" "$direct" 2>&1 | tail -3
    done
  done
} | tee "$OUT"
