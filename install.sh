#!/usr/bin/env bash
# Instala voice-claude-handler en ~/.local/share/voice-claude y ~/.local/bin.
# Descarga los modelos Kokoro, crea el venv y genera los UUIDs de sesión.
# Idempotente: puedes correrlo varias varias veces.
#
# Flags opcionales:
#   --no-overlay   No instalar overlay visual (requiere gtk4-layer-shell)
#   --no-sound     No generar sonidos de estado
#   --no-extras    Equivale a --no-overlay --no-sound

set -euo pipefail

STATE_DIR="$HOME/.local/share/voice-claude"
BIN_DIR="$HOME/.local/bin"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

KOKORO_MODEL_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
KOKORO_VOICES_URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

say() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31mXX\033[0m %s\n' "$*" >&2; exit 1; }

command -v claude >/dev/null 2>&1 || die "Claude Code CLI no encontrado. Instala desde https://claude.com/claude-code"
command -v handy   >/dev/null 2>&1 || warn "Handy no encontrado en PATH. Instálalo desde https://handy.computer/"
command -v grim    >/dev/null 2>&1 || warn "grim no encontrado (capturas de Wayland)."
command -v paplay  >/dev/null 2>&1 || die "paplay no encontrado (pulseaudio/pipewire-pulse)."
command -v jq      >/dev/null 2>&1 || warn "jq no encontrado (recomendado para el handler)."
command -v python3 >/dev/null 2>&1 || die "python3 no encontrado."
command -v uuidgen >/dev/null 2>&1 || die "uuidgen no encontrado."

# --- Selección de características ---
ENABLE_OVERLAY=1
ENABLE_SOUND=1

for arg in "$@"; do
  case "$arg" in
    --no-overlay) ENABLE_OVERLAY=0 ;;
    --no-sound)   ENABLE_SOUND=0   ;;
    --no-extras)  ENABLE_OVERLAY=0; ENABLE_SOUND=0 ;;
  esac
done

if [[ $# -eq 0 ]] && [[ -t 0 ]]; then
  echo ""
  say "¿Qué indicadores de estado quieres instalar?"
  echo "   1) Ambos: overlay visual + sonidos  (recomendado)"
  echo "   2) Solo overlay visual               (sin sonidos)"
  echo "   3) Solo sonidos                      (sin overlay)"
  echo "   4) Ninguno"
  printf "Opción [1]: "
  read -r FEAT_CHOICE
  FEAT_CHOICE="${FEAT_CHOICE:-1}"
  case "$FEAT_CHOICE" in
    2) ENABLE_SOUND=0 ;;
    3) ENABLE_OVERLAY=0 ;;
    4) ENABLE_OVERLAY=0; ENABLE_SOUND=0 ;;
  esac
fi

# Overlay: verificar dependencias si está habilitado
if [[ "$ENABLE_OVERLAY" -eq 1 ]]; then
  HAS_OVERLAY_LIBS=1
  for cand in /usr/lib/libgtk4-layer-shell.so /usr/lib64/libgtk4-layer-shell.so \
              /usr/lib/x86_64-linux-gnu/libgtk4-layer-shell.so; do
    [[ -e "$cand" ]] && HAS_OVERLAY_LIBS=1 && break || HAS_OVERLAY_LIBS=0
  done
  if [[ "$HAS_OVERLAY_LIBS" -eq 0 ]]; then
    warn "gtk4-layer-shell no encontrado. El overlay no podrá iniciar."
    warn "Arch: 'sudo pacman -S gtk4-layer-shell python-gobject'."
  fi
  python3 -c 'import gi; gi.require_version("Gtk","4.0"); from gi.repository import Gtk' 2>/dev/null \
    || warn "python-gobject + gtk4 no detectados. El overlay no podrá iniciar."
fi

say "Creando directorios en $STATE_DIR y $BIN_DIR"
mkdir -p "$STATE_DIR"/{kokoro,workdir,logs,tts_chunks,voices} "$BIN_DIR"
[[ "$ENABLE_SOUND" -eq 1 ]] && mkdir -p "$STATE_DIR/sounds"

say "Copiando handler.sh, cancel.sh → $BIN_DIR/"
install -m 755 "$REPO_DIR/bin/voice-claude-handler.sh" "$BIN_DIR/voice-claude-handler.sh"
install -m 755 "$REPO_DIR/bin/voice-claude-cancel.sh"  "$BIN_DIR/voice-claude-cancel.sh"

if [[ "$ENABLE_OVERLAY" -eq 1 ]]; then
  say "Copiando overlay → $BIN_DIR/"
  install -m 755 "$REPO_DIR/bin/voice-claude-overlay"    "$BIN_DIR/voice-claude-overlay"
  install -m 755 "$REPO_DIR/bin/voice-claude-overlay.py" "$BIN_DIR/voice-claude-overlay.py"
fi

say "Copiando scripts Kokoro → $STATE_DIR/kokoro/"
install -m 755 "$REPO_DIR/kokoro/stream_tts.py" "$STATE_DIR/kokoro/stream_tts.py"
install -m 755 "$REPO_DIR/kokoro/tts.py" "$STATE_DIR/kokoro/tts.py"
install -m 755 "$REPO_DIR/kokoro/daemon.py" "$STATE_DIR/kokoro/daemon.py"

if [[ ! -f "$STATE_DIR/workdir/CLAUDE.md" ]]; then
  say "Copiando CLAUDE.md de ejemplo → $STATE_DIR/workdir/CLAUDE.md (edítalo a tu gusto)"
  install -m 644 "$REPO_DIR/workdir/CLAUDE.md" "$STATE_DIR/workdir/CLAUDE.md"
