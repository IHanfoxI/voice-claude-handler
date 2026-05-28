🇪🇸 [Español](README.md) &nbsp;·&nbsp; [🇬🇧 English](README.en.md) &nbsp;·&nbsp; [🇧🇷 Português](README.pt.md) &nbsp;·&nbsp; [🇩🇪 Deutsch](README.de.md) &nbsp;·&nbsp; [🇫🇷 Français](README.fr.md) &nbsp;·&nbsp; [🇨🇳 中文](README.zh.md) &nbsp;·&nbsp; 🟩 Esperanto

---

# voice-claude-handler

Voĉasistanto kiu diktas al **Claude Code** el ajna aplikaĵo (eĉ el tutekranaj ludoj). Via demando eliras kiel voĉo, la respondo revenas kiel voĉo — **sen** tajpi tekston en la aktivan fenestron kaj **sen** ŝteli la fokuson.

```
klavkombino → Handy (parol-rekonado) → ĉi tiu handler → Claude Code → Kokoro (tekst-al-voĉo) → aŭdio
```

Kreita por homoj kiuj volas demandi Claudon dum ili ludas, redaktas videojn aŭ havas la manojn okupataj. Desegnita por Linux + Hyprland + Wayland, sed adaptigebla al ajna aranĝo kiu povas lanĉi skripton per klavkombino.

## Kion ĝi faras?

- **Alt+Z (rapida):** Claude Haiku 4.5 kun `--allowedTools Read`. Por rapidaj, malmultekostaj demandoj.
- **Super+Z (plena):** Claude Opus 4.7 kun eksplicita permeslisto de komandoj (`hyprctl`, `pactl`, `playerctl`, `omarchy*`, `steam`, `uwsm-app`, `setsid`, `notify-send`, `ls/cat/grep/find/jq/du/df`, ktp.) kaj nedetrua iloj (`Read`, `Write`, `Edit`, `WebFetch`, `WebSearch`). Por peti agojn: "malfermu Spotify", "kiom pezas la elŝuta dosierujo", "paŭzigu la filmeton".
- **Alt+Shift+Z (nuligi):** ĉesigas la kuriantan respondon per kooperativa signalo — `stream_tts.py` haltas inter frazoj kaj finas la aktualan `paplay`.
- **Maldiligentan ekrankopio:** se via demando havas vidajn ŝlosilvortojn ("kion diras tiu fenestro", "legu ĉi tiun eraron", "tiu butono"), ĝi faras ekrankopiojn per `grim` kaj sendas ĝin kun la demando. Alie ĝi preterlasas tion — ŝparas ~500ms kaj ~3k ĵetonojn por alvoko.
- **Fluema TTS kun 3-fadena dukto:** sintezado kaj reproduktado kuras paralele (fadeno stdin, fadeno synth, fadeno player). Daŭra Kokoro-demono forigas ~1-2s da modelŝargado. TTFA ~0.3s.
- **Stataj sonoj:** supreniranta ĉirpo dum registrado, malsupreniranta dum pretigo, mola sonorilo en buklo dum Claude pensas. Funkcias kun ekskluziva tutekrana reĝimo (aŭdio, ne surtavolo).
- **Daŭraj sesioj:** ĉiu reĝimo konservas sian propran Claude Code-sesion (fiksa UUID), do Claude memoras la kuntekston inter demandoj.
- **Voĉa nuligo:** diru "viŝu la konversacion" (aŭ "nova konversacio", "forviŝu la historion") por rekomenci — tuja TTS-respondo, sen voki Claudon.

## Postuloj

