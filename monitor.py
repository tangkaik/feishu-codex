#!/usr/bin/env python3
"""
Codex 日志监控脚本
监控 ~/.codex/logs_2.sqlite，当看到 turn/completed 事件时，提取输出并发送飞书
"""

import sqlite3
import time
import sys
import json
import ast
import re
from pathlib import Path

import send_to_feishu
import send_image_to_feishu

# ========== 配置 ==========

POLL_INTERVAL = 2  # 秒
WORK_DIR = Path(__file__).resolve().parent
LAST_CHECKPOINT_FILE = WORK_DIR / ".codex_monitor_last_id.txt"
IMAGE_CHECKPOINT_FILE = WORK_DIR / ".codex_monitor_last_image_mtime.txt"
GENERATED_IMAGES_DIR = Path.home() / ".codex" / "generated_images"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def get_codex_log_db():
    candidates = [
        Path.home() / ".codex" / "sqlite" / "logs_2.sqlite",
        Path.home() / ".codex" / "logs_2.sqlite",
    ]
    existing = [path for path in candidates if path.exists()]
    if existing:
        return max(existing, key=lambda path: path.stat().st_mtime)
    return candidates[-1]


CODEX_LOG_DB = get_codex_log_db()


def get_checkpoint_file(log_db=None):
    log_db = Path(log_db or CODEX_LOG_DB)
    if log_db.parent.name == "sqlite":
        return WORK_DIR / ".codex_monitor_last_id_sqlite.txt"
    return LAST_CHECKPOINT_FILE


def get_last_checked_id(log_db=None):
    """获取上次检查到的最大日志 ID"""
    checkpoint_file = get_checkpoint_file(log_db)
    if checkpoint_file.exists():
        try:
            return int(checkpoint_file.read_text().strip())
        except:
            pass
    return None


def save_last_checked_id(last_id, log_db=None):
    """保存检查到的最大日志 ID"""
    get_checkpoint_file(log_db).write_text(str(last_id))


def get_last_image_mtime(checkpoint_file=IMAGE_CHECKPOINT_FILE):
    """获取上次已发送图片的最大修改时间。"""
    checkpoint_file = Path(checkpoint_file)
    if checkpoint_file.exists():
        try:
            return float(checkpoint_file.read_text().strip())
        except Exception:
            pass
    return time.time()


def save_last_image_mtime(last_mtime, checkpoint_file=IMAGE_CHECKPOINT_FILE):
    Path(checkpoint_file).write_text(str(float(last_mtime)))


def list_new_generated_images(image_root=GENERATED_IMAGES_DIR, since_mtime=None):
    """列出 checkpoint 之后新生成的图片。"""
    image_root = Path(image_root).expanduser()
    if not image_root.exists():
        return []

    since_mtime = float(since_mtime or 0)
    images = []
    for path in image_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if path.stat().st_mtime > since_mtime:
            images.append(path)
    return sorted(images, key=lambda path: (path.stat().st_mtime, str(path)))


def send_new_generated_images(image_root=GENERATED_IMAGES_DIR, checkpoint_file=IMAGE_CHECKPOINT_FILE):
    """发送新生成的图片到飞书，并推进图片 checkpoint。"""
    checkpoint_file = Path(checkpoint_file)
    last_mtime = get_last_image_mtime(checkpoint_file)
    images = list_new_generated_images(image_root, last_mtime)
    if not images:
        return 0

    sent_count = 0
    for image_path in images:
        print(f"🖼️ 发送生成图片到飞书: {image_path}")
        if not send_image_to_feishu.send_image(image_path):
            print(f"❌ 图片发送失败，保留 checkpoint: {image_path}")
            break
        sent_count += 1
        last_mtime = max(last_mtime, image_path.stat().st_mtime)
        save_last_image_mtime(last_mtime, checkpoint_file)
    return sent_count


def send_feishu(text: str) -> bool:
    """发送文本到飞书"""
    if len(text) > 4000:
        parts = []
        for i in range(0, len(text), 3990):
            parts.append(text[i:i+3990])
        for idx, part in enumerate(parts):
            part_text = f"[{idx+1}/{len(parts)}]\n{part}"
            if not send_to_feishu.send_codex_output(part_text):
                return False
        return True

    return send_to_feishu.send_codex_output(text)


def parse_sse_json(log_body: str) -> dict:
    for prefix in ['SSE event: ', 'Received message ']:
        json_start = log_body.find(prefix)
        if json_start != -1:
            json_str = log_body[json_start + len(prefix):]
            return json.loads(json_str)
    return {}


