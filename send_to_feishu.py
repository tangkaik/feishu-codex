#!/usr/bin/env python3
"""
飞书消息发送模块
通过飞书 Webhook 发送文本消息到群组
"""

import json
import sys
import os
import urllib.request
import urllib.error
from datetime import datetime

from env_loader import load_env_file

# 飞书 Webhook 配置
# 请替换为你的飞书群机器人 Webhook 地址
FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "")

# 飞书机器人的名称
BOT_NAME = "Codex 监控"

# 应用机器人发送配置
DEFAULT_CHAT_ID = "oc_3dd7f944c29d45316c1e0e657258d8b9"


load_env_file()


def get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def send_text_message(text: str, phone_numbers: list = None) -> bool:
    """
    发送文本消息到飞书群

    Args:
        text: 消息内容（最多 4000 字符）
        phone_numbers: 需要 @ 的手机号列表（可选）

    Returns:
        bool: 发送是否成功
    """
    if len(text) > 4000:
        # 飞书单条消息限制 4000 字符，分多条发送
        parts = []
        for i in range(0, len(text), 3990):
            parts.append(text[i:i+3990])
        success = True
        for idx, part in enumerate(parts):
            part_text = f"[{idx+1}/{len(parts)}]\n{part}"
            if not _send_single_message(part_text, phone_numbers):
                success = False
        return success

    return _send_single_message(text, phone_numbers)


def _send_single_message(text: str, phone_numbers: list = None) -> bool:
    """发送单条消息（4000 字以内）"""
    webhook_url = get_env("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        return _send_single_message_via_app(text)

    # 构建消息内容
    content = {
        "msg_type": "text",
        "content": {
            "text": text
        }
    }

    # 如果有需要 @ 的人，把手机号加到文本里
    if phone_numbers:
        at_text = " ".join([f"<at phone=\"{phone}\"></at>" for phone in phone_numbers])
        content["content"]["text"] = text + "\n" + at_text

    try:
        data = json.dumps(content).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("code") == 0:
                print(f"✅ 消息发送成功: {text[:50]}...")
                return True
            else:
                print(f"❌ 发送失败: {result}")
                return False
    except urllib.error.URLError as e:
        print(f"❌ 网络错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 发送异常: {e}")
        return False


def get_tenant_access_token() -> str:
    app_id = get_env("FEISHU_APP_ID")
    app_secret = get_env("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        print("❌ 未配置 FEISHU_APP_ID 或 FEISHU_APP_SECRET")
        return ""

    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("code") != 0:
            print(f"❌ 获取 token 失败: {result}")
            return ""
        return result.get("tenant_access_token", "")
    except Exception as e:
        print(f"❌ 获取 token 异常: {e}")
        return ""


def _send_single_message_via_app(text: str) -> bool:
    """使用当前飞书应用机器人发送群消息。"""
    token = get_tenant_access_token()
    if not token:
        return False

    chat_id = get_env("FEISHU_CHAT_ID", DEFAULT_CHAT_ID)
    content = json.dumps({"text": text}, ensure_ascii=False)
    payload = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": content,
    }
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"

    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("code") == 0:
            print(f"✅ 消息发送成功: {text[:50]}...")
            return True
        print(f"❌ 发送失败: {result}")
        return False
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"❌ 发送 HTTP {e.code}: {body[:500]}")
        return False
    except Exception as e:
        print(f"❌ 发送异常: {e}")
        return False


def send_codex_output(output_text: str, session_id: str = None) -> bool:
    """
    发送 Codex 输出，专门格式化

    Args:
        output_text: Codex 的输出内容
        session_id: 可选的会话 ID

    Returns:
        bool: 发送是否成功
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header = f"🤖 **Codex 执行完成**\n"
    header += f"🕐 时间: {timestamp}\n"
    if session_id:
        header += f"📋 会话: {session_id}\n"
    header += "=" * 20 + "\n\n"

    full_message = header + output_text

    return send_text_message(full_message)


def main():
    """从 stdin 读取内容并发送"""
    if len(sys.argv) > 1:
        # 从命令行参数读取
        message = " ".join(sys.argv[1:])
    else:
        # 从 stdin 读取
        message = sys.stdin.read()

    if not message.strip():
        print("⚠️ 没有内容需要发送")
        return

    success = send_codex_output(message)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
