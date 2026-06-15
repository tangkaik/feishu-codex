import unittest
from pathlib import Path

import codex_input


class CodexInputTest(unittest.TestCase):
    def test_paste_delay_grows_for_long_text(self):
        self.assertLess(
            codex_input.calculate_paste_delay("short"),
            codex_input.calculate_paste_delay("x" * 5000),
        )

    def test_paste_delay_is_capped(self):
        self.assertEqual(codex_input.calculate_paste_delay("x" * 100000), 3.0)

    def test_focus_applescript_returns_input_coordinates_without_clicking(self):
        script = codex_input.build_focus_applescript()

        self.assertIn('process "Codex"', script)
        self.assertIn("frontmost", script)
        self.assertIn("count windows", script)
        self.assertIn('error "Codex window not available"', script)
        self.assertIn("as integer", script)
        self.assertNotIn("key code 53", script)
        self.assertNotIn("click at", script)
        self.assertIn('return (inputX as text) & "," & (inputY as text)', script)

    def test_submit_applescript_pastes_and_submits_after_external_focus(self):
        script = codex_input.build_submit_applescript(1.2)

        self.assertIn('keystroke "v" using command down', script)
        self.assertIn("delay 1.2", script)
        self.assertIn("key code 36", script)

    def test_image_applescript_copies_file_and_waits_before_submit(self):
        script = codex_input.build_image_clipboard_applescript("/tmp/example.png")
        submit_script = codex_input.build_submit_applescript(5.0)

        self.assertIn('POSIX file "/tmp/example.png"', script)
        self.assertIn('tell application "Finder"', script)
        self.assertIn('keystroke "v" using command down', submit_script)
        self.assertIn("delay 5.0", submit_script)
        self.assertIn("key code 36", submit_script)

    def test_dismiss_edit_applescript_returns_cancel_button_area(self):
        script = codex_input.build_dismiss_edit_applescript()

        self.assertIn("cancelX", script)
        self.assertIn("cancelY", script)
        self.assertIn('return (cancelX as text) & "," & (cancelY as text)', script)
        self.assertNotIn("key code 53", script)

    def test_click_helper_uses_applescript_screen_coordinates_directly(self):
        source = Path("click_helper.c").read_text()

        self.assertNotIn("CGDisplayBounds", source)
        self.assertIn("CGPointMake(x, y)", source)


if __name__ == "__main__":
    unittest.main()
