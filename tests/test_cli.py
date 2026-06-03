import tempfile
import unittest
from datetime import date
from pathlib import Path

from email_agent.cli import save_markdown


class CliTests(unittest.TestCase):
    def test_save_markdown_uses_kind_in_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = save_markdown(Path(tmp), date(2026, 6, 3), "hello", kind="listing")
            self.assertEqual(path.name, "email-listing-2026-06-03.md")
            self.assertEqual(path.read_text(encoding="utf-8").strip(), "hello")


if __name__ == "__main__":
    unittest.main()
