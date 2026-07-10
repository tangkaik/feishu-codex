#!/bin/bash
# 加载项目内环境变量，然后运行 feishu_to_codex.py
cd "$(dirname "$0")"
if [ -f ./.env ]; then
  set -a
  source ./.env
  set +a
fi
python3 feishu_to_codex.py >> feishu_to_codex_cron.log 2>&1
