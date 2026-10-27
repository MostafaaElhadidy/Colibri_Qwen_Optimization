#!/usr/bin/env bash
# Copy the Qwen3-Coder-30B colibri-int4 checkpoint to a WSL ext4 directory, read-only
# with respect to the source. The engine's side files (.coli_usage, .coli_analysis.json)
# are NOT copied, so the benchmark copy starts with no expert history, and nothing is
# ever written back to SRC.
#
# usage: prepare_model.sh [SRC] [DST]
set -euo pipefail
SRC="${1:-/mnt/c/Users/mosta/colibri-models/qwen3-coder-30b}"
DST="${2:-$HOME/colibri-models/qwen3-coder-30b}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$DST" "$HERE/env"
rsync -a --info=progress2 --exclude='.coli_usage' --exclude='.coli_analysis.json' \
      --exclude='.coli_ssd*' "$SRC/" "$DST/"
# size check against the downloader's manifest
python3 -I - "$SRC/.colibri-download.json" "$DST" <<'PY'
import json, os, sys
man, dst = sys.argv[1], sys.argv[2]
bad = 0
for f in json.load(open(man))["files"]:
    p = os.path.join(dst, f["path"])
    sz = os.path.getsize(p) if os.path.exists(p) else -1
    if sz != f["size"]:
        print(f"SIZE MISMATCH {f['path']}: {sz} != {f['size']}"); bad += 1
print("manifest check:", "OK" if not bad else f"{bad} mismatches")
sys.exit(1 if bad else 0)
PY
( cd "$DST" && sha256sum *.safetensors *.json > "$HERE/env/model_inventory.sha256" )
echo "model ready at $DST"
