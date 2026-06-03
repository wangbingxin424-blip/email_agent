import unittest
from email.message import EmailMessage

from email_agent.mail.parser import decode_mime_header, extract_body, parse_email, parse_email_date


class ParserTests(unittest.TestCase):
    def test_decode_mime_header_handles_encoded_subject(self):
        self.assertEqual(decode_mime_header("=?utf-8?b?5rWL6K+V6YKu5Lu2?="), "测试邮件")

    def test_parse_email_extracts_plain_text_body(self):
        message = EmailMessage()
        message["Subject"] = "Hello"
        message["From"] = "alice@example.com"
        message["To"] = "bob@example.com"
        message["Date"] = "Wed, 03 Jun 2026 09:00:00 +0800"
        message.set_content("Line 1\n\nLine 2")

        item = parse_email(message.as_bytes(), uid="42")

        self.assertEqual(item.uid, "42")
        self.assertEqual(item.subject, "Hello")
        self.assertEqual(item.sender, "alice@example.com")
        self.assertIsNotNone(item.sent_at)
        self.assertIsNotNone(item.sent_at.utcoffset())
        self.assertEqual(item.body, "Line 1\nLine 2")

    def test_extract_body_falls_back_to_html(self):
        message = EmailMessage()
        message["Subject"] = "HTML"
        message.add_alternative("<html><body><p>Hello<br>World</p></body></html>", subtype="html")

        self.assertEqual(extract_body(message), "Hello\nWorld")

    def test_parse_email_date_invalid_returns_none(self):
        self.assertIsNone(parse_email_date("not a date"))


if __name__ == "__main__":
    unittest.main()
