from __future__ import annotations

import imaplib
import re
from datetime import date, datetime, time, timedelta
from typing import Iterable

from email_agent.config import MailConfig
from email_agent.mail.parser import parse_email
from email_agent.models import EmailItem


IMAP_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
UID_PATTERN = re.compile(rb"\bUID\s+(\d+)\b", re.IGNORECASE)


def format_imap_date(value: datetime) -> str:
    return f"{value.day:02d}-{IMAP_MONTHS[value.month - 1]}-{value.year}"


def chunked(values: list[bytes], size: int) -> Iterable[list[bytes]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


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
            self._send_client_id(imap)
            status, select_data = imap.select(self.config.mailbox, readonly=True)
            if status != "OK":
                detail = self._format_response(select_data)
                raise RuntimeError(f"IMAP select failed for {self.config.address}: {detail or status}")
            status, data = imap.uid("SEARCH", None, f'(SINCE "{since}" BEFORE "{before}")')
            if status != "OK":
                raise RuntimeError(f"IMAP search failed for {self.config.address}: {status}")

            uids = data[0].split()
            selected = list(reversed(uids))[:limit]
            emails: list[EmailItem] = []

            for uid_group in chunked(list(reversed(selected)), 20):
                uid_set = b",".join(uid_group).decode("ascii", errors="replace")
                status, fetched = imap.uid("FETCH", uid_set, "(UID RFC822)")
                if status != "OK" or not fetched:
                    continue
                for uid, raw_message in self._iter_fetched_messages(fetched):
                    item = parse_email(
                        raw_message,
                        uid=uid,
                        account=self.config.address,
                        provider=self.config.provider,
                    )
                    if self._belongs_to_date(item, target_date, tz):
                        emails.append(item)

            return emails

    @staticmethod
    def _iter_fetched_messages(fetched) -> Iterable[tuple[str, bytes]]:
        fallback_index = 0
        for part in fetched:
            if not (isinstance(part, tuple) and len(part) >= 2 and isinstance(part[1], bytes)):
                continue
            meta = part[0] if isinstance(part[0], bytes) else b""
            match = UID_PATTERN.search(meta)
            uid = match.group(1).decode("ascii", errors="replace") if match else f"unknown-{fallback_index}"
            fallback_index += 1
            yield uid, part[1]

    def _send_client_id(self, imap: imaplib.IMAP4_SSL) -> None:
        if self.config.provider not in {"163", "126", "yeah"}:
            return
        try:
            imap._simple_command("ID", '("name" "email-agent" "version" "0.3" "vendor" "local")')
        except Exception:
            return

    @staticmethod
    def _format_response(data) -> str:
        if not data:
            return ""
        parts: list[str] = []
        for item in data:
            if isinstance(item, bytes):
                parts.append(item.decode("utf-8", errors="replace"))
            else:
                parts.append(str(item))
        return "; ".join(parts)

    @staticmethod
    def _belongs_to_date(item: EmailItem, target_date: date, tz) -> bool:
        if item.sent_at is None:
            return True
        sent_at = item.sent_at
        if sent_at.tzinfo is None:
            sent_at = sent_at.replace(tzinfo=tz)
        return sent_at.astimezone(tz).date() == target_date
