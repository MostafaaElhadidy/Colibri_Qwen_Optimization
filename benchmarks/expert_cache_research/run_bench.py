#!/usr/bin/env python3
"""Expert-cache benchmark matrix for colibri's qwen36 engine (Qwen3-Coder-30B-A3B int4).

Two measurement modes, kept apart because they measure different cache states
(docs/benchmarking.md, rule 1):

  cold  One fresh CLI process per run. The model's shards are evicted from the page
        cache first (posix_fadvise DONTNEED, checked with mincore), so the expert
        LRU is empty and every miss is a real disk read. Engine-reported TTFT,
        tok/s, hit/miss and timers; kernel-reported bytes read and peak RSS.
  warm  One SERVE=1 process per (cell, rep), driven through c/openai_server.Engine.
        Each prompt (the same ChatML text as the CLI arm) is sent twice: "first" (the LRU holds whatever earlier
        prompts left) then "repeat" (the LRU was just filled by the identical
        request: the warm upper bound). COLI_KV_PREFIX=0 so the repeat really
        prefills again. The serve DONE frame carries no hit rate, so misses are
        derived from bytes the process read from disk divided by the bytes of
        one expert.

Several arms (binaries and/or env) are interleaved run by run, alternating their
order every repetition, so drift cannot masquerade as a difference between arms.

usage:
  run_bench.py --snap ~/colibri-models/qwen3-coder-30b \
      --arm baseline=bin/qwen36.baseline [--arm optimized=../../c/qwen36:FLAG=1] \
      [--modes cold,warm] [--caps 32,12] [--pilot 0,1] [--prompts short,medium,long] \
      [--reps 3] [--n-new 64] [--threads 16] [--out DIR]
"""
import argparse
import hashlib
import json
import os
import re
import shlex
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
C_DIR = REPO / "c"
sys.path.insert(0, str(HERE))
import evict_cache  # noqa: E402
import expert_iobench  # noqa: E402

CHAT = "<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n"

# Fixed for every arm: only the arm's own env differs between arms.
COMMON_ENV = {
    "COLI_TIMERS": "1",      # per-phase decode timers, incl. expert fetch vs compute
    "COLI_LOOKUP": "0",      # prompt-lookup speculation off: S==1 decode steps only,
                             # so the timers' decode split is clean (greedy output is
                             # identical either way; the drafts only batch steps)
    "COLI_KV_PREFIX": "0",   # a repeated prompt must prefill again (warm mode)
    "OMP_PROC_BIND": "close",
    "OMP_PLACES": "cores",
}

RE = {
    "prompt_tokens": re.compile(r"\[enc\] prompt tokens: (\d+)"),
    "ttft_s": re.compile(r"TTFT: ([\d.]+) s"),
    "speed": re.compile(r"Speed: ([\d.]+) tok/s \(([\d.]+)s for (\d+) tokens\)"),
    "hits": re.compile(r"Expert cache hit rate: ([\d.]+)% \(hit=(\d+) miss=(\d+)\)"),
    "peak_rss_gb": re.compile(r"PEAK RSS: ([\d.]+) GB"),
    "dec_tokens": re.compile(r"\[timers\] decode: (\d+) tokens"),
    "moe_ms_tok": re.compile(r"\[timers\]\s+moe_total\s+[\d.]+ ms\s+([\d.]+) ms/token"),
    "attn_ms_tok": re.compile(r"\[timers\]\s+attention\s+[\d.]+ ms\s+([\d.]+) ms/token"),
    "head_ms_tok": re.compile(r"\[timers\]\s+lm_head\s+[\d.]+ ms\s+([\d.]+) ms/token"),
    "router_ms_tok": re.compile(r"\[timers\]\s+\(router\)\s+[\d.]+ ms\s+([\d.]+) ms/token"),
    "total_ms_tok": re.compile(r"\[timers\]\s+TOTAL\s+[\d.]+ ms\s+([\d.]+) ms/token"),
    "step_ms_tok": re.compile(r"step\(\) total: ([\d.]+) ms/token"),
    "xf": re.compile(r"expert kernel: fetch ([\d.]+) \| compute ([\d.]+) ms/token"),
    "prefill": re.compile(r"\[timers\] prefill: (\d+) tokens\s+dn=(\d+) attn=(\d+) moe=(\d+)\(sh=(\d+) rt=(\d+)\) head=(\d+) ms"),
    "waves": re.compile(r"\[waves\] (\d+) layer blocks, (\d+) waves, (\d+) experts \((\d+) resident at plan\), (\d+) pairs(?: \| hold ([\d.]+) s, compute ([\d.]+) s)?"),
    "prefill_cache": re.compile(r"\[timers\] prefill cache: hit=(\d+) miss=(\d+)"),
    "text": re.compile(r"Text : (.*?)\n(?:TTFT:|\[timers\]|\nPEAK RSS)", re.S),
}


