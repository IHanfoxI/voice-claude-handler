#!/usr/bin/env python3
"""Streaming TTS para voice-claude — pipeline 3 hilos.

  Hilo 1 (main/stdin): lee stream-json de claude → detecta sentence
                        boundaries → pone oraciones en sentence_q.
  Hilo 2 (synth):      sentence_q → daemon o Kokoro local → play_q.
  Hilo 3 (player):     play_q → paplay, trackea Popen.

Sentinela None propaga shutdown limpio: sentence_q(None) →
synth_worker → play_q(None) → player → exit.
"""
import json
import os
import queue
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
import soundfile as sf

OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/voice-claude-tts")
VOICE_SPEC = sys.argv[2] if len(sys.argv) > 2 else "ef_dora"
SPEED = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
LANG = sys.argv[4] if len(sys.argv) > 4 else "es"
SINK = sys.argv[5] if len(sys.argv) > 5 else ""

PIPER_BIN = os.environ.get("VOICE_CLAUDE_PIPER_BIN", "piper-tts")
USE_PIPER = VOICE_SPEC.startswith("piper:")
PIPER_MODEL = VOICE_SPEC[len("piper:"):] if USE_PIPER else None
PIPER_NOISE_SCALE = os.environ.get("VOICE_CLAUDE_PIPER_NOISE_SCALE", "0.9")
PIPER_NOISE_W = os.environ.get("VOICE_CLAUDE_PIPER_NOISE_W", "1.0")
PIPER_LENGTH_SCALE = os.environ.get("VOICE_CLAUDE_PIPER_LENGTH_SCALE", "0.9")

DAEMON_SOCK = Path(os.environ.get(
    "VOICE_CLAUDE_DAEMON_SOCK",
    Path.home() / ".local/share/voice-claude/kokoro.sock",
))
DAEMON_TIMEOUT_S = float(os.environ.get("VOICE_CLAUDE_DAEMON_TIMEOUT", "30"))

STATE_FILE = Path(os.environ.get(
    "VOICE_CLAUDE_STATE_FILE",
    Path.home() / ".local/share/voice-claude/state",
))
THINKING_LOOP_PID_FILE = STATE_FILE.parent / "thinking_loop.pid"
CANCEL_FILE = STATE_FILE.parent / "cancel"


def set_state(s: str) -> None:
    try:
        STATE_FILE.write_text(s)
    except OSError:
        pass
    if s in ("speaking", "idle", "error"):
        try:
            pid = int(THINKING_LOOP_PID_FILE.read_text().strip())
            try:
                subprocess.run(["pkill", "-P", str(pid)], capture_output=True)
            except Exception:
                pass
            os.kill(pid, signal.SIGTERM)
            THINKING_LOOP_PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass


def is_cancelled() -> bool:
    return CANCEL_FILE.exists()


OUT_DIR.mkdir(parents=True, exist_ok=True)
for old in OUT_DIR.glob("chunk_*.wav"):
    try:
        old.unlink()
    except OSError:
        pass


def log(msg: str) -> None:
    sys.stderr.write(f"[stream_tts {time.strftime('%H:%M:%S')}] {msg}\n")
    sys.stderr.flush()


def prewarm_sink() -> None:
    silence_path = OUT_DIR / "_prewarm_silence.wav"
    if not silence_path.exists():
        sr = 24000
        sf.write(silence_path, np.zeros(int(sr * 0.5), dtype="float32"), sr)
    cmd = ["paplay"]
    if SINK:
        cmd.append(f"--device={SINK}")
    cmd.append(str(silence_path))
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("prewarm: silence stream launched")
    except FileNotFoundError:
        log("prewarm: paplay not found")


prewarm_sink()


def _ping_daemon() -> bool:
    if not DAEMON_SOCK.exists():
        return False
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect(str(DAEMON_SOCK))
        s.sendall(b'{"cmd":"ping"}\n')
        data = s.recv(1024)
        s.close()
        return bool(json.loads(data.decode().strip()).get("ok"))
    except Exception:
        return False


USE_DAEMON = False
kokoro = None
voice_local = None

if USE_PIPER:
    log(f"using piper backend: {PIPER_MODEL}")
else:
    USE_DAEMON = _ping_daemon()
    if USE_DAEMON:
        log(f"using kokoro daemon at {DAEMON_SOCK}")
    else:
        log("daemon unavailable, loading kokoro in-process")
        from kokoro_onnx import Kokoro
        base = Path(__file__).resolve().parent
        t0 = time.monotonic()
        kokoro = Kokoro(str(base / "kokoro-v1.0.onnx"), str(base / "voices-v1.0.bin"))
        log(f"kokoro ready in {time.monotonic()-t0:.2f}s")
        if "+" in VOICE_SPEC:
            parts = VOICE_SPEC.split("+")
            styles = [kokoro.get_voice_style(p) for p in parts]
            voice_local = sum(styles) / len(styles)
        else:
            voice_local = VOICE_SPEC


def daemon_synth(text: str, out_path: Path, lead_silence: float) -> None:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(DAEMON_TIMEOUT_S)
    s.connect(str(DAEMON_SOCK))
    req = {
        "cmd": "synth",
        "text": text,
        "out_path": str(out_path),
        "voice": VOICE_SPEC,
        "speed": SPEED,
        "lang": LANG,
        "lead_silence": lead_silence,
    }
    s.sendall((json.dumps(req) + "\n").encode())
    buf = b""
    while b"\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
    s.close()
    resp = json.loads(buf.decode().strip())
    if "error" in resp:
        raise RuntimeError(resp["error"])


