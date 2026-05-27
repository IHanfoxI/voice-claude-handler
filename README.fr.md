🇪🇸 [Español](README.md) &nbsp;·&nbsp; [🇬🇧 English](README.en.md) &nbsp;·&nbsp; [🇧🇷 Português](README.pt.md) &nbsp;·&nbsp; [🇩🇪 Deutsch](README.de.md) &nbsp;·&nbsp; 🇫🇷 Français &nbsp;·&nbsp; [🇨🇳 中文](README.zh.md) &nbsp;·&nbsp; [🟩 Esperanto](README.eo.md)

---

# voice-claude-handler

Assistant vocal qui dicte à **Claude Code** depuis n'importe quelle application (même les jeux en plein écran). Ta question sort en voix, la réponse revient en voix — **sans** taper de texte dans la fenêtre active et **sans** voler le focus.

```
raccourci → Handy (STT) → ce handler → Claude Code → Kokoro (TTS) → audio
```

Conçu pour les gens qui veulent poser une question à Claude en jouant, en montant une vidéo ou les mains occupées. Pensé pour Linux + Hyprland + Wayland, mais adaptable à tout setup capable de lancer un script depuis un raccourci.

## Que fait-il ?

- **Alt+Z (rapide) :** Claude Haiku 4.5 avec `--allowedTools Read`. Pour des requêtes rapides et économiques.
- **Super+Z (complet) :** Claude Opus 4.7 avec une liste blanche explicite de commandes (`hyprctl`, `pactl`, `playerctl`, `omarchy*`, `steam`, `uwsm-app`, `setsid`, `notify-send`, `ls/cat/grep/find/jq/du/df`, etc.) plus des outils non-destructifs (`Read`, `Write`, `Edit`, `WebFetch`, `WebSearch`). Pour demander des actions : « ouvre Spotify », « combien pèse le dossier téléchargements », « mets en pause la vidéo ».
- **Alt+Shift+Z (annuler) :** tue la réponse en cours (TTS + Claude + synthèse) si elle a commencé à répondre quelque chose que tu ne veux pas attendre.
- **Capture paresseuse :** si ta question contient des mots visuels (« que dit cette fenêtre », « lis cette erreur », « ce bouton »), une capture d'écran est prise avec `grim` et envoyée avec la question. Sinon elle est ignorée — économise ~500ms et ~3k tokens par invocation.
- **TTS en streaming :** la réponse de Claude est synthétisée avec [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) phrase par phrase au fur et à mesure de la génération. TTFA ~0.3s.
- **Sessions persistantes :** chaque mode maintient sa propre session Claude Code (UUID fixe), donc Claude se souvient du contexte entre les questions.

## Prérequis

