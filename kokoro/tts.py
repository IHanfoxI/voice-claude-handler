#!/usr/bin/env python3
"""Kokoro TTS: reads text from stdin, writes WAV to argv[1]. Voice defaults to ef_dora."""
import sys
from pathlib import Path
from kokoro_onnx import Kokoro
import soundfile as sf

if len(sys.argv) < 2:
    sys.stderr.write("usage: tts.py <output_wav> [voice] [speed] [lang]\n")
    sys.stderr.write("voice puede ser un nombre (ef_dora) o blend separado por '+' (ef_dora+af_bella)\n")
    sys.exit(2)

output_wav = sys.argv[1]
voice_spec = sys.argv[2] if len(sys.argv) > 2 else "ef_dora"
speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
lang = sys.argv[4] if len(sys.argv) > 4 else "es"

base = Path(__file__).resolve().parent
kokoro = Kokoro(str(base / "kokoro-v1.0.onnx"), str(base / "voices-v1.0.bin"))

# Soporte para blending: "ef_dora+af_bella" -> mezcla 50/50
if "+" in voice_spec:
    parts = voice_spec.split("+")
    styles = [kokoro.get_voice_style(p) for p in parts]
    voice = sum(styles) / len(styles)
else:
    voice = voice_spec

text = sys.stdin.read().strip()
if not text:
    sys.stderr.write("empty text\n")
    sys.exit(1)

samples, sr = kokoro.create(text, voice=voice, speed=speed, lang=lang)
sf.write(output_wav, samples, sr)