def local_synth(text: str, out_path: Path, lead_silence: float) -> None:
    samples, sr = kokoro.create(text, voice=voice_local, speed=SPEED, lang=LANG)
    if lead_silence > 0:
        lead = np.zeros(int(sr * lead_silence), dtype=samples.dtype)
        samples = np.concatenate([lead, samples])
    sf.write(out_path, samples, sr)


def piper_synth(text: str, out_path: Path, lead_silence: float) -> None:
    proc = subprocess.run(
        [
            PIPER_BIN, "--model", PIPER_MODEL,
            "--noise_scale", PIPER_NOISE_SCALE,
            "--noise_w", PIPER_NOISE_W,
            "--length_scale", PIPER_LENGTH_SCALE,
            "--output_file", str(out_path),
        ],
        input=text.encode(),
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"piper-tts: {proc.stderr.decode()[:300]}")
    if lead_silence > 0:
        data, sr = sf.read(out_path)
        lead = np.zeros(int(sr * lead_silence), dtype=data.dtype)
        sf.write(out_path, np.concatenate([lead, data]), sr)


SENTENCE_BOUNDARY = re.compile(r"[.!?…\n](\s+)")


def split_complete(buffer: str):
    """Returns (complete_sentences, remainder). Sentence complete = .!?… followed by whitespace."""
    sentences = []
    last = 0
    for m in SENTENCE_BOUNDARY.finditer(buffer):
        sentence = buffer[last:m.start(1)].strip()
        if sentence:
            sentences.append(sentence)
        last = m.end()
    return sentences, buffer[last:]


# ---- Queues ----
sentence_q: "queue.Queue[str | None]" = queue.Queue()
play_q: "queue.Queue[Path | None]" = queue.Queue()

_current_proc: "subprocess.Popen | None" = None
_current_proc_lock = threading.Lock()

FIRST_CHUNK_LEAD_SILENCE_S = 0.2


def synth_worker() -> None:
    """Thread 2: sentence_q → synth → play_q. Propagates None sentinel."""
    idx = 0
    while True:
        sentence = sentence_q.get()
        if sentence is None or is_cancelled():
            play_q.put(None)
            return
        t = time.monotonic()
        wav_path = OUT_DIR / f"chunk_{idx:03d}.wav"
        lead = FIRST_CHUNK_LEAD_SILENCE_S if idx == 0 else 0.0
        try:
            if USE_PIPER:
                piper_synth(sentence, wav_path, lead)
            elif USE_DAEMON:
                daemon_synth(sentence, wav_path, lead)
            else:
                local_synth(sentence, wav_path, lead)
        except Exception as e:
            log(f"synth #{idx} failed: {e}")
            idx += 1
            continue
        log(f"synth #{idx} ({len(sentence)} chars) in {time.monotonic()-t:.2f}s -> {wav_path.name}")
        play_q.put(wav_path)
        idx += 1


def player() -> None:
    """Thread 3: play_q → paplay. Tracks current Popen for cancel."""
    global _current_proc
    first = True
    while True:
        item = play_q.get()
        if item is None:
            set_state("idle")
            return
        if is_cancelled():
            with _current_proc_lock:
                proc = _current_proc
            if proc:
                try:
                    proc.terminate()
                except Exception:
                    pass
            set_state("idle")
            return
        if first:
            set_state("speaking")
            first = False
        cmd = ["paplay"]
        if SINK:
            cmd.append(f"--device={SINK}")
        cmd.append(str(item))
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with _current_proc_lock:
                _current_proc = proc
            proc.wait()
            with _current_proc_lock:
                _current_proc = None
        except FileNotFoundError:
            log("paplay not found")
            set_state("idle")
            return


synth_thread = threading.Thread(target=synth_worker, daemon=True)
play_thread = threading.Thread(target=player, daemon=True)
synth_thread.start()
play_thread.start()


text_indices: set[int] = set()
buffer = ""
full_text_parts: list[str] = []
saw_any_text = False
result_text = None
queued_count = 0

try:
    for line in sys.stdin:
        if is_cancelled():
            log("cancel detected in stdin loop")
            break
        line = line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue

        etype = evt.get("type")

        if etype == "result":
            result_text = evt.get("result")
            continue

        if etype != "stream_event":
            continue

        inner = evt.get("event", {})
        itype = inner.get("type")

        if itype == "content_block_start":
            idx = inner.get("index")
            cb = inner.get("content_block", {})
            if cb.get("type") == "text":
                text_indices.add(idx)

        elif itype == "content_block_delta":
            idx = inner.get("index")
            if idx not in text_indices:
                continue
            delta = inner.get("delta", {})
            if delta.get("type") != "text_delta":
                continue
            text = delta.get("text", "")
            if not text:
                continue
            buffer += text
            saw_any_text = True
            complete, buffer = split_complete(buffer)
            for s in complete:
                if is_cancelled():
                    break
                full_text_parts.append(s)
                sentence_q.put(s)
                queued_count += 1

    if not is_cancelled():
        tail = buffer.strip()
        if tail:
            full_text_parts.append(tail)
            sentence_q.put(tail)
            queued_count += 1

        if not saw_any_text and result_text:
            log("no stream text, using result fallback")
            sentence_q.put(result_text.strip())
            full_text_parts.append(result_text.strip())
            queued_count += 1

finally:
    sentence_q.put(None)
    synth_thread.join(timeout=120)
    play_thread.join(timeout=120)

if full_text_parts:
    log("full response:")
    log(" ".join(full_text_parts))
else:
    log("no text produced")

sys.exit(0 if queued_count > 0 else 1)
