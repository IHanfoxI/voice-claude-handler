# voice-claude-handler

Voice assistant que dicta a **Claude Code** desde cualquier app (incluso juegos en fullscreen). Tu pregunta sale por voz, la respuesta vuelve por voz — **sin** escribir texto en la ventana enfocada y **sin** robarle foco.

```
keybind → Handy (STT) → este handler → Claude Code → Kokoro (TTS) → audio
```

Construido para gente que quiere preguntarle algo a Claude mientras juega, edita video, o tiene las manos ocupadas. Pensado en Linux + Hyprland + Wayland, pero se adapta a cualquier setup que pueda lanzar un script desde un atajo.

## ¿Qué hace?

- **Alt+Z (quick):** Claude Haiku 4.5 con `--allowedTools Read`. Para consultas rápidas y baratas.
- **Super+Z (full):** Claude Opus 4.7 con `--dangerously-skip-permissions` — TODAS las tools (Bash, Edit, Write, WebFetch…) sin confirmación. Para pedir acciones: "abre Spotify", "cuánto pesa la carpeta de descargas", "pausa el video".
- **Captura lazy:** si tu pregunta tiene palabras visuales ("qué dice esa ventana", "lee este error", "ese botón"), toma un screenshot con `grim` y lo manda con la pregunta. Si no, lo omite — ahorra ~500ms y ~3k tokens por invocación.
- **TTS streaming:** la respuesta de Claude se va sintetizando con [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) por oraciones a medida que se genera. TTFA ~0.3s.
- **Sesiones persistentes:** cada modo mantiene su propia sesión de Claude Code (UUID fijo), así Claude recuerda el contexto entre preguntas.

## Requisitos

| Componente | Para qué |
|---|---|
| [Claude Code CLI](https://claude.com/claude-code) | el cerebro |
| [Handy](https://handy.computer/) | STT local con Parakeet v3 (o el modelo que prefieras) |
| Hyprland (o cualquier WM con atajos globales) | para Alt+Z / Super+Z |
| `grim` | capturas de Wayland |
| `paplay` (pulseaudio / pipewire-pulse) | reproducción de audio |
| `jq`, `iconv`, `notify-send` | utilidades del handler |
| Python 3.10+ | venv para Kokoro |

Lo probé en CachyOS + Hyprland + Omarchy. Debería funcionar en cualquier Arch derivative; en otras distros Linux con Wayland también, ajustando los nombres de paquetes.

## Instalación

```bash
git clone git@github.com:IHanfoxI/voice-claude-handler.git
cd voice-claude-handler
./install.sh
```

El instalador:
- Copia `bin/voice-claude-handler.sh` a `~/.local/bin/`.
- Copia los scripts Python a `~/.local/share/voice-claude/kokoro/`.
- Descarga el modelo Kokoro (~325 MB) y voices (~28 MB) en el mismo directorio.
- Crea un venv en `~/.local/share/voice-claude/venv` con `kokoro-onnx`, `soundfile`, `numpy`.
- Genera los UUIDs de las sesiones de Claude.
- Te imprime los pasos finales (configurar Handy + Hyprland).

## Configuración

### 1. Handy

Abre Handy → **Settings**:
- **Output → Paste method:** `External script`
- **Output → External script path:** `~/.local/bin/voice-claude-handler.sh`
- **Audio → Microphone:** elige el tuyo
- **General → App language:** el que hables

Si prefieres editar el JSON directamente (con Handy **cerrado**), mira `examples/handy-settings-relevant.json` para las claves que importan. **No sobrescribas el archivo completo**: Handy lo gestiona y tiene defaults que no quieres romper.

### 2. Hyprland (atajos)

Agrega los dos bindings a tu config:

- **Omarchy / lua:** copia `examples/hyprland-bindings.lua` a `~/.config/hypr/bindings.lua`.
- **Hyprland.conf clásico:** copia `examples/hyprland-bindings.conf` a `~/.config/hypr/hyprland.conf`.

Recarga: `hyprctl reload`.

### 3. (Opcional) Sink de audio fijo

Por default el TTS sale al sink default del sistema. Si querés forzar otro (p.ej. los parlantes del monitor por HDMI), exporta:

```bash
# Lista sinks disponibles
pactl list short sinks

# Elige uno y exporta en tu shell o en el atajo
export VOICE_CLAUDE_SINK="alsa_output.pci-0000_XX_00.X.hdmi-stereo"
```

Otras variables: `VOICE_CLAUDE_VOICE` (default `ef_dora+af_bella`), `VOICE_CLAUDE_SPEED` (default `1.3`).

### 4. CLAUDE.md del workdir

El handler hace `cd ~/.local/share/voice-claude/workdir` antes de llamar a Claude, así que el `CLAUDE.md` que está ahí se carga automáticamente como contexto. Edítalo con tus apps, atajos, juegos de Steam favoritos, etc. — Claude lo usa para saber cómo accionar cosas en tu sistema específico.

El instalador copia un ejemplo. Sustituye los placeholders por tus datos.

## Uso

1. Presiona **Alt+Z** (quick) o **Super+Z** (full).
2. Habla. Handy escucha hasta que vuelves a presionar el atajo (o detecta silencio, según tu config).
3. Suelta. Handy transcribe → el handler decide si necesita captura → llama a Claude → escuchas la respuesta por TTS.

Logs: `~/.local/share/voice-claude/logs/handler.log`.

## ⚠️ Advertencia sobre el modo Super+Z (full)

El modo full corre Claude Opus con `--dangerously-skip-permissions`. Esto significa que Claude puede:

- Ejecutar comandos de shell sin confirmación (`Bash`)
- Crear, editar y borrar archivos (`Write`, `Edit`)
- Acceder a internet (`WebFetch`)
- Lo que sea que el CLI le permita

Si la transcripción de tu voz es imprecisa (ruido de fondo, micrófono malo, palabras ambiguas), Claude puede ejecutar la acción equivocada. **No uses el modo full para tareas críticas, no lo uses bajo influencia, no lo uses si no sabés exactamente qué le acabás de pedir.**

El modo quick (Alt+Z) solo permite `Read`, así que es seguro probarlo sin riesgo.

## Personalización

- **Voz:** `VOICE_CLAUDE_VOICE` acepta nombres (`ef_dora`, `em_alex`, `if_sara`, etc.) o blends (`ef_dora+af_bella`). Lista completa en [el README de kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx).
- **Modelo / effort:** edita el bloque `if/else` del modo en `voice-claude-handler.sh`.
- **Keywords para captura:** ajusta `SCREEN_KW_RE` y `SCREEN_PHRASE_RE` en el handler. La lista actual está en español; añade las tuyas.

## Créditos / inspiración

- Idea original inspirada en [un video de NateGentile](https://www.youtube.com/@NateGentile) sobre asistentes de voz para Claude.
- STT: [Handy](https://handy.computer/) (Parakeet v3 local).
- TTS: [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) por [@thewh1teagle](https://github.com/thewh1teagle).
- CLI: [Claude Code](https://claude.com/claude-code) de Anthropic.

## Licencia

MIT. Ver `LICENSE`.
