import unittest
from pathlib import Path

import monitor


PROJECT_DIR = Path(__file__).resolve().parent


class SelfContainedTest(unittest.TestCase):
    def test_monitor_checkpoint_lives_in_project_directory(self):
        checkpoint = monitor.LAST_CHECKPOINT_FILE.resolve()

        self.assertTrue(checkpoint.is_relative_to(PROJECT_DIR))

    def test_runtime_code_does_not_read_hermes_env_or_state(self):
        runtime_files = [
            PROJECT_DIR / "feishu_to_codex.py",
            PROJECT_DIR / "send_to_feishu.py",
            PROJECT_DIR / "send_image_to_feishu.py",
            PROJECT_DIR / "monitor.py",
            PROJECT_DIR / "feishu-to-codex-wrapper.sh",
            PROJECT_DIR / "monitor-wrapper.sh",
        ]

        for path in runtime_files:
            self.assertNotIn(".hermes", path.read_text())


if __name__ == "__main__":
    unittest.main()
