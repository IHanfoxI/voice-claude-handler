#!/usr/bin/env python3
"""Kokoro TTS daemon — persistent process, Unix socket, single load.

Elimina el costo de cargar el modelo (~1-2s) en cada invocacion del handler.
El cliente (stream_tts.py) conecta al socket, envia JSON, recibe el path del wav.

Protocolo: linea JSON pedido -> linea JSON respuesta. Una request por conexion
(simple, sin multiplexado: cada synth abre un socket nuevo).

Comandos:
  {"cmd":"ping"}                              -> {"ok":true,"pid":N}
  {"cmd":"shutdown"}                          -> {"ok":true} y exit
  {"cmd":"synth","text":"...","out_path":"...",
   "voice":"ef_dora+af_bella","speed":1.3,"lang":"es"}
                                              -> {"path":"..."} | {"error":"..."}

Uso:
  daemon.py                  # foreground (systemd, debug)
  daemon.py --ping           # exit 0 si daemon responde, 1 si no
  daemon.py --stop           # pide shutdown limpio
"""
import json
import os
import signal
import socket
import sys
import threading
import time
from pathlib import Path

STATE_DIR = Path(os.environ.get("VOICE_CLAUDE_STATE_DIR", Path.home() / ".local/share/voice-claude"))
SOCK_PATH = STATE_DIR / "kokoro.sock"
PID_PATH = STATE_DIR / "kokoro-daemon.pid"
LOG_PATH = STATE_DIR / "logs" / "daemon.log"
MODEL_DIR = Path(__file__).resolve().parent

CONNECT_TIMEOUT = 1.0  # cliente: cuanto esperar al daemon


def log(msg: str) -> None:
    line = f"[daemon {time.strftime('%H:%M:%S')}] {msg}\n"
    sys.stderr.write(line)
    sys.stderr.flush()


def ping_daemon() -> bool:
    """Cliente: True si el daemon responde."""
    if not SOCK_PATH.exists():
        return False
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(CONNECT_TIMEOUT)
        s.connect(str(SOCK_PATH))
        s.sendall(b'{"cmd":"ping"}\n')
        data = s.recv(1024)
        s.close()
        resp = json.loads(data.decode().strip())
        return bool(resp.get("ok"))
    except Exception:
        return False


def request_shutdown() -> bool:
    if not SOCK_PATH.exists():
        return False
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(CONNECT_TIMEOUT)
        s.connect(str(SOCK_PATH))
        s.sendall(b'{"cmd":"shutdown"}\n')
        s.recv(1024)
        s.close()
        return True
    except Exception:
        return False


def serve() -> int:
    import numpy as np
    import soundfile as sf
    from kokoro_onnx import Kokoro

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # PID file. Si ya hay daemon vivo, salir.
    if ping_daemon():
        log("daemon already running, exiting")
        return 0
    # Socket viejo (daemon crasheado) -> limpiar
    if SOCK_PATH.exists():
        try:
            SOCK_PATH.unlink()
        except OSError:
            pass

    PID_PATH.write_text(str(os.getpid()))

    log("loading kokoro model")
    t0 = time.monotonic()
    kokoro = Kokoro(str(MODEL_DIR / "kokoro-v1.0.onnx"),
                    str(MODEL_DIR / "voices-v1.0.bin"))
    log(f"kokoro ready in {time.monotonic()-t0:.2f}s")

    # Cache de voice blends. Key = spec string.
    voice_cache: dict[str, object] = {}
    voice_lock = threading.Lock()
    model_lock = threading.Lock()  # Kokoro.create no es thread-safe

    def resolve_voice(spec: str):
        with voice_lock:
            if spec in voice_cache:
                return voice_cache[spec]
            if "+" in spec:
                parts = spec.split("+")
                styles = [kokoro.get_voice_style(p) for p in parts]
                v = sum(styles) / len(styles)
            else:
                v = spec
            voice_cache[spec] = v
            return v

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(SOCK_PATH))
    SOCK_PATH.chmod(0o600)
    server.listen(8)
    log(f"listening on {SOCK_PATH}")

    shutdown_event = threading.Event()

    def cleanup(*_):
        log("shutdown signal, cleaning up")
        shutdown_event.set()
        try:
            server.close()
        except Exception:
            pass

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    def handle(conn: socket.socket) -> None:
        with conn:
            try:
                buf = b""
                conn.settimeout(5.0)
                while b"\n" not in buf:
                    chunk = conn.recv(8192)
                    if not chunk:
                        break
                    buf += chunk
                line = buf.split(b"\n", 1)[0]
                if not line:
                    return
                req = json.loads(line.decode())
                cmd = req.get("cmd")

                if cmd == "ping":
                    conn.sendall(json.dumps({"ok": True, "pid": os.getpid()}).encode() + b"\n")
                    return

                if cmd == "shutdown":
                    conn.sendall(b'{"ok":true}\n')
                    cleanup()
                    return

                if cmd == "synth":
                    text = req.get("text", "")
                    out_path = req.get("out_path")
                    voice_spec = req.get("voice", "ef_dora")
                    speed = float(req.get("speed", 1.0))
                    lang = req.get("lang", "es")
                    lead_silence = float(req.get("lead_silence", 0.0))
                    if not text or not out_path:
                        conn.sendall(json.dumps({"error": "text and out_path required"}).encode() + b"\n")
                        return
                    voice = resolve_voice(voice_spec)
                    t = time.monotonic()
                    with model_lock:
                        samples, sr = kokoro.create(text, voice=voice, speed=speed, lang=lang)
                    if lead_silence > 0:
                        lead = np.zeros(int(sr * lead_silence), dtype=samples.dtype)
                        samples = np.concatenate([lead, samples])
                    sf.write(out_path, samples, sr)
                    log(f"synth {len(text)} chars in {time.monotonic()-t:.2f}s -> {out_path}")
                    conn.sendall(json.dumps({"path": out_path}).encode() + b"\n")
                    return

                conn.sendall(json.dumps({"error": f"unknown cmd: {cmd}"}).encode() + b"\n")
            except Exception as e:
                log(f"handler error: {e}")
                try:
                    conn.sendall(json.dumps({"error": str(e)}).encode() + b"\n")
                except Exception:
                    pass

    try:
        while not shutdown_event.is_set():
            try:
                conn, _ = server.accept()
            except OSError:
                break
            threading.Thread(target=handle, args=(conn,), daemon=True).start()
    finally:
        try:
            SOCK_PATH.unlink()
        except OSError:
            pass
        try:
            PID_PATH.unlink()
        except OSError:
            pass
        log("exited")

    return 0


def main() -> int:
    if "--ping" in sys.argv:
        return 0 if ping_daemon() else 1
    if "--stop" in sys.argv:
        return 0 if request_shutdown() else 1
    return serve()


if __name__ == "__main__":
    sys.exit(main())