def extract_output_from_log(log_body: str) -> str:
    """从日志中提取 Codex 的输出文本"""
    if not log_body:
        return ""

    # 支持两种格式:
    # 1. SSE event: {"type":"response.output_item.done","item":{"content":[{"type":"output_text","text":"..."}]}}
    # 2. Received message {"type":"response.output_item.done","item":{"content":[{"type":"output_text","text":"..."}]}}
    try:
        data = parse_sse_json(log_body)
        item = data.get("item", {})
        content = item.get("content", [])
        for c in content:
            if c.get("type") == "output_text":
                text = c.get("text", "")
                if text:
                    return text.strip()
    except:
        pass

    return ""


def extract_delta_from_log(log_body: str) -> str:
    """从流式 output_text.delta 日志中提取增量文本。"""
    if not log_body:
        return ""
    try:
        data = parse_sse_json(log_body)
        if data.get("type") == "response.output_text.delta":
            return data.get("delta", "")
    except:
        pass
    return ""


def extract_debug_output_from_log(log_body: str) -> str:
    """从新版 Rust debug 风格 Output item 日志中提取输出文本。"""
    if not log_body or "Output item item=Message" not in log_body:
        return ""

    match = re.search(r'OutputText \{ text: "((?:\\.|[^"\\])*)"', log_body, re.S)
    if not match:
        return ""

    raw_text = match.group(1)
    try:
        return ast.literal_eval(f'"{raw_text}"').strip()
    except Exception:
        return raw_text.replace("\\n", "\n").replace('\\"', '"').strip()


def collect_output_from_rows(rows, last_id):
    """从新增日志行中收集完整输出，并决定检查点应推进到哪里。"""
    new_max_id = last_id
    output_buffer = []
    saw_completion = False
    saw_streaming_output = False
    saw_legacy_done_output = False

    for row in rows:
        row_id, ts, level, target, body = row
        new_max_id = max(new_max_id, row_id)
        if not body:
            continue

        if "turn/completed" in body or "response.completed" in body or "item/completed" in body:
            saw_completion = True
            if "turn/completed" in body:
                print(f"\n🔔 检测到 turn/completed 事件 (id={row_id})")

        if "response.output_item.done" in body:
            output = extract_output_from_log(body)
            if output:
                output_buffer.append(output)
                saw_legacy_done_output = True
                print(f"📝 提取到输出 ({len(output)} 字符)")
            continue

        if "response.output_text.delta" in body:
            delta = extract_delta_from_log(body)
            if delta:
                output_buffer.append(delta)
                saw_streaming_output = True

        if "Output item item=Message" in body:
            output = extract_debug_output_from_log(body)
            if output:
                output_buffer.append(output)
                saw_legacy_done_output = True
                print(f"📝 提取到新版输出 ({len(output)} 字符)")

    if output_buffer and (saw_legacy_done_output or saw_completion):
        return new_max_id, "".join(output_buffer).strip()

    if saw_streaming_output and not saw_completion:
        return last_id, ""

    return new_max_id, ""


def rows_have_completion(rows):
    """判断新增日志是否包含一轮输出完成事件。"""
    for row in rows:
        body = row[4] if len(row) > 4 else ""
        if body and ("turn/completed" in body or "response.completed" in body or "item/completed" in body):
            return True
    return False


def check_for_turn_completed():
    """检查日志中是否有新的 turn/completed 事件"""
    log_db = get_codex_log_db()
    if not log_db.exists():
        print(f"❌ 日志文件不存在: {log_db}")
        return

    last_id = get_last_checked_id(log_db)
    conn = sqlite3.connect(log_db, timeout=5)
    cursor = conn.cursor()

    try:
        if last_id is None:
            # 第一次运行，获取最新的 ID
            cursor.execute("SELECT MAX(id) FROM logs")
            max_id = cursor.fetchone()[0]
            if max_id:
                save_last_checked_id(max_id, log_db)
                print(f"📍 初始化检查点: id={max_id}")
            return

        # 查询新增的日志
        query = """
            SELECT id, ts, level, target, feedback_log_body
            FROM logs
            WHERE id > ?
            ORDER BY id ASC
        """
        cursor.execute(query, (last_id,))
        rows = cursor.fetchall()

        if not rows:
            return

        new_max_id, full_output = collect_output_from_rows(rows, last_id)
        saw_completion = rows_have_completion(rows)

        # 如果检测到完整的 turn，发送飞书
        if full_output:
            print(f"📤 发送 {len(full_output)} 字符到飞书...")
            send_feishu(full_output)
        if saw_completion:
            sent_images = send_new_generated_images()
            if sent_images:
                print(f"✅ 已发送 {sent_images} 张生成图片到飞书")

        # 更新检查点
        save_last_checked_id(new_max_id, log_db)

    finally:
        conn.close()


def main():
    print("=" * 50)
    print("🚀 Codex 日志监控启动")
    print(f"📁 日志文件: {get_codex_log_db()}")
    print(f"⏱️ 轮询间隔: {POLL_INTERVAL} 秒")
    print("=" * 50)

    try:
        while True:
            check_for_turn_completed()
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n👋 监控停止")
        sys.exit(0)


if __name__ == "__main__":
    main()
