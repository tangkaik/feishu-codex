# feishu-codex

## 中文说明

`feishu-codex` 是一个很小的 macOS 本地桥接工具，用来让一个飞书群和 Codex 桌面 App 双向通信。

它的设计目标是个人使用、尽量自包含：配置、日志、消息状态、下载图片和 LaunchAgent wrapper 都围绕这个项目目录存放，避免依赖共享的全局助手目录。

### 功能

- 只轮询一个指定飞书群。
- 只处理一个指定飞书用户发来的消息。
- 将飞书文本消息粘贴到 Codex 桌面 App 并提交。
- 将飞书图片消息下载到本地，再把图片文件粘贴到 Codex，等待上传后提交。
- 监听 Codex 桌面日志，把 Codex 完成输出发回飞书群。
- 支持把本地图片上传并发送到飞书群。

### 环境要求

- macOS
- Python 3
- 已安装 Codex 桌面 App
- 一个具备读消息、发消息权限的飞书应用机器人
- 给运行脚本的终端或 shell、`osascript`、Codex 开启 macOS 辅助功能权限

这个工具通过 AppleScript 和 macOS 剪贴板控制 Codex GUI，所以需要电脑处于已登录、未锁屏的桌面会话中。锁屏、睡眠或合盖后不保证工作。

### 配置

先创建项目内 `.env`：

```bash
cp .env.example .env
```

然后填写：

```text
FEISHU_APP_ID
FEISHU_APP_SECRET
FEISHU_CHAT_ID
FEISHU_OWNER_USER_ID
```

可选：要求消息带命令前缀：

```text
FEISHU_CODEX_PREFIX=/codex
FEISHU_CODEX_REQUIRE_PREFIX=true
```

默认不要求前缀。这个工具只会监听 `FEISHU_CHAT_ID` 里的 `FEISHU_OWNER_USER_ID`。

如果飞书群里机器人回传消息很多，可以调整每次轮询读取的最近消息数量：

```text
FEISHU_POLL_PAGE_SIZE=50
```

飞书 API 当前最多支持 50。默认值也是 50。

### 单次运行

飞书到 Codex：

```bash
./feishu-to-codex-wrapper.sh
```

Codex 到飞书：

```bash
./monitor-wrapper.sh
```

发送本地图片到飞书：

```bash
python3 send_image_to_feishu.py /path/to/image.png
```

### 安装为 macOS 后台任务

安装两个 LaunchAgent：

```bash
./install.sh
```

安装后会创建：

- `~/Library/LaunchAgents/com.kaitang.feishu-codex.plist`
- `~/Library/LaunchAgents/com.kaitang.codex-feishu-output.plist`

飞书轮询任务每 10 秒运行一次。Codex 输出监听任务会常驻运行。

### 卸载

```bash
./uninstall.sh
```

执行后可以删除整个项目目录。这个项目的配置和运行状态不会和其他桥接工具共享。

### 文件说明

- `feishu_to_codex.py`：轮询飞书，并把符合条件的文本或图片消息转发到 Codex。
- `codex_input.py`：通过剪贴板和 AppleScript 控制 Codex GUI。
- `monitor.py`：监听 `~/.codex/logs_2.sqlite`，发现 Codex 完成输出后发回飞书。
- `send_to_feishu.py`：向飞书发送文本消息。
- `send_image_to_feishu.py`：上传并发送图片消息到飞书。
- `env_loader.py`：加载项目内 `.env`。
- `install.sh`：创建并加载 LaunchAgent。
- `uninstall.sh`：停止并移除 LaunchAgent。

### 测试

```bash
python3 -m unittest test_self_contained.py test_env_loader.py test_feishu_to_codex.py test_send_to_feishu.py test_send_image_to_feishu.py test_codex_input.py
python3 -m py_compile env_loader.py feishu_to_codex.py monitor.py send_to_feishu.py send_image_to_feishu.py codex_input.py
```

### 安全说明

