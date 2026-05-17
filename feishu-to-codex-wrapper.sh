#!/bin/bash
# 加载项目内环境变量，然后运行 feishu_to_codex.py
cd "$(dirname "$0")"
set -a
source ./.env
set +a
python3 feishu_to_codex.py >> feishu_to_codex_cron.log 2>&1