# ---------------------------------------------------------------- helpers
def expert_bytes(snap):
    """On-disk bytes of one routed expert (all tensors of layer 0 / expert 0)."""
    prefix = "model.layers.0.mlp.experts.0."
    for shard in sorted(Path(snap).glob("*.safetensors")):
        with open(shard, "rb") as f:
            n = struct.unpack("<Q", f.read(8))[0]
            hdr = json.loads(f.read(n))
        hits = [v for k, v in hdr.items() if k.startswith(prefix)]
        if hits:
            return sum(v["data_offsets"][1] - v["data_offsets"][0] for v in hits)
    raise SystemExit("expert 0 of layer 0 not found in any shard")


def block_device(path):
    st = os.stat(path)
    major, minor = os.major(st.st_dev), os.minor(st.st_dev)
    with open("/proc/diskstats") as f:
        for line in f:
            p = line.split()
            if int(p[0]) == major and int(p[1]) == minor:
                return p[2]
    return None


def disk_sectors_read(dev):
    if not dev:
        return None
    with open("/proc/diskstats") as f:
        for line in f:
            p = line.split()
            if p[2] == dev:
                return int(p[5])
    return None


def proc_io(pid):
    out = {}
    try:
        with open(f"/proc/{pid}/io") as f:
            for line in f:
                k, v = line.split(":")
                out[k] = int(v)
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith(("VmHWM", "VmRSS")):
                    out[line.split(":")[0]] = int(line.split()[1])  # kB
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        pass
    return out


