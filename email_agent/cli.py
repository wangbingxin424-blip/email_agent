from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

from email_agent.ai import OpenAISummarizer
from email_agent.config import AgentConfig, MailConfig, OpenAIConfig, load_env_files
from email_agent.mail import QQMailClient
from email_agent.models import EmailItem


def parse_target_date(value: str, tz) -> date:
    if value.lower() == "today":
        return datetime.now(tz).date()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be 'today' or YYYY-MM-DD") from exc


def render_email_listing(emails: list[EmailItem], target_date: date) -> str:
    if not emails:
        return f"# {target_date.isoformat()} 邮件列表\n\n没有读取到当天邮件。"

    lines = [f"# {target_date.isoformat()} 邮件列表", "", f"共读取到 {len(emails)} 封邮件。"]
    for index, item in enumerate(emails, start=1):
        sent = item.sent_at.isoformat() if item.sent_at else "未知时间"
        lines.extend(
            [
                "",
                f"## {index}. {item.subject or '无主题'}",
                "",
                f"- 发件人: {item.sender or '未知'}",
                f"- 时间: {sent}",
                f"- UID: {item.uid}",
                "",
                item.compact_body(800) or "无正文",
            ]
        )
    return "\n".join(lines)


def save_markdown(output_dir: Path, target_date: date, content: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"email-summary-{target_date.isoformat()}.md"
    path.write_text(content + "\n", encoding="utf-8")
    return path


def summarize_command(args: argparse.Namespace) -> int:
    load_env_files()
    agent_config = AgentConfig.from_env()
    target_date = parse_target_date(args.date, agent_config.timezone)

    mail_config = MailConfig.qq_from_env()
    mail_client = QQMailClient(mail_config)
    emails = mail_client.fetch_for_date(target_date, agent_config.timezone, limit=args.max_emails or agent_config.max_emails)

    if args.no_ai:
        output = render_email_listing(emails, target_date)
    else:
        openai_config = OpenAIConfig.from_env()
        output = OpenAISummarizer(openai_config).summarize(emails, target_date)

    print(output)
    if not args.no_save:
        path = save_markdown(agent_config.output_dir, target_date, output)
        print(f"\nSaved summary to {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="email-agent", description="Read email and summarize what happened today.")
    subparsers = parser.add_subparsers(dest="command")

    summarize = subparsers.add_parser("summarize", help="Summarize QQ Mail for a date.")
    summarize.add_argument("--date", default="today", help="today or YYYY-MM-DD. Default: today.")
    summarize.add_argument("--max-emails", type=int, default=None, help="Maximum number of emails to read.")
    summarize.add_argument("--no-ai", action="store_true", help="Only list fetched emails without calling AI.")
    summarize.add_argument("--no-save", action="store_true", help="Do not save the Markdown output.")
    summarize.set_defaults(func=summarize_command)

    parser.set_defaults(func=summarize_command, date="today", max_emails=None, no_ai=False, no_save=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("Interrupted.")
        return 130
    except Exception as exc:
        print(f"Error: {exc}")
        return 1
