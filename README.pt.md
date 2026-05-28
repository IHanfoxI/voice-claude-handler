🇪🇸 [Español](README.md) &nbsp;·&nbsp; [🇬🇧 English](README.en.md) &nbsp;·&nbsp; 🇧🇷 Português &nbsp;·&nbsp; [🇩🇪 Deutsch](README.de.md) &nbsp;·&nbsp; [🇫🇷 Français](README.fr.md) &nbsp;·&nbsp; [🇨🇳 中文](README.zh.md) &nbsp;·&nbsp; [🟩 Esperanto](README.eo.md)

---

# voice-claude-handler

Assistente de voz que dita para o **Claude Code** a partir de qualquer app (inclusive jogos em tela cheia). Sua pergunta sai como voz, a resposta volta como voz — **sem** digitar texto na janela em foco e **sem** roubar o foco.

```
keybind → Handy (STT) → este handler → Claude Code → Kokoro (TTS) → áudio
```

Feito para quem quer perguntar algo ao Claude enquanto joga, edita vídeo ou está com as mãos ocupadas. Pensado para Linux + Hyprland + Wayland, mas adaptável a qualquer setup que consiga disparar um script a partir de um atalho.

## O que faz?

- **Alt+Z (rápido):** Claude Haiku 4.5 com `--allowedTools Read`. Para consultas rápidas e baratas.
- **Super+Z (completo):** Claude Opus 4.7 com uma whitelist explícita de comandos (`hyprctl`, `pactl`, `playerctl`, `omarchy*`, `steam`, `uwsm-app`, `setsid`, `notify-send`, `ls/cat/grep/find/jq/du/df`, etc.) mais tools não-destrutivas (`Read`, `Write`, `Edit`, `WebFetch`, `WebSearch`). Para pedir ações: "abre o Spotify", "quanto pesa a pasta de downloads", "pausa o vídeo".
- **Alt+Shift+Z (cancelar):** cancela a resposta em andamento com sinal cooperativo — `stream_tts.py` para entre sentenças e encerra o `paplay` atual.
- **Screenshot preguiçoso:** se sua pergunta tem palavras visuais ("o que diz aquela janela", "lê esse erro", "aquele botão"), tira um screenshot com `grim` e envia junto com a pergunta. Caso contrário, pula — economiza ~500ms e ~3k tokens por invocação.
- **TTS em streaming com pipeline de 3 threads:** síntese e reprodução rodam em paralelo (thread stdin, thread synth, thread player). Daemon Kokoro persistente elimina ~1-2s de carregamento do modelo. TTFA ~0.3s.
- **Sons de estado:** chirp ascendente ao gravar, descendente ao processar, sino suave em loop enquanto o Claude pensa. Funcionam com fullscreen exclusivo (áudio, não overlay).
- **Sessões persistentes:** cada modo mantém sua própria sessão do Claude Code (UUID fixo), então o Claude lembra o contexto entre perguntas.
- **Reset por voz:** diga "limpar a conversa" (ou "nova conversa", "apagar histórico") para começar do zero — resposta instantânea via TTS, sem chamar o Claude.

## Requisitos

