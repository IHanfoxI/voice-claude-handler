🇪🇸 [Español](README.md) &nbsp;·&nbsp; 🇬🇧 English &nbsp;·&nbsp; [🇧🇷 Português](README.pt.md) &nbsp;·&nbsp; [🇩🇪 Deutsch](README.de.md) &nbsp;·&nbsp; [🇫🇷 Français](README.fr.md) &nbsp;·&nbsp; [🇨🇳 中文](README.zh.md) &nbsp;·&nbsp; [🟩 Esperanto](README.eo.md)

---

# voice-claude-handler

Voice assistant that dictates to **Claude Code** from any app (even fullscreen games). Your question goes out as voice, the answer comes back as voice — **without** typing text into the focused window and **without** stealing focus.

```
keybind → Handy (STT) → this handler → Claude Code → Kokoro (TTS) → audio
```

Built for people who want to ask Claude something while gaming, video editing, or with their hands busy. Designed for Linux + Hyprland + Wayland, but adaptable to any setup that can launch a script from a shortcut.

## What does it do?

- **Alt+Z (quick):** Claude Haiku 4.5 with `--allowedTools Read`. For quick, cheap queries.
- **Super+Z (full):** Claude Opus 4.7 with an explicit command whitelist (`hyprctl`, `pactl`, `playerctl`, `omarchy*`, `steam`, `uwsm-app`, `setsid`, `notify-send`, `ls/cat/grep/find/jq/du/df`, etc.) plus non-destructive tools (`Read`, `Write`, `Edit`, `WebFetch`, `WebSearch`). For requesting actions: "open Spotify", "how big is the downloads folder", "pause the video".
- **Alt+Shift+Z (cancel):** kills the in-progress response (TTS + Claude + synthesis) if it started answering something you don't want to wait for.
- **Lazy screenshot:** if your question has visual keywords ("what does that window say", "read this error", "that button"), it takes a screenshot with `grim` and sends it with the question. Otherwise it skips it — saves ~500ms and ~3k tokens per invocation.
- **Streaming TTS:** Claude's response is synthesized with [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) sentence by sentence as it's generated. TTFA ~0.3s.
- **Persistent sessions:** each mode maintains its own Claude Code session (fixed UUID), so Claude remembers context between questions.

## Requirements

