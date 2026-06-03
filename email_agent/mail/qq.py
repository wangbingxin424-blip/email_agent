from __future__ import annotations

import imaplib
from datetime import date, datetime, time, timedelta

from email_agent.config import MailConfig
from email_agent.mail.parser import parse_email
from email_agent.models import EmailItem


IMAP_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def format_imap_date(value: datetime) -> str:
    return f"{value.day:02d}-{IMAP_MONTHS[value.month - 1]}-{value.year}"


class QQMailClient:
    def __init__(self, config: MailConfig):
        self.config = config

    def fetch_for_date(self, target_date: date, tz, limit: int = 80) -> list[EmailItem]:
        start = datetime.combine(target_date, time.min, tzinfo=tz)
        end = start + timedelta(days=1)
        since = format_imap_date(start)
        before = format_imap_date(end)

        with imaplib.IMAP4_SSL(self.config.host, self.config.port) as imap:
            imap.login(self.config.address, self.config.auth_code)
            imap.select(self.config.mailbox, readonly=True)
            status, data = imap.uid("SEARCH", None, f'(SINCE "{since}" BEFORE "{before}")')
            if status != "OK":
                raise RuntimeError(f"IMAP search failed: {status}")

            uids = data[0].split()
            selected = list(reversed(uids))[:limit]
            emails: list[EmailItem] = []

            for raw_uid in reversed(selected):
                uid = raw_uid.decode("ascii", errors="replace")
                status, fetched = imap.uid("FETCH", raw_uid, "(RFC822 INTERNALDATE)")
                if status != "OK" or not fetched:
                    continue
                raw_message = self._extract_rfc822(fetched)
                if not raw_message:
                    continue
                item = parse_email(raw_message, uid=uid)
                if self._belongs_to_date(item, target_date, tz):
                    emails.append(item)

            return emails

    @staticmethod
    def _extract_rfc822(fetched) -> bytes | None:
        for part in fetched:
            if isinstance(part, tuple) and len(part) >= 2 and isinstance(part[1], bytes):
                return part[1]
        return None

    @staticmethod
    def _belongs_to_date(item: EmailItem, target_date: date, tz) -> bool:
        if item.sent_at is None:
            return True
        sent_at = item.sent_at
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=tz)
        return sent_at.astimezone(tz).date() == target_date
