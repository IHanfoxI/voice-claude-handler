#!/usr/bin/env python3
"""Streaming TTS para voice-claude.

Lee stream-json de `claude -p` por stdin, extrae text_delta de bloques tipo
text (ignora thinking_delta), parte por oraciones y manda cada una a Kokoro
en cuanto se cierra el boundary. La reproducción corre en un hilo aparte
para que la sintesis de la oracion N+1 se solape con el playback de la N.

Uso: stream_tts.py <out_dir> [voice] [speed] [lang] [sink]
"""
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/voice-claude-tts")
VOICE_SPEC = sys.argv[2] if len(sys.argv) > 2 else "ef_dora"
SPEED = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
LANG = sys.argv[4] if len(sys.argv) > 4 else "es"
SINK = sys.argv[5] if len(sys.argv) > 5 else ""

OUT_DIR.mkdir(parents=True, exist_ok=True)
for old in OUT_DIR.glob("chunk_*.wav"):
    try:
        old.unlink()
    except OSError:
        pass

def log(msg: str) -> None:
    sys.stderr.write(f"[stream_tts {time.strftime('%H:%M:%S')}] {msg}\n")
    sys.stderr.flush()

# Pre-warm: el sink HDMI suspende cuando esta idle y, al despertar, se come
# los primeros ~200-300ms del primer audio. Disparamos un paplay con 500ms
# de silencio en background ahora; mientras kokoro carga + claude empieza a
# generar, el sink ya esta abierto para cuando llegue el primer chunk real.
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

base = Path(__file__).resolve().parent
log("loading kokoro model")
t0 = time.monotonic()
kokoro = Kokoro(str(base / "kokoro-v1.0.onnx"), str(base / "voices-v1.0.bin"))
log(f"kokoro ready in {time.monotonic()-t0:.2f}s")

if "+" in VOICE_SPEC:
    parts = VOICE_SPEC.split("+")
    styles = [kokoro.get_voice_style(p) for p in parts]
    voice = sum(styles) / len(styles)
else:
    voice = VOICE_SPEC

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
    """Reproduce wav files en orden FIFO."""
    while True:
        item = play_q.get()
        if item is None:
            return
        cmd = ["paplay"]
        if SINK:
            cmd.append(f"--device={SINK}")
        cmd.append(str(item))
        try:
            subprocess.run(cmd, check=False)
        except FileNotFoundError:
            log("paplay not found")
            return

play_thread = threading.Thread(target=player, daemon=True)
play_thread.start()

FIRST_CHUNK_LEAD_SILENCE_S = 0.2  # red de seguridad: si el prewarm fue insuficiente, este margen evita comerse las primeras palabras

def synthesize_and_queue(text: str, idx: int) -> None:
    t = time.monotonic()
    samples, sr = kokoro.create(text, voice=voice, speed=SPEED, lang=LANG)
    if idx == 0 and FIRST_CHUNK_LEAD_SILENCE_S > 0:
        lead = np.zeros(int(sr * FIRST_CHUNK_LEAD_SILENCE_S), dtype=samples.dtype)
        samples = np.concatenate([lead, samples])
    wav_path = OUT_DIR / f"chunk_{idx:03d}.wav"
    sf.write(wav_path, samples, sr)
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
