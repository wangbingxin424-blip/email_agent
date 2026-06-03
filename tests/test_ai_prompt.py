import unittest
from datetime import date, datetime, timezone

from email_agent.ai import build_user_prompt
from email_agent.models import EmailItem


class AIPromptTests(unittest.TestCase):
    def test_build_user_prompt_contains_summary_sections(self):
        prompt = build_user_prompt(
            [
                EmailItem(
                    uid="1",
                    subject="项目更新",
                    sender="alice@example.com",
                    recipients="me@example.com",
                    sent_at=datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc),
                    body="今天完成了第一版方案，需要明天确认预算。",
                    account="me@example.com",
                )
            ],
            date(2026, 6, 3),
        )

        self.assertIn("今日总览", prompt)
        self.assertIn("待办任务", prompt)
        self.assertIn("项目更新", prompt)
        self.assertIn("需要明天确认预算", prompt)
        self.assertIn("me@example.com", prompt)


if __name__ == "__main__":
    unittest.main()
