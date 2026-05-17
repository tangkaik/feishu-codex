#!/usr/bin/env python3
"""
Codex 日志监控脚本
监控 ~/.codex/logs_2.sqlite，当看到 turn/completed 事件时，提取输出并发送飞书
"""

import sqlite3
import time
import sys
import json
from pathlib import Path

import send_to_feishu

# ========== 配置 ==========

CODEX_LOG_DB = Path.home() / ".codex" / "logs_2.sqlite"
POLL_INTERVAL = 2  # 秒
WORK_DIR = Path(__file__).resolve().parent
LAST_CHECKPOINT_FILE = WORK_DIR / ".codex_monitor_last_id.txt"

def get_last_checked_id():
    """获取上次检查到的最大日志 ID"""
    if LAST_CHECKPOINT_FILE.exists():
        try:
            return int(LAST_CHECKPOINT_FILE.read_text().strip())
        except:
            pass
    return None


def save_last_checked_id(last_id):
    """保存检查到的最大日志 ID"""
    LAST_CHECKPOINT_FILE.write_text(str(last_id))


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


def extract_output_from_log(log_body: str) -> str:
    """从日志中提取 Codex 的输出文本"""
    if not log_body:
        return ""

    # 支持两种格式:
    # 1. SSE event: {"type":"response.output_item.done","item":{"content":[{"type":"output_text","text":"..."}]}}
    # 2. Received message {"type":"response.output_item.done","item":{"content":[{"type":"output_text","text":"..."}]}}
    try:
        # 找到 JSON 部分（两种前缀都支持）
        for prefix in ['SSE event: ', 'Received message ']:
            json_start = log_body.find(prefix)
            if json_start != -1:
                json_str = log_body[json_start + len(prefix):]
                import json as json_module
                data = json_module.loads(json_str)

                # 提取 text 字段
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


def check_for_turn_completed():
    """检查日志中是否有新的 turn/completed 事件"""
    if not CODEX_LOG_DB.exists():
        print(f"❌ 日志文件不存在: {CODEX_LOG_DB}")
        return

    last_id = get_last_checked_id()
    conn = sqlite3.connect(CODEX_LOG_DB, timeout=5)
    cursor = conn.cursor()

    try:
        if last_id is None:
            # 第一次运行，获取最新的 ID
            cursor.execute("SELECT MAX(id) FROM logs")
            max_id = cursor.fetchone()[0]
            if max_id:
                save_last_checked_id(max_id)
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

        new_max_id = last_id
        output_buffer = []
        in_turn = False

        for row in rows:
            row_id, ts, level, target, body = row
            new_max_id = max(new_max_id, row_id)

            if body and "turn/completed" in body:
                # 发现 turn/completed 事件
                in_turn = True
                print(f"\n🔔 检测到 turn/completed 事件 (id={row_id})")

            if body and "response.output_item.done" in body:
                # 提取输出文本
                output = extract_output_from_log(body)
                if output:
                    output_buffer.append(output)
                    print(f"📝 提取到输出 ({len(output)} 字符)")

        # 如果检测到完整的 turn，发送飞书
        if output_buffer:
            full_output = "\n\n---\n\n".join(output_buffer)
            print(f"📤 发送 {len(full_output)} 字符到飞书...")
            send_feishu(full_output)

        # 更新检查点
        save_last_checked_id(new_max_id)

    finally:
        conn.close()


def main():
    print("=" * 50)
    print("🚀 Codex 日志监控启动")
    print(f"📁 日志文件: {CODEX_LOG_DB}")
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
