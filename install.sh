#!/bin/bash
set -eu

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_ID="$(id -u)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

mkdir -p "$LAUNCH_AGENTS_DIR"

cat > "$LAUNCH_AGENTS_DIR/com.kaitang.feishu-codex.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.kaitang.feishu-codex</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$PROJECT_DIR/feishu-to-codex-wrapper.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StartInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/feishu_to_codex_launchd.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/feishu_to_codex_launchd.err.log</string>
</dict>
</plist>
PLIST

cat > "$LAUNCH_AGENTS_DIR/com.kaitang.codex-feishu-output.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.kaitang.codex-feishu-output</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$PROJECT_DIR/monitor-wrapper.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/monitor_launchd.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/monitor_launchd.err.log</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$USER_ID" "$LAUNCH_AGENTS_DIR/com.kaitang.feishu-codex.plist" >/dev/null 2>&1 || true
launchctl bootout "gui/$USER_ID" "$LAUNCH_AGENTS_DIR/com.kaitang.codex-feishu-output.plist" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$USER_ID" "$LAUNCH_AGENTS_DIR/com.kaitang.feishu-codex.plist"
launchctl bootstrap "gui/$USER_ID" "$LAUNCH_AGENTS_DIR/com.kaitang.codex-feishu-output.plist"

echo "feishu-codex LaunchAgent 已安装。"
echo "feishu-codex launch agents installed."
