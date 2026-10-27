#!/bin/bash
# Phase 0: one short cold run per arm with the fault profiler
O=$(cd "$(dirname "$0")" && pwd)
cd "$(dirname "$0")/.."
M=~/colibri-models/qwen3-coder-30b
B=bin/qwen36.v2
for arm in qd0 qd8; do
  qd=0; [ $arm = qd8 ] && qd=8
  python3 evict_cache.py $M >/dev/null
  SNAP=$M N_NEW=32 COLI_TIMERS=1 COLI_LOOKUP=0 COLI_KV_PREFIX=0 OMP_NUM_THREADS=16 OMP_PROC_BIND=close OMP_PLACES=cores \
    COLI_Q36_FAULT_PROF=1 COLI_Q36_MISS_QD=$qd DUMP=$O/$arm.f32 /usr/bin/time -v $B 32 4 prompts/rendered/short.txt > $O/$arm.log 2>&1
done
