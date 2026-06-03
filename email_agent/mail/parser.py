from __future__ import annotations

import re
from datetime import datetime
from email import policy
from email.header import decode_header, make_header
from email.message import EmailMessage as StdEmailMessage
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from html import unescape

from email_agent.models import EmailItem


def decode_mime_header(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value))).strip()
    except Exception:
        return value.strip()


def parse_email_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</p\s*>", "\n", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = unescape(text)
    return normalize_text(text)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def _payload_to_text(part: StdEmailMessage) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        raw = part.get_payload()
        return raw if isinstance(raw, str) else ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def extract_body(message: StdEmailMessage) -> str:
    plain_parts: list[str] = []
    html_parts: list[str] = []

    for part in message.walk():
        if part.is_multipart():
            continue
        disposition = (part.get_content_disposition() or "").lower()
        if disposition == "attachment":
            continue
        content_type = part.get_content_type().lower()
        text = _payload_to_text(part)
        if content_type == "text/plain":
            plain_parts.append(normalize_text(text))
        elif content_type == "text/html":
            html_parts.append(html_to_text(text))

    if plain_parts:
        return normalize_text("\n\n".join(plain_parts))
    if html_parts:
        return normalize_text("\n\n".join(html_parts))
    return ""


def parse_email(raw: bytes, uid: str, account: str = "", provider: str = "") -> EmailItem:
    message = BytesParser(policy=policy.default).parsebytes(raw)
    return EmailItem(
        uid=uid,
        subject=decode_mime_header(message.get("Subject")),
        sender=decode_mime_header(message.get("From")),
        recipients=decode_mime_header(message.get("To")),
        sent_at=parse_email_date(message.get("Date")),
        body=extract_body(message),
        account=account,
        provider=provider,
    )
