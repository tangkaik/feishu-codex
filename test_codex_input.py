import unittest

import codex_input


class CodexInputTest(unittest.TestCase):
    def test_paste_delay_grows_for_long_text(self):
        self.assertLess(
            codex_input.calculate_paste_delay("short"),
            codex_input.calculate_paste_delay("x" * 5000),
        )

    def test_paste_delay_is_capped(self):
        self.assertEqual(codex_input.calculate_paste_delay("x" * 100000), 3.0)

    def test_applescript_clicks_bottom_input_without_escape(self):
        script = codex_input.build_applescript(1.2)

        self.assertIn('process "Codex"', script)
        self.assertIn("frontmost", script)
        self.assertIn("count windows", script)
        self.assertIn('error "Codex window not available"', script)
        self.assertIn("as integer", script)
        self.assertNotIn("key code 53", script)
        self.assertIn("click at {inputX, inputY}", script)
        self.assertIn("delay 1.2", script)

    def test_image_applescript_copies_file_and_waits_before_submit(self):
        script = codex_input.build_image_applescript("/tmp/example.png", 5.0)

        self.assertIn('POSIX file "/tmp/example.png"', script)
        self.assertIn('tell application "Finder"', script)
        self.assertIn("as integer", script)
        self.assertNotIn("key code 53", script)
        self.assertIn("click at {inputX, inputY}", script)
        self.assertIn('keystroke "v" using command down', script)
        self.assertIn("delay 5.0", script)
        self.assertIn("key code 36", script)


if __name__ == "__main__":
    unittest.main()
