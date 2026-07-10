import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import monitor


def sse(payload):
    return "SSE event: " + json.dumps(payload, ensure_ascii=False)


class MonitorOutputExtractionTest(unittest.TestCase):
    def test_prefers_most_recent_codex_log_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            nested_db = home / ".codex" / "sqlite" / "logs_2.sqlite"
            root_db = home / ".codex" / "logs_2.sqlite"
            nested_db.parent.mkdir(parents=True)
            root_db.parent.mkdir(parents=True, exist_ok=True)
            nested_db.write_text("")
            root_db.write_text("")
            old_time = 1000
            new_time = 2000
            nested_db.touch()
            root_db.touch()
            import os
            os.utime(nested_db, (old_time, old_time))
            os.utime(root_db, (new_time, new_time))

            with patch.object(Path, "home", return_value=home):
                self.assertEqual(monitor.get_codex_log_db(), root_db)

    def test_checkpoint_file_is_separate_for_new_log_location(self):
        new_db = Path.home() / ".codex" / "sqlite" / "logs_2.sqlite"
        old_db = Path.home() / ".codex" / "logs_2.sqlite"

        self.assertNotEqual(
            monitor.get_checkpoint_file(new_db),
            monitor.get_checkpoint_file(old_db),
        )

    def test_extracts_legacy_output_item_done_text(self):
        body = sse({
            "type": "response.output_item.done",
            "item": {
                "content": [
                    {"type": "output_text", "text": "legacy text"},
                ],
            },
        })

        self.assertEqual(monitor.extract_output_from_log(body), "legacy text")

    def test_extracts_streaming_output_delta_text(self):
        body = sse({
            "type": "response.output_text.delta",
            "delta": "流式片段",
        })

        self.assertEqual(monitor.extract_delta_from_log(body), "流式片段")

    def test_extracts_debug_output_item_message_text(self):
        body = (
            'handle_output_item_done: Output item item=Message { '
            'role: "assistant", content: [OutputText { text: "第一行\\n第二行" }], '
            'phase: Some(FinalAnswer) }'
        )

        self.assertEqual(monitor.extract_debug_output_from_log(body), "第一行\n第二行")

    def test_completed_streaming_rows_are_joined_and_sent(self):
        rows = [
            (101, 0, "INFO", "target", sse({"type": "response.output_text.delta", "delta": "阿呆"})),
            (102, 0, "INFO", "target", sse({"type": "response.output_text.delta", "delta": "收到"})),
            (103, 0, "INFO", "target", "app-server event: turn/completed targeted_connections=1"),
        ]

        checkpoint, output = monitor.collect_output_from_rows(rows, last_id=100)

        self.assertEqual(checkpoint, 103)
        self.assertEqual(output, "阿呆收到")

    def test_debug_output_item_with_item_completed_is_sent(self):
        rows = [
            (
                101,
                0,
                "INFO",
                "target",
                'handle_output_item_done: Output item item=Message { '
                'role: "assistant", content: [OutputText { text: "新版输出" }], '
                'phase: Some(FinalAnswer) }',
            ),
            (102, 0, "INFO", "target", "app-server event: item/completed targeted_connections=1"),
        ]

        checkpoint, output = monitor.collect_output_from_rows(rows, last_id=100)

        self.assertEqual(checkpoint, 102)
        self.assertEqual(output, "新版输出")

    def test_incomplete_streaming_rows_keep_checkpoint_before_output(self):
        rows = [
            (101, 0, "INFO", "target", sse({"type": "response.output_text.delta", "delta": "阿呆"})),
            (102, 0, "INFO", "target", sse({"type": "response.output_text.delta", "delta": "收到"})),
        ]

        checkpoint, output = monitor.collect_output_from_rows(rows, last_id=100)

        self.assertEqual(checkpoint, 100)
        self.assertEqual(output, "")

    def test_detects_completion_events(self):
        rows = [
            (101, 0, "INFO", "target", "app-server event: item/completed targeted_connections=1"),
        ]

        self.assertTrue(monitor.rows_have_completion(rows))

    def test_lists_only_new_generated_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_image = root / "old.png"
            new_image = root / "nested" / "new.PNG"
            ignored = root / "note.txt"
            new_image.parent.mkdir()
            old_image.write_bytes(b"old")
            new_image.write_bytes(b"new")
            ignored.write_text("nope")
            os.utime(old_image, (1000, 1000))
            os.utime(new_image, (2000, 2000))

            images = monitor.list_new_generated_images(root, since_mtime=1500)

        self.assertEqual(images, [new_image])

    def test_send_new_generated_images_updates_checkpoint_after_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "images"
            root.mkdir()
            checkpoint = Path(tmp) / "image-checkpoint.txt"
            image = root / "new.png"
            image.write_bytes(b"new")
            os.utime(image, (2000, 2000))
            checkpoint.write_text("1500")
            sent = []

            with patch.object(monitor.send_image_to_feishu, "send_image", lambda path: sent.append(Path(path)) or True):
                monitor.send_new_generated_images(root, checkpoint)

            self.assertEqual(sent, [image])
            self.assertEqual(float(checkpoint.read_text()), 2000.0)


if __name__ == "__main__":
    unittest.main()
