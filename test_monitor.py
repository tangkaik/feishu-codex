import json
import unittest

import monitor


def sse(payload):
    return "SSE event: " + json.dumps(payload, ensure_ascii=False)


class MonitorOutputExtractionTest(unittest.TestCase):
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

    def test_completed_streaming_rows_are_joined_and_sent(self):
        rows = [
            (101, 0, "INFO", "target", sse({"type": "response.output_text.delta", "delta": "阿呆"})),
            (102, 0, "INFO", "target", sse({"type": "response.output_text.delta", "delta": "收到"})),
            (103, 0, "INFO", "target", "app-server event: turn/completed targeted_connections=1"),
        ]

        checkpoint, output = monitor.collect_output_from_rows(rows, last_id=100)

        self.assertEqual(checkpoint, 103)
        self.assertEqual(output, "阿呆收到")

    def test_incomplete_streaming_rows_keep_checkpoint_before_output(self):
        rows = [
            (101, 0, "INFO", "target", sse({"type": "response.output_text.delta", "delta": "阿呆"})),
            (102, 0, "INFO", "target", sse({"type": "response.output_text.delta", "delta": "收到"})),
        ]

        checkpoint, output = monitor.collect_output_from_rows(rows, last_id=100)

        self.assertEqual(checkpoint, 100)
        self.assertEqual(output, "")


if __name__ == "__main__":
    unittest.main()
