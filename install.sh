#!/usr/bin/env bash
# Instala voice-claude-handler en ~/.local/share/voice-claude y ~/.local/bin.
# Descarga los modelos Kokoro, crea el venv y genera los UUIDs de sesión.
# Idempotente: puedes correrlo varias veces.

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

say "Creando directorios en $STATE_DIR y $BIN_DIR"
mkdir -p "$STATE_DIR"/{kokoro,workdir,logs,tts_chunks,voices} "$BIN_DIR"

say "Copiando handler.sh → $BIN_DIR/voice-claude-handler.sh"
install -m 755 "$REPO_DIR/bin/voice-claude-handler.sh" "$BIN_DIR/voice-claude-handler.sh"

say "Copiando scripts Kokoro → $STATE_DIR/kokoro/"
install -m 755 "$REPO_DIR/kokoro/stream_tts.py" "$STATE_DIR/kokoro/stream_tts.py"
install -m 755 "$REPO_DIR/kokoro/tts.py" "$STATE_DIR/kokoro/tts.py"

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

⚠️  El modo Super+Z corre Claude con --dangerously-skip-permissions:
   puede ejecutar comandos en tu sistema sin confirmar. Una transcripción
   mal interpretada puede disparar acciones destructivas. Úsalo solo si
   entendés y aceptás ese riesgo.
EOF
