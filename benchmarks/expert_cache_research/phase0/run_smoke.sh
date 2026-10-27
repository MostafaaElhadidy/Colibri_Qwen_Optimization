#!/bin/bash
# smoke: short prompt, cap 32, cold; MISS_QD=8 plus each new flag
O=$(cd "$(dirname "$0")" && pwd)
cd "$(dirname "$0")/.."
M=~/colibri-models/qwen3-coder-30b; B=bin/qwen36.v2
run() { name=$1; shift
  python3 evict_cache.py $M >/dev/null
  env SNAP=$M N_NEW=32 COLI_TIMERS=1 COLI_LOOKUP=0 COLI_KV_PREFIX=0 OMP_NUM_THREADS=16 OMP_PROC_BIND=close OMP_PLACES=cores \
    COLI_Q36_FAULT_PROF=1 COLI_Q36_MISS_QD=8 DUMP=$O/$name.f32 "$@" /usr/bin/time -v $B 32 4 prompts/rendered/short.txt > $O/$name.log 2>&1
}
run waves COLI_Q36_PREFILL_WAVES=1
run arena COLI_Q36_SLOT_ARENA=1
run both COLI_Q36_PREFILL_WAVES=1 COLI_Q36_SLOT_ARENA=1
