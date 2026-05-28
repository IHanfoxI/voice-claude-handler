#!/usr/bin/env python3
"""Generate subtle audio cues for voice-claude state transitions.

Produces 3 WAV files in the same directory:
  listening_start.wav  — short ascending chirp (key pressed, recording started)
  listening_stop.wav   — short descending chirp (recording stopped, processing)
  thinking.wav         — gentle bell tone (looped in background while Claude processes)
"""

import array
import math
import os
import wave

RATE = 22050
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def _write_wav(name: str, samples: list) -> None:
    path = os.path.join(OUT_DIR, name)
    data = array.array("h", [max(-32768, min(32767, int(s * 32767))) for s in samples])
    with wave.open(path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(data.tobytes())
    print(f"  {path}")


def _fade(t: float, duration: float, attack: float = 0.010, release: float = 0.025) -> float:
    a = min(t / attack, 1.0)
    r = min((duration - t) / release, 1.0)
    return max(0.0, min(a, r))


def chirp(freq_start: float, freq_end: float, duration: float, volume: float = 0.22) -> list:
    n = int(RATE * duration)
    samples = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        freq = freq_start + (freq_end - freq_start) * (t / duration)
        phase += 2 * math.pi * freq / RATE
        samples.append(volume * math.sin(phase) * _fade(t, duration))
    return samples


def bell(freq: float, duration: float, volume: float = 0.18, decay: float = 3.5) -> list:
    n = int(RATE * duration)
    samples = []
    for i in range(n):
        t = i / RATE
        env = math.exp(-decay * t) * min(t / 0.005, 1.0)
        samples.append(volume * math.sin(2 * math.pi * freq * t) * env)
    return samples


print("Generating voice-claude audio cues:")
_write_wav("listening_start.wav", chirp(400, 750, 0.18))
_write_wav("listening_stop.wav",  chirp(750, 400, 0.15, volume=0.20))
_write_wav("thinking.wav",        bell(600, 0.9, volume=0.18))
