🇪🇸 [Español](README.md) &nbsp;·&nbsp; [🇬🇧 English](README.en.md) &nbsp;·&nbsp; [🇧🇷 Português](README.pt.md) &nbsp;·&nbsp; 🇩🇪 Deutsch &nbsp;·&nbsp; [🇫🇷 Français](README.fr.md) &nbsp;·&nbsp; [🇨🇳 中文](README.zh.md) &nbsp;·&nbsp; [🟩 Esperanto](README.eo.md)

---

# voice-claude-handler

Sprachassistent, der **Claude Code** aus jeder App heraus steuert (auch aus Vollbild-Spielen). Deine Frage geht als Sprache raus, die Antwort kommt als Sprache zurück — **ohne** Text ins aktive Fenster zu tippen und **ohne** den Fokus zu stehlen.

```
Tastenkürzel → Handy (STT) → dieser Handler → Claude Code → Kokoro (TTS) → Audio
```

Gebaut für Leute, die Claude etwas fragen wollen, während sie spielen, Videos schneiden oder die Hände beschäftigt haben. Konzipiert für Linux + Hyprland + Wayland, aber anpassbar an jedes Setup, das ein Skript per Tastenkürzel starten kann.

## Was macht es?

- **Alt+Z (schnell):** Claude Haiku 4.5 mit `--allowedTools Read`. Für schnelle, günstige Abfragen.
- **Super+Z (vollständig):** Claude Opus 4.7 mit einer expliziten Befehlsliste (`hyprctl`, `pactl`, `playerctl`, `omarchy*`, `steam`, `uwsm-app`, `setsid`, `notify-send`, `ls/cat/grep/find/jq/du/df`, etc.) plus nicht-destruktiven Tools (`Read`, `Write`, `Edit`, `WebFetch`, `WebSearch`). Für Aktionen: „öffne Spotify", „wie groß ist der Downloads-Ordner", „pausiere das Video".
- **Alt+Shift+Z (abbrechen):** bricht die laufende Antwort mit kooperativem Signal ab — `stream_tts.py` stoppt zwischen Sätzen und beendet das aktuelle `paplay`.
- **Lazy Screenshot:** enthält deine Frage visuelle Schlüsselwörter („was steht in dem Fenster", „lies diesen Fehler", „dieser Button"), macht der Handler einen Screenshot mit `grim` und schickt ihn mit. Andernfalls wird er übersprungen — spart ~500ms und ~3k Tokens pro Aufruf.
- **Streaming-TTS mit 3-Thread-Pipeline:** Synthese und Wiedergabe laufen parallel (stdin-Thread, synth-Thread, player-Thread). Persistenter Kokoro-Daemon eliminiert ~1-2s Modell-Ladezeit. TTFA ~0.3s.
- **Statusgeräusche:** aufsteigendes Chirp beim Aufnehmen, absteigendes beim Verarbeiten, sanfte Glocke in Schleife während Claude denkt. Funktionieren mit exklusivem Vollbild (Audio, kein Overlay).
- **Persistente Sitzungen:** jeder Modus hält seine eigene Claude Code-Sitzung (feste UUID), sodass Claude den Kontext zwischen Fragen beibehält.
- **Sprach-Reset:** sage „Unterhaltung löschen" (oder „neue Unterhaltung", „Verlauf löschen") um neu zu beginnen — sofortige TTS-Antwort, kein Claude-Aufruf.

## Voraussetzungen

| Komponente | Zweck |
|---|---|
| [Claude Code CLI](https://claude.com/claude-code) | das Gehirn |
| [Handy](https://handy.computer/) | lokales STT mit Parakeet v3 (oder deinem Modell) |
| Hyprland (oder ein WM mit globalen Tastenkürzeln) | für Alt+Z / Super+Z |
| `grim` | Wayland-Screenshots |
| `paplay` (pulseaudio / pipewire-pulse) | Audiowiedergabe |
| `jq`, `iconv`, `notify-send` | Handler-Hilfsprogramme |
| Python 3.10+ | venv für Kokoro |

Getestet auf CachyOS + Hyprland + Omarchy. Sollte auf jeder Arch-Derivat funktionieren; auch auf anderen Linux-Distros mit Wayland, mit angepassten Paketnamen.

## Installation

```bash
git clone git@github.com:IHanfoxI/voice-claude-handler.git
cd voice-claude-handler
./install.sh
```

Das Installationsskript fragt, welche Statusindikatoren du möchtest (visuelles Overlay, Geräusche, beides oder keins). Danach:
- Kopiert `bin/voice-claude-handler.sh` und Python-Skripte an ihre Ziele.
- Lädt das Kokoro-Modell (~325 MB) und Stimmen (~28 MB) herunter.
- Erstellt ein venv mit `kokoro-onnx`, `soundfile`, `numpy`, `pyyaml`.
- Generiert die Claude-Sitzungs-UUIDs.
- Kopiert `config.yaml`-Vorlage nach `~/.local/share/voice-claude/config.yaml`.
- Gibt die nächsten Schritte aus.

Flags für nicht-interaktive Installation: `--no-overlay`, `--no-sound`, `--no-extras`.

## Konfiguration

### 1. Handy

Handy öffnen → **Settings**:
- **Output → Paste method:** `External script`
- **Output → External script path:** `~/.local/bin/voice-claude-handler.sh`
- **Audio → Microphone:** deins auswählen
- **General → App language:** deine Sprache

Wenn du die JSON-Datei lieber direkt bearbeiten möchtest (bei **geschlossenem** Handy), sieh dir `examples/handy-settings-relevant.json` für die relevanten Schlüssel an. **Die ganze Datei nicht überschreiben**: Handy verwaltet sie und hat Standardwerte, die du nicht kaputt machen möchtest.

### 2. Hyprland (Tastenkürzel)

Füge die beiden Bindings zu deiner Konfiguration hinzu:

- **Omarchy / lua:** kopiere `examples/hyprland-bindings.lua` nach `~/.config/hypr/bindings.lua`.
- **Klassisches hyprland.conf:** kopiere `examples/hyprland-bindings.conf` nach `~/.config/hypr/hyprland.conf`.

Neu laden: `hyprctl reload`.

### 3. (Optional) config.yaml

Das Installationsskript kopiert eine dokumentierte Vorlage nach `~/.local/share/voice-claude/config.yaml`. Dort kannst du Stimme, Geschwindigkeit, Audio-Sink und die Screenshot-Schlüsselwörter ändern:

```yaml
tts:
  voice: "ef_dora+af_bella"
  speed: 1.3
  sink: ""           # leer = System-Standard. Bsp: "alsa_output.pci-0000_XX_00.X.hdmi-stereo"
screen_keywords:
  words: [Bildschirm, Fenster, ...]   # eigene hinzufügen
  phrases: ["was steht", ...]
```

Die Umgebungsvariablen (`VOICE_CLAUDE_VOICE`, `VOICE_CLAUDE_SPEED`, `VOICE_CLAUDE_SINK`) funktionieren weiterhin und haben Vorrang gegenüber dem YAML.

### 4. Workdir CLAUDE.md

Der Handler führt `cd ~/.local/share/voice-claude/workdir` aus, bevor Claude aufgerufen wird, sodass das dortige `CLAUDE.md` automatisch als Kontext geladen wird. Bearbeite es mit deinen Apps, Tastenkürzeln, Lieblings-Steam-Spielen usw. — Claude nutzt es, um zu wissen, wie es in deinem spezifischen System agieren soll.

Das Installationsskript kopiert ein Beispiel. Ersetze die Platzhalter durch deine Daten.

## Verwendung

1. Drücke **Alt+Z** (schnell) oder **Super+Z** (vollständig).
2. Sprich. Handy hört zu, bis du das Kürzel erneut drückst (oder Stille erkennt, je nach Konfiguration).
3. Loslassen. Handy transkribiert → Handler entscheidet ob Screenshot nötig → ruft Claude auf → du hörst die Antwort per TTS.

Logs: `~/.local/share/voice-claude/logs/handler.log`.

## Status-Overlay (optional)

Ein kleiner Punkt oben rechts (layer-shell, sichtbar selbst über Vollbild) der die Farbe je nach Systemzustand wechselt:

| Farbe | Zustand |
|---|---|
| 🟢 grün | Handy hört deine Stimme |
| 🟡 bernstein | Claude denkt nach (generiert Antwort) |
| 🔵 blau | TTS spielt die Antwort ab |
| 🔴 rot | Fehler (verschwindet nach ~2.5s) |
| (versteckt) | idle |

Benötigt `gtk4-layer-shell` + `python-gobject` (Arch: `sudo pacman -S gtk4-layer-shell python-gobject`). Für Hyprland-Autostart enthalten die Snippets in `examples/hyprland-bindings.{lua,conf}` bereits `exec-once`. Manueller Test:

```bash
voice-claude-overlay &
echo speaking > ~/.local/share/voice-claude/state
```

Der Zustand wird automatisch vom Handler, `stream_tts.py`, Cancel und den Keybinds (`listening`) geschrieben. Größe/Position konfigurierbar via env: `VOICE_CLAUDE_OVERLAY_SIZE`, `VOICE_CLAUDE_OVERLAY_MARGIN_TOP`, `VOICE_CLAUDE_OVERLAY_MARGIN_RIGHT`.

## ⚠️ Über den Super+Z-Modus (vollständig)

Der vollständige Modus läuft Claude Opus mit `--allowedTools`, das auf eine **explizite Whitelist** zeigt:

- **Bash:** nur `hyprctl`, `pactl`, `playerctl`, `wpctl`, `brightnessctl`, `omarchy*`, `uwsm-app`, `steam`, `setsid`, `notify-send`, `ls`, `cat`, `grep`, `rg`, `find`, `jq`, `du`, `df`, `date`, `uptime`, `free`, `echo`, `printf`.
- **Tools:** `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`, `WebSearch`.
- **Blockiert:** `rm`, `sudo`, `chmod`, `chown`, `dd`, `mv` und alle anderen nicht aufgeführten Bash-Befehle.

Falls eine Transkription dich verrät („Downloads-Ordner löschen" falsch verstanden), hat Claude **keine Berechtigung**, Schaden anzurichten. Der Sys-Prompt weist es an zu sagen „ich kann nicht" und eine Alternative vorzuschlagen, wenn du etwas außerhalb des Umfangs anforderst.

Dennoch: Der Umfang ist großzügig. Es kann Dateien verschieben, bearbeiten und erstellen (`Edit`, `Write`), beliebige Steam-Spiele öffnen, `omarchy *` ausführen. Verwende gesunden Menschenverstand. Um Befehle hinzuzufügen, bearbeite `CLAUDE_FULL_BASH_ALLOW` in `bin/voice-claude-handler.sh`. **Niemals `Bash(*:*)` verwenden** — das entspricht `--dangerously-skip-permissions`.

Der schnelle Modus (Alt+Z) erlaubt nur `Read`, ist also völlig sicher.

## Fehlerbehebung

**`paplay: Failed to open audio file` / `Connection refused`**
Dein System verwendet pipewire aber ohne `pipewire-pulse`, oder pulseaudio läuft nicht. Installiere `pipewire-pulse` (auf Arch: `sudo pacman -S pipewire-pulse`) und starte die Sitzung neu. Überprüfe mit `pactl info`, dass dort „Server Name: PulseAudio (on PipeWire ...)" steht.

**`paplay: Failure: No such entity` oder Audio kommt aus dem falschen Sink**
Der exportierte `VOICE_CLAUDE_SINK` existiert nicht oder hat sich geändert. Liste die aktuellen mit `pactl list short sinks`, kopiere den genauen Namen (zweite Spalte) und exportiere erneut. Wenn du keinen bestimmten Sink brauchst, exportiere nichts — der Handler verwendet den Systemstandard.

**Handy nimmt auf, aber danach passiert nichts / ich höre keine Antwort**
1. Sieh in `~/.local/share/voice-claude/logs/handler.log` nach — dort ist der vollständige Trace.
2. Bestätige, dass `paste_method` auf `"external_script"` gesetzt ist und `external_script_path` auf das richtige `voice-claude-handler.sh` zeigt.
3. Wenn das Log `claude: command not found` sagt, füge den CLI-Pfad zum globalen PATH hinzu oder verwende einen absoluten Pfad im Handler.

**`claude: command not found` im Handler, obwohl es im Terminal funktioniert**
Der Handy-Prozess hat möglicherweise dein Shell-RC nicht geladen. Lösungen: (a) Claude Code global installieren (`/usr/local/bin/claude` oder äquivalent), oder (b) den Handler bearbeiten und `claude` durch den absoluten Pfad ersetzen.

**Das erste Audio-Chunk wird abgeschnitten / die Stimme „verschluckt" die erste Silbe**
Der HDMI-Sink war im Suspend-Modus. Der Handler macht Pre-Warm, aber manchmal reicht es nicht. Erhöhe `FIRST_CHUNK_LEAD_SILENCE_S` in `kokoro/stream_tts.py` (von 0.2s auf 0.4s z.B.) oder verhindere das Suspendieren mit `pactl unload-module module-suspend-on-idle`.

**Kokoro braucht lange / hohe Antwortlatenz**
Der persistente Daemon sollte ~1-2s Modell-Ladezeit eliminieren. Prüfe ob er läuft: `python3 ~/.local/share/voice-claude/kokoro/daemon.py --ping`. Antwortet er nicht, startet der Handler ihn beim nächsten Aufruf automatisch neu. Daemon-Logs: `~/.local/share/voice-claude/logs/daemon.log`.

**Ungenaue Transkription technischer Wörter (Befehlsnamen, Apps)**
Handy unterstützt „custom words" in der Konfiguration. Füge `hyprctl`, `pactl`, die Namen der Apps, die du am häufigsten verwendest, etc. hinzu. Du kannst auch ein anderes Whisper/Parakeet-Modell über Handys UI ausprobieren.

**Alt+Z macht nichts**
Überprüfe, dass Hyprland den Binding neu geladen hat: `hyprctl reload` und schaue die Ausgabe auf Fehler durch. Prüfe, ob das Kürzel mit einem anderen kollidiert: `hyprctl binds | grep -i ',Z,'`.

**Der vollständige Modus antwortet „ich habe keine Berechtigung"**
Die Whitelist enthält den benötigten Befehl nicht. Füge ihn mit dem Muster `Bash(befehl:*)` zu `CLAUDE_FULL_BASH_ALLOW` im Handler hinzu. Verwende nicht `Bash(*:*)`, außer du weißt genau, was du tust.

## Anpassung

- **Stimme / Geschwindigkeit / Sink:** bearbeite `~/.local/share/voice-claude/config.yaml` (Abschnitt `tts`) oder exportiere `VOICE_CLAUDE_VOICE`, `VOICE_CLAUDE_SPEED`, `VOICE_CLAUDE_SINK`. Verfügbare Stimmen unter [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx); Blends wie `ef_dora+af_bella` werden unterstützt.
- **Screenshot-Keywords:** in `config.yaml`, Abschnitt `screen_keywords.words` und `screen_keywords.phrases`. Eigene hinzufügen; falsche Positive entfernen.
- **Modell / Aufwand:** Abschnitt `models.quick` / `models.full` in `config.yaml`, oder direkt in `voice-claude-handler.sh`.
- **Whitelist des vollständigen Modus:** `CLAUDE_FULL_BASH_ALLOW` und `CLAUDE_FULL_TOOLS_ALLOW` im Handler. Befehle nach Bedarf hinzufügen oder entfernen. **Niemals `Bash(*:*)` verwenden** — das entspricht `--dangerously-skip-permissions`.

## Credits / Inspiration

- Ursprüngliche Idee inspiriert durch [ein NateGentile-Video](https://www.youtube.com/@NateGentile) über Sprachassistenten für Claude.
- STT: [Handy](https://handy.computer/) (Parakeet v3 lokal).
- TTS: [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) von [@thewh1teagle](https://github.com/thewh1teagle).
- CLI: [Claude Code](https://claude.com/claude-code) von Anthropic.

## Lizenz

MIT. Siehe `LICENSE`.
