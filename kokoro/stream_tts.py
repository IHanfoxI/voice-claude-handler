#!/usr/bin/env python3
"""Streaming TTS para voice-claude.

Lee stream-json de `claude -p` por stdin, extrae text_delta de bloques tipo
text (ignora thinking_delta), parte por oraciones y manda cada una a Kokoro
en cuanto se cierra el boundary. La reproducción corre en un hilo aparte
para que la sintesis de la oracion N+1 se solape con el playback de la N.

Si hay un daemon Kokoro escuchando en VOICE_CLAUDE_DAEMON_SOCK (o el path por
defecto), se usa para sintetizar — evita cargar el modelo en cada invocacion.
Si el daemon no responde, fallback a carga local de Kokoro (modo legacy).

Uso: stream_tts.py <out_dir> [voice] [speed] [lang] [sink]
"""
import json
import os
import queue
import re
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

DAEMON_SOCK = Path(os.environ.get(
    "VOICE_CLAUDE_DAEMON_SOCK",
    Path.home() / ".local/share/voice-claude/kokoro.sock",
))
DAEMON_TIMEOUT_S = float(os.environ.get("VOICE_CLAUDE_DAEMON_TIMEOUT", "30"))

# Indicador de estado leído por el overlay (voice-claude-overlay).
STATE_FILE = Path(os.environ.get(
    "VOICE_CLAUDE_STATE_FILE",
    Path.home() / ".local/share/voice-claude/state",
))


def set_state(s: str) -> None:
    try:
        STATE_FILE.write_text(s)
    except OSError:
        pass

OUT_DIR.mkdir(parents=True, exist_ok=True)
for old in OUT_DIR.glob("chunk_*.wav"):
    try:
        old.unlink()
    except OSError:
        pass


def log(msg: str) -> None:
    sys.stderr.write(f"[stream_tts {time.strftime('%H:%M:%S')}] {msg}\n")
    sys.stderr.flush()


# Pre-warm: el sink HDMI suspende cuando esta idle y al despertar se come los
# primeros ~200-300ms del primer audio. Disparamos un paplay con 500ms de
# silencio en background ahora; mientras claude empieza a generar, el sink ya
# esta abierto para cuando llegue el primer chunk real.
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


# ---- Backend: daemon o local ----
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


USE_DAEMON = _ping_daemon()
kokoro = None
voice_local = None

if USE_DAEMON:
    log(f"using kokoro daemon at {DAEMON_SOCK}")
else:
    log("daemon unavailable, loading kokoro in-process")
    from kokoro_onnx import Kokoro  # import diferido (caro)
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


# Boundary = puntuacion final seguida de espacio. Si la puntuacion queda al
# final del buffer sin espacio detras, esperamos por si viene mas texto.
SENTENCE_BOUNDARY = re.compile(r"[.!?…\n](\s+)")


def split_complete(buffer: str):
    """Devuelve (oraciones_completas, resto). Una oracion es completa cuando
    termina en .!?… seguido de whitespace (otro token ya llego)."""
    sentences = []
    last = 0
    for m in SENTENCE_BOUNDARY.finditer(buffer):
        sentence = buffer[last:m.start(1)].strip()
        if sentence:
            sentences.append(sentence)
        last = m.end()
    return sentences, buffer[last:]


play_q: "queue.Queue[Path | None]" = queue.Queue()


def player():
    """Reproduce wav files en orden FIFO. Escribe 'speaking' al overlay
    cuando arranca el primer wav y 'idle' al recibir el sentinel."""
    first = True
    while True:
        item = play_q.get()
        if item is None:
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
            subprocess.run(cmd, check=False)
        except FileNotFoundError:
            log("paplay not found")
            set_state("idle")
            return


play_thread = threading.Thread(target=player, daemon=True)
play_thread.start()


FIRST_CHUNK_LEAD_SILENCE_S = 0.2  # red de seguridad si el prewarm no alcanzo


def synthesize_and_queue(text: str, idx: int) -> None:
    t = time.monotonic()
    wav_path = OUT_DIR / f"chunk_{idx:03d}.wav"
    lead = FIRST_CHUNK_LEAD_SILENCE_S if idx == 0 else 0.0
    try:
        if USE_DAEMON:
            daemon_synth(text, wav_path, lead)
        else:
            local_synth(text, wav_path, lead)
    except Exception as e:
        log(f"synth #{idx} failed: {e}")
        return
    log(f"synth #{idx} ({len(text)} chars) in {time.monotonic()-t:.2f}s -> {wav_path.name}")
    play_q.put(wav_path)


# Track which content_block indices are "text" (vs "thinking")
text_indices: set[int] = set()
buffer = ""
chunk_idx = 0
full_text_parts: list[str] = []
saw_any_text = False
result_text = None

try:
    for line in sys.stdin:
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
                full_text_parts.append(s)
                synthesize_and_queue(s, chunk_idx)
                chunk_idx += 1

    # Flush remaining buffer
    tail = buffer.strip()
    if tail:
        full_text_parts.append(tail)
        synthesize_and_queue(tail, chunk_idx)
        chunk_idx += 1

    # Si por alguna razon no llegaron text_deltas pero hay result text, usalo.
    if not saw_any_text and result_text:
        log("no stream text, using result fallback")
        synthesize_and_queue(result_text.strip(), chunk_idx)
        chunk_idx += 1
        full_text_parts.append(result_text.strip())

finally:
    play_q.put(None)
    play_thread.join(timeout=120)

if full_text_parts:
    log("full response:")
    log(" ".join(full_text_parts))
else:
    log("no text produced")

sys.exit(0 if chunk_idx > 0 else 1)