| Komponento | Celo |
|---|---|
| [Claude Code CLI](https://claude.com/claude-code) | la cerbo |
| [Handy](https://handy.computer/) | loka parol-rekonado kun Parakeet v3 (aŭ via preferata modelo) |
| Hyprland (aŭ ajna fenestroadministranto kun tutaj klavkombinoj) | por Alt+Z / Super+Z |
| `grim` | Wayland-ekrankopiaĵoj |
| `paplay` (pulseaudio / pipewire-pulse) | aŭdio-ludado |
| `jq`, `iconv`, `notify-send` | helpiloj de la handler |
| Python 3.10+ | venv por Kokoro |

Testita sur CachyOS + Hyprland + Omarchy. Devus funkcii sur ajna Arch-derivaĵo; ankaŭ sur aliaj Linux-distribucioj kun Wayland, adaptante la pakaĵnomojn.

## Instalado

```bash
git clone git@github.com:IHanfoxI/voice-claude-handler.git
cd voice-claude-handler
./install.sh
```

La instalilo demandas pri statosurtavolo kaj sonoj. Poste:
- Kopias `bin/voice-claude-handler.sh` kaj Python-skriptojn al siaj celoj.
- Elŝutas la Kokoro-modelon (~325 MB) kaj voĉojn (~28 MB).
- Kreas venv kun `kokoro-onnx`, `soundfile`, `numpy`, `pyyaml`.
- Generas la UUID-ojn de la Claude-sesioj.
- Kopias la ekzemplon de `config.yaml` al `~/.local/share/voice-claude/config.yaml`.
- Presas la finajn paŝojn.

Flagoj por ne-interaga instalado: `--no-overlay`, `--no-sound`, `--no-extras`.

## Agordado

### 1. Handy

Malfermu Handy → **Settings**:
- **Output → Paste method:** `External script`
- **Output → External script path:** `~/.local/bin/voice-claude-handler.sh`
- **Audio → Microphone:** elektu la vian
- **General → App language:** la lingvo kiun vi parolas

Se vi preferas redakti la JSON-dosieron rekte (kun Handy **fermita**), rigardu `examples/handy-settings-relevant.json` por la gravaj ŝlosiloj. **Ne anstataŭigu la tutan dosieron**: Handy administras ĝin kaj havas defaŭltojn kiujn vi ne volas rompi.

### 2. Hyprland (klavkombinoj)

Aldonu la du ligilojn al via agordo:

- **Omarchy / lua:** kopiu `examples/hyprland-bindings.lua` al `~/.config/hypr/bindings.lua`.
- **Klasika hyprland.conf:** kopiu `examples/hyprland-bindings.conf` al `~/.config/hypr/hyprland.conf`.

Reŝargu: `hyprctl reload`.

### 3. (Laŭvola) config.yaml

La instalilo kopias dokumentitan ŝablonon al `~/.local/share/voice-claude/config.yaml`. Tie vi povas ŝanĝi voĉon, rapidecon, aŭdian eliujon, kaj la ŝlosilvortojn kiuj ekigas ekrankopion:

```yaml
tts:
  voice: "ef_dora+af_bella"
  speed: 1.3
  sink: ""           # malplena = sistema defaŭlto. Ekz: "alsa_output.pci-0000_XX_00.X.hdmi-stereo"
screen_keywords:
  words: [ekrano, fenestro, ...]   # aldonu viajn
  phrases: ["kion diras", ...]
```

La env-variabloj (`VOICE_CLAUDE_VOICE`, `VOICE_CLAUDE_SPEED`, `VOICE_CLAUDE_SINK`) ankoraŭ funkcias kaj havas prioritaton super la YAML.

### 4. CLAUDE.md de la laboradresaro

La handler faras `cd ~/.local/share/voice-claude/workdir` antaŭ ol voki Claudon, do la `CLAUDE.md` tie estas aŭtomate ŝargita kiel kunteksto. Redaktu ĝin kun viaj aplikaĵoj, klavkombinoj, plej ŝatataj Steam-ludoj, ktp. — Claude uzas ĝin por scii kiel agi sur via specifa sistemo.

La instalilo kopias ekzemplon. Anstataŭigu la loktenilojn per viaj datumoj.

## Uzado

1. Premu **Alt+Z** (rapida) aŭ **Super+Z** (plena).
2. Parolu. Handy aŭskultas ĝis vi denove premas la klavkombinon (aŭ detektas silenton, laŭ via agordo).
3. Liberigu. Handy transskribus → la handler decidas ĉu ekrankopio estas bezonata → vokas Claudon → vi aŭdas la respondon per TTS.

Protokoloj: `~/.local/share/voice-claude/logs/handler.log`.

## Statobildo (laŭvola)

Eta punkto en la supra-dekstra angulo (layer-shell, videbla eĉ super tutekrana reĝimo) kiu ŝanĝas koloron laŭ kio okazas en la sistemo:

| Koloro | Stato |
|---|---|
| 🟢 verda | Handy aŭskultas vian voĉon |
| 🟡 sukcena | Claude pensas (generas respondon) |
| 🔵 blua | TTS reproduktas la respondon |
| 🔴 ruĝa | eraro (aŭtomate kaŝiĝas post ~2.5s) |
| (kaŝita) | senokupa |

Bezonas `gtk4-layer-shell` + `python-gobject` (Arch: `sudo pacman -S gtk4-layer-shell python-gobject`). Por aŭtomata starto en Hyprland, la fragmentoj en `examples/hyprland-bindings.{lua,conf}` jam inkluzivas `exec-once`. Mana testo:

```bash
voice-claude-overlay &
echo speaking > ~/.local/share/voice-claude/state
```

La stato estas skribita aŭtomate de la handler, `stream_tts.py`, cancel kaj la klavkombinoj (`listening`). Grandeco/pozicio agordeblas per env: `VOICE_CLAUDE_OVERLAY_SIZE`, `VOICE_CLAUDE_OVERLAY_MARGIN_TOP`, `VOICE_CLAUDE_OVERLAY_MARGIN_RIGHT`.

## ⚠️ Pri la reĝimo Super+Z (plena)

La plena reĝimo ruladas Claude Opus kun `--allowedTools` montranta al **eksplicita permeslisto**:

- **Bash:** nur `hyprctl`, `pactl`, `playerctl`, `wpctl`, `brightnessctl`, `omarchy*`, `uwsm-app`, `steam`, `setsid`, `notify-send`, `ls`, `cat`, `grep`, `rg`, `find`, `jq`, `du`, `df`, `date`, `uptime`, `free`, `echo`, `printf`.
- **Iloj:** `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`, `WebSearch`.
- **Blokitaj:** `rm`, `sudo`, `chmod`, `chown`, `dd`, `mv` kaj iu ajn alia Bash-komando ne listigita.

Se transskribo perfidas vin ("forigi la elŝutan dosierujon" miskomprenita), Claude **ne havas permeson** kaŭzi damaĝon. La sistema prompto petas ĝin diri "mi ne povas" kaj proponi alternativan se vi petas ion ekster la amplekso.

Tamen: la amplekso estas malavara. Ĝi povas movi, redakti kaj krei dosierojn (`Edit`, `Write`), malfermi ajnan Steam-ludon, ekzekuti `omarchy *`. Uzu juĝon. Por aldoni komandojn, redaktu `CLAUDE_FULL_BASH_ALLOW` en `bin/voice-claude-handler.sh`. **Neniam uzu `Bash(*:*)`** — ĝi ekvivalas al `--dangerously-skip-permissions`.

La rapida reĝimo (Alt+Z) nur permesas `Read`, do ĝi estas tute sekura.

## Problemsolvo

**`paplay: Failed to open audio file` / `Connection refused`**
Via sistemo uzas pipewire sed sen `pipewire-pulse`, aŭ pulseaudio ne funkcias. Instalu `pipewire-pulse` (en Arch: `sudo pacman -S pipewire-pulse`) kaj restaru la sesion. Kontrolu per `pactl info` ke ĝi diras "Server Name: PulseAudio (on PipeWire ...)".

**`paplay: Failure: No such entity` aŭ la aŭdio eliras el la malĝusta eligujo**
La eksportita `VOICE_CLAUDE_SINK` ne ekzistas aŭ ŝanĝiĝis. Listu la aktualajn per `pactl list short sinks`, kopiu la ĝustan nomon (dua kolumno) kaj re-eksportu. Se vi ne bezonas specifan eliujon, ne eksportu ion — la handler uzas la sisteman defaŭlton.

**Handy registras sed nenio okazas / mi ne aŭdas respondon**
1. Rigardu `~/.local/share/voice-claude/logs/handler.log` — la kompleta spurado estas tie.
2. Konfirmu ke `paste_method` estas `"external_script"` kaj `external_script_path` montras al la ĝusta `voice-claude-handler.sh`.
3. Se la protokolo diras `claude: command not found`, aldonu la CLI-vojon al la tutmonda PATH aŭ uzu absolutan vojon en la handler.

**`claude: command not found` el la handler kvankam ĝi funkcias en la terminalo**
La Handy-procezo eble ne ŝargis vian ŝelan rc. Solvoj: (a) instalu Claude Code tutmonde (`/usr/local/bin/claude` aŭ ekvivalente), aŭ (b) redaktu la handler kaj anstataŭigu `claude` per la absoluta vojo.

**La unua aŭdioparto estas tranĉita / la voĉo "glutas" la unuan silabon**
La HDMI-eligujo estis en suspendo. La handler faras antaŭvarmon sed foje ĝi ne sufiĉas. Plialigu `FIRST_CHUNK_LEAD_SILENCE_S` en `kokoro/stream_tts.py` (de 0.2s al 0.4s, ekzemple) aŭ malhelpas la eliujon suspendi per `pactl unload-module module-suspend-on-idle`.

**Kokoro estas malrapida / la respondo havas altan latentemon**
La daŭra demono devus forigi ~1-2s da modelŝargado. Kontrolu ke ĝi funkcias: `python3 ~/.local/share/voice-claude/kokoro/daemon.py --ping`. Se ĝi ne respondas, ĉe la sekva alvoko la handler aŭtomate restartas ĝin. Protokoloj de la demono: `~/.local/share/voice-claude/logs/daemon.log`.

**Malĝusta transskribo de teknikaj vortoj (komandnomoj, aplikaĵoj)**
Handy subtenas "kutimajn vortojn" en ĝia agordo. Aldonu `hyprctl`, `pactl`, la nomojn de la aplikaĵoj kiujn vi plej uzas, ktp. Vi ankaŭ povas provi alian Whisper/Parakeet-modelon el la interfaco de Handy.

**Alt+Z ne faras ion**
Kontrolu ke Hyprland reŝargis la klavkombinon: `hyprctl reload` kaj reviziu la eliron por eraroj. Kontrolu ke la klavkombino ne konfliktas kun alia: `hyprctl binds | grep -i ',Z,'`.

**La plena reĝimo respondas "mi ne havas permeson"**
La permeslisto ne inkluzivas la komandon kiun vi bezonas. Aldonu ĝin al `CLAUDE_FULL_BASH_ALLOW` en la handler kun la ŝablono `Bash(komando:*)`. Ne uzu `Bash(*:*)` krom se vi precize scias kion vi faras.

## Personigado

- **Voĉo / rapideco / eligujo:** redaktu `~/.local/share/voice-claude/config.yaml` (sekcio `tts`) aŭ eksportu `VOICE_CLAUDE_VOICE`, `VOICE_CLAUDE_SPEED`, `VOICE_CLAUDE_SINK`. Disponeblaj voĉoj en [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx); akceptas miksaĵojn kiel `ef_dora+af_bella`.
- **Ŝlosilvortoj por ekrankopiaĵoj:** en `config.yaml`, sekcio `screen_keywords.words` kaj `screen_keywords.phrases`. Aldonu viajn; forigu tiujn kiuj donas falsajn pozitivojn.
- **Modelo / penado:** sekcio `models.quick` / `models.full` en `config.yaml`, aŭ rekte en `voice-claude-handler.sh`.
- **Permeslisto de plena reĝimo:** `CLAUDE_FULL_BASH_ALLOW` kaj `CLAUDE_FULL_TOOLS_ALLOW` en la handler. Aldonu aŭ forigu laŭ via laborfluo. **Neniam uzu `Bash(*:*)`** — ĝi ekvivalas al `--dangerously-skip-permissions`.

## Kreditoj / inspiro

- Origina ideo inspirita de [NateGentile-filmeto](https://www.youtube.com/@NateGentile) pri voĉasistantoj por Claude.
- Parol-rekonado: [Handy](https://handy.computer/) (loka Parakeet v3).
- Tekst-al-voĉo: [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) de [@thewh1teagle](https://github.com/thewh1teagle).
- CLI: [Claude Code](https://claude.com/claude-code) de Anthropic.

## Permesilo

MIT. Vidu `LICENSE`.
