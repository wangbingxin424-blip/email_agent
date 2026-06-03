from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EmailItem:
    uid: str
    subject: str
    sender: str
    recipients: str
    sent_at: datetime | None
    body: str

    def compact_body(self, max_chars: int = 4000) -> str:
        text = " ".join(self.body.split())
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rstrip() + "..."
