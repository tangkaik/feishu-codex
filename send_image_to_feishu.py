#!/usr/bin/env python3
"""上传本地图片并通过飞书应用机器人发送到 Codex 群。"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from env_loader import PROJECT_ENV_FILE, load_env_file as load_project_env_file


DEFAULT_CHAT_ID = "oc_3dd7f944c29d45316c1e0e657258d8b9"


load_project_env_file()


def get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def get_tenant_access_token() -> str:
    app_id = get_env("FEISHU_APP_ID")
    app_secret = get_env("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        print("❌ 未配置 FEISHU_APP_ID 或 FEISHU_APP_SECRET")
        return ""

    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=data,
        headers={"Content-Type": "application/json"},
    )
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


def upload_image(token: str, image_path: Path) -> str:
    result = subprocess.run(
        [
            "curl",
            "-sS",
            "-X",
            "POST",
            "https://open.feishu.cn/open-apis/im/v1/images",
            "-H",
            f"Authorization: Bearer {token}",
            "-F",
            "image_type=message",
            "-F",
            f"image=@{image_path}",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        print(f"❌ 图片上传命令失败: {result.stderr.strip()}")
        return ""

    response = json.loads(result.stdout)
    if response.get("code") != 0:
        print(f"❌ 图片上传失败: {response}")
        return ""
    return response.get("data", {}).get("image_key", "")


def send_image_message(token: str, image_key: str) -> bool:
    chat_id = get_env("FEISHU_CHAT_ID", DEFAULT_CHAT_ID)
    payload = {
        "receive_id": chat_id,
        "msg_type": "image",
        "content": json.dumps({"image_key": image_key}, ensure_ascii=False),
    }
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("code") == 0:
            print("✅ 图片消息发送成功")
            return True
        print(f"❌ 图片消息发送失败: {result}")
        return False
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"❌ 发送 HTTP {e.code}: {body[:500]}")
        return False
    except Exception as e:
        print(f"❌ 发送异常: {e}")
        return False


def send_image(image_path) -> bool:
    path = Path(image_path).expanduser().resolve()
    if not path.exists():
        print(f"❌ 图片不存在: {path}")
        return False

    token = get_tenant_access_token()
    if not token:
        return False

    image_key = upload_image(token, path)
    if not image_key:
        return False

    return send_image_message(token, image_key)


def load_env_file():
    return load_project_env_file(PROJECT_ENV_FILE)


def main():
    load_env_file()
    if len(sys.argv) != 2:
        print("用法: python3 send_image_to_feishu.py /path/to/image.png")
        sys.exit(1)
    sys.exit(0 if send_image(sys.argv[1]) else 1)


if __name__ == "__main__":
    main()
