#!/usr/bin/env python3
"""Config loader para voice-claude.

Carga ~/.local/share/voice-claude/config.yaml (si existe),
aplica defaults embebidos, y permite overrides vía env vars.

CLI:
  --shell   emite variables sourceables por bash (eval "$(config.py --shell)")
  --json    emite config completa como JSON (debug)
"""

import json
import os
import shlex
import sys
from pathlib import Path

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

CONFIG_FILE = Path(os.environ.get(
    "VOICE_CLAUDE_CONFIG",
    Path.home() / ".local/share/voice-claude/config.yaml",
))

_DEFAULTS: dict = {
    "tts": {
        "voice": "ef_dora+af_bella",
        "speed": 1.3,
        "lang": "es",
        "sink": "",
        "daemon_timeout": 30,
    },
    "models": {
        "quick": {"model": "haiku", "effort": "low"},
        "full":  {"model": "opus",  "effort": "high"},
    },
    "screen_keywords": {
        "words": [
            "pantalla", "ventana", "ventanas", "monitor", "escritorio",
            "captura", "capturas", "screenshot", "imagen", "imagenes",
            "foto", "fotos", "aplicacion", "aplicaciones", "programa",
            "programas", "pestana", "pestanas", "navegador", "terminal",
            "consola", "codigo", "editor", "mira", "miro", "miras",
            "miramos", "miran", "mirando", "mirar", "fijate", "fijar",
            "fija", "fijese", "ves", "veo", "vemos", "veas", "ver",
            "viendo", "viste", "leer", "lee", "leelo", "leen", "leyendo",
            "cursor", "raton", "mouse", "click", "clickea", "clic",
            "boton", "botones", "menu", "menus", "icono", "iconos",
            "color", "colores",
        ],
        "phrases": [
            "que dice", "que pone", "que sale", "que aparece", "que muestra",
            "que tengo abierto", "esta abierto", "esta abierta",
            "en pantalla", "aca arriba", "aca abajo", "aqui arriba",
            "aqui abajo", "ese error", "este error", "ese mensaje",
            "este mensaje", "esta linea", "esta funcion", "esta pestana",
            "este boton", "ese boton",
        ],
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        elif k in result and isinstance(result[k], list) and isinstance(v, list):
            result[k] = v  # lists: override replaces (don't concat)
        else:
            result[k] = v
    return result


def load() -> dict:
    cfg = _deep_merge(_DEFAULTS, {})

    if _HAS_YAML and CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                user = yaml.safe_load(f) or {}
            cfg = _deep_merge(cfg, user)
        except Exception as e:
            print(f"# config.py: warning: failed to load {CONFIG_FILE}: {e}", file=sys.stderr)

    # Env vars override YAML (backwards compat with existing exports)
    tts = cfg["tts"]
    if os.environ.get("VOICE_CLAUDE_VOICE"):
        tts["voice"] = os.environ["VOICE_CLAUDE_VOICE"]
    if os.environ.get("VOICE_CLAUDE_SPEED"):
        tts["speed"] = float(os.environ["VOICE_CLAUDE_SPEED"])
    if os.environ.get("VOICE_CLAUDE_SINK"):
        tts["sink"] = os.environ["VOICE_CLAUDE_SINK"]

    return cfg


def _build_screen_kw_re(words: list) -> str:
    return r"\b(" + "|".join(words) + r")\b"


def _build_screen_phrase_re(phrases: list) -> str:
    return "(" + "|".join(phrases) + ")"


if __name__ == "__main__":
    cfg = load()

    if "--shell" in sys.argv:
        tts = cfg["tts"]
        print(f"VOICE_CLAUDE_VOICE={shlex.quote(str(tts['voice']))}")
        print(f"VOICE_CLAUDE_SPEED={shlex.quote(str(tts['speed']))}")
        print(f"VOICE_CLAUDE_SINK={shlex.quote(str(tts['sink']))}")
        print(f"VOICE_CLAUDE_LANG={shlex.quote(str(tts['lang']))}")
        kw = cfg["screen_keywords"]
        print(f"VOICE_CLAUDE_SCREEN_KW_RE={shlex.quote(_build_screen_kw_re(kw['words']))}")
        print(f"VOICE_CLAUDE_SCREEN_PHRASE_RE={shlex.quote(_build_screen_phrase_re(kw['phrases']))}")

    elif "--json" in sys.argv:
        print(json.dumps(cfg, indent=2, ensure_ascii=False))

    else:
        print(f"Usage: {sys.argv[0]} --shell | --json", file=sys.stderr)
        sys.exit(1)
