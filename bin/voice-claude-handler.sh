#!/usr/bin/env bash
# Handy external_script_path handler.
# Llamado por Handy con la transcripción como $1.
# Modo (quick/full) se lee desde $STATE_DIR/mode (escrito por el keybind).
#   quick → haiku + Read only (Alt+Z)
#   full  → opus + TODAS las tools + permisos saltados (Super+Z)
# Ambos modos: extensión libre, sin límite de oraciones. Solo se prohibe
# markdown/código/listas porque va a TTS.
# Pipeline: read mode -> decidir captura por keywords -> grim si aplica
#   -> claude -p (stream-json) -> stream_tts.py (Kokoro por oraciones) -> paplay.

set -u
TEXT="${1:-}"

STATE_DIR="$HOME/.local/share/voice-claude"
WORKDIR="$STATE_DIR/workdir"
LOG_DIR="$STATE_DIR/logs"
LOG_FILE="$LOG_DIR/handler.log"
SCREEN_FILE="$STATE_DIR/screen.png"
MODE_FILE="$STATE_DIR/mode"

VOICE_FILE="$STATE_DIR/voices/es_ES-sharvard-medium.onnx"  # piper (fallback)
KOKORO_PY="$STATE_DIR/venv/bin/python"
KOKORO_SCRIPT="$STATE_DIR/kokoro/tts.py"            # legacy single-shot
KOKORO_STREAM_SCRIPT="$STATE_DIR/kokoro/stream_tts.py"  # streaming por oraciones
KOKORO_VOICE="${VOICE_CLAUDE_VOICE:-ef_dora+af_bella}"
KOKORO_SPEED="${VOICE_CLAUDE_SPEED:-1.3}"
# Sink de pulseaudio para reproducir el TTS. Vacío = sink default del sistema.
# Para listar sinks: pactl list short sinks
# Para fijarlo permanentemente, exporta VOICE_CLAUDE_SINK en tu shell o en el atajo.
TTS_SINK="${VOICE_CLAUDE_SINK:-}"
TTS_CHUNK_DIR="$STATE_DIR/tts_chunks"

mkdir -p "$WORKDIR" "$LOG_DIR"
exec >>"$LOG_FILE" 2>&1

log() { printf '%s %s\n' "$(date +'%H:%M:%S')" "$*"; }

MODE=$(cat "$MODE_FILE" 2>/dev/null || echo "quick")
log "===== handler invoked (mode=$MODE) ====="
log "text: $TEXT"

if [[ -z "${TEXT// }" ]]; then
  log "empty transcription, exiting"
  notify-send -t 2000 "Claude" "No te escuché nada" || true
  exit 0
fi

# Despertar el sink lo antes posible (evita perder los primeros ~200ms del
# primer chunk cuando el DAC sale de suspend). pactl es no-op si ya esta
# activo o si TTS_SINK esta vacio.
[[ -n "$TTS_SINK" ]] && pactl suspend-sink "$TTS_SINK" 0 2>/dev/null || true

# ---- Decision: ¿necesitamos captura? ----
# Heuristica por keywords en la transcripcion. Si la pregunta no aparenta ser
# visual, omitimos `grim` + upload de imagen (ahorra ~500ms y ~3k tokens).
# Falsos negativos > falsos positivos en perjuicio, asi que la lista es generosa.
SCREEN_KW_RE='\b(pantalla|ventana|ventanas|monitor|escritorio|captura|capturas|screenshot|imagen|imagenes|foto|fotos|aplicacion|aplicaciones|programa|programas|pestana|pestanas|navegador|terminal|consola|codigo|editor|mira|miro|miras|miramos|miran|mirando|mirar|fijate|fijar|fija|fijese|ves|veo|vemos|veas|ver|viendo|viste|leer|lee|leelo|leen|leyendo|cursor|raton|mouse|click|clickea|clic|boton|botones|menu|menus|icono|iconos|color|colores)\b'
SCREEN_PHRASE_RE='(que dice|que pone|que sale|que aparece|que muestra|que tengo abierto|esta abierto|esta abierta|en pantalla|aca arriba|aca abajo|aqui arriba|aqui abajo|ese error|este error|ese mensaje|este mensaje|esta linea|esta funcion|esta pestana|este boton|ese boton)'

needs_screenshot() {
  local norm
  norm=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]' \
    | iconv -f utf-8 -t ascii//TRANSLIT 2>/dev/null \
    || printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
  if echo "$norm" | grep -Eq "$SCREEN_KW_RE"; then return 0; fi
  if echo "$norm" | grep -Eq "$SCREEN_PHRASE_RE"; then return 0; fi
  return 1
}

