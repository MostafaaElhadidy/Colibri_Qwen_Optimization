#!/usr/bin/env bash
# Capture the machine, toolchain, repository and model state a benchmark ran on.
# usage: env_capture.sh <model_dir> [out.json]
set -euo pipefail
SNAP="${1:?model dir}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${2:-$HERE/env/environment.json}"
REPO="$(cd "$HERE/../.." && pwd)"
python3 -I - "$SNAP" "$OUT" "$REPO" <<'PY'
import json, os, platform, shutil, subprocess, sys
snap, out, repo = sys.argv[1:4]
def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as e:
        return f"error: {e}"
env = {
    "captured_at": sh("date -Is"),
    "git_commit": sh(f"git -C {repo} rev-parse HEAD"),
    "git_branch": sh(f"git -C {repo} rev-parse --abbrev-ref HEAD"),
    "git_status_porcelain": sh(f"git -C {repo} status --porcelain -- c"),
    "uname": platform.uname()._asdict(),
    "lscpu": sh("lscpu"),
    "nproc": os.cpu_count(),
    "meminfo": sh("grep -E 'MemTotal|MemAvailable|SwapTotal' /proc/meminfo"),
    "wslconfig": sh("powershell.exe -NoProfile -c 'Get-Content $env:USERPROFILE\\.wslconfig' 2>/dev/null | tr -d '\\r'"),
    "host_ram_bytes": sh("powershell.exe -NoProfile -c '(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory' 2>/dev/null | tr -d '\\r'"),
    "nvidia_smi": sh("nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version,pstate --format=csv"),
    "nvcc": sh("nvcc --version | tail -2"),
    "gcc": sh("gcc --version | head -1"),
    "python": sys.version,
    "model_dir": snap,
    "model_fs": sh(f"df -hT {snap} | tail -1"),
    "model_block_device": sh(f"lsblk -no NAME,MODEL,SIZE,ROTA $(df --output=source {snap} | tail -1) 2>/dev/null"),
    "model_size": sh(f"du -sh {snap} | cut -f1"),
    "disk_free_root": sh("df -h / | tail -1"),
    "model_config": json.load(open(os.path.join(snap, "config.json"))),
    "model_meta": json.load(open(os.path.join(snap, "qwen36_meta.json"))),
    "model_download_manifest_repo": json.load(open(os.path.join(snap, ".colibri-download.json"))).get("repo")
        if os.path.exists(os.path.join(snap, ".colibri-download.json")) else None,
    "omp_env": {k: v for k, v in os.environ.items() if k.startswith(("OMP_", "GOMP_"))},
    "pagecache_checker": "bin/pagecache_resident (mincore)",
}
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(env, open(out, "w"), indent=1)
print("wrote", out)
PY
