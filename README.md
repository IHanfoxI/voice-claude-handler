🇪🇸 Español &nbsp;·&nbsp; [🇬🇧 English](README.en.md) &nbsp;·&nbsp; [🇧🇷 Português](README.pt.md) &nbsp;·&nbsp; [🇩🇪 Deutsch](README.de.md) &nbsp;·&nbsp; [🇫🇷 Français](README.fr.md) &nbsp;·&nbsp; [🇨🇳 中文](README.zh.md) &nbsp;·&nbsp; [🟩 Esperanto](README.eo.md)

---

# voice-claude-handler

Voice assistant que dicta a **Claude Code** desde cualquier app (incluso juegos en fullscreen). Tu pregunta sale por voz, la respuesta vuelve por voz — **sin** escribir texto en la ventana enfocada y **sin** robarle foco.

```
keybind → Handy (STT) → este handler → Claude Code → Kokoro (TTS) → audio
```

Construido para gente que quiere preguntarle algo a Claude mientras juega, edita video, o tiene las manos ocupadas. Pensado en Linux + Hyprland + Wayland, pero se adapta a cualquier setup que pueda lanzar un script desde un atajo.

## ¿Qué hace?

- **Alt+Z (quick):** Claude Haiku 4.5 con `--allowedTools Read`. Para consultas rápidas y baratas.
- **Super+Z (full):** Claude Opus 4.7 con una whitelist explícita de comandos (`hyprctl`, `pactl`, `playerctl`, `omarchy*`, `steam`, `uwsm-app`, `setsid`, `notify-send`, `ls/cat/grep/find/jq/du/df`, etc.) más las tools no destructivas (`Read`, `Write`, `Edit`, `WebFetch`, `WebSearch`). Para pedir acciones: "abre Spotify", "cuánto pesa la carpeta de descargas", "pausa el video".
- **Alt+Shift+Z (cancel):** cancela la respuesta en curso con señal cooperativa — `stream_tts.py` para entre oraciones y termina el `paplay` actual.
- **Captura lazy:** si tu pregunta tiene palabras visuales ("qué dice esa ventana", "lee este error", "ese botón"), toma un screenshot con `grim` y lo manda con la pregunta. Si no, lo omite — ahorra ~500ms y ~3k tokens por invocación.
- **TTS streaming con pipeline 3 hilos:** síntesis y reproducción corren en paralelo (hilo stdin, hilo synth, hilo player). Daemon Kokoro persistente elimina ~1-2s de carga de modelo. TTFA ~0.3s.
- **Sonidos de estado:** chirp ascendente al grabar, descendente al procesar, campana suave en loop mientras Claude piensa. Funcionan con fullscreen exclusivo (audio, no overlay).
- **Sesiones persistentes:** cada modo mantiene su propia sesión de Claude Code (UUID fijo), así Claude recuerda el contexto entre preguntas.
- **Reset por voz:** di "limpia la conversación" (o "nueva conversación", "borra el historial") para empezar desde cero — respuesta instantánea por TTS, sin llamar a Claude.

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

El instalador te pregunta qué indicadores de estado querés (overlay visual, sonidos, ambos o ninguno). Luego:
- Copia `bin/voice-claude-handler.sh` y scripts Python a sus destinos.
- Descarga el modelo Kokoro (~325 MB) y voices (~28 MB).
- Crea un venv con `kokoro-onnx`, `soundfile`, `numpy`, `pyyaml`.
- Genera los UUIDs de las sesiones de Claude.
- Copia `config.yaml` de ejemplo a `~/.local/share/voice-claude/config.yaml`.
- Te imprime los pasos finales.

Flags para instalación no interactiva: `--no-overlay`, `--no-sound`, `--no-extras`.

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

### 3. (Opcional) config.yaml

El instalador copia una plantilla documentada a `~/.local/share/voice-claude/config.yaml`. Ahí podés cambiar voz, velocidad, sink de audio, y las palabras que disparan capturas de pantalla:

```yaml
tts:
  voice: "ef_dora+af_bella"
  speed: 1.3
  sink: ""           # vacío = sink default. Ej: "alsa_output.pci-0000_XX_00.X.hdmi-stereo"
screen_keywords:
  words: [pantalla, ventana, ...]   # agrega los tuyos
  phrases: ["que dice", ...]
```

