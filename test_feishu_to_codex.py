import json
import os
import unittest
from unittest.mock import patch

import feishu_to_codex


def text_message(message_id, create_time, sender_id, text, chat_id=None, msg_type="text"):
    msg = {
        "message_id": message_id,
        "create_time": str(create_time),
        "sender": {"id": sender_id, "sender_type": "user"},
        "msg_type": msg_type,
        "body": {"content": json.dumps({"text": text})},
    }
    if chat_id is not None:
        msg["chat_id"] = chat_id
    return msg


def image_message(message_id, create_time, sender_id, image_key, chat_id=None):
    msg = {
        "message_id": message_id,
        "create_time": str(create_time),
        "sender": {"id": sender_id, "sender_type": "user"},
        "msg_type": "image",
        "body": {"content": json.dumps({"image_key": image_key})},
    }
    if chat_id is not None:
        msg["chat_id"] = chat_id
    return msg


class FeishuMessageSelectionTest(unittest.TestCase):
    def test_selects_only_new_owner_text_from_target_chat(self):
        messages = [
            text_message("old-owner", 100, feishu_to_codex.OWNER_USER_ID, "old", feishu_to_codex.CHAT_ID),
            text_message("bot", 300, "cli_bot", "bot", feishu_to_codex.CHAT_ID),
            text_message("other-chat", 400, feishu_to_codex.OWNER_USER_ID, "wrong chat", "oc_other"),
            text_message("image", 500, feishu_to_codex.OWNER_USER_ID, "image", feishu_to_codex.CHAT_ID, "image"),
            text_message("new-owner", 600, feishu_to_codex.OWNER_USER_ID, "hello", feishu_to_codex.CHAT_ID),
        ]

        selected = feishu_to_codex.select_new_messages(
            messages,
            last_msg_id="old-owner",
            last_msg_time=100,
        )

        self.assertEqual(
            selected,
            [{"id": "new-owner", "time": 600.0, "type": "text", "text": "hello"}],
        )

    def test_all_older_messages_are_skipped_even_when_id_differs(self):
        messages = [
            text_message("older-but-different-id", 90, feishu_to_codex.OWNER_USER_ID, "repeat", feishu_to_codex.CHAT_ID),
        ]

        selected = feishu_to_codex.select_new_messages(
            messages,
            last_msg_id="old-owner",
            last_msg_time=100,
        )

        self.assertEqual(selected, [])

    def test_optional_command_prefix_can_still_be_required(self):
        messages = [
            text_message("plain", 600, feishu_to_codex.OWNER_USER_ID, "plain", feishu_to_codex.CHAT_ID),
            text_message("prefixed", 700, feishu_to_codex.OWNER_USER_ID, "/codex hello", feishu_to_codex.CHAT_ID),
        ]

        with patch.dict(os.environ, {"FEISHU_CODEX_PREFIX": "/codex"}):
            selected = feishu_to_codex.select_new_messages(
                messages,
                last_msg_id="old-owner",
                last_msg_time=100,
            )

        self.assertEqual(
            selected,
            [{"id": "prefixed", "time": 700.0, "type": "text", "text": "hello"}],
        )

    def test_selects_owner_image_from_target_chat(self):
        messages = [
            image_message("image-owner", 600, feishu_to_codex.OWNER_USER_ID, "img_v3_test", feishu_to_codex.CHAT_ID),
        ]

        selected = feishu_to_codex.select_new_messages(
            messages,
            last_msg_id="old-owner",
            last_msg_time=100,
        )

        self.assertEqual(
            selected,
            [{"id": "image-owner", "time": 600.0, "type": "image", "image_key": "img_v3_test"}],
        )

    def test_owner_and_chat_can_be_overridden_by_environment(self):
        messages = [
            text_message("default-owner", 600, feishu_to_codex.OWNER_USER_ID, "wrong owner", "oc_target"),
            text_message("default-chat", 700, "ou_target", "wrong chat", feishu_to_codex.CHAT_ID),
            text_message("target", 800, "ou_target", "hello", "oc_target"),
        ]

        env = {
            "FEISHU_OWNER_USER_ID": "ou_target",
            "FEISHU_CHAT_ID": "oc_target",
        }
        with patch.dict(os.environ, env):
            selected = feishu_to_codex.select_new_messages(
                messages,
                last_msg_id="old-owner",
                last_msg_time=100,
            )

        self.assertEqual(
            selected,
            [{"id": "target", "time": 800.0, "type": "text", "text": "hello"}],
        )


if __name__ == "__main__":
    unittest.main()
