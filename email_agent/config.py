from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


PLACEHOLDER_VALUES = {
    "your_openai_api_key_here",
    "your_api_key_here",
    "replace_with_your_aliyun_dashscope_key",
    "your_email@example.com",
    "your_mail_imap_authorization_code",
    "your_qq_email@qq.com",
    "your_qq_mail_imap_authorization_code",
    "replace_with_your_qq_mail_imap_authorization_code",
}


IMAP_HOST_BY_DOMAIN = {
    "qq.com": "imap.qq.com",
    "vip.qq.com": "imap.qq.com",
    "163.com": "imap.163.com",
    "126.com": "imap.126.com",
    "yeah.net": "imap.yeah.net",
    "gmail.com": "imap.gmail.com",
    "outlook.com": "outlook.office365.com",
    "hotmail.com": "outlook.office365.com",
    "live.com": "outlook.office365.com",
}


PROVIDER_HOSTS = {
    "qq": "imap.qq.com",
    "163": "imap.163.com",
    "126": "imap.126.com",
    "yeah": "imap.yeah.net",
    "custom": "",
}


def is_placeholder(value: str) -> bool:
    return value.strip() in PLACEHOLDER_VALUES


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_env_files(root: Path | None = None) -> None:
    root = root or Path.cwd()
    load_dotenv(root / ".env")
    load_dotenv(root / ".env.local")


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def guess_imap_host(address: str) -> str:
    domain = address.rsplit("@", 1)[-1].lower()
    return IMAP_HOST_BY_DOMAIN.get(domain, f"imap.{domain}")


def guess_provider(address: str) -> str:
    domain = address.rsplit("@", 1)[-1].lower()
    if domain in {"qq.com", "vip.qq.com"}:
        return "qq"
    if domain == "163.com":
        return "163"
    if domain == "126.com":
        return "126"
    if domain == "yeah.net":
        return "yeah"
    return "custom"


def host_for_provider(provider: str, address: str, custom_host: str = "") -> str:
    provider = (provider or guess_provider(address)).strip().lower()
    if provider == "custom" and custom_host.strip():
        return custom_host.strip()
    return PROVIDER_HOSTS.get(provider) or guess_imap_host(address)


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    model: str = "gpt-4.1-mini"
    base_url: str = "https://api.openai.com/v1"
    max_tokens: int = 1800

    @classmethod
    def from_env(cls) -> "OpenAIConfig":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or is_placeholder(api_key):
            raise RuntimeError("OPENAI_API_KEY is missing. Fill it in .env.local before running AI summaries.")
        return cls(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini",
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            max_tokens=_get_int("OPENAI_MAX_TOKENS", 1800),
        )


@dataclass(frozen=True)
class MailConfig:
    address: str
    auth_code: str
    host: str
    port: int = 993
    mailbox: str = "INBOX"
    provider: str = "imap"
    label: str = ""

    @property
    def display_name(self) -> str:
        return self.label or self.address

    @classmethod
    def from_env_prefix(cls, prefix: str, default_provider: str = "imap") -> "MailConfig":
        address = os.getenv(f"{prefix}_ADDRESS", "").strip()
        auth_code = os.getenv(f"{prefix}_AUTH_CODE", "").strip()
        if not address or is_placeholder(address):
            raise RuntimeError(f"{prefix}_ADDRESS is missing. Fill it in .env.local.")
        if not auth_code or is_placeholder(auth_code):
            raise RuntimeError(f"{prefix}_AUTH_CODE is missing. Fill the IMAP authorization code in .env.local.")
        return cls(
            address=address,
            auth_code=auth_code,
            host=os.getenv(f"{prefix}_IMAP_HOST", "").strip() or guess_imap_host(address),
            port=_get_int(f"{prefix}_IMAP_PORT", 993),
            mailbox=os.getenv(f"{prefix}_MAILBOX", "INBOX").strip() or "INBOX",
            provider=os.getenv(f"{prefix}_PROVIDER", default_provider).strip() or default_provider,
            label=os.getenv(f"{prefix}_LABEL", "").strip(),
        )

    @classmethod
    def qq_from_env(cls) -> "MailConfig":
        address = os.getenv("QQ_EMAIL_ADDRESS", "").strip()
        auth_code = os.getenv("QQ_EMAIL_AUTH_CODE", "").strip()
        if not address or is_placeholder(address):
            raise RuntimeError("QQ_EMAIL_ADDRESS is missing. Fill it in .env.local.")
        if not auth_code or is_placeholder(auth_code):
            raise RuntimeError("QQ_EMAIL_AUTH_CODE is missing. Fill the QQ Mail IMAP authorization code in .env.local.")
        return cls(
            address=address,
            auth_code=auth_code,
            host=os.getenv("QQ_IMAP_HOST", "").strip() or guess_imap_host(address),
            port=_get_int("QQ_IMAP_PORT", 993),
            mailbox=os.getenv("QQ_MAILBOX", "INBOX").strip() or "INBOX",
            provider=os.getenv("QQ_EMAIL_PROVIDER", "qq").strip() or "qq",
            label=os.getenv("QQ_EMAIL_LABEL", "").strip(),
        )

    @classmethod
    def all_from_env(cls) -> list["MailConfig"]:
        accounts: list[MailConfig] = []
        index = 1
        while os.getenv(f"EMAIL_ACCOUNT_{index}_ADDRESS") or os.getenv(f"EMAIL_ACCOUNT_{index}_AUTH_CODE"):
            accounts.append(cls.from_env_prefix(f"EMAIL_ACCOUNT_{index}"))
            index += 1

        if accounts:
            return accounts
        if os.getenv("EMAIL_ACCOUNTS_MANAGED", "").strip() in {"1", "true", "yes"}:
            return []

        return [cls.qq_from_env()]


@dataclass(frozen=True)
class AgentConfig:
    timezone: ZoneInfo
    max_emails: int
    output_dir: Path
    fetch_workers: int

    @classmethod
    def from_env(cls) -> "AgentConfig":
        timezone_name = os.getenv("EMAIL_AGENT_TIMEZONE", "Asia/Shanghai").strip() or "Asia/Shanghai"
        return cls(
            timezone=ZoneInfo(timezone_name),
            max_emails=_get_int("EMAIL_AGENT_MAX_EMAILS", 80),
            output_dir=Path(os.getenv("EMAIL_AGENT_OUTPUT_DIR", "outputs")),
            fetch_workers=_get_int("EMAIL_AGENT_FETCH_WORKERS", 4),
        )