Las env vars (`VOICE_CLAUDE_VOICE`, `VOICE_CLAUDE_SPEED`, `VOICE_CLAUDE_SINK`) siguen funcionando y tienen prioridad sobre el YAML.

### 4. CLAUDE.md del workdir

El handler hace `cd ~/.local/share/voice-claude/workdir` antes de llamar a Claude, así que el `CLAUDE.md` que está ahí se carga automáticamente como contexto. Edítalo con tus apps, atajos, juegos de Steam favoritos, etc. — Claude lo usa para saber cómo accionar cosas en tu sistema específico.

El instalador copia un ejemplo. Sustituye los placeholders por tus datos.

## Uso

1. Presiona **Alt+Z** (quick) o **Super+Z** (full).
2. Habla. Handy escucha hasta que vuelves a presionar el atajo (o detecta silencio, según tu config).
3. Suelta. Handy transcribe → el handler decide si necesita captura → llama a Claude → escuchas la respuesta por TTS.

Logs: `~/.local/share/voice-claude/logs/handler.log`.

## Overlay de estado (opcional)

Un punto pequeño arriba a la derecha (layer-shell, visible incluso sobre fullscreen) que cambia de color según lo que está haciendo el sistema:

| Color | Estado |
|---|---|
| 🟢 verde | Handy escuchando tu voz |
| 🟡 ámbar | Claude pensando (generando respuesta) |
| 🔵 azul | TTS reproduciendo la respuesta |
| 🔴 rojo | error (vuelve a ocultarse en ~2.5s) |
| (oculto) | idle |

Requiere `gtk4-layer-shell` + `python-gobject` (Arch: `sudo pacman -S gtk4-layer-shell python-gobject`). Para autostart en Hyprland, los snippets de `examples/hyprland-bindings.{lua,conf}` incluyen `exec-once`. Test manual:

```bash
voice-claude-overlay &
echo speaking > ~/.local/share/voice-claude/state
```

El estado lo escriben automáticamente el handler, `stream_tts.py`, el cancel y los keybinds (`listening`). Tamaño/posición configurables por env: `VOICE_CLAUDE_OVERLAY_SIZE`, `VOICE_CLAUDE_OVERLAY_MARGIN_TOP`, `VOICE_CLAUDE_OVERLAY_MARGIN_RIGHT`.

## ⚠️ Sobre el modo Super+Z (full)

El modo full corre Claude Opus con `--allowedTools` apuntando a una **whitelist explícita**:

- **Bash:** solo `hyprctl`, `pactl`, `playerctl`, `wpctl`, `brightnessctl`, `omarchy*`, `uwsm-app`, `steam`, `setsid`, `notify-send`, `ls`, `cat`, `grep`, `rg`, `find`, `jq`, `du`, `df`, `date`, `uptime`, `free`, `echo`, `printf`.
- **Tools:** `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`, `WebSearch`.
- **Bloqueado:** `rm`, `sudo`, `chmod`, `chown`, `dd`, `mv`, y cualquier otro Bash no listado.

Si una transcripción te traiciona ("borrar la carpeta de descargas" mal entendido), Claude **no tiene permiso** para hacer destrozos. El sys-prompt le pide que diga "no puedo" y proponga una alternativa si pedís algo fuera del scope.

Aun así: el alcance es generoso. Puede mover, editar y crear archivos (`Edit`, `Write`), abrir cualquier juego de Steam, ejecutar `omarchy *`. Usá criterio. Si querés sumar comandos, editá `CLAUDE_FULL_BASH_ALLOW` en `bin/voice-claude-handler.sh`. **Nunca uses `Bash(*:*)`** — equivale a `--dangerously-skip-permissions`.

El modo quick (Alt+Z) solo permite `Read`, así que es completamente seguro.

## Troubleshooting

**`paplay: Failed to open audio file` / `Connection refused`**
Tu sistema usa pipewire pero sin `pipewire-pulse`, o pulseaudio no está corriendo. Instalá `pipewire-pulse` (en Arch: `sudo pacman -S pipewire-pulse`) y reiniciá la sesión. Verificá con `pactl info` que diga "Server Name: PulseAudio (on PipeWire ...)".

**`paplay: Failure: No such entity` o el audio sale por el sink equivocado**
El `VOICE_CLAUDE_SINK` que exportaste no existe o cambió. Listá los actuales con `pactl list short sinks`, copiá el nombre exacto (segunda columna) y volvé a exportar. Si no necesitás un sink específico, no exportes nada — el handler usa el default del sistema.

