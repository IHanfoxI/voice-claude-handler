🇪🇸 [Español](README.md) &nbsp;·&nbsp; [🇬🇧 English](README.en.md) &nbsp;·&nbsp; [🇧🇷 Português](README.pt.md) &nbsp;·&nbsp; [🇩🇪 Deutsch](README.de.md) &nbsp;·&nbsp; [🇫🇷 Français](README.fr.md) &nbsp;·&nbsp; 🇨🇳 中文 &nbsp;·&nbsp; [🟩 Esperanto](README.eo.md)

---

# voice-claude-handler

语音助手，可在任何应用程序（包括全屏游戏）中向 **Claude Code** 发出指令。你的问题以语音输入，答案以语音输出——**无需**在当前窗口输入文字，**不会**抢夺焦点。

```
快捷键 → Handy（语音转文字） → 本 handler → Claude Code → Kokoro（文字转语音） → 音频
```

专为那些在游戏、视频剪辑或双手忙碌时想询问 Claude 的用户而设计。针对 Linux + Hyprland + Wayland 构建，但可适配任何能通过快捷键启动脚本的环境。

## 功能介绍

- **Alt+Z（快速模式）：** Claude Haiku 4.5，使用 `--allowedTools Read`。适合快速、低成本的查询。
- **Super+Z（完整模式）：** Claude Opus 4.7，使用显式命令白名单（`hyprctl`、`pactl`、`playerctl`、`omarchy*`、`steam`、`uwsm-app`、`setsid`、`notify-send`、`ls/cat/grep/find/jq/du/df` 等）以及非破坏性工具（`Read`、`Write`、`Edit`、`WebFetch`、`WebSearch`）。用于执行操作："打开 Spotify"、"下载文件夹有多大"、"暂停视频"。
- **Alt+Shift+Z（取消）：** 以协作信号取消当前响应——`stream_tts.py` 在句子间停止并终止当前 `paplay` 进程。
- **懒加载截图：** 如果你的问题包含视觉关键词（"那个窗口显示什么"、"读一下这个错误"、"那个按钮"），则使用 `grim` 截图并随问题一起发送；否则跳过——每次调用节省约 500ms 和 3k tokens。
- **流式 TTS，三线程管道：** 合成与播放并行运行（stdin 线程、synth 线程、player 线程）。持久 Kokoro 守护进程消除约 1-2s 的模型加载延迟。首字节时间约 0.3s。
- **状态音效：** 录音时播放上升音，处理时播放下降音，Claude 思考时循环播放柔和铃声。兼容独占全屏（音频，非 overlay）。
- **持久会话：** 每种模式维护独立的 Claude Code 会话（固定 UUID），Claude 在多次提问间保持上下文记忆。
- **语音重置：** 说"清除对话"（或"新对话"、"清空历史"）即可重新开始——即时 TTS 响应，不调用 Claude。

## 依赖项

