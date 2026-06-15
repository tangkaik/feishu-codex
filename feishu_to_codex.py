#!/usr/bin/env python3
"""
飞书 → Codex 自动转发脚本
每分钟运行一次，检查飞书群新消息，有来自主人的新消息就转发到 Codex
"""

import json
import os
import sys
import time
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from env_loader import load_env_file

# ========== 配置 ==========
WORK_DIR = Path(__file__).resolve().parent
STATE_FILE = WORK_DIR / ".last_feishu_msg.json"
CODEX_INPUT = WORK_DIR / "codex_input.py"
IMAGE_DIR = WORK_DIR / "inbox" / "images"

DEFAULT_OWNER_USER_ID = "ou_8855b63bbe7b897506524b494581bd75"
DEFAULT_CHAT_ID = "oc_3dd7f944c29d45316c1e0e657258d8b9"
OWNER_USER_ID = DEFAULT_OWNER_USER_ID
CHAT_ID = DEFAULT_CHAT_ID

# 日志
LOG_FILE = WORK_DIR / "feishu_to_codex.log"


load_env_file()


def log(msg):
    ts = time.strftime("%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def get_token():
    """获取飞书 access token"""
    import urllib.request
    app_id = os.environ.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        log("错误: 未设置 FEISHU_APP_ID 或 FEISHU_APP_SECRET")
        sys.exit(1)

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(url, data=data,
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        resp = json.loads(r.read())
    return resp.get("tenant_access_token", "")


def get_owner_user_id():
    return os.environ.get("FEISHU_OWNER_USER_ID", DEFAULT_OWNER_USER_ID)


def get_chat_id():
    return os.environ.get("FEISHU_CHAT_ID", DEFAULT_CHAT_ID)


def get_poll_page_size():
    try:
        page_size = int(os.environ.get("FEISHU_POLL_PAGE_SIZE", "50"))
    except ValueError:
        page_size = 50
    return min(50, max(10, page_size))


def get_recent_messages(token):
    """获取群最近消息（按时间正序）"""
    import urllib.request
    chat_id = get_chat_id()
    page_size = get_poll_page_size()
    url = (f"https://open.feishu.cn/open-apis/im/v1/messages"
           f"?container_id_type=chat&container_id={chat_id}"
           f"&sort_type=ByCreateTimeDesc&page_size={page_size}")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        log(f"获取消息 HTTP {e.code}: {body[:500]}")
        return []

    if resp.get("code") != 0:
        log(f"获取消息失败: {resp}")
        return []

    items = resp.get("data", {}).get("items", [])
    # 按时间正序（最旧的在前）
    items.reverse()
    return items


def extract_text(msg):
    """提取飞书文本消息内容。"""
    body = msg.get("body", {})
    content = body.get("content", "")
    try:
        content_obj = json.loads(content)
        return content_obj.get("text", "").strip()
    except Exception:
        return content.strip() if content else ""


def extract_image_key(msg):
    """提取飞书图片消息的 image_key。"""
    body = msg.get("body", {})
    content = body.get("content", "")
    try:
        content_obj = json.loads(content)
        return content_obj.get("image_key", "").strip()
    except Exception:
        return ""


def strip_command_prefix(text):
    """只接受带命令前缀的消息，避免普通聊天误投喂给 Codex。"""
    command_prefix = os.environ.get("FEISHU_CODEX_PREFIX", "")
    if os.environ.get("FEISHU_CODEX_REQUIRE_PREFIX", "").lower() in {"1", "true", "yes"}:
        command_prefix = command_prefix or "/codex"

    if not command_prefix:
        return text
    if text == command_prefix:
        return ""
    prefix = command_prefix + " "
    if text.startswith(prefix):
        return text[len(prefix):].strip()
    return ""


def select_new_messages(messages, last_msg_id=None, last_msg_time=0):
    """筛选需要发送给 Codex 的新消息。"""
    selected = []
    last_msg_time = float(last_msg_time or 0)
    owner_user_id = get_owner_user_id()
    chat_id = get_chat_id()

    for msg in messages:
        msg_id = msg.get("message_id", "")
        msg_time = float(msg.get("create_time", 0) or 0)
        sender = msg.get("sender", {})
        sender_id = sender.get("id", "") if isinstance(sender, dict) else ""
        msg_type = msg.get("msg_type", "")
        message_chat_id = msg.get("chat_id", chat_id)

        if message_chat_id != chat_id:
            continue
        if sender_id != owner_user_id:
            continue
        if msg_time < last_msg_time:
            continue
        if msg_time == last_msg_time and msg_id <= (last_msg_id or ""):
            continue

        if msg_type == "text":
            text = strip_command_prefix(extract_text(msg))
            if not text:
                continue
            selected.append({"id": msg_id, "time": msg_time, "type": "text", "text": text})
            continue

        if msg_type == "image":
            image_key = extract_image_key(msg)
            if not image_key:
                continue
            selected.append({"id": msg_id, "time": msg_time, "type": "image", "image_key": image_key})
            continue


    return selected


def download_image(token, message_id, image_key):
    """下载飞书图片消息到本地文件。"""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    safe_message_id = "".join(c for c in message_id if c.isalnum() or c in {"_", "-"})
    image_path = IMAGE_DIR / f"{safe_message_id}.png"
    url = (
        f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}"
        f"/resources/{image_key}?type=image"
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            image_path.write_bytes(r.read())
        return image_path
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        log(f"下载图片 HTTP {e.code}: {body[:500]}")
        return None
    except Exception as e:
        log(f"下载图片失败: {e}")
        return None


def record_processed_message(state, message, returncode, state_file=STATE_FILE):
    """Only advance the checkpoint after Codex GUI delivery succeeds."""
    if returncode != 0:
        return False

    state["last_msg_id"] = message["id"]
    state["last_msg_time"] = message["time"]
    if state_file is not None:
        state_file.write_text(json.dumps(state))
    return True


def main():
    # 加载上次处理状态
    state = {}
    if STATE_FILE.exists() and STATE_FILE.stat().st_size > 0:
        state = json.loads(STATE_FILE.read_text())

    last_msg_id = state.get("last_msg_id")
    last_msg_time = float(state.get("last_msg_time", 0))

    token = get_token()
    if not token:
        log("获取 token 失败")
        sys.exit(1)

    messages = get_recent_messages(token)
    if not messages:
        log("无新消息")
        sys.exit(0)

    new_messages = select_new_messages(messages, last_msg_id, last_msg_time)

    if not new_messages:
        log("无新消息（已处理到最新）")
        sys.exit(0)

    log(f"发现 {len(new_messages)} 条新消息")

    # 按时间顺序处理（最早在前）
    for m in new_messages:
        if m["type"] == "image":
            log(f"→ 转发图片到 Codex: {m['image_key']}")
            image_path = download_image(token, m["id"], m["image_key"])
            if not image_path:
                result = subprocess.CompletedProcess([], 1, "", "图片下载失败")
            else:
                result = subprocess.run(
                    [sys.executable, str(CODEX_INPUT), "--image", str(image_path)],
                    capture_output=True, text=True, timeout=60
                )
        else:
            text = m["text"]
            preview = text[:50] + ("..." if len(text) > 50 else "")
            log(f"→ 转发到 Codex: {preview}")
            result = subprocess.run(
                [sys.executable, str(CODEX_INPUT)],
                input=text,
                capture_output=True, text=True, timeout=45
            )
        if result.returncode == 0:
            log(f"  ✅ 发送成功")
        else:
            detail = (result.stderr or result.stdout or "").strip()
            log(f"  ❌ 失败: {detail[:500]}")
            log("  ⏳ 未更新飞书消息状态，下一轮会重试")
            break

        record_processed_message(state, m, result.returncode)

    log("完成")


if __name__ == "__main__":
    main()