if needs_screenshot "$TEXT"; then
  WITH_SCREEN=1
  ACTIVE_MON=$(hyprctl monitors -j 2>/dev/null | jq -r '.[] | select(.focused).name' 2>/dev/null || echo "")
  if [[ -n "$ACTIVE_MON" ]]; then
    grim -o "$ACTIVE_MON" "$SCREEN_FILE" || grim "$SCREEN_FILE"
  else
    grim "$SCREEN_FILE"
  fi
  log "screenshot: included ($SCREEN_FILE, $(stat -c%s "$SCREEN_FILE" 2>/dev/null) bytes)"
else
  WITH_SCREEN=0
  log "screenshot: skipped (no visual keywords matched)"
fi

# Config por modo
if [[ "$MODE" == "full" ]]; then
  SESSION_FILE="$STATE_DIR/session-full.id"
  SESSION_INIT_FLAG="$STATE_DIR/.session-full_initialized"
  CLAUDE_MODEL="opus"
  CLAUDE_EFFORT="high"
  # Whitelist explícita: comandos comunes de control del sistema + tools no
  # destructivas. Una transcripción mala NO puede disparar rm/sudo/chmod/dd
  # porque no están permitidos. Si necesitas algo que no esté acá, agrégalo
  # con criterio (evita Bash(*:*) — equivale a --dangerously-skip-permissions).
  CLAUDE_FULL_BASH_ALLOW=(
    'Bash(hyprctl:*)'
    'Bash(pactl:*)'
    'Bash(playerctl:*)'
    'Bash(wpctl:*)'
    'Bash(brightnessctl:*)'
    'Bash(omarchy:*)'
    'Bash(omarchy-launch-or-focus:*)'
    'Bash(uwsm-app:*)'
    'Bash(steam:*)'
    'Bash(setsid:*)'
    'Bash(notify-send:*)'
    'Bash(ls:*)'
    'Bash(cat:*)'
    'Bash(grep:*)'
    'Bash(rg:*)'
    'Bash(find:*)'
    'Bash(jq:*)'
    'Bash(du:*)'
    'Bash(df:*)'
    'Bash(date:*)'
    'Bash(uptime:*)'
    'Bash(free:*)'
    'Bash(echo:*)'
    'Bash(printf:*)'
  )
  CLAUDE_FULL_TOOLS_ALLOW=(Read Write Edit Glob Grep WebFetch WebSearch)
  ALLOWED="${CLAUDE_FULL_BASH_ALLOW[*]} ${CLAUDE_FULL_TOOLS_ALLOW[*]}"
  CLAUDE_PERMS=(--allowedTools "$ALLOWED")
  SYS_PROMPT="Eres un asistente de voz con permisos acotados al control del sistema del usuario. Puedes ejecutar comandos comunes (hyprctl, pactl, playerctl, omarchy*, steam, uwsm-app, ls/cat/grep/find/jq/du/df, notify-send, etc.) y usar las tools Read/Write/Edit/WebFetch/WebSearch. NO tienes permiso para rm, sudo, chmod, dd, mv ni otros destructivos; si te piden eso, di que no puedes y propone una alternativa. Tu respuesta se LEE EN VOZ ALTA con TTS: español, sin markdown, sin código, sin listas, sin viñetas. Habla todo lo que necesites para responder bien; no te autocensures por longitud."
  if [[ "$WITH_SCREEN" == "1" ]]; then
    USER_PROMPT="Te hablo por voz. Captura del monitor enfocado: \`$SCREEN_FILE\` (léela si la pregunta lo requiere).

Pregunta: $TEXT

Si pide acción concreta (ejecutar, editar, buscar, instalar…), hazla. Responde en español hablado (va a TTS) sin formato ni listas. Extensión libre."
  else
    USER_PROMPT="Te hablo por voz.

Pregunta: $TEXT

Si pide acción concreta (ejecutar, editar, buscar, instalar…), hazla. Responde en español hablado (va a TTS) sin formato ni listas. Extensión libre."
  fi
else
  # quick (default)
  SESSION_FILE="$STATE_DIR/session.id"
  SESSION_INIT_FLAG="$STATE_DIR/.session_initialized"
  CLAUDE_MODEL="haiku"
  CLAUDE_EFFORT="low"
  CLAUDE_PERMS=(--allowedTools "Read")
  SYS_PROMPT="Eres un asistente de voz. Respondes en español hablado para TTS: sin markdown, sin código, sin listas, sin viñetas. Habla lo que haga falta para responder bien; sin auto-censura de longitud."
  if [[ "$WITH_SCREEN" == "1" ]]; then
    USER_PROMPT="Te hablo por voz mientras hago otra cosa. La captura en \`$SCREEN_FILE\` es lo que veo. Léela solo si la pregunta lo requiere.

Pregunta: $TEXT

