import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import send_image_to_feishu


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class SendImageToFeishuTest(unittest.TestCase):
    def test_uploads_image_then_sends_image_message(self):
        calls = []

        def fake_run(command, capture_output, text, timeout):
            calls.append(("curl", command))

            class Result:
                returncode = 0
                stdout = json.dumps({"code": 0, "data": {"image_key": "img_test"}})
                stderr = ""

            return Result()

        def fake_urlopen(req, timeout=10):
            calls.append(("urlopen", req.full_url, getattr(req, "data", b"")))
            if req.full_url.endswith("/auth/v3/tenant_access_token/internal"):
                return FakeResponse({"code": 0, "tenant_access_token": "token"})
            return FakeResponse({"code": 0, "msg": "success"})

        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "image.png"
            image_path.write_bytes(b"png")
            env = {
                "FEISHU_APP_ID": "cli_test",
                "FEISHU_APP_SECRET": "secret",
                "FEISHU_CHAT_ID": "oc_test",
            }
            with patch.dict(os.environ, env, clear=True), patch("subprocess.run", fake_run), patch("urllib.request.urlopen", fake_urlopen):
                self.assertTrue(send_image_to_feishu.send_image(image_path))

        self.assertEqual(calls[0][0], "urlopen")
        self.assertEqual(calls[1][0], "curl")
        self.assertEqual(calls[2][0], "urlopen")
        payload = json.loads(calls[2][2].decode("utf-8"))
        self.assertEqual(payload["receive_id"], "oc_test")
        self.assertEqual(payload["msg_type"], "image")
        self.assertEqual(payload["content"], json.dumps({"image_key": "img_test"}, ensure_ascii=False))

    def test_load_env_file_uses_project_env_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("FEISHU_CHAT_ID=oc_project\n")

            with patch.dict(os.environ, {}, clear=True), patch.object(send_image_to_feishu, "PROJECT_ENV_FILE", env_path):
                send_image_to_feishu.load_env_file()

                self.assertEqual(os.environ["FEISHU_CHAT_ID"], "oc_project")


if __name__ == "__main__":
    unittest.main()