- `.env` 会被 git 忽略。
- 运行日志和状态文件会被 git 忽略。
- 从飞书下载的图片会被 git 忽略。
- 工具会读取 Codex 本地日志数据库，但不会修改它。
- 工具提交消息时会临时写入 macOS 剪贴板，提交后会尝试恢复原剪贴板内容。

## English

`feishu-codex` is a small local macOS bridge that lets one Feishu group talk to the Codex desktop app in both directions.

It is built for personal use and tries to stay self-contained: configuration, logs, message state, downloaded images, and LaunchAgent wrappers live around this project directory instead of a shared global helper directory.

### Features

- Polls one configured Feishu group.
- Only accepts messages from one configured Feishu user.
- Pastes Feishu text messages into the Codex desktop app and submits them.
- Downloads Feishu image messages, pastes the image file into Codex, waits for upload, then submits.
- Watches Codex desktop logs and sends completed Codex output back to the Feishu group.
- Supports uploading and sending local images to Feishu.

### Requirements

- macOS
- Python 3
- Codex desktop app installed
- A Feishu app robot with message read/send permissions
- macOS Accessibility permission enabled for the terminal or shell that runs the scripts, `osascript`, and Codex

The bridge controls the Codex GUI through AppleScript and the macOS clipboard, so it needs an unlocked desktop session. It is not designed to keep working after the Mac is locked, asleep, or closed.

### Configuration

Create a project-local `.env`:

```bash
cp .env.example .env
```

Fill in:

```text
FEISHU_APP_ID
FEISHU_APP_SECRET
FEISHU_CHAT_ID
FEISHU_OWNER_USER_ID
```

Optional command prefix behavior:

```text
FEISHU_CODEX_PREFIX=/codex
FEISHU_CODEX_REQUIRE_PREFIX=true
```

By default, no prefix is required. The bridge only listens to `FEISHU_OWNER_USER_ID` inside `FEISHU_CHAT_ID`.

If the Feishu group has many bot reply messages, you can tune how many recent messages each poll reads:

```text
FEISHU_POLL_PAGE_SIZE=50
```

The Feishu API currently supports up to 50. The default is also 50.

### Run Once

Feishu to Codex:

```bash
./feishu-to-codex-wrapper.sh
```

Codex to Feishu:

```bash
./monitor-wrapper.sh
```

Send a local image to Feishu:

```bash
python3 send_image_to_feishu.py /path/to/image.png
```

### Install As macOS Background Jobs

Install both LaunchAgents:

```bash
./install.sh
```

This creates:

- `~/Library/LaunchAgents/com.kaitang.feishu-codex.plist`
- `~/Library/LaunchAgents/com.kaitang.codex-feishu-output.plist`

The Feishu polling job runs every 10 seconds. The Codex output monitor stays running.

### Uninstall

```bash
./uninstall.sh
```

After that, you can delete the project folder. Configuration and runtime state are not shared with other bridge tools.

### Files

- `feishu_to_codex.py`: polls Feishu and forwards eligible text/image messages into Codex.
- `codex_input.py`: controls the Codex GUI with clipboard and AppleScript.
- `monitor.py`: watches `~/.codex/logs_2.sqlite` for completed Codex output.
- `send_to_feishu.py`: sends text messages to Feishu.
- `send_image_to_feishu.py`: uploads and sends image messages to Feishu.
- `env_loader.py`: loads the project-local `.env`.
- `install.sh`: creates and loads LaunchAgents.
- `uninstall.sh`: stops and removes LaunchAgents.

### Tests

```bash
python3 -m unittest test_self_contained.py test_env_loader.py test_feishu_to_codex.py test_send_to_feishu.py test_send_image_to_feishu.py test_codex_input.py
python3 -m py_compile env_loader.py feishu_to_codex.py monitor.py send_to_feishu.py send_image_to_feishu.py codex_input.py
```

### Safety Notes

- `.env` is ignored by git.
- Runtime logs and state files are ignored by git.
- Downloaded Feishu images are ignored by git.
- The bridge reads Codex's local log database but does not modify it.
- The bridge writes to the macOS clipboard while submitting messages and then attempts to restore the previous clipboard content.