Responde EN ESPAÑOL hablado (va a TTS). Sin preámbulos, sin markdown, sin código, sin listas. Extensión libre."
  else
    USER_PROMPT="Te hablo por voz mientras hago otra cosa.

Pregunta: $TEXT

Responde EN ESPAÑOL hablado (va a TTS). Sin preámbulos, sin markdown, sin código, sin listas. Extensión libre."
  fi
fi

# Sesión persistente (UUID fijo por modo). Se genera con `uuidgen > session.id`
# y session-full.id al instalar (ver install.sh).
SESSION_ID=$(cat "$SESSION_FILE")
if [[ -f "$SESSION_INIT_FLAG" ]]; then
  SESSION_OPT=(--resume "$SESSION_ID")
else
  SESSION_OPT=(--session-id "$SESSION_ID")
fi
log "session: $SESSION_ID (${SESSION_OPT[0]}) model=$CLAUDE_MODEL effort=$CLAUDE_EFFORT"

cd "$WORKDIR"

# Pipeline streaming: claude emite stream-json -> stream_tts.py parsea
# text_deltas, parte por oraciones y va sintetizando + reproduciendo con
# Kokoro mientras Claude sigue generando. TTFA ~0.3s para la 1a oracion.
mkdir -p "$TTS_CHUNK_DIR"

if [[ -x "$KOKORO_PY" && -f "$KOKORO_STREAM_SCRIPT" ]]; then
  claude -p \
    "${SESSION_OPT[@]}" \
    --model "$CLAUDE_MODEL" \
    --effort "$CLAUDE_EFFORT" \
    --output-format stream-json --include-partial-messages --verbose \
    "${CLAUDE_PERMS[@]}" \
    --append-system-prompt "$SYS_PROMPT" \
    "$USER_PROMPT" \
  | "$KOKORO_PY" "$KOKORO_STREAM_SCRIPT" "$TTS_CHUNK_DIR" "$KOKORO_VOICE" "$KOKORO_SPEED" es "$TTS_SINK"
  CLAUDE_EXIT=${PIPESTATUS[0]}
  TTS_EXIT=${PIPESTATUS[1]}
  log "claude exit: $CLAUDE_EXIT  stream_tts exit: $TTS_EXIT"

  if [[ $CLAUDE_EXIT -eq 0 ]]; then
    touch "$SESSION_INIT_FLAG"
  else
    notify-send -t 4000 "Claude (error)" "claude exit=$CLAUDE_EXIT mode=$MODE — revisa $LOG_FILE" || true
  fi

  if [[ $TTS_EXIT -ne 0 ]]; then
    log "stream_tts produjo 0 chunks — sin audio"
    notify-send -t 4000 "Claude (sin audio)" "stream_tts no genero audio. Revisa $LOG_FILE" || true
  fi

  log "done"
  exit 0
fi

# --- Fallback: kokoro streaming no disponible. Modo legacy text + piper ---
log "stream_tts no disponible, usando flujo legacy"
RESPONSE=$(claude -p \
  "${SESSION_OPT[@]}" \
  --model "$CLAUDE_MODEL" \
  --effort "$CLAUDE_EFFORT" \
  --output-format text \
  "${CLAUDE_PERMS[@]}" \
  --append-system-prompt "$SYS_PROMPT" \
  "$USER_PROMPT" 2>>"$LOG_FILE")
CLAUDE_EXIT=$?
[[ $CLAUDE_EXIT -eq 0 ]] && touch "$SESSION_INIT_FLAG"
log "claude exit: $CLAUDE_EXIT"
log "response: $RESPONSE"

if [[ $CLAUDE_EXIT -ne 0 ]] || [[ -z "${RESPONSE// }" ]]; then
  notify-send -t 4000 "Claude (error)" "exit=$CLAUDE_EXIT mode=$MODE — revisa $LOG_FILE" || true
  exit 0
fi

TTS_WAV="$STATE_DIR/response.wav"
rm -f "$TTS_WAV"

if command -v piper-tts >/dev/null 2>&1 && [[ -f "$VOICE_FILE" ]]; then
  printf '%s' "$RESPONSE" | piper-tts --model "$VOICE_FILE" --output_file "$TTS_WAV" 2>>"$LOG_FILE"
fi

if [[ -s "$TTS_WAV" ]]; then
  if [[ -n "$TTS_SINK" ]]; then
    paplay --device="$TTS_SINK" "$TTS_WAV" 2>>"$LOG_FILE" \
      || paplay "$TTS_WAV" 2>>"$LOG_FILE" \
      || log "paplay failed on $TTS_SINK and default"
  else
    paplay "$TTS_WAV" 2>>"$LOG_FILE" || log "paplay failed on default sink"
  fi
else
  log "no tts wav generated"
fi

log "done"
exit 0