else
  say "CLAUDE.md del workdir ya existe; no lo sobrescribo. Compara con $REPO_DIR/workdir/CLAUDE.md si quieres actualizarlo."
fi

say "Descargando modelo Kokoro (~325 MB) si falta"
if [[ ! -s "$STATE_DIR/kokoro/kokoro-v1.0.onnx" ]]; then
  curl -fL --progress-bar -o "$STATE_DIR/kokoro/kokoro-v1.0.onnx" "$KOKORO_MODEL_URL"
else
  say "kokoro-v1.0.onnx ya existe ($(du -h "$STATE_DIR/kokoro/kokoro-v1.0.onnx" | cut -f1))"
fi

say "Descargando voices.bin (~28 MB) si falta"
if [[ ! -s "$STATE_DIR/kokoro/voices-v1.0.bin" ]]; then
  curl -fL --progress-bar -o "$STATE_DIR/kokoro/voices-v1.0.bin" "$KOKORO_VOICES_URL"
else
  say "voices-v1.0.bin ya existe ($(du -h "$STATE_DIR/kokoro/voices-v1.0.bin" | cut -f1))"
fi

say "Creando virtualenv en $STATE_DIR/venv (si falta)"
if [[ ! -x "$STATE_DIR/venv/bin/python" ]]; then
  python3 -m venv "$STATE_DIR/venv"
fi

say "Instalando dependencias Python (kokoro-onnx, soundfile, numpy)"
"$STATE_DIR/venv/bin/pip" install --quiet --upgrade pip
"$STATE_DIR/venv/bin/pip" install --quiet -r "$REPO_DIR/requirements.txt"

if [[ "$ENABLE_SOUND" -eq 1 ]]; then
  say "Generando sonidos de estado → $STATE_DIR/sounds/"
  install -m 644 "$REPO_DIR/sounds/generate.py" "$STATE_DIR/sounds/generate.py"
  "$STATE_DIR/venv/bin/python" "$STATE_DIR/sounds/generate.py"
fi

say "Generando UUIDs de sesión Claude (si faltan)"
[[ -s "$STATE_DIR/session.id" ]]      || uuidgen > "$STATE_DIR/session.id"
[[ -s "$STATE_DIR/session-full.id" ]] || uuidgen > "$STATE_DIR/session-full.id"

say "Listo."
cat <<EOF

Próximos pasos:

  1. Configura Handy (\`handy\` en el menú):
       - Output → Paste method: "External script"
       - External script path: $BIN_DIR/voice-claude-handler.sh
       - Audio → Microphone: elige el tuyo
     O edita $HOME/.local/share/com.pais.handy/settings_store.json
     (con Handy cerrado) usando examples/handy-settings-relevant.json como guía.

  2. Agrega los atajos a Hyprland:
       - lua (Omarchy):  examples/hyprland-bindings.lua  →  ~/.config/hypr/bindings.lua
       - conf clásico:   examples/hyprland-bindings.conf →  ~/.config/hypr/hyprland.conf
     Recarga Hyprland: hyprctl reload

  3. (Opcional) Fija el sink de audio del TTS si quieres reproducir en uno
     específico (HDMI, auriculares, etc.). Lista los disponibles con
     \`pactl list short sinks\` y exporta en tu shell:

       export VOICE_CLAUDE_SINK="alsa_output.pci-0000_XX_00.X.hdmi-stereo"

     Si no lo defines, usa el sink default del sistema.

  4. Edita $STATE_DIR/workdir/CLAUDE.md con tus apps y atajos personales.

  5. Asegúrate de tener una sesión Claude Code logueada: \`claude\` una vez para
     verificar que el CLI funciona.

  6. Prueba: presiona Alt+Z, habla algo, suelta. Deberías oír la respuesta
     por el sink configurado. Logs en $STATE_DIR/logs/handler.log.

EOF

if [[ "$ENABLE_OVERLAY" -eq 1 ]]; then
  cat <<EOF
  7. Overlay de estado: un punto coloreado arriba-derecha que indica
     escuchando (verde), pensando (ámbar), contestando (azul) o error (rojo).
     Arranca con: \`exec-once = $BIN_DIR/voice-claude-overlay\` en Hyprland
     (ya incluido en los ejemplos del paso 2).
     Test manual: \`$BIN_DIR/voice-claude-overlay &\` y \`echo speaking > $STATE_DIR/state\`.

EOF
fi

if [[ "$ENABLE_SOUND" -eq 1 ]]; then
  cat <<EOF
  8. Sonidos de estado (en $STATE_DIR/sounds/):
       - listening_start.wav  al presionar Alt+Z/Super+Z (chirp ascendente)
       - listening_stop.wav   al terminar de grabar / empezar a procesar
       - thinking.wav         loop suave mientras Claude genera la respuesta
     Funcionan incluso con fullscreen exclusivo (audio no pasa por compositor).
     Para regenerar: \`python3 $STATE_DIR/sounds/generate.py\`

EOF
fi

cat <<EOF
⚠️  El modo Super+Z corre Claude con una whitelist explícita de comandos
   (hyprctl, pactl, omarchy*, steam, etc.) y tools no destructivas
   (Read/Write/Edit/WebFetch/WebSearch). rm/sudo/chmod/dd están bloqueados.
   Una transcripción mal interpretada igual puede mover/editar archivos o
   abrir apps — revisá CLAUDE_FULL_BASH_ALLOW en el handler si querés
   restringir más.
EOF
