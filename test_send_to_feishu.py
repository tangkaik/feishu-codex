import json
import os
import unittest
from unittest.mock import patch

import send_to_feishu


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class SendToFeishuTest(unittest.TestCase):
    def test_sends_via_app_api_when_webhook_is_missing(self):
        requests = []

        def fake_urlopen(req, timeout=10):
            requests.append(req)
            if req.full_url.endswith("/auth/v3/tenant_access_token/internal"):
                return FakeResponse({"code": 0, "tenant_access_token": "token"})
            return FakeResponse({"code": 0, "msg": "success"})

        env = {
            "FEISHU_APP_ID": "cli_test",
            "FEISHU_APP_SECRET": "secret",
            "FEISHU_CHAT_ID": "oc_test",
        }

        with patch.dict(os.environ, env, clear=True), patch("urllib.request.urlopen", fake_urlopen):
            self.assertTrue(send_to_feishu.send_text_message("hello"))

        self.assertEqual(len(requests), 2)
        self.assertIn("receive_id_type=chat_id", requests[1].full_url)
        payload = json.loads(requests[1].data.decode("utf-8"))
        self.assertEqual(payload["receive_id"], "oc_test")
        self.assertEqual(payload["content"], json.dumps({"text": "hello"}, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