| Composant | Rôle |
|---|---|
| [Claude Code CLI](https://claude.com/claude-code) | le cerveau |
| [Handy](https://handy.computer/) | STT local avec Parakeet v3 (ou le modèle de ton choix) |
| Hyprland (ou tout WM avec raccourcis globaux) | pour Alt+Z / Super+Z |
| `grim` | captures d'écran Wayland |
| `paplay` (pulseaudio / pipewire-pulse) | lecture audio |
| `jq`, `iconv`, `notify-send` | utilitaires du handler |
| Python 3.10+ | venv pour Kokoro |

Testé sur CachyOS + Hyprland + Omarchy. Devrait fonctionner sur n'importe quelle dérivée d'Arch ; sur d'autres distros Linux avec Wayland aussi, en ajustant les noms de paquets.

## Installation

```bash
git clone git@github.com:IHanfoxI/voice-claude-handler.git
cd voice-claude-handler
./install.sh
```

Le script d'installation :
- Copie `bin/voice-claude-handler.sh` dans `~/.local/bin/`.
- Copie les scripts Python dans `~/.local/share/voice-claude/kokoro/`.
- Télécharge le modèle Kokoro (~325 Mo) et les voix (~28 Mo) dans le même répertoire.
- Crée un venv dans `~/.local/share/voice-claude/venv` avec `kokoro-onnx`, `soundfile`, `numpy`.
- Génère les UUIDs de session Claude.
- Affiche les étapes finales (configurer Handy + Hyprland).

## Configuration

### 1. Handy

Ouvre Handy → **Settings** :
- **Output → Paste method :** `External script`
- **Output → External script path :** `~/.local/bin/voice-claude-handler.sh`
- **Audio → Microphone :** choisis le tien
- **General → App language :** ta langue

Si tu préfères éditer le JSON directement (avec Handy **fermé**), consulte `examples/handy-settings-relevant.json` pour les clés importantes. **Ne remplace pas le fichier entier** : Handy le gère et contient des valeurs par défaut à ne pas casser.

### 2. Hyprland (raccourcis)

Ajoute les deux bindings à ta config :

- **Omarchy / lua :** copie `examples/hyprland-bindings.lua` dans `~/.config/hypr/bindings.lua`.
- **Hyprland.conf classique :** copie `examples/hyprland-bindings.conf` dans `~/.config/hypr/hyprland.conf`.

Recharge : `hyprctl reload`.

### 3. (Optionnel) Sink audio fixe

Par défaut le TTS sort sur le sink par défaut du système. Pour en forcer un précis (ex : enceintes du moniteur via HDMI), exporte :

```bash
# Liste les sinks disponibles
pactl list short sinks

# Choisis-en un et exporte dans ton shell ou dans le raccourci
export VOICE_CLAUDE_SINK="alsa_output.pci-0000_XX_00.X.hdmi-stereo"
```

Autres variables : `VOICE_CLAUDE_VOICE` (défaut `ef_dora+af_bella`), `VOICE_CLAUDE_SPEED` (défaut `1.3`).

### 4. CLAUDE.md du workdir

Le handler fait `cd ~/.local/share/voice-claude/workdir` avant d'appeler Claude, donc le `CLAUDE.md` présent là est chargé automatiquement comme contexte. Édite-le avec tes applications, raccourcis, jeux Steam favoris, etc. — Claude l'utilise pour savoir comment agir sur ton système spécifique.

Le script d'installation copie un exemple. Remplace les placeholders par tes données.

## Utilisation

1. Appuie sur **Alt+Z** (rapide) ou **Super+Z** (complet).
2. Parle. Handy écoute jusqu'à ce que tu rappuies sur le raccourci (ou détecte le silence, selon ta config).
3. Relâche. Handy transcrit → le handler décide si une capture est nécessaire → appelle Claude → tu entends la réponse via TTS.

Logs : `~/.local/share/voice-claude/logs/handler.log`.

## Overlay d'état (optionnel)

Un petit point en haut à droite (layer-shell, visible même au-dessus du plein écran) qui change de couleur selon l'état du système :

| Couleur | État |
|---|---|
| 🟢 vert | Handy t'écoute |
| 🟡 ambre | Claude réfléchit (génère la réponse) |
| 🔵 bleu | TTS joue la réponse |
| 🔴 rouge | erreur (disparaît seul en ~2.5s) |
| (caché) | idle |

Nécessite `gtk4-layer-shell` + `python-gobject` (Arch : `sudo pacman -S gtk4-layer-shell python-gobject`). Pour le démarrage automatique sur Hyprland, les snippets dans `examples/hyprland-bindings.{lua,conf}` incluent déjà `exec-once`. Test manuel :

```bash
voice-claude-overlay &
echo speaking > ~/.local/share/voice-claude/state
```

L'état est écrit automatiquement par le handler, `stream_tts.py`, cancel et les raccourcis (`listening`). Taille/position configurables via env : `VOICE_CLAUDE_OVERLAY_SIZE`, `VOICE_CLAUDE_OVERLAY_MARGIN_TOP`, `VOICE_CLAUDE_OVERLAY_MARGIN_RIGHT`.

## ⚠️ À propos du mode Super+Z (complet)

Le mode complet lance Claude Opus avec `--allowedTools` pointant vers une **liste blanche explicite** :

- **Bash :** uniquement `hyprctl`, `pactl`, `playerctl`, `wpctl`, `brightnessctl`, `omarchy*`, `uwsm-app`, `steam`, `setsid`, `notify-send`, `ls`, `cat`, `grep`, `rg`, `find`, `jq`, `du`, `df`, `date`, `uptime`, `free`, `echo`, `printf`.
- **Tools :** `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`, `WebSearch`.
- **Bloqué :** `rm`, `sudo`, `chmod`, `chown`, `dd`, `mv` et tout autre commande Bash non listée.

Si une transcription te trahit (« supprimer le dossier téléchargements » mal compris), Claude **n'a pas la permission** de causer des dégâts. Le sys-prompt lui demande de dire « je ne peux pas » et de proposer une alternative si tu demandes quelque chose hors périmètre.

Malgré tout : le périmètre est généreux. Il peut déplacer, éditer et créer des fichiers (`Edit`, `Write`), ouvrir n'importe quel jeu Steam, exécuter `omarchy *`. Use de jugement. Pour ajouter des commandes, édite `CLAUDE_FULL_BASH_ALLOW` dans `bin/voice-claude-handler.sh`. **N'utilise jamais `Bash(*:*)`** — c'est équivalent à `--dangerously-skip-permissions`.

Le mode rapide (Alt+Z) n'autorise que `Read`, donc il est complètement sûr.

## Dépannage

**`paplay: Failed to open audio file` / `Connection refused`**
Ton système utilise pipewire mais sans `pipewire-pulse`, ou pulseaudio ne tourne pas. Installe `pipewire-pulse` (sur Arch : `sudo pacman -S pipewire-pulse`) et redémarre la session. Vérifie avec `pactl info` qu'il affiche « Server Name: PulseAudio (on PipeWire ...) ».

**`paplay: Failure: No such entity` ou l'audio sort du mauvais sink**
Le `VOICE_CLAUDE_SINK` exporté n'existe pas ou a changé. Liste les actuels avec `pactl list short sinks`, copie le nom exact (deuxième colonne) et ré-exporte. Si tu n'as pas besoin d'un sink spécifique, n'exporte rien — le handler utilise le défaut du système.

**Handy enregistre mais rien ne se passe / je n'entends pas de réponse**
1. Consulte `~/.local/share/voice-claude/logs/handler.log` — la trace complète est là.
2. Confirme que `paste_method` est `"external_script"` et que `external_script_path` pointe vers le bon `voice-claude-handler.sh`.
3. Si le log dit `claude: command not found`, ajoute le chemin du CLI au PATH global ou utilise un chemin absolu dans le handler.

**`claude: command not found` dans le handler alors que ça fonctionne dans le terminal**
Le processus Handy n'a peut-être pas chargé ton shell rc. Solutions : (a) installe Claude Code globalement (`/usr/local/bin/claude` ou équivalent), ou (b) édite le handler et remplace `claude` par le chemin absolu.

**Le premier chunk audio est tronqué / la voix « avale » la première syllabe**
Le sink HDMI était en suspend. Le handler fait un pré-réveil mais parfois ce n'est pas suffisant. Augmente `FIRST_CHUNK_LEAD_SILENCE_S` dans `kokoro/stream_tts.py` (de 0.2s à 0.4s, par exemple) ou empêche le sink de se suspendre avec `pactl unload-module module-suspend-on-idle`.

**Kokoro prend beaucoup de temps la première fois**
Le chargement du modèle prend ~1-2s sur CPU. C'est un coût unique par invocation. Pour l'éliminer il faudrait faire tourner Kokoro comme démon persistant — c'est dans la feuille de route mais pas trivial.

**Transcription imprécise des mots techniques (noms de commandes, apps)**
Handy supporte les « custom words » dans sa configuration. Ajoute `hyprctl`, `pactl`, les noms des apps que tu utilises le plus, etc. Tu peux aussi essayer un autre modèle Whisper/Parakeet depuis l'interface de Handy.

**Alt+Z ne fait rien**
Vérifie que Hyprland a rechargé le binding : `hyprctl reload` et examine la sortie pour des erreurs. Vérifie que le raccourci n'entre pas en conflit avec un autre : `hyprctl binds | grep -i ',Z,'`.

**Le mode complet répond « je n'ai pas la permission »**
La liste blanche ne contient pas la commande dont tu as besoin. Ajoute-la à `CLAUDE_FULL_BASH_ALLOW` dans le handler avec le pattern `Bash(commande:*)`. N'utilise pas `Bash(*:*)` à moins de savoir exactement ce que tu fais.

## Personnalisation

- **Voix :** `VOICE_CLAUDE_VOICE` accepte des noms (`ef_dora`, `em_alex`, `if_sara`, etc.) ou des blends (`ef_dora+af_bella`). Liste complète dans [le README kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx).
- **Vitesse :** `VOICE_CLAUDE_SPEED` (défaut `1.3`). Les valeurs entre `0.8` et `1.5` sonnent généralement bien.
- **Modèle / effort :** édite le bloc `if/else` du mode dans `voice-claude-handler.sh`.
- **Liste blanche du mode complet :** `CLAUDE_FULL_BASH_ALLOW` et `CLAUDE_FULL_TOOLS_ALLOW` au début du bloc `if [[ "$MODE" == "full" ]]` dans le handler. Ajoute ou supprime des commandes selon ton workflow.
- **Mots-clés pour captures :** ajuste `SCREEN_KW_RE` et `SCREEN_PHRASE_RE` dans le handler. La liste actuelle est en espagnol ; ajoute les tiennes.

## Crédits / inspiration

- Idée originale inspirée par [une vidéo de NateGentile](https://www.youtube.com/@NateGentile) sur les assistants vocaux pour Claude.
- STT : [Handy](https://handy.computer/) (Parakeet v3 local).
- TTS : [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) par [@thewh1teagle](https://github.com/thewh1teagle).
- CLI : [Claude Code](https://claude.com/claude-code) d'Anthropic.

## Licence

MIT. Voir `LICENSE`.
