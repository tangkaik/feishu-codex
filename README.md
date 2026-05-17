# feishu-codex

A small macOS bridge that lets a Feishu group talk to the Codex desktop app.

It is intentionally personal and local-first: configuration, logs, message state, downloaded images, and LaunchAgent wrappers all live around this project instead of a shared global helper directory.

## What It Does

- Polls one Feishu group for messages from one allowed user.
- Pastes text messages into the Codex desktop app and submits them.
- Downloads Feishu image messages, pastes the image file into Codex, waits for upload, then submits.
- Watches Codex desktop logs and sends completed Codex output back to the Feishu group.
- Sends generated/local images back to Feishu through the Feishu app robot.

## Requirements

- macOS
- Python 3
- Codex desktop app installed
- A Feishu app robot with message read/send permissions
- Accessibility permission enabled for the terminal/shell that runs the scripts, `osascript`, and Codex

The bridge controls the Codex GUI through AppleScript and the macOS clipboard, so it needs an unlocked desktop session. It is not designed to keep working after the Mac is locked or asleep.

## Configuration

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

Optional prefix behavior:

```text
FEISHU_CODEX_PREFIX=/codex
FEISHU_CODEX_REQUIRE_PREFIX=true
```

By default, the prefix is disabled. The bridge only listens to `FEISHU_CHAT_ID` and `FEISHU_OWNER_USER_ID`.

## Run Once

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

## Install As macOS LaunchAgents

Install both background jobs:

```bash
./install.sh
```

This creates:

- `~/Library/LaunchAgents/com.kaitang.feishu-codex.plist`
- `~/Library/LaunchAgents/com.kaitang.codex-feishu-output.plist`

The Feishu polling job runs every 10 seconds. The Codex output monitor stays running.

## Uninstall

```bash
./uninstall.sh
```

After that, you can delete the project folder. The project is designed so local configuration and runtime state are not shared with other bridges.

## Files

- `feishu_to_codex.py`: polls Feishu and forwards eligible text/image messages into Codex.
- `codex_input.py`: controls the Codex GUI with clipboard and AppleScript.
- `monitor.py`: watches `~/.codex/logs_2.sqlite` for completed Codex output.
- `send_to_feishu.py`: sends text back to Feishu.
- `send_image_to_feishu.py`: uploads and sends image messages to Feishu.
- `env_loader.py`: loads project-local `.env`.
- `install.sh`: creates and loads the LaunchAgents.
- `uninstall.sh`: stops and removes the LaunchAgents.

## Tests

```bash
python3 -m unittest test_self_contained.py test_env_loader.py test_feishu_to_codex.py test_send_to_feishu.py test_send_image_to_feishu.py test_codex_input.py
python3 -m py_compile env_loader.py feishu_to_codex.py monitor.py send_to_feishu.py send_image_to_feishu.py codex_input.py
```

## Safety Notes

- `.env` is ignored by git.
- Runtime logs and state files are ignored by git.
- Downloaded Feishu images are ignored by git.
- The bridge reads Codex's local log database but does not modify it.
- The bridge writes to the macOS clipboard while submitting messages and then attempts to restore the previous clipboard content.
