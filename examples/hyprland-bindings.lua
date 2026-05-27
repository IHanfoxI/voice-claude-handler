-- Snippet para ~/.config/hypr/bindings.lua (Omarchy/Hyprland con plugin lua).
-- Si usas hyprland.conf clásico, traduce a sintaxis `bind = ...,exec,sh -c ...`.

-- Autostart del overlay de estado (punto coloreado arriba-derecha que indica
-- escuchando/pensando/contestando/error). Necesita gtk4-layer-shell instalado.
hl.exec_once("$HOME/.local/bin/voice-claude-overlay")

-- Voice → Claude (quick): Alt+Z. Haiku + Read only. Para preguntas simples y rápidas.
-- Antes de invocar Handy escribimos "listening" para que el overlay marque verde.
hl.bind(
  "ALT + Z",
  hl.dsp.exec_cmd("sh -c 'echo listening > $HOME/.local/share/voice-claude/state; echo quick > $HOME/.local/share/voice-claude/mode; handy --toggle-transcription'"),
  { description = "Voice → Claude (quick: haiku, Read only)" }
)

-- Voice → Claude (full): Super+Z. Opus + whitelist explícita de Bash/tools.
-- Puede controlar el sistema (hyprctl, pactl, playerctl, omarchy*, steam,
-- uwsm-app, etc.) y editar archivos, pero NO ejecuta rm, sudo, chmod ni dd.
hl.bind(
  "SUPER + Z",
  hl.dsp.exec_cmd("sh -c 'echo listening > $HOME/.local/share/voice-claude/state; echo full > $HOME/.local/share/voice-claude/mode; handy --toggle-transcription'"),
  { description = "Voice → Claude (full: opus, whitelist de comandos)" }
)

-- Cancelar respuesta en curso (mata TTS + claude + stream_tts, resetea overlay).
hl.bind(
  "ALT SHIFT + Z",
  hl.dsp.exec_cmd("$HOME/.local/bin/voice-claude-cancel.sh"),
  { description = "Voice → Claude: cancelar respuesta en curso" }
)

-- Window rules para que la ventana de Handy no robe foco al juego/app activa.
hl.window_rule({ match = { class = "handy" }, no_initial_focus = true })
hl.window_rule({ match = { class = "handy" }, no_focus = true })
