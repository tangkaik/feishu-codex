#!/usr/bin/env python3
"""
通过 AppleScript 向 Codex App 输入文字并提交
1. 激活 Codex（确保目标窗口在前台）
2. 剪贴板粘贴文字
3. 按回车提交
"""

import subprocess
import sys
import time
from pathlib import Path


def calculate_paste_delay(text: str) -> float:
    """长文本粘贴后给 Codex 输入框更多消化时间。"""
    return min(3.0, max(0.5, len(text) / 2500))


def build_applescript(paste_delay: float) -> str:
    """生成更保守的 Codex GUI 输入脚本。"""
    return f'''
    tell application "Codex"
        activate
    end tell

    tell application "System Events"
        repeat with i from 1 to 20
            if exists process "Codex" then
                tell process "Codex"
                    if frontmost and (count windows) > 0 then exit repeat
                end tell
            end if
            delay 0.2
        end repeat

        if not (exists process "Codex") then error "Codex process not available"
        tell process "Codex"
            if not frontmost then error "Codex is not frontmost"
            if (count windows) = 0 then error "Codex window not available"
        end tell

        keystroke "v" using command down
        delay {paste_delay:.1f}
        key code 36
    end tell

    return "submitted"
    '''


def applescript_string(value: str) -> str:
    """转义 AppleScript 字符串。"""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def build_image_applescript(image_path: str, upload_delay: float) -> str:
    """生成图片文件粘贴脚本。"""
    escaped_path = applescript_string(image_path)
    return f'''
    set imagePath to POSIX file "{escaped_path}"
    tell application "Finder"
        set the clipboard to imagePath
    end tell

    tell application "Codex"
        activate
    end tell

    tell application "System Events"
        repeat with i from 1 to 20
            if exists process "Codex" then
                tell process "Codex"
                    if frontmost and (count windows) > 0 then exit repeat
                end tell
            end if
            delay 0.2
        end repeat

        if not (exists process "Codex") then error "Codex process not available"
        tell process "Codex"
            if not frontmost then error "Codex is not frontmost"
            if (count windows) = 0 then error "Codex window not available"
        end tell

        keystroke "v" using command down
        delay {upload_delay:.1f}
        key code 36
    end tell

    return "submitted"
    '''


def set_clipboard(text: str) -> bool:
    """写入剪贴板并读回确认，避免空剪贴板或截断后继续发送。"""
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    pasted = subprocess.run(["pbpaste"], capture_output=True, check=True)
    return pasted.stdout.decode("utf-8", errors="replace") == text


def input_image_to_codex(image_path: str, upload_delay: float = 5.0) -> bool:
    """通过剪贴板把图片文件粘贴到 Codex，并等待上传后提交。"""
    path = Path(image_path).expanduser().resolve()
    if not path.exists():
        print(f"❌ 图片不存在: {path}")
        return False

    script = build_image_applescript(str(path), upload_delay)
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=max(20, int(upload_delay) + 15),
        )
        if result.returncode == 0:
            print(f"✅ 已粘贴图片并提交: {path}")
            return True
        print(f"❌ 失败: {result.stderr.strip()}")
        return False
    except subprocess.TimeoutExpired:
        print("❌ 图片粘贴 AppleScript 执行超时")
        return False
    except Exception as e:
        print(f"❌ 图片粘贴异常: {e}")
        return False


def input_to_codex(text: str) -> bool:
    """
    通过剪贴板粘贴 + 回车提交的方式向 Codex 输入文字
    """
    if not text.strip():
        print("⚠️ 没有文字需要输入")
        return False

    # 保存当前剪贴板内容
    get_clipboard = subprocess.run(['pbpaste'], capture_output=True)
    original_clipboard = get_clipboard.stdout

    try:
        # 1. 把文本放入剪贴板，并确认写入完整。
        if not set_clipboard(text):
            print("❌ 剪贴板写入校验失败，已取消发送")
            return False
        time.sleep(0.3)

        # 2. AppleScript：激活 Codex → 确认窗口 → 粘贴 → 回车
        script = build_applescript(calculate_paste_delay(text))

        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=15
        )

        # 恢复原始剪贴板内容
        time.sleep(0.5)
        subprocess.run(['pbcopy'], input=original_clipboard, check=False)

        if result.returncode == 0:
            print(f"✅ 已粘贴并提交 ({len(text)} 字符)")
            return True
        else:
            print(f"❌ 失败: {result.stderr.strip()}")
            return False

    except subprocess.TimeoutExpired:
        subprocess.run(['pbcopy'], input=original_clipboard, check=False)
        print("❌ AppleScript 执行超时")
        return False
    except Exception as e:
        subprocess.run(['pbcopy'], input=original_clipboard, check=False)
        print(f"❌ 异常: {e}")
        return False


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--image":
        success = input_image_to_codex(sys.argv[2])
        sys.exit(0 if success else 1)

    if len(sys.argv) < 2 and sys.stdin.isatty():
        print("用法: python3 codex_input.py <要输入的文字>")
        sys.exit(1)

    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = sys.stdin.read()
    success = input_to_codex(text)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
