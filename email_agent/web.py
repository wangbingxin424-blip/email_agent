from __future__ import annotations

import json
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from email_agent.accounts import add_mail_account, delete_mail_account
from email_agent.ai import OpenAISummarizer
from email_agent.cli import parse_target_date, render_email_listing, save_markdown
from email_agent.config import AgentConfig, MailConfig, OpenAIConfig, load_env_files
from email_agent.fetcher import fetch_accounts_for_date
from email_agent.models import EmailItem


WEB_DIR = Path(__file__).resolve().parent / "web_static"


def email_to_dict(item: EmailItem) -> dict:
    return {
        "uid": item.uid,
        "account": item.account,
        "provider": item.provider,
        "subject": item.subject,
        "sender": item.sender,
        "recipients": item.recipients,
        "sent_at": item.sent_at.isoformat() if item.sent_at else None,
        "snippet": item.compact_body(360),
    }


def extract_section(markdown: str, title: str) -> str:
    pattern = re.compile(rf"(?ms)^#+\s*\d*\.?\s*{re.escape(title)}\s*(.*?)(?=^#+\s*\d*\.?\s*|\Z)")
    match = pattern.search(markdown)
    if match:
        return match.group(1).strip()
    numbered = re.compile(rf"(?ms)^\s*(?:\*\*)?\d+\.\s*{re.escape(title)}(?:\*\*)?.*?(?:\n|$)(.*?)(?=^\s*(?:\*\*)?\d+\.\s*|\Z)")
    match = numbered.search(markdown)
    return match.group(1).strip() if match else ""


def section_payload(markdown: str) -> dict:
    return {
        "overview": extract_section(markdown, "今日总览"),
        "tasks": extract_section(markdown, "待办任务"),
        "risks": extract_section(markdown, "风险与异常"),
        "important": extract_section(markdown, "重要事项"),
        "schedule": extract_section(markdown, "会议与日程"),
        "reply": extract_section(markdown, "建议回复"),
    }


def summarize_for_date(date_value: str, no_ai: bool = False) -> dict:
    load_env_files()
    agent_config = AgentConfig.from_env()
    target_date = parse_target_date(date_value, agent_config.timezone)
    accounts = MailConfig.all_from_env()
    emails, account_results = fetch_accounts_for_date(
        accounts,
        target_date,
        agent_config.timezone,
        per_account_limit=agent_config.max_emails,
        workers=agent_config.fetch_workers,
    )

    if no_ai:
        markdown = render_email_listing(emails, target_date)
    else:
        markdown = OpenAISummarizer(OpenAIConfig.from_env()).summarize(emails, target_date)

    output_path = save_markdown(agent_config.output_dir, target_date, markdown, kind="listing" if no_ai else "summary")
    result = {
        "date": target_date.isoformat(),
        "email_count": len(emails),
        "account_count": len(accounts),
        "accounts": account_results,
        "markdown": markdown,
        "sections": section_payload(markdown),
        "emails": [email_to_dict(item) for item in emails],
        "output_path": str(output_path),
    }
    output_path.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def latest_summary() -> dict:
    load_env_files()
    agent_config = AgentConfig.from_env()
    files = sorted(agent_config.output_dir.glob("email-summary-*.md"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not files:
        return {"found": False}

    path = files[0]
    sidecar_path = path.with_suffix(".json")
    if sidecar_path.exists():
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
        payload["found"] = True
        return payload

    markdown = path.read_text(encoding="utf-8")
    date_match = re.search(r"email-summary-(\d{4}-\d{2}-\d{2})\.md$", path.name)
    count_match = re.search(r"邮件数量[:：]\s*(\d+)", markdown)
    return {
        "found": True,
        "date": date_match.group(1) if date_match else None,
        "email_count": int(count_match.group(1)) if count_match else None,
        "account_count": None,
        "accounts": [],
        "markdown": markdown,
        "sections": section_payload(markdown),
        "emails": [],
        "output_path": str(path),
    }


def config_status() -> dict:
    load_env_files()
    result = {
        "mail": {"configured": False, "count": 0, "accounts": []},
        "ai": {"configured": False, "base_url": None},
        "agent": {"max_emails": None, "fetch_workers": None, "timezone": None},
    }
    try:
        accounts = MailConfig.all_from_env()
        result["mail"] = {
            "configured": bool(accounts),
            "count": len(accounts),
            "accounts": [
                {
                    "address": account.address,
                    "label": account.display_name,
                    "host": account.host,
                    "mailbox": account.mailbox,
                    "provider": account.provider,
                }
                for account in accounts
            ],
        }
    except Exception as exc:
        result["mail"]["error"] = str(exc)
    try:
        ai = OpenAIConfig.from_env()
        result["ai"] = {"configured": True, "base_url": ai.base_url}
    except Exception as exc:
        result["ai"]["error"] = str(exc)
    try:
        agent = AgentConfig.from_env()
        result["agent"] = {
            "max_emails": agent.max_emails,
            "fetch_workers": agent.fetch_workers,
            "timezone": str(agent.timezone),
        }
    except Exception as exc:
        result["agent"]["error"] = str(exc)
    return result


class EmailAgentHandler(BaseHTTPRequestHandler):
    server_version = "EmailAgent/0.3"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self.write_json(config_status())
            return
        if parsed.path == "/api/latest":
            self.write_json(latest_summary())
            return
        if parsed.path in {"/", "/index.html"}:
            self.write_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self.write_file(WEB_DIR / "app.js", "text/javascript; charset=utf-8")
            return
        if parsed.path == "/styles.css":
            self.write_file(WEB_DIR / "styles.css", "text/css; charset=utf-8")
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/accounts":
            self.add_account()
            return
        if parsed.path == "/api/accounts/delete":
            self.delete_account()
            return
        if parsed.path != "/api/summarize":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            result = summarize_for_date(str(payload.get("date", "today")), bool(payload.get("no_ai", False)))
            self.write_json(result)
        except Exception as exc:
            self.write_json({"error": str(exc)}, status=500)

    def add_account(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            account = add_mail_account(payload)
            self.write_json({"ok": True, "account": account, "status": config_status()})
        except Exception as exc:
            self.write_json({"error": str(exc)}, status=400)

    def delete_account(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            result = delete_mail_account(str(payload.get("address", "")))
            self.write_json({"ok": True, "result": result, "status": config_status()})
        except Exception as exc:
            self.write_json({"error": str(exc)}, status=400)

    def write_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def write_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        print(f"[web] {self.address_string()} - {format % args}")


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), EmailAgentHandler)
    print(f"Email Agent web app running at http://{host}:{port}")
    server.serve_forever()
