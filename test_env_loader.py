import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import env_loader


class EnvLoaderTest(unittest.TestCase):
    def test_loads_project_env_without_overwriting_existing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "FEISHU_APP_ID=cli_from_file",
                        "FEISHU_APP_SECRET='secret from file'",
                        "FEISHU_CHAT_ID=\"oc_from_file\"",
                    ]
                )
            )

            with patch.dict(os.environ, {"FEISHU_APP_ID": "cli_existing"}, clear=True):
                loaded = env_loader.load_env_file(env_path)

                self.assertTrue(loaded)
                self.assertEqual(os.environ["FEISHU_APP_ID"], "cli_existing")
                self.assertEqual(os.environ["FEISHU_APP_SECRET"], "secret from file")
                self.assertEqual(os.environ["FEISHU_CHAT_ID"], "oc_from_file")


if __name__ == "__main__":
    unittest.main()
