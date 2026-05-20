-- Snippet para ~/.config/hypr/bindings.lua (Omarchy/Hyprland con plugin lua).
-- Si usas hyprland.conf clásico, traduce a sintaxis `bind = ...,exec,sh -c ...`.
--
-- Voice → Claude (quick): Alt+Z. Haiku + Read only. Para preguntas simples y rápidas.
hl.bind(
  "ALT + Z",
  hl.dsp.exec_cmd("sh -c 'echo quick > $HOME/.local/share/voice-claude/mode; handy --toggle-transcription'"),
  { description = "Voice → Claude (quick: haiku, Read only)" }
)

-- Voice → Claude (full): Super+Z. Opus + TODAS las tools + permisos saltados.
-- ATENCIÓN: puede ejecutar Bash, Edit, Write, WebFetch, etc. sin confirmar.
-- Una mala transcripción puede disparar acciones no deseadas. Úsalo a sabiendas.
hl.bind(
  "SUPER + Z",
  hl.dsp.exec_cmd("sh -c 'echo full > $HOME/.local/share/voice-claude/mode; handy --toggle-transcription'"),
  { description = "Voice → Claude (full: opus, todas las tools)" }
)

-- Window rules para que la ventana de Handy no robe foco al juego/app activa.
hl.window_rule({ match = { class = "handy" }, no_initial_focus = true })
hl.window_rule({ match = { class = "handy" }, no_focus = true })
