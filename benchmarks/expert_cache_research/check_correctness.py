#!/usr/bin/env python3
"""Correctness gate: every arm must produce the same greedy output as the reference arm.

For each (mode, kind, prompt, cap, pilot) cell and each rep, compares:
  cold: the sha256 of the last-token logits (DUMP, raw float32) -- bit-identical
        logits at the last position mean the whole greedy trajectory matched -- and
        the decoded text;
  warm: the sha256 of the streamed text.
Exits non-zero on any mismatch. Also checks that every rep of an arm agrees with
itself (determinism across repetitions).

usage: check_correctness.py <reference_arm_dir> <arm_dir> [<arm_dir> ...]
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_bench import clean_text  # noqa: E402  (also normalises rows logged before the fix)


def load(arm_dir):
    out = defaultdict(set)
    texts = {}
    for line in open(Path(arm_dir) / "runs.jsonl"):
        if not line.strip():
            continue
        r = json.loads(line)
        if not r.get("ok"):
            continue
        key = f"{r['mode']}|{r['kind']}|{r['prompt']}|cap{r['cap']}|pilot{r['pilot']}"
        sig = r.get("logits_sha256") or r.get("text_sha256")
        out[key].add(sig)
        texts.setdefault(key, clean_text(r.get("text")))
    return out, texts


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    ref, ref_text = load(sys.argv[1])
    failures = 0
    report = []
    for key, sigs in sorted(ref.items()):
        if len(sigs) != 1:
            failures += 1
            report.append(f"NONDETERMINISTIC reference {key}: {len(sigs)} distinct outputs")
    for arm in sys.argv[2:]:
        got, got_text = load(arm)
        for key, sigs in sorted(got.items()):
            if key not in ref:
                report.append(f"SKIP {Path(arm).name} {key}: no reference cell")
                continue
            same = sigs == ref[key]
            text_same = got_text.get(key) == ref_text.get(key)
            status = "OK  " if same and text_same else "FAIL"
            failures += 0 if same and text_same else 1
            report.append(f"{status} {Path(arm).name:>10} {key}: output "
                          f"{'identical' if same else 'DIFFERS'}, text {'identical' if text_same else 'DIFFERS'}")
    print("\n".join(report))
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
