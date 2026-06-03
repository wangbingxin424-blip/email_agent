from __future__ import annotations

import os
import re
from pathlib import Path

from email_agent.config import guess_provider, host_for_provider, is_placeholder, load_env_files


ACCOUNT_KEY = re.compile(r"EMAIL_ACCOUNT_(\d+)_(LABEL|ADDRESS|AUTH_CODE|PROVIDER|IMAP_HOST|IMAP_PORT|MAILBOX)$")


def read_env_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def read_accounts(values: dict[str, str]) -> list[dict[str, str]]:
    accounts: list[dict[str, str]] = []
    index = 1
    while f"EMAIL_ACCOUNT_{index}_ADDRESS" in values or f"EMAIL_ACCOUNT_{index}_AUTH_CODE" in values:
        prefix = f"EMAIL_ACCOUNT_{index}"
        address = values.get(f"{prefix}_ADDRESS", "").strip()
        if address:
            accounts.append(
                {
                    "label": values.get(f"{prefix}_LABEL", "") or address,
                    "address": address,
                    "auth_code": values.get(f"{prefix}_AUTH_CODE", ""),
                    "provider": values.get(f"{prefix}_PROVIDER", "") or guess_provider(address),
                    "host": values.get(f"{prefix}_IMAP_HOST", "") or host_for_provider("", address),
                    "port": values.get(f"{prefix}_IMAP_PORT", "993") or "993",
                    "mailbox": values.get(f"{prefix}_MAILBOX", "INBOX") or "INBOX",
                }
            )
        index += 1
    return accounts


def configured_addresses(values: dict[str, str]) -> set[str]:
    addresses = {account["address"].lower() for account in read_accounts(values)}
    if values.get("EMAIL_ACCOUNTS_MANAGED", "").strip() in {"1", "true", "yes"}:
        return addresses
    qq_address = values.get("QQ_EMAIL_ADDRESS", "").strip().lower()
    if qq_address:
        addresses.add(qq_address)
    return addresses


def _legacy_qq_account(values: dict[str, str]) -> dict[str, str] | None:
    address = values.get("QQ_EMAIL_ADDRESS") or os.getenv("QQ_EMAIL_ADDRESS", "")
    auth_code = values.get("QQ_EMAIL_AUTH_CODE") or os.getenv("QQ_EMAIL_AUTH_CODE", "")
    if not address or not auth_code or is_placeholder(address) or is_placeholder(auth_code):
        return None
    return {
        "label": values.get("QQ_EMAIL_LABEL", "") or address,
        "address": address,
        "auth_code": auth_code,
        "provider": values.get("QQ_EMAIL_PROVIDER", "qq") or "qq",
        "host": values.get("QQ_IMAP_HOST", "") or host_for_provider("qq", address),
        "port": values.get("QQ_IMAP_PORT", "993") or "993",
        "mailbox": values.get("QQ_MAILBOX", "INBOX") or "INBOX",
    }


def _account_env_lines(index: int, account: dict[str, str]) -> list[str]:
    prefix = f"EMAIL_ACCOUNT_{index}"
    return [
        "",
        f"# Email account {index}",
        f"{prefix}_LABEL={account.get('label', '')}",
        f"{prefix}_ADDRESS={account['address']}",
        f"{prefix}_AUTH_CODE={account['auth_code']}",
        f"{prefix}_PROVIDER={account.get('provider', 'custom')}",
        f"{prefix}_IMAP_HOST={account['host']}",
        f"{prefix}_IMAP_PORT={account.get('port', '993')}",
        f"{prefix}_MAILBOX={account.get('mailbox', 'INBOX')}",
    ]


def _base_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    cleaned: list[str] = []
    skip_blank_after_account = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"#\s*Email account \d+\s*$", stripped):
            skip_blank_after_account = False
            continue
        if ACCOUNT_KEY.match(stripped.split("=", 1)[0] if "=" in stripped else ""):
            skip_blank_after_account = True
            continue
        if skip_blank_after_account and not stripped:
            skip_blank_after_account = False
            continue
        skip_blank_after_account = False
        cleaned.append(line)
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()
    return cleaned