| Componente | Para quê |
|---|---|
| [Claude Code CLI](https://claude.com/claude-code) | o cérebro |
| [Handy](https://handy.computer/) | STT local com Parakeet v3 (ou o modelo que preferir) |
| Hyprland (ou qualquer WM com atalhos globais) | para Alt+Z / Super+Z |
| `grim` | screenshots no Wayland |
| `paplay` (pulseaudio / pipewire-pulse) | reprodução de áudio |
| `jq`, `iconv`, `notify-send` | utilitários do handler |
| Python 3.10+ | venv para o Kokoro |

Testado em CachyOS + Hyprland + Omarchy. Deve funcionar em qualquer derivada do Arch; em outras distros Linux com Wayland também, ajustando os nomes dos pacotes.

## Instalação

```bash
git clone git@github.com:IHanfoxI/voice-claude-handler.git
cd voice-claude-handler
./install.sh
```

O instalador pergunta quais indicadores de estado você quer (overlay visual, sons, ambos ou nenhum). Em seguida:
- Copia `bin/voice-claude-handler.sh` e scripts Python para seus destinos.
- Baixa o modelo Kokoro (~325 MB) e as vozes (~28 MB).
- Cria um venv com `kokoro-onnx`, `soundfile`, `numpy`, `pyyaml`.
- Gera os UUIDs de sessão do Claude.
- Copia o template `config.yaml` para `~/.local/share/voice-claude/config.yaml`.
- Imprime os passos finais.

Flags para instalação não interativa: `--no-overlay`, `--no-sound`, `--no-extras`.

## Configuração

### 1. Handy

Abra o Handy → **Settings**:
- **Output → Paste method:** `External script`
- **Output → External script path:** `~/.local/bin/voice-claude-handler.sh`
- **Audio → Microphone:** escolha o seu
- **General → App language:** o que você fala

Se preferir editar o JSON diretamente (com o Handy **fechado**), veja `examples/handy-settings-relevant.json` para as chaves relevantes. **Não sobrescreva o arquivo inteiro**: o Handy o gerencia e tem defaults que você não quer quebrar.

### 2. Hyprland (atalhos)

Adicione os dois bindings à sua config:

- **Omarchy / lua:** copie `examples/hyprland-bindings.lua` para `~/.config/hypr/bindings.lua`.
- **Hyprland.conf clássico:** copie `examples/hyprland-bindings.conf` para `~/.config/hypr/hyprland.conf`.

Recarregue: `hyprctl reload`.

### 3. (Opcional) config.yaml

O instalador copia um template documentado para `~/.local/share/voice-claude/config.yaml`. Lá você pode alterar voz, velocidade, sink de áudio e as palavras que disparam screenshots:

```yaml
tts:
  voice: "ef_dora+af_bella"
  speed: 1.3
  sink: ""           # vazio = sink padrão. Ex: "alsa_output.pci-0000_XX_00.X.hdmi-stereo"
screen_keywords:
  words: [tela, janela, ...]   # adicione os seus
  phrases: ["o que diz", ...]
```

As variáveis de ambiente (`VOICE_CLAUDE_VOICE`, `VOICE_CLAUDE_SPEED`, `VOICE_CLAUDE_SINK`) continuam funcionando e têm prioridade sobre o YAML.

### 4. CLAUDE.md do workdir

O handler faz `cd ~/.local/share/voice-claude/workdir` antes de chamar o Claude, então o `CLAUDE.md` de lá é carregado automaticamente como contexto. Edite com seus apps, atalhos, jogos favoritos do Steam, etc. — o Claude usa isso para saber como agir no seu sistema específico.

O instalador copia um exemplo. Substitua os placeholders pelos seus dados.

## Uso

1. Pressione **Alt+Z** (rápido) ou **Super+Z** (completo).
2. Fale. O Handy escuta até você pressionar o atalho novamente (ou detectar silêncio, conforme sua config).
3. Solte. Handy transcreve → handler decide se precisa de screenshot → chama o Claude → você ouve a resposta via TTS.

Logs: `~/.local/share/voice-claude/logs/handler.log`.

## Overlay de estado (opcional)

Um pontinho no canto superior direito (layer-shell, visível mesmo sobre fullscreen) que muda de cor conforme o que o sistema está fazendo:

| Cor | Estado |
|---|---|
| 🟢 verde | Handy ouvindo sua voz |
| 🟡 âmbar | Claude pensando (gerando resposta) |
| 🔵 azul | TTS reproduzindo a resposta |
| 🔴 vermelho | erro (some sozinho em ~2.5s) |
| (oculto) | idle |

Requer `gtk4-layer-shell` + `python-gobject` (Arch: `sudo pacman -S gtk4-layer-shell python-gobject`). Para autostart no Hyprland, os snippets em `examples/hyprland-bindings.{lua,conf}` já incluem `exec-once`. Teste manual:

```bash
voice-claude-overlay &
echo speaking > ~/.local/share/voice-claude/state
```

O estado é escrito automaticamente pelo handler, `stream_tts.py`, cancel e os keybinds (`listening`). Tamanho/posição configuráveis via env: `VOICE_CLAUDE_OVERLAY_SIZE`, `VOICE_CLAUDE_OVERLAY_MARGIN_TOP`, `VOICE_CLAUDE_OVERLAY_MARGIN_RIGHT`.

## ⚠️ Sobre o modo Super+Z (completo)

O modo completo roda o Claude Opus com `--allowedTools` apontando para uma **whitelist explícita**:

- **Bash:** apenas `hyprctl`, `pactl`, `playerctl`, `wpctl`, `brightnessctl`, `omarchy*`, `uwsm-app`, `steam`, `setsid`, `notify-send`, `ls`, `cat`, `grep`, `rg`, `find`, `jq`, `du`, `df`, `date`, `uptime`, `free`, `echo`, `printf`.
- **Tools:** `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebFetch`, `WebSearch`.
- **Bloqueado:** `rm`, `sudo`, `chmod`, `chown`, `dd`, `mv`, e qualquer outro comando Bash não listado.

Se uma transcrição te trair ("deletar a pasta de downloads" mal interpretado), o Claude **não tem permissão** para causar danos. O sys-prompt pede que ele diga "não consigo" e proponha uma alternativa se você pedir algo fora do escopo.

Mesmo assim: o escopo é generoso. Pode mover, editar e criar arquivos (`Edit`, `Write`), abrir qualquer jogo do Steam, executar `omarchy *`. Use bom senso. Se quiser adicionar comandos, edite `CLAUDE_FULL_BASH_ALLOW` em `bin/voice-claude-handler.sh`. **Nunca use `Bash(*:*)`** — equivale a `--dangerously-skip-permissions`.

O modo rápido (Alt+Z) só permite `Read`, então é completamente seguro.

## Solução de problemas

**`paplay: Failed to open audio file` / `Connection refused`**
Seu sistema usa pipewire mas sem `pipewire-pulse`, ou o pulseaudio não está rodando. Instale `pipewire-pulse` (no Arch: `sudo pacman -S pipewire-pulse`) e reinicie a sessão. Verifique com `pactl info` que diz "Server Name: PulseAudio (on PipeWire ...)".

**`paplay: Failure: No such entity` ou o áudio sai pelo sink errado**
O `VOICE_CLAUDE_SINK` que você exportou não existe ou mudou. Liste os atuais com `pactl list short sinks`, copie o nome exato (segunda coluna) e re-exporte. Se não precisar de um sink específico, não exporte nada — o handler usa o padrão do sistema.

**Handy grava mas não acontece nada / não ouço resposta**
1. Veja `~/.local/share/voice-claude/logs/handler.log` — o trace completo está lá.
2. Confirme que `paste_method` está como `"external_script"` e `external_script_path` aponta para o `voice-claude-handler.sh` correto (saída de `cat ~/.local/share/com.pais.handy/settings_store.json | jq '.settings.paste_method, .settings.external_script_path'`).
3. Se o log diz `claude: command not found`, adicione o caminho do CLI ao PATH global ou use um caminho absoluto no handler.

**`claude: command not found` no handler mesmo funcionando no terminal**
O processo do Handy pode não ter seu shell rc carregado. Soluções: (a) instale o Claude Code globalmente (`/usr/local/bin/claude` ou equivalente), ou (b) edite o handler e substitua `claude` pelo caminho absoluto (`/home/$USER/.local/bin/claude` ou onde você o tiver).

**O primeiro chunk de áudio corta / a voz "engole" a primeira sílaba**
O sink HDMI estava em suspend. O handler faz pre-warm mas às vezes não é suficiente. Aumente `FIRST_CHUNK_LEAD_SILENCE_S` em `kokoro/stream_tts.py` (de 0.2s para 0.4s, por exemplo) ou evite que o sink suspenda com `pactl unload-module module-suspend-on-idle`.

**Kokoro demora muito / a resposta tem latência alta**
O daemon persistente deve eliminar ~1-2s de carregamento do modelo. Verifique se está rodando: `python3 ~/.local/share/voice-claude/kokoro/daemon.py --ping`. Se não responder, na próxima invocação o handler o reinicia automaticamente. Logs do daemon: `~/.local/share/voice-claude/logs/daemon.log`.

**Transcrição imprecisa de palavras técnicas (nomes de comandos, apps)**
O Handy suporta "custom words" na sua configuração. Adicione `hyprctl`, `pactl`, os nomes dos apps que você mais usa, etc. Você também pode tentar outro modelo Whisper/Parakeet na UI do Handy.

**Alt+Z não faz nada**
Verifique que o Hyprland recarregou o binding: `hyprctl reload` e revise a saída por erros. Verifique que o atalho não conflita com outro: `hyprctl binds | grep -i ',Z,'`.

**O modo completo responde "não tenho permissão"**
A whitelist não inclui o comando que você precisa. Adicione-o em `CLAUDE_FULL_BASH_ALLOW` no handler com o padrão `Bash(comando:*)`. Não use `Bash(*:*)` a menos que saiba exatamente o que está fazendo.

## Personalização

- **Voz / velocidade / sink:** edite `~/.local/share/voice-claude/config.yaml` (seção `tts`) ou exporte `VOICE_CLAUDE_VOICE`, `VOICE_CLAUDE_SPEED`, `VOICE_CLAUDE_SINK`. Vozes disponíveis em [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx); aceita blends como `ef_dora+af_bella`.
- **Keywords para screenshot:** em `config.yaml`, seção `screen_keywords.words` e `screen_keywords.phrases`. Adicione as suas; remova as que gerarem falsos positivos.
- **Modelo / esforço:** seção `models.quick` / `models.full` em `config.yaml`, ou diretamente em `voice-claude-handler.sh`.
- **Whitelist do modo completo:** `CLAUDE_FULL_BASH_ALLOW` e `CLAUDE_FULL_TOOLS_ALLOW` no handler. Adicione ou remova conforme seu workflow. **Nunca use `Bash(*:*)`** — equivale a `--dangerously-skip-permissions`.

## Créditos / inspiração

- Ideia original inspirada em [um vídeo do NateGentile](https://www.youtube.com/@NateGentile) sobre assistentes de voz para o Claude.
- STT: [Handy](https://handy.computer/) (Parakeet v3 local).
- TTS: [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) por [@thewh1teagle](https://github.com/thewh1teagle).
- CLI: [Claude Code](https://claude.com/claude-code) da Anthropic.

## Licença

MIT. Veja `LICENSE`.
