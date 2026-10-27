#!/usr/bin/env python3
"""Talk to Qwen3-Coder-30B through the original or the modified colibri engine.

    python3 chat.py original          # the frozen original engine (bin/qwen36.baseline)
    python3 chat.py modified          # this project's engine with MISS_QD=8 + prefill waves

Options: --cap N (experts kept in RAM per layer, default 12), --max-tokens N (default 512),
--temp T (default 0 = deterministic). Commands while chatting: /reset (new conversation),
/quit. After every reply it prints the time to first token and the speed, so you can feel
the difference between the two engines on the same conversation.

The model is loaded once and stays loaded. The conversation is sent as plain ChatML, the
format Qwen3-Coder expects; colibri's `coli chat` uses a template that makes this model
answer with nothing (docs/expert_cache_research.md, section 3).
"""
import argparse
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
C_DIR = HERE.parent.parent / "c"
sys.path.insert(0, str(C_DIR))
import openai_server as runtime  # noqa: E402

ENGINES = {
    "original": (HERE / "bin" / "qwen36.baseline", {}),
    "modified": (C_DIR / "qwen36", {"COLI_Q36_MISS_QD": "8", "COLI_Q36_PREFILL_WAVES": "1"}),
}


def render(history):
    """ChatML: every turn so far, then an open assistant turn."""
    out = "".join(f"<|im_start|>{role}\n{text}<|im_end|>\n" for role, text in history)
    return out + "<|im_start|>assistant\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("engine", choices=sorted(ENGINES))
    ap.add_argument("--model", default=os.path.expanduser("~/colibri-models/qwen3-coder-30b"))
    ap.add_argument("--cap", type=int, default=12)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--threads", type=int, default=os.cpu_count() // 2 or 4)
    args = ap.parse_args()

    binary, flags = ENGINES[args.engine]
    if not binary.exists():
        sys.exit(f"{binary} not found. Build it first: make -C {C_DIR} qwen36"
                 + ("  (the original: see CLAUDE.md, 'Frozen original')" if args.engine == "original" else ""))
    env = dict(os.environ, OMP_NUM_THREADS=str(args.threads), **flags)
    family = runtime.resolve_model(args.model).descriptor
    runtime.ARCH = family.id

    # the engine's own diagnostics go to a log file, so they don't land inside the replies
    log_path = f"/tmp/colibri_chat_{args.engine}.log"
    log = open(log_path, "w")
    real_stderr = os.dup(2)
    os.dup2(log.fileno(), 2)
    print(f"Loading Qwen3-Coder-30B with the {args.engine.upper()} engine "
          f"(cap {args.cap}{', ' + ', '.join(f'{k}={v}' for k, v in flags.items()) if flags else ''})...", flush=True)
    t0 = time.monotonic()
    eng = runtime.Engine(str(binary), args.model, cap=args.cap, max_tokens=args.max_tokens, env=env,
                         kv_slots=1, family=family)
    print(f"Ready in {time.monotonic() - t0:.0f} s. Type a message and press Enter. /reset starts over, /quit leaves.")
    print(f"(engine messages go to {log_path})\n")

    history = []
    try:
        while True:
            try:
                msg = input("you › ").strip()
            except EOFError:
                break
            if not msg:
                continue
            if msg in ("/quit", "/exit"):
                break
            if msg == "/reset":
                history = []
                print("(new conversation)\n")
                continue
            history.append(("user", msg))
            first, pieces, start = [None], [], time.monotonic()

            def on_text(t):
                if first[0] is None:
                    first[0] = time.monotonic()
                    print("model › ", end="", flush=True)
                pieces.append(t)
                print(t, end="", flush=True)

            stats = eng.generate(render(history), args.max_tokens, args.temp, 1.0, on_text, cache_slot=0)
            wall = time.monotonic() - start
            ttft = (first[0] - start) if first[0] else wall
            n = int(stats.get("completion_tokens", 0))
            history.append(("assistant", "".join(pieces)))
            print(f"\n\n   ⏱  first token after {ttft:.1f} s · {n} tokens in {wall:.1f} s "
                  f"({stats.get('tokens_per_second', 0):.2f} tok/s) · prompt {stats.get('prompt_tokens', '?')} tokens\n")
    except KeyboardInterrupt:
        print()
    finally:
        eng.close()
        os.dup2(real_stderr, 2)
        print("bye")


if __name__ == "__main__":
    main()
