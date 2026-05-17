#!/bin/bash
set -u

USER_ID="$(id -u)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
SERVICES=(
  "com.kaitang.feishu-codex"
  "com.kaitang.codex-feishu-output"
)

for service in "${SERVICES[@]}"; do
  plist="$LAUNCH_AGENTS_DIR/$service.plist"
  launchctl bootout "gui/$USER_ID" "$plist" >/dev/null 2>&1 || true
  rm -f "$plist"
done

rm -f /tmp/codex_monitor_last_id.txt

echo "feishu-codex launch agents removed. You can delete this folder now."
