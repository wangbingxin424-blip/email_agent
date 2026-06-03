from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone

from email_agent.config import MailConfig
from email_agent.mail import QQMailClient
from email_agent.models import EmailItem


def fetch_accounts_for_date(
    accounts: list[MailConfig],
    target_date: date,
    tz,
    per_account_limit: int,
    workers: int = 4,
) -> tuple[list[EmailItem], list[dict]]:
    if not accounts:
        return [], []

    max_workers = max(1, min(workers, len(accounts)))
    emails: list[EmailItem] = []
    account_results: list[dict] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(QQMailClient(account).fetch_for_date, target_date, tz, per_account_limit): account
            for account in accounts
        }
        for future in as_completed(futures):
            account = futures[future]
            try:
                account_emails = future.result()
            except Exception as exc:
                account_results.append(
                    {
                        "address": account.address,
                        "label": account.display_name,
                        "host": account.host,
                        "mailbox": account.mailbox,
                        "provider": account.provider,
                        "configured": True,
                        "ok": False,
                        "count": 0,
                        "error": str(exc),
                    }
                )
                continue

            emails.extend(account_emails)
            account_results.append(
                {
                    "address": account.address,
                    "label": account.display_name,
                    "host": account.host,
                    "mailbox": account.mailbox,
                    "provider": account.provider,
                    "configured": True,
                    "ok": True,
                    "count": len(account_emails),
                    "error": None,
                }
            )

    def sort_key(item: EmailItem) -> datetime:
        if item.sent_at is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if item.sent_at.tzinfo is None:
            return item.sent_at.replace(tzinfo=timezone.utc)
        return item.sent_at.astimezone(timezone.utc)

    emails.sort(key=sort_key)
    account_results.sort(key=lambda item: item["address"])
    return emails, account_results
