#!/usr/bin/env bash
# Cancela una respuesta de voice-claude en curso (TTS + sintesis + claude).
# Pensado para colgarse de un atajo (ej. Alt+Shift+Z) y matar todo en cuanto
# digas "no, dejá, ya está".
#
# No mata Handy ni la grabacion en si — solo lo que pasa DESPUES de la
# transcripcion (handler.sh, stream_tts.py, claude -p, paplay de los chunks).

set -u

STATE_DIR="$HOME/.local/share/voice-claude"
STATE_INDICATOR="$STATE_DIR/state"

# Señal cooperativa: stream_tts.py y handler.sh chequean este archivo entre
# oraciones/pasos y se detienen limpiamente al detectarlo.
touch "$STATE_DIR/cancel" 2>/dev/null || true

# Resetea overlay inmediatamente (sin esperar a que mueran los procesos).
printf 'idle' > "$STATE_INDICATOR" 2>/dev/null || true

KILLED=0
kill_pattern() {
  if pkill -INT -f "$1" 2>/dev/null; then
    KILLED=1
  fi
}

# Orden: primero el productor (Claude), luego el procesador (stream_tts.py),
# luego los reproductores (paplay de nuestros chunks), por ultimo el handler.
kill_pattern 'claude -p'
kill_pattern 'stream_tts\.py'
kill_pattern 'paplay.*tts_chunks'
kill_pattern 'voice-claude-handler\.sh'

# Fallback duro por si quedo un paplay reproduciendo response.wav (modo legacy)
pkill -INT -f 'paplay.*voice-claude' 2>/dev/null && KILLED=1

if [[ $KILLED -eq 1 ]]; then
  notify-send -t 1500 "Claude" "Cancelado" 2>/dev/null || true
else
  notify-send -t 1500 "Claude" "Nada que cancelar" 2>/dev/null || true
fi

exit 0