class GpuSampler(threading.Thread):
    """Peak GPU memory used (MiB) while a run is live, nvidia-smi every 200 ms."""

    def __init__(self):
        super().__init__(daemon=True)
        self.peak = None
        self.idle = None
        self.proc = None

    def run(self):
        try:
            self.proc = subprocess.Popen(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits",
                 "-lms", "200"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        except FileNotFoundError:
            return
        for line in self.proc.stdout:
            try:
                v = int(line.strip())
            except ValueError:
                continue
            if self.idle is None:
                self.idle = v
            self.peak = v if self.peak is None else max(self.peak, v)

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


class IoPoller(threading.Thread):
    """Last /proc/<pid>/io and VmHWM seen before the process exits."""

    def __init__(self, pid):
        super().__init__(daemon=True)
        self.pid, self.last, self.done = pid, {}, False

    def run(self):
        while not self.done:
            s = proc_io(self.pid)
            if s:
                self.last = s
            time.sleep(0.1)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_text(text):
    """The generated text only: the CLI streams it to stderr, where engine notes
    ("[qwen36] ...", "[dump] wrote <path>") land in between, in an order that depends
    on thread timing (a parallel miss path prints its one-time note later)."""
    if text is None:
        return None
    text = re.sub(r"\[dump\] wrote .*", "", text)
    return "\n".join(ln for ln in text.split("\n") if not ln.startswith("[")).strip()


def parse_cli_log(text):
    r = {}
    for key in ("prompt_tokens", "dec_tokens"):
        m = RE[key].search(text)
        r[key] = int(m.group(1)) if m else None
    for key in ("ttft_s", "peak_rss_gb", "moe_ms_tok", "attn_ms_tok", "head_ms_tok",
                "router_ms_tok", "total_ms_tok", "step_ms_tok"):
        m = RE[key].search(text)
        r[key] = float(m.group(1)) if m else None
    m = RE["speed"].search(text)
    r["engine_tok_s"], r["gen_s"], r["gen_tokens"] = (
        (float(m.group(1)), float(m.group(2)), int(m.group(3))) if m else (None, None, None))
    m = RE["hits"].search(text)
    r["hit_rate_pct"], r["hits"], r["misses"] = (
        (float(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (None, None, None))
    m = RE["xf"].search(text)
    r["fetch_ms_tok"], r["compute_ms_tok"] = (
        (float(m.group(1)), float(m.group(2))) if m else (None, None))
    m = RE["prefill"].search(text)
    if m:
        keys = ("prefill_tokens", "prefill_dn_ms", "prefill_attn_ms", "prefill_moe_ms",
                "prefill_shared_ms", "prefill_router_ms", "prefill_head_ms")
        r.update({k: int(v) for k, v in zip(keys, m.groups())})
    m = RE["waves"].search(text)
    if m:
        keys = ("waves_blocks", "waves_waves", "waves_experts", "waves_resident", "waves_pairs")
        r.update({k: int(v) for k, v in zip(keys, m.groups()[:5])})
        if m.group(6):
            r["waves_hold_s"], r["waves_compute_s"] = float(m.group(6)), float(m.group(7))
    m = RE["prefill_cache"].search(text)
    if m:
        r["prefill_hits"], r["prefill_misses"] = int(m.group(1)), int(m.group(2))
        if r.get("misses") is not None:
            r["decode_misses"] = r["misses"] - r["prefill_misses"]
    # the "[timers] prefill cache:" line (qwen36.v4+) prints between "Text :" and the
    # streamed text; it must not end the capture
    m = RE["text"].search(re.sub(r"\[timers\] prefill cache:[^\n]*\n", "", text))
    r["text"] = clean_text(m.group(1)) if m else None
    # decode-only throughput: tokens after the first over the time after TTFT
    if r["ttft_s"] is not None and r["gen_s"] and r["gen_tokens"] and r["gen_s"] > r["ttft_s"]:
        r["decode_tok_s"] = (r["gen_tokens"] - 1) / (r["gen_s"] - r["ttft_s"])
    else:
        r["decode_tok_s"] = None
    return r


def parse_arm(spec):
    """NAME=BINARY[:K=V,K=V]"""
    name, rest = spec.split("=", 1)
    binary, _, envs = rest.partition(":")
    env = dict(kv.split("=", 1) for kv in envs.split(",") if kv)
    path = Path(binary)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.is_file():
        raise SystemExit(f"arm {name}: binary {path} not found")
    return {"name": name, "binary": str(path), "env": env, "sha256": sha256_file(path)}


_CANARY = {}


def storage_canary(snap, n=16):
    """Sanity metric (docs/benchmarking.md rule 4): QD1 latency of n random experts
    read right before a run. The model volume is a VHDX on the host's NVMe, and host
    activity (write-back, scanners) moved this from 3 to 28 ms during setup; a run whose
    canary is far off the session's norm is flagged, not silently averaged."""
    import random
    if "idx" not in _CANARY:
        _CANARY["idx"] = expert_iobench.expert_index(snap)
        _CANARY["keys"] = sorted(_CANARY["idx"])
        _CANARY["rng"] = random.Random(4242)
    keys = _CANARY["rng"].sample(_CANARY["keys"], n)
    r = expert_iobench.run_row(_CANARY["idx"], keys, 1)
    return {"canary_ms_p50": r["lat_ms_p50"], "canary_ms_mean": r["lat_ms_mean"]}


def host_memory():
    """Host-side canary (WSL only): the Windows host's free RAM and the VM's host
    working set, read just before a run. The VM can be paged out by the host when the
    host runs short, and touching a paged-out guest page is a host fault the guest never
    sees (docs/expert_cache_research_2.md, Phase 0). None outside WSL or on any error."""
    ps = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    if not os.path.exists(ps):
        return {}
    cmd = ("$v=Get-Process vmmemWSL -ErrorAction SilentlyContinue; $o=Get-CimInstance Win32_OperatingSystem; "
           "'{0} {1}' -f [int]($o.FreePhysicalMemory/1KB),[int]($v.WorkingSet64/1MB)")
    try:
        out = subprocess.run([ps, "-NoProfile", "-Command", cmd], capture_output=True, text=True,
                             timeout=30).stdout.split()
        return {"host_free_mb": int(out[0]), "host_vm_ws_mb": int(out[1])}
    except Exception:
        return {}


# ---------------------------------------------------------------- one cold run
def run_cold(arm, snap, prompt_name, prompt_path, cap, pilot, rep, args, out_dir, ebytes, dev):
    run_id = f"cold_{prompt_name}_cap{cap}_pilot{pilot}_rep{rep}"
    raw = out_dir / arm["name"] / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    log_path, dump_path = raw / f"{run_id}.log", raw / f"{run_id}.logits.f32"
    env = dict(os.environ, **COMMON_ENV, SNAP=str(snap), N_NEW=str(args.n_new),
               PILOT=str(pilot), OMP_NUM_THREADS=str(args.threads), DUMP=str(dump_path))
    env.update(arm["env"])
    cmd = [arm["binary"], str(cap), "4", str(prompt_path)]

    canary = storage_canary(snap)
    canary.update(host_memory())
    files = evict_cache.evict(snap)
    resident = evict_cache.resident_bytes(files)
    sect0 = disk_sectors_read(dev)
    gpu = GpuSampler(); gpu.start(); time.sleep(0.3)
    t0 = time.monotonic()
    with open(log_path, "w") as log:
        p = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
        poller = IoPoller(p.pid); poller.start()
        _, status, ru = os.wait4(p.pid, 0)
        p.returncode = os.waitstatus_to_exitcode(status)
        poller.done = True
    wall = time.monotonic() - t0
    gpu.stop()
    sect1 = disk_sectors_read(dev)
    text = log_path.read_text(errors="replace")
    row = {
        "run_id": run_id, "arm": arm["name"], "mode": "cold", "kind": "cold-process",
        "prompt": prompt_name, "cap": cap, "pilot": pilot, "rep": rep,
        "cmd": shlex.join(cmd),
        "env": {k: env[k] for k in sorted(set(COMMON_ENV) | set(arm["env"]) |
                                           {"SNAP", "N_NEW", "PILOT", "OMP_NUM_THREADS"})},
        "binary_sha256": arm["sha256"], "exit_code": p.returncode, "wall_s": wall,
        "pagecache_resident_before_bytes": resident,
        "ru_maxrss_gb": ru.ru_maxrss / 1048576, "ru_inblock_bytes": ru.ru_inblock * 512,
        "ru_utime_s": ru.ru_utime, "ru_stime_s": ru.ru_stime,
        "ru_minflt": ru.ru_minflt, "ru_majflt": ru.ru_majflt,
        "proc_read_bytes": poller.last.get("read_bytes"), "proc_rchar": poller.last.get("rchar"),
        "disk_read_bytes": (sect1 - sect0) * 512 if sect0 is not None and sect1 is not None else None,
        "gpu_mem_idle_mib": gpu.idle, "gpu_mem_peak_mib": gpu.peak,
        "expert_bytes": ebytes, "log": str(log_path.relative_to(out_dir)),
        **canary,
    }
    row.update(parse_cli_log(text))
    if dump_path.exists():
        row["logits_sha256"] = sha256_file(dump_path)
        if rep != 1:
            dump_path.unlink()
    row["ok"] = p.returncode == 0 and row["engine_tok_s"] is not None
    return row


# ---------------------------------------------------------------- one warm session
def run_warm(arm, snap, prompts, cap, pilot, rep, args, out_dir, ebytes):
    sys.path.insert(0, str(C_DIR))
    import openai_server as runtime  # noqa: E402

    family = runtime.resolve_model(str(snap)).descriptor
    runtime.ARCH = family.id
    env = dict(os.environ, **COMMON_ENV, PILOT=str(pilot), OMP_NUM_THREADS=str(args.threads),
               COLI_TEMP="0")
    env.update(arm["env"])
    raw = out_dir / arm["name"] / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    session = f"warm_cap{cap}_pilot{pilot}_rep{rep}"
    canary = storage_canary(snap)
    evict_cache.evict(snap)
    rows = []
    gpu = GpuSampler(); gpu.start(); time.sleep(0.3)
    t0 = time.monotonic()
    eng = runtime.Engine(arm["binary"], str(snap), cap=cap, max_tokens=args.n_new, env=env,
                         kv_slots=1, family=family)
    load_s = time.monotonic() - t0
    pid = eng.process.pid
    try:
        for pname, ppath in prompts:
            # The same ChatML text the CLI arm encodes. Not render_chat_for_arch: for this
            # checkpoint the gateway resolves the qwen36 family template, which appends an
            # empty <think></think> block that Qwen3-Coder (no thinking mode) answers with
            # an immediate end-of-turn -- 0 tokens (observed 2026-10-26).
            rendered = CHAT.format(Path(ppath).read_text().rstrip("\n"))
            for kind in ("first", "repeat"):
                first = [None]
                io0 = proc_io(pid)
                start = time.monotonic()
                pieces = []

                def on_text(t, first=first, pieces=pieces):
                    if first[0] is None:
                        first[0] = time.monotonic()
                    pieces.append(t)
                stats = eng.generate(rendered, args.n_new, 0.0, 1.0, on_text, cache_slot=0)
                wall = time.monotonic() - start
                time.sleep(0.15)  # let the trailing PROF frame land
                io1 = proc_io(pid)
                ttft = (first[0] - start) if first[0] else wall
                ntok = int(stats["completion_tokens"])
                dread = (io1.get("read_bytes", 0) - io0.get("read_bytes", 0)) if io0 and io1 else None
                prof = dict(eng.profile[-1]) if getattr(eng, "profile", None) else None
                text = "".join(pieces)
                rows.append({
                    "run_id": f"{session}_{pname}_{kind}", "arm": arm["name"], "mode": "warm",
                    "kind": kind, "prompt": pname, "cap": cap, "pilot": pilot, "rep": rep,
                    "cmd": f"SERVE=1 {arm['binary']} {cap}",
                    "env": {k: env[k] for k in sorted(set(COMMON_ENV) | set(arm["env"]) |
                                                       {"PILOT", "OMP_NUM_THREADS"})},
                    "binary_sha256": arm["sha256"], "engine_load_s": load_s,
                    "prompt_tokens": int(stats.get("prompt_tokens", 0)),
                    "gen_tokens": ntok, "wall_s": wall, "ttft_s": ttft,
                    "engine_tok_s": float(stats["tokens_per_second"]),
                    "decode_tok_s": (ntok - 1) / (wall - ttft) if ntok > 1 and wall > ttft else None,
                    "proc_read_bytes": dread, "expert_bytes": ebytes,
                    "est_misses": dread / ebytes if dread is not None else None,
                    "peak_rss_gb": (io1.get("VmHWM", 0) / 1048576) if io1 else None,
                    "rss_gb": float(stats.get("rss_gb", 0.0)),
                    "stats": dict(stats), "prof": prof, "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "text": text, "ok": ntok > 0,
                })
    finally:
        try:
            eng.close()
        except Exception as exc:  # noqa: BLE001
            print(f"[bench] engine close: {exc}", file=sys.stderr)
        gpu.stop()
    for r in rows:
        r["gpu_mem_idle_mib"], r["gpu_mem_peak_mib"] = gpu.idle, gpu.peak
        r.update(canary)
    return rows


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snap", required=True)
    ap.add_argument("--arm", action="append", required=True, help="NAME=BINARY[:K=V,K=V]")
    ap.add_argument("--modes", default="cold,warm")
    ap.add_argument("--caps", default="32,12")
    ap.add_argument("--pilot", default="0,1")
    ap.add_argument("--prompts", default="short,medium,long")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--n-new", type=int, default=64)
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--out", default=str(HERE))
    args = ap.parse_args()

    snap = Path(args.snap).expanduser().resolve()
    out_dir = Path(args.out).resolve()
    arms = [parse_arm(a) for a in args.arm]
    caps = [int(x) for x in args.caps.split(",")]
    pilots = [int(x) for x in args.pilot.split(",")]
    pnames = args.prompts.split(",")
    modes = args.modes.split(",")
    ebytes = expert_bytes(snap)
    dev = block_device(snap)

    # chat-rendered prompt files for the CLI (the engine's text mode encodes raw text)
    rendered_dir = out_dir / "prompts" / "rendered"
    rendered_dir.mkdir(parents=True, exist_ok=True)
    prompts = []
    for name in pnames:
        src = HERE / "prompts" / f"{name}.txt"
        dst = rendered_dir / f"{name}.txt"
        dst.write_text(CHAT.format(src.read_text().rstrip("\n")))
        prompts.append((name, src, dst))

    for arm in arms:
        d = out_dir / arm["name"]
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "invocation.json", "a") as f:
            f.write(json.dumps({"argv": sys.argv, "arm": arm, "snap": str(snap), "device": dev,
                                "expert_bytes": ebytes, "common_env": COMMON_ENV,
                                "started": time.strftime("%Y-%m-%dT%H:%M:%S")}) + "\n")

    def emit(rows):
        for r in rows if isinstance(rows, list) else [rows]:
            with open(out_dir / r["arm"] / "runs.jsonl", "a") as f:
                f.write(json.dumps(r) + "\n")
            print(f"[bench] {r['arm']:>10} {r['run_id']:<42} ok={r['ok']} "
                  f"ttft={r.get('ttft_s')} tok/s={r.get('engine_tok_s')} "
                  f"decode={r.get('decode_tok_s') and round(r['decode_tok_s'], 2)} "
                  f"hit={r.get('hit_rate_pct')} canary={r.get('canary_ms_p50') and round(r['canary_ms_p50'], 1)}ms est_miss={r.get('est_misses') and round(r['est_misses'])}",
                  flush=True)

    for rep in range(1, args.reps + 1):
        order = arms if rep % 2 else list(reversed(arms))   # ABBA across repetitions
        for cap in caps:
            for pilot in pilots:
                if "cold" in modes:
                    for name, _src, rendered in prompts:
                        for arm in order:
                            emit(run_cold(arm, snap, name, rendered, cap, pilot, rep, args,
                                          out_dir, ebytes, dev))
                if "warm" in modes:
                    for arm in order:
                        emit(run_warm(arm, snap, [(n, s) for n, s, _ in prompts], cap, pilot,
                                      rep, args, out_dir, ebytes))


if __name__ == "__main__":
    main()
