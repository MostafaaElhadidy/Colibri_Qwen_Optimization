#!/bin/bash
# Phase 0: the Windows host's view of the WSL VM during one cold short run (read-only
# PowerShell queries): host free RAM, the VM's host working set and commit, next to
# the engine's guest RSS. Output: one line per ~12 s.
O=$(cd "$(dirname "$0")" && pwd)
cd "$(dirname "$0")/.."
M=~/colibri-models/qwen3-coder-30b
python3 evict_cache.py $M >/dev/null
(SNAP=$M N_NEW=32 COLI_TIMERS=1 COLI_LOOKUP=0 OMP_NUM_THREADS=16 OMP_PROC_BIND=close OMP_PLACES=cores \
  COLI_Q36_MISS_QD=8 COLI_Q36_FAULT_PROF=1 bin/qwen36.v2 32 4 prompts/rendered/short.txt > $O/hostws.log 2>&1 &)
sleep 2
while p=$(pgrep -x qwen36.v2); do
  r=$(grep -oP '^Rss:\s+\K\d+' /proc/$p/smaps_rollup 2>/dev/null)
  h=$(timeout 20 powershell.exe -NoProfile -Command "\$v=Get-Process vmmemWSL; \$o=Get-CimInstance Win32_OperatingSystem; '{0} {1} {2}' -f [int](\$v.WorkingSet64/1MB),[int](\$v.PrivateMemorySize64/1MB),[int](\$o.FreePhysicalMemory/1KB)" 2>/dev/null | tr -d '\r')
  echo "$(date +%T) guest_rss_mb=$((r/1024)) host: vm_ws_mb/vm_commit_mb/host_free_mb=$h"
  sleep 12
done
