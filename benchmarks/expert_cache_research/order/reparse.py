#!/usr/bin/env python3
"""Re-parse the text field of order/*/runs.jsonl from the raw logs with the fixed
parse_cli_log (the first parse stopped at the new "[timers] prefill cache:" line)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from run_bench import parse_cli_log
root = Path(__file__).resolve().parent
for arm in ("first", "last", "token"):
    p = root / arm / "runs.jsonl"
    rows = [json.loads(l) for l in open(p) if l.strip()]
    for r in rows:
        r["text"] = parse_cli_log((root / r["log"]).read_text(errors="replace"))["text"]
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(arm, len(rows), "rows re-parsed")
