# TODO — voice-claude-handler v2

Refactor en 4 ejes. Orden = dependencias + impacto.

## 1. Daemon TTS persistente ✅

Elimina costo de carga de modelo Kokoro (~1-2s) por invocación. Socket Unix.

- [x] `kokoro/daemon.py` — servidor Unix socket, carga Kokoro 1 vez, responde JSON
- [x] Cliente integrado en `stream_tts.py` (ping, synth via daemon, fallback a load local)
- [x] Auto-start desde `handler.sh` (nohup en background si socket no responde, espera 3s)
- [x] PID file + cleanup al salir (SIGTERM/SIGINT)
- [x] Cache de voice blends en daemon (clave = spec string)
- [x] Test: daemon arranca, ping OK, synth 0.18-0.32s, shutdown limpio, fallback funciona

**Medido:** carga modelo 0.33s en daemon, synth 0.16-0.32s por oración (vs ~2-3s antes con carga + synth combinados). Stream_tts.py ya no importa `kokoro_onnx` cuando daemon está vivo.

## 2. Pipeline 3 hilos explícito

`stream_tts.py` actualmente: síntesis bloquea stdin reader. Separar.

- [ ] Hilo 1 (main/stdin): lee stream-json → boundary detect → `sentence_q`
- [ ] Hilo 2 (synth worker): `sentence_q` → daemon call → `play_q`
- [ ] Hilo 3 (player): `play_q` → `paplay` (trackea `Popen` para cancel)
- [ ] Sentinel `None` para shutdown limpio por hilo

## 3. Cancel real (graceful)

Hoy: `pkill` por patrón. Mejor: flag file + signal cooperativo.

- [ ] Flag: `~/.local/share/voice-claude/cancel`
- [ ] `cancel.sh` → `touch cancel` + `SIGINT` al `claude -p`
- [ ] `stream_tts.py` chequea flag en los 3 hilos (entre oraciones, antes de synth, después de wav)
- [ ] Player `.terminate()` al `paplay` actual
- [ ] Handler limpia flag al inicio (evita estado viejo)

## 4. Config modular

YAML único en `~/.local/share/voice-claude/config.yaml`. Env vars siguen como override.

- [ ] `kokoro/config.py` — carga YAML + defaults + env overrides
- [ ] Bloques: `tts`, `models` (quick/full), `permissions.full.bash/tools`, `screen_keywords.words/phrases`
- [ ] `config.py --shell` emite env vars sourceables por `handler.sh`
- [ ] `config.py --json` para debug
- [ ] `examples/config.yaml` plantilla
- [ ] `requirements.txt` += `pyyaml`
- [ ] `install.sh` copia plantilla si no existe (no sobreescribe)

## Compatibilidad

- Sin daemon disponible → fallback a carga directa de Kokoro (modo actual)
- Sin config.yaml → defaults embebidos en `config.py` (= valores actuales)
- Env vars existentes (`VOICE_CLAUDE_VOICE/SPEED/SINK`) siguen funcionando