| Component | Purpose |
|---|---|
| [Claude Code CLI](https://claude.com/claude-code) | the brain |
| [Handy](https://handy.computer/) | local STT with Parakeet v3 (or your model of choice) |
| Hyprland (or any WM with global shortcuts) | for Alt+Z / Super+Z |
| `grim` | Wayland screenshots |
| `paplay` (pulseaudio / pipewire-pulse) | audio playback |
| `jq`, `iconv`, `notify-send` | handler utilities |
| Python 3.10+ | venv for Kokoro |

Tested on CachyOS + Hyprland + Omarchy. Should work on any Arch derivative; on other Linux distros with Wayland too, adjusting package names.

## Installation

```bash
git clone git@github.com:IHanfoxI/voice-claude-handler.git
cd voice-claude-handler
./install.sh
```

The installer:
- Copies `bin/voice-claude-handler.sh` to `~/.local/bin/`.
- Copies Python scripts to `~/.local/share/voice-claude/kokoro/`.
- Downloads the Kokoro model (~325 MB) and voices (~28 MB) to the same directory.
- Creates a venv in `~/.local/share/voice-claude/venv` with `kokoro-onnx`, `soundfile`, `numpy`.
- Generates the Claude session UUIDs.
- Prints the final steps (configure Handy + Hyprland).

## Configuration

### 1. Handy

Open Handy → **Settings**:
- **Output → Paste method:** `External script`
- **Output → External script path:** `~/.local/bin/voice-claude-handler.sh`
- **Audio → Microphone:** choose yours
- **General → App language:** whatever you speak

If you prefer editing the JSON directly (with Handy **closed**), see `examples/handy-settings-relevant.json` for the relevant keys. **Don't overwrite the full file**: Handy manages it and has defaults you don't want to break.

### 2. Hyprland (shortcuts)

Add the two bindings to your config:

- **Omarchy / lua:** copy `examples/hyprland-bindings.lua` to `~/.config/hypr/bindings.lua`.
- **Classic hyprland.conf:** copy `examples/hyprland-bindings.conf` to `~/.config/hypr/hyprland.conf`.

Reload: `hyprctl reload`.

### 3. (Optional) Fixed audio sink

By default TTS outputs to the system default sink. If you want to force a specific one (e.g. monitor speakers via HDMI), export:

```bash
# List available sinks
pactl list short sinks

# Choose one and export in your shell or in the shortcut
export VOICE_CLAUDE_SINK="alsa_output.pci-0000_XX_00.X.hdmi-stereo"
```

Other variables: `VOICE_CLAUDE_VOICE` (default `ef_dora+af_bella`), `VOICE_CLAUDE_SPEED` (default `1.3`).

### 4. Workdir CLAUDE.md

The handler runs `cd ~/.local/share/voice-claude/workdir` before calling Claude, so the `CLAUDE.md` there is automatically loaded as context. Edit it with your apps, shortcuts, favorite Steam games, etc. — Claude uses it to know how to act on your specific system.

The installer copies an example. Replace the placeholders with your data.

## Usage

1. Press **Alt+Z** (quick) or **Super+Z** (full).
2. Speak. Handy listens until you press the shortcut again (or detects silence, depending on your config).
3. Release. Handy transcribes → handler decides if a screenshot is needed → calls Claude → you hear the response via TTS.

Logs: `~/.local/share/voice-claude/logs/handler.log`.

## ⚠️ About Super+Z mode (full)

The full mode runs Claude Opus with `--allowedTools` pointing to an **explicit whitelist**:

- **Bash:** only `hyprctl`, `pactl`, `playerctl`, `wpctl`, `brightnessctl`, `omarchy*`, `uwsm-app`, `steam`, `setsid`, `notify-send`, `ls`, `cat`, `grep`, `rg`, `find`, `jq`, `du`, `df`, `date`, `uptime`, `free`, `echo`, `printf`.
- **Tools:** `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`, `WebSearch`.
- **Blocked:** `rm`, `sudo`, `chmod`, `chown`, `dd`, `mv`, and any other unlisted Bash command.

If a transcription betrays you ("delete the downloads folder" misheard), Claude **has no permission** to cause damage. The sys-prompt asks it to say "I can't" and propose an alternative if you ask for something out of scope.

Even so: the scope is generous. It can move, edit and create files (`Edit`, `Write`), open any Steam game, run `omarchy *`. Use judgment. If you want to add commands, edit `CLAUDE_FULL_BASH_ALLOW` in `bin/voice-claude-handler.sh`. **Never use `Bash(*:*)`** — it's equivalent to `--dangerously-skip-permissions`.

Quick mode (Alt+Z) only allows `Read`, so it's completely safe.

## Troubleshooting

**`paplay: Failed to open audio file` / `Connection refused`**
Your system uses pipewire but without `pipewire-pulse`, or pulseaudio isn't running. Install `pipewire-pulse` (on Arch: `sudo pacman -S pipewire-pulse`) and restart the session. Verify with `pactl info` that it says "Server Name: PulseAudio (on PipeWire ...)".

**`paplay: Failure: No such entity` or audio comes out of the wrong sink**
The `VOICE_CLAUDE_SINK` you exported doesn't exist or changed. List current ones with `pactl list short sinks`, copy the exact name (second column) and re-export. If you don't need a specific sink, don't export anything — the handler uses the system default.

**Handy records but nothing happens / I hear no response**
1. Check `~/.local/share/voice-claude/logs/handler.log` — the full trace is there.
2. Confirm `paste_method` is `"external_script"` and `external_script_path` points to the correct `voice-claude-handler.sh` (output of `cat ~/.local/share/com.pais.handy/settings_store.json | jq '.settings.paste_method, .settings.external_script_path'`).
3. If the log says `claude: command not found`, add the CLI path to the global PATH or use an absolute path in the handler (Handy inherits the environment from the process that launched it, normally the Hyprland session — the `Alt+Z` shortcut loads your login shell's PATH).

**`claude: command not found` from the handler even though it works in the terminal**
The Handy process may not have your shell rc loaded. Solutions: (a) install Claude Code globally (`/usr/local/bin/claude` or equivalent), or (b) edit the handler and replace `claude` with the absolute path (`/home/$USER/.local/bin/claude` or wherever you have it).

**The first audio chunk cuts off / the voice swallows the first syllable**
The HDMI sink was in suspend. The handler does pre-warm but sometimes it's not enough. Increase `FIRST_CHUNK_LEAD_SILENCE_S` in `kokoro/stream_tts.py` (from 0.2s to 0.4s, for example) or prevent the sink from suspending with `pactl unload-module module-suspend-on-idle`.

**Kokoro takes a long time the first time**
Model loading is ~1-2s on CPU. It's a one-time cost per invocation. To eliminate it you'd need to run Kokoro as a persistent daemon — it's on the roadmap but not trivial.

**Imprecise transcription of technical words (command names, apps)**
Handy supports "custom words" in its configuration. Add `hyprctl`, `pactl`, the names of the apps you use most, etc. You can also try another Whisper/Parakeet model from Handy's UI.

**Alt+Z does nothing**
Check that Hyprland reloaded the binding: `hyprctl reload` and review the output for errors. Verify the shortcut doesn't conflict with another: `hyprctl binds | grep -i ',Z,'`.

**Full mode responds "I don't have permission"**
The whitelist doesn't include the command you need. Add it to `CLAUDE_FULL_BASH_ALLOW` in the handler with the pattern `Bash(command:*)`. Don't use `Bash(*:*)` unless you know exactly what you're doing.

## Customization

- **Voice:** `VOICE_CLAUDE_VOICE` accepts names (`ef_dora`, `em_alex`, `if_sara`, etc.) or blends (`ef_dora+af_bella`). Full list in [the kokoro-onnx README](https://github.com/thewh1teagle/kokoro-onnx).
- **Speed:** `VOICE_CLAUDE_SPEED` (default `1.3`). Values between `0.8` and `1.5` usually sound good.
- **Model / effort:** edit the mode `if/else` block in `voice-claude-handler.sh`.
- **Full mode whitelist:** `CLAUDE_FULL_BASH_ALLOW` and `CLAUDE_FULL_TOOLS_ALLOW` at the start of the `if [[ "$MODE" == "full" ]]` block in the handler. Add or remove commands to fit your workflow.
- **Screenshot keywords:** adjust `SCREEN_KW_RE` and `SCREEN_PHRASE_RE` in the handler. The current list is in Spanish; add your own.

## Credits / inspiration

- Original idea inspired by [a NateGentile video](https://www.youtube.com/@NateGentile) about voice assistants for Claude.
- STT: [Handy](https://handy.computer/) (Parakeet v3 local).
- TTS: [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) by [@thewh1teagle](https://github.com/thewh1teagle).
- CLI: [Claude Code](https://claude.com/claude-code) by Anthropic.

## License

MIT. See `LICENSE`.
