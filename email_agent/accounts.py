from __future__ import annotations

import os
from pathlib import Path

from email_agent.config import guess_provider, host_for_provider, is_placeholder, load_env_files


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


def has_multi_accounts(values: dict[str, str]) -> bool:
    index = 1
    while f"EMAIL_ACCOUNT_{index}_ADDRESS" in values or f"EMAIL_ACCOUNT_{index}_AUTH_CODE" in values:
        if values.get(f"EMAIL_ACCOUNT_{index}_ADDRESS"):
            return True
        index += 1
    return False


def next_account_index(values: dict[str, str]) -> int:
    index = 1
    while f"EMAIL_ACCOUNT_{index}_ADDRESS" in values or f"EMAIL_ACCOUNT_{index}_AUTH_CODE" in values:
        index += 1
    return index


def configured_addresses(values: dict[str, str]) -> set[str]:
    addresses: set[str] = set()
    index = 1
    while f"EMAIL_ACCOUNT_{index}_ADDRESS" in values or f"EMAIL_ACCOUNT_{index}_AUTH_CODE" in values:
        address = values.get(f"EMAIL_ACCOUNT_{index}_ADDRESS", "").strip().lower()
        if address:
            addresses.add(address)
        index += 1
    qq_address = values.get("QQ_EMAIL_ADDRESS", "").strip().lower()
    if qq_address:
        addresses.add(qq_address)
    return addresses


def _account_env_lines(index: int, account: dict[str, str]) -> list[str]:
    prefix = f"EMAIL_ACCOUNT_{index}"
    lines = [
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
    return lines


def _set_account_environ(index: int, account: dict[str, str]) -> None:
    prefix = f"EMAIL_ACCOUNT_{index}"
    os.environ[f"{prefix}_LABEL"] = account.get("label", "")
    os.environ[f"{prefix}_ADDRESS"] = account["address"]
    os.environ[f"{prefix}_AUTH_CODE"] = account["auth_code"]
    os.environ[f"{prefix}_PROVIDER"] = account.get("provider", "custom")
    os.environ[f"{prefix}_IMAP_HOST"] = account["host"]
    os.environ[f"{prefix}_IMAP_PORT"] = account.get("port", "993")
    os.environ[f"{prefix}_MAILBOX"] = account.get("mailbox", "INBOX")


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

    account = {
        "label": label or address,
        "address": address,
        "auth_code": auth_code,
        "provider": provider,
        "host": host_for_provider(provider, address, custom_host),
        "port": port,
        "mailbox": mailbox,
    }

    appended: list[str] = []
    index = next_account_index(values)
    if not has_multi_accounts(values):
        legacy = _legacy_qq_account(values)
        if legacy:
            appended.extend(_account_env_lines(index, legacy))
            _set_account_environ(index, legacy)
            index += 1

    appended.extend(_account_env_lines(index, account))
    _set_account_environ(index, account)

    existing = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    suffix = "\n".join(appended) + "\n"
    separator = "" if not existing or existing.endswith("\n") else "\n"
    env_path.write_text(existing + separator + suffix, encoding="utf-8")

    return {
        "address": account["address"],
        "label": account["label"],
        "provider": account["provider"],
        "host": account["host"],
        "mailbox": account["mailbox"],
    }