| 组件 | 用途 |
|---|---|
| [Claude Code CLI](https://claude.com/claude-code) | 核心大脑 |
| [Handy](https://handy.computer/) | 本地语音转文字（Parakeet v3 或你选择的模型） |
| Hyprland（或支持全局快捷键的窗口管理器） | 用于 Alt+Z / Super+Z |
| `grim` | Wayland 截图 |
| `paplay`（pulseaudio / pipewire-pulse） | 音频播放 |
| `jq`、`iconv`、`notify-send` | handler 工具 |
| Python 3.10+ | Kokoro 的虚拟环境 |

在 CachyOS + Hyprland + Omarchy 上测试通过。应可在任何 Arch 衍生发行版以及其他使用 Wayland 的 Linux 发行版上运行（需根据包名稍作调整）。

## 安装

```bash
git clone git@github.com:IHanfoxI/voice-claude-handler.git
cd voice-claude-handler
./install.sh
```

安装脚本会询问你需要哪些状态指示器（视觉 overlay、声音、两者或均不需要）。然后：
- 将 `bin/voice-claude-handler.sh` 及 Python 脚本复制到各自目标位置。
- 下载 Kokoro 模型（约 325 MB）和语音文件（约 28 MB）。
- 在虚拟环境中安装 `kokoro-onnx`、`soundfile`、`numpy`、`pyyaml`。
- 生成 Claude 会话的 UUID。
- 将示例 `config.yaml` 复制到 `~/.local/share/voice-claude/config.yaml`。
- 输出后续配置步骤。

非交互式安装标志：`--no-overlay`、`--no-sound`、`--no-extras`。

## 配置

### 1. Handy

打开 Handy → **Settings**：
- **Output → Paste method：** `External script`
- **Output → External script path：** `~/.local/bin/voice-claude-handler.sh`
- **Audio → Microphone：** 选择你的麦克风
- **General → App language：** 你使用的语言

如需直接编辑 JSON（请在 Handy **关闭**时操作），参考 `examples/handy-settings-relevant.json` 中的相关字段。**不要覆盖整个文件**：Handy 自行管理该文件，其中有不应破坏的默认值。

### 2. Hyprland（快捷键）

将两个绑定添加到你的配置文件：

- **Omarchy / lua：** 将 `examples/hyprland-bindings.lua` 复制到 `~/.config/hypr/bindings.lua`。
- **经典 hyprland.conf：** 将 `examples/hyprland-bindings.conf` 复制到 `~/.config/hypr/hyprland.conf`。

重新加载：`hyprctl reload`。

### 3.（可选）config.yaml

安装脚本会将带注释的模板复制到 `~/.local/share/voice-claude/config.yaml`。你可以在此修改语音、速度、音频输出设备及触发截图的关键词：

```yaml
tts:
  voice: "ef_dora+af_bella"
  speed: 1.3
  sink: ""           # 空 = 默认输出设备。例如："alsa_output.pci-0000_XX_00.X.hdmi-stereo"
screen_keywords:
  words: [屏幕, 窗口, ...]   # 添加你自己的关键词
  phrases: ["显示什么", ...]
```

环境变量（`VOICE_CLAUDE_VOICE`、`VOICE_CLAUDE_SPEED`、`VOICE_CLAUDE_SINK`）仍然有效，且优先级高于 YAML 配置。

### 4. 工作目录中的 CLAUDE.md

handler 在调用 Claude 前执行 `cd ~/.local/share/voice-claude/workdir`，因此该目录中的 `CLAUDE.md` 会自动作为上下文加载。在其中填入你的应用程序、快捷键、常用 Steam 游戏等信息——Claude 以此了解如何在你的特定系统上执行操作。

安装脚本会复制一份示例文件，请将占位符替换为你的实际数据。

## 使用方法

1. 按下 **Alt+Z**（快速模式）或 **Super+Z**（完整模式）。
2. 说话。Handy 持续监听，直到你再次按下快捷键（或根据你的配置检测到静音）。
3. 松开。Handy 转录 → handler 判断是否需要截图 → 调用 Claude → 通过 TTS 听到响应。

日志：`~/.local/share/voice-claude/logs/handler.log`。

## 状态指示器（可选）

右上角的小圆点（layer-shell，即使在全屏下也可见），根据系统状态变换颜色：

| 颜色 | 状态 |
|---|---|
| 🟢 绿色 | Handy 正在听你说话 |
| 🟡 琥珀色 | Claude 正在思考（生成回复） |
| 🔵 蓝色 | TTS 正在播放回复 |
| 🔴 红色 | 错误（约 2.5 秒后自动隐藏） |
| （隐藏） | 空闲 |

需要 `gtk4-layer-shell` + `python-gobject`（Arch：`sudo pacman -S gtk4-layer-shell python-gobject`）。Hyprland 自动启动配置已包含在 `examples/hyprland-bindings.{lua,conf}` 的 `exec-once` 中。手动测试：

```bash
voice-claude-overlay &
echo speaking > ~/.local/share/voice-claude/state
```

状态由 handler、`stream_tts.py`、cancel 脚本和快捷键（`listening`）自动写入。大小/位置可通过环境变量配置：`VOICE_CLAUDE_OVERLAY_SIZE`、`VOICE_CLAUDE_OVERLAY_MARGIN_TOP`、`VOICE_CLAUDE_OVERLAY_MARGIN_RIGHT`。

## ⚠️ 关于 Super+Z 模式（完整模式）

完整模式使用 `--allowedTools` 启动 Claude Opus，指向**显式白名单**：

- **Bash：** 仅限 `hyprctl`、`pactl`、`playerctl`、`wpctl`、`brightnessctl`、`omarchy*`、`uwsm-app`、`steam`、`setsid`、`notify-send`、`ls`、`cat`、`grep`、`rg`、`find`、`jq`、`du`、`df`、`date`、`uptime`、`free`、`echo`、`printf`。
- **工具：** `Read`、`Write`、`Edit`、`Glob`、`Grep`、`WebFetch`、`WebSearch`。
- **已封锁：** `rm`、`sudo`、`chmod`、`chown`、`dd`、`mv` 以及任何未列出的 Bash 命令。

如果转录出错（例如"删除下载文件夹"被误解），Claude **没有权限**造成破坏。系统提示会要求 Claude 说"我做不到"并提供替代方案。

尽管如此，白名单范围依然宽泛：可移动、编辑和创建文件（`Edit`、`Write`），打开任何 Steam 游戏，执行 `omarchy *`。请谨慎使用。若需添加命令，编辑 `bin/voice-claude-handler.sh` 中的 `CLAUDE_FULL_BASH_ALLOW`。**永远不要使用 `Bash(*:*)`**——这等同于 `--dangerously-skip-permissions`。

快速模式（Alt+Z）仅允许 `Read`，完全安全。

## 故障排查

**`paplay: Failed to open audio file` / `Connection refused`**
系统使用 pipewire 但未安装 `pipewire-pulse`，或 pulseaudio 未运行。安装 `pipewire-pulse`（Arch：`sudo pacman -S pipewire-pulse`）并重启会话。用 `pactl info` 验证是否显示"Server Name: PulseAudio (on PipeWire ...)"。

**`paplay: Failure: No such entity` 或音频从错误设备输出**
导出的 `VOICE_CLAUDE_SINK` 不存在或已更改。用 `pactl list short sinks` 列出当前设备，复制准确名称（第二列）并重新导出。如果不需要指定设备，无需导出——handler 使用系统默认值。

**Handy 录音但什么都没发生 / 听不到响应**
1. 查看 `~/.local/share/voice-claude/logs/handler.log`——完整追踪记录在那里。
2. 确认 `paste_method` 为 `"external_script"` 且 `external_script_path` 指向正确的 `voice-claude-handler.sh`。
3. 若日志显示 `claude: command not found`，将 CLI 路径添加到全局 PATH 或在 handler 中使用绝对路径。

**handler 中显示 `claude: command not found`，但终端中可以正常运行**
Handy 进程可能未加载你的 shell rc。解决方案：(a) 全局安装 Claude Code（`/usr/local/bin/claude` 或同等位置），或 (b) 编辑 handler，将 `claude` 替换为绝对路径。

**第一段音频被截断 / 语音"吞掉"了第一个音节**
HDMI 设备处于挂起状态。handler 会预热，但有时不够。将 `kokoro/stream_tts.py` 中的 `FIRST_CHUNK_LEAD_SILENCE_S` 从 0.2s 增加到 0.4s，或用 `pactl unload-module module-suspend-on-idle` 阻止设备挂起。

**Kokoro 延迟高 / 响应慢**
持久守护进程应消除约 1-2s 的模型加载延迟。验证守护进程是否运行：`python3 ~/.local/share/voice-claude/kokoro/daemon.py --ping`。若无响应，handler 将在下次调用时自动重启。守护进程日志：`~/.local/share/voice-claude/logs/daemon.log`。

**技术词汇（命令名、应用名）转录不准确**
Handy 在配置中支持"自定义词汇"。添加 `hyprctl`、`pactl`、你最常用的应用名称等。也可以从 Handy 界面尝试其他 Whisper/Parakeet 模型。

**Alt+Z 没有反应**
检查 Hyprland 是否重新加载了绑定：`hyprctl reload` 并查看输出是否有错误。验证快捷键是否与其他冲突：`hyprctl binds | grep -i ',Z,'`。

**完整模式回复"没有权限"**
白名单中不包含你需要的命令。以 `Bash(命令:*)` 格式将其添加到 handler 中的 `CLAUDE_FULL_BASH_ALLOW`。除非清楚自己在做什么，否则不要使用 `Bash(*:*)`。

## 自定义

- **语音 / 速度 / 输出设备：** 编辑 `~/.local/share/voice-claude/config.yaml`（`tts` 部分），或导出 `VOICE_CLAUDE_VOICE`、`VOICE_CLAUDE_SPEED`、`VOICE_CLAUDE_SINK`。可用语音列表见 [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx)；支持混合如 `ef_dora+af_bella`。
- **速度：** `VOICE_CLAUDE_SPEED`（默认 `1.3`）。`0.8` 到 `1.5` 之间的值通常效果较好。
- **模型 / 推理强度：** `config.yaml` 中的 `models.quick` / `models.full` 部分，或直接编辑 `voice-claude-handler.sh`。
- **完整模式白名单：** handler 中 `if [[ "$MODE" == "full" ]]` 块开头的 `CLAUDE_FULL_BASH_ALLOW` 和 `CLAUDE_FULL_TOOLS_ALLOW`。根据你的工作流添加或删除命令。
- **截图关键词：** 在 `config.yaml` 的 `screen_keywords.words` 和 `screen_keywords.phrases` 中配置。添加你自己的关键词，删除导致误触发的条目。

## 致谢 / 灵感来源

- 原始创意灵感来自 [NateGentile 的视频](https://www.youtube.com/@NateGentile)（关于 Claude 的语音助手）。
- 语音转文字：[Handy](https://handy.computer/)（本地 Parakeet v3）。
- 文字转语音：[@thewh1teagle](https://github.com/thewh1teagle) 的 [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx)。
- CLI：Anthropic 的 [Claude Code](https://claude.com/claude-code)。

## 许可证

MIT。详见 `LICENSE`。
