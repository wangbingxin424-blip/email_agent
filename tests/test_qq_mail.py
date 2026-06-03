import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from email_agent.mail.qq import format_imap_date


class QQMailTests(unittest.TestCase):
    def test_format_imap_date_uses_english_months(self):
        dt = datetime(2026, 6, 3, tzinfo=ZoneInfo("Asia/Shanghai"))
        self.assertEqual(format_imap_date(dt), "03-Jun-2026")


if __name__ == "__main__":
    unittest.main()