**Handy graba pero no pasa nada después / no escucho respuesta**
1. Mirá `~/.local/share/voice-claude/logs/handler.log` — ahí queda toda la traza.
2. Confirmá que `paste_method` esté en `"external_script"` y `external_script_path` apunte al `voice-claude-handler.sh` correcto (output de `cat ~/.local/share/com.pais.handy/settings_store.json | jq '.settings.paste_method, .settings.external_script_path'`).
3. Si el log dice `claude: command not found`, agregá la ruta del CLI al PATH global o usá una ruta absoluta en el handler (Handy hereda el environment del proceso que lo lanzó, normalmente la sesión de Hyprland — el atajo `Alt+Z` carga el PATH de tu shell de login).

**`claude: command not found` desde el handler aunque funciona en la terminal**
El proceso de Handy puede no tener tu shell rc cargado. Soluciones: (a) instalá Claude Code globalmente (`/usr/local/bin/claude` o equivalente), o (b) editá el handler y reemplazá `claude` por la ruta absoluta (`/home/$USER/.local/bin/claude` o donde lo tengas).

**El primer chunk de audio se corta / la voz se "come" la primera sílaba**
El sink HDMI estaba en suspend. El handler hace pre-warm pero a veces no alcanza. Aumentá `FIRST_CHUNK_LEAD_SILENCE_S` en `kokoro/stream_tts.py` (de 0.2s a 0.4s, por ejemplo) o evitá que el sink suspenda con `pactl unload-module module-suspend-on-idle`.

**Kokoro tarda mucho / la respuesta tiene latencia alta**
El daemon persistente debería eliminar ~1-2s de carga de modelo. Verificá que esté corriendo: `python3 ~/.local/share/voice-claude/kokoro/daemon.py --ping`. Si no responde, en la próxima invocación el handler lo reinicia automáticamente. Logs del daemon: `~/.local/share/voice-claude/logs/daemon.log`.

**Transcripción imprecisa de palabras técnicas (nombres de comandos, apps)**
Handy soporta "custom words" en su configuración. Agregá ahí `hyprctl`, `pactl`, los nombres de las apps que más usás, etc. También podés probar otro modelo Whisper/Parakeet desde la UI de Handy.

**Alt+Z no hace nada**
Verificá que Hyprland recargó el binding: `hyprctl reload` y revisá la salida por errores. Comprobá que el atajo no choque con otro: `hyprctl binds | grep -i ',Z,'`.

**El modo full responde "no tengo permiso"**
La whitelist no incluye el comando que necesitás. Agregalo a `CLAUDE_FULL_BASH_ALLOW` en el handler con el patrón `Bash(comando:*)`. No uses `Bash(*:*)` salvo que sepas exactamente lo que estás haciendo.

## Personalización

- **Voz / velocidad / sink:** edita `~/.local/share/voice-claude/config.yaml` (sección `tts`) o exporta `VOICE_CLAUDE_VOICE`, `VOICE_CLAUDE_SPEED`, `VOICE_CLAUDE_SINK`. Voces disponibles en [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx); acepta blends como `ef_dora+af_bella`.
- **Keywords para captura:** en `config.yaml`, sección `screen_keywords.words` y `screen_keywords.phrases`. Agregá los tuyos; quitá los que te den falsos positivos.
- **Modelo / effort:** sección `models.quick` / `models.full` en `config.yaml`, o directamente en `voice-claude-handler.sh`.
- **Whitelist del modo full:** `CLAUDE_FULL_BASH_ALLOW` y `CLAUDE_FULL_TOOLS_ALLOW` en el handler. Agregá o quitá según tu workflow. **Nunca uses `Bash(*:*)`** — equivale a `--dangerously-skip-permissions`.

## Créditos / inspiración

- Idea original inspirada en [un video de NateGentile](https://www.youtube.com/@NateGentile) sobre asistentes de voz para Claude.
- STT: [Handy](https://handy.computer/) (Parakeet v3 local).
- TTS: [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) por [@thewh1teagle](https://github.com/thewh1teagle).
- CLI: [Claude Code](https://claude.com/claude-code) de Anthropic.

## Licencia

MIT. Ver `LICENSE`.
