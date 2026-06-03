from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


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


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    model: str = "gpt-4.1-mini"
    base_url: str = "https://api.openai.com/v1"

    @classmethod
    def from_env(cls) -> "OpenAIConfig":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or api_key == "your_openai_api_key_here":
            raise RuntimeError("OPENAI_API_KEY is missing. Fill it in .env.local before running AI summaries.")
        return cls(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini",
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        )


@dataclass(frozen=True)
class MailConfig:
    address: str
    auth_code: str
    host: str = "imap.qq.com"
    port: int = 993
    mailbox: str = "INBOX"

    @classmethod
    def qq_from_env(cls) -> "MailConfig":
        address = os.getenv("QQ_EMAIL_ADDRESS", "").strip()
        auth_code = os.getenv("QQ_EMAIL_AUTH_CODE", "").strip()
        if not address or address == "your_qq_email@qq.com":
            raise RuntimeError("QQ_EMAIL_ADDRESS is missing. Fill it in .env.local.")
        if not auth_code or auth_code == "your_qq_mail_imap_authorization_code":
            raise RuntimeError("QQ_EMAIL_AUTH_CODE is missing. Fill the QQ Mail IMAP authorization code in .env.local.")
        return cls(
            address=address,
            auth_code=auth_code,
            host=os.getenv("QQ_IMAP_HOST", "imap.qq.com").strip() or "imap.qq.com",
            port=_get_int("QQ_IMAP_PORT", 993),
            mailbox=os.getenv("QQ_MAILBOX", "INBOX").strip() or "INBOX",
        )


@dataclass(frozen=True)
class AgentConfig:
    timezone: ZoneInfo
    max_emails: int
    output_dir: Path

    @classmethod
    def from_env(cls) -> "AgentConfig":
        timezone_name = os.getenv("EMAIL_AGENT_TIMEZONE", "Asia/Shanghai").strip() or "Asia/Shanghai"
        return cls(
            timezone=ZoneInfo(timezone_name),
            max_emails=_get_int("EMAIL_AGENT_MAX_EMAILS", 80),
            output_dir=Path(os.getenv("EMAIL_AGENT_OUTPUT_DIR", "outputs")),
        )