def _sync_account_environ(accounts: list[dict[str, str]], max_existing: int = 20) -> None:
    for index in range(1, max(max_existing, len(accounts)) + 1):
        prefix = f"EMAIL_ACCOUNT_{index}"
        for suffix in ("LABEL", "ADDRESS", "AUTH_CODE", "PROVIDER", "IMAP_HOST", "IMAP_PORT", "MAILBOX"):
            os.environ.pop(f"{prefix}_{suffix}", None)

    for index, account in enumerate(accounts, start=1):
        prefix = f"EMAIL_ACCOUNT_{index}"
        os.environ[f"{prefix}_LABEL"] = account.get("label", "")
        os.environ[f"{prefix}_ADDRESS"] = account["address"]
        os.environ[f"{prefix}_AUTH_CODE"] = account["auth_code"]
        os.environ[f"{prefix}_PROVIDER"] = account.get("provider", "custom")
        os.environ[f"{prefix}_IMAP_HOST"] = account["host"]
        os.environ[f"{prefix}_IMAP_PORT"] = account.get("port", "993")
        os.environ[f"{prefix}_MAILBOX"] = account.get("mailbox", "INBOX")


def _write_accounts(env_path: Path, accounts: list[dict[str, str]], values: dict[str, str]) -> None:
    base = _base_lines(env_path)
    if not any(line.strip().startswith("EMAIL_ACCOUNTS_MANAGED=") for line in base):
        base.append("EMAIL_ACCOUNTS_MANAGED=1")
    lines = list(base)
    for index, account in enumerate(accounts, start=1):
        lines.extend(_account_env_lines(index, account))
    env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    os.environ["EMAIL_ACCOUNTS_MANAGED"] = "1"
    _sync_account_environ(accounts, max_existing=max(20, len(read_accounts(values)) + 5))


def add_mail_account(payload: dict, root: Path | None = None) -> dict:
    root = root or Path.cwd()
    env_path = root / ".env.local"
    load_env_files(root)
    values = read_env_values(env_path)

    address = str(payload.get("address", "")).strip()
    auth_code = str(payload.get("auth_code", "")).strip()
    label = str(payload.get("label", "")).strip()
    provider = str(payload.get("provider", "")).strip().lower() or guess_provider(address)
    custom_host = str(payload.get("host", "")).strip()
    mailbox = str(payload.get("mailbox", "INBOX")).strip() or "INBOX"
    port = str(payload.get("port", "993")).strip() or "993"

    if not address or "@" not in address:
        raise ValueError("请输入有效的邮箱地址。")
    if not auth_code or is_placeholder(auth_code):
        raise ValueError("请输入邮箱 IMAP 授权码。")
    if provider not in {"qq", "163", "126", "yeah", "custom"}:
        raise ValueError("暂不支持这个邮箱类型。")
    if provider == "custom" and not custom_host:
        raise ValueError("自定义邮箱需要填写 IMAP 服务器。")
    if address.lower() in configured_addresses(values):
        raise ValueError("这个邮箱已经添加过了。")

    accounts = read_accounts(values)
    if not accounts:
        legacy = _legacy_qq_account(values)
        if legacy:
            accounts.append(legacy)

    account = {
        "label": label or address,
        "address": address,
        "auth_code": auth_code,
        "provider": provider,
        "host": host_for_provider(provider, address, custom_host),
        "port": port,
        "mailbox": mailbox,
    }
    accounts.append(account)
    _write_accounts(env_path, accounts, values)
    return public_account(account)


def delete_mail_account(address: str, root: Path | None = None) -> dict:
    root = root or Path.cwd()
    env_path = root / ".env.local"
    load_env_files(root)
    values = read_env_values(env_path)
    target = address.strip().lower()
    if not target:
        raise ValueError("缺少要删除的邮箱地址。")

    accounts = read_accounts(values)
    kept = [account for account in accounts if account["address"].lower() != target]
    if len(kept) == len(accounts):
        raise ValueError("没有找到这个邮箱。")

    _write_accounts(env_path, kept, values)
    return {"deleted": address, "remaining": len(kept)}


def public_account(account: dict[str, str]) -> dict:
    return {
        "address": account["address"],
        "label": account.get("label", account["address"]),
        "provider": account.get("provider", "custom"),
        "host": account["host"],
        "mailbox": account.get("mailbox", "INBOX"),
    }
