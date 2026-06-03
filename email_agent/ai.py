from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date

from email_agent.config import OpenAIConfig
from email_agent.models import EmailItem


SYSTEM_PROMPT = """你是我的每日邮件处理助手。你会根据邮件事实生成准确、简洁的中文简报。
不要编造邮件中不存在的信息。遇到不确定内容，请标注“需要确认”。
不要写任何会暗示你已经发送、删除、移动邮件的内容。"""


def build_user_prompt(emails: list[EmailItem], target_date: date) -> str:
    if not emails:
        return f"{target_date.isoformat()} 没有可总结的邮件。请直接说明当天没有可总结邮件。"

    accounts = sorted({item.account for item in emails if item.account})
    chunks = [
        f"请总结 {target_date.isoformat()} 的邮件。输出结构必须包含：",
        "1. 今日总览：3-5 句话概括今天邮件里发生了什么。",
        "2. 重要事项：列出最重要的邮件事件，说明发件人、主题、核心内容、影响。",
        "3. 待办任务：提取需要我处理、回复、确认、提交、参加的事项，并标注优先级。",
        "4. 会议与日程：提取会议、截止时间、预约、时间地点等信息。",
        "5. 风险与异常：标记紧急、投诉、逾期、财务、合同、账号安全等风险邮件。",
        "6. 可忽略信息：简要列出营销、通知、低优先级邮件类别。",
        "7. 建议回复：如果有需要回复的邮件，给出简短回复建议，但不要自动发送。",
        "",
        f"邮件数量：{len(emails)}",
        f"邮箱账号：{', '.join(accounts) if accounts else '未标注'}",
    ]

    for index, item in enumerate(emails, start=1):
        sent = item.sent_at.isoformat() if item.sent_at else "未知时间"
        chunks.extend(
            [
                "",
                f"--- 邮件 {index} ---",
                f"账号: {item.account or '未知账号'}",
                f"UID: {item.uid}",
                f"发件人: {item.sender or '未知'}",
                f"收件人: {item.recipients or '未知'}",
                f"时间: {sent}",
                f"主题: {item.subject or '无主题'}",
                "正文:",
                item.compact_body(1600),
            ]
        )

    return "\n".join(chunks)


class OpenAISummarizer:
    def __init__(self, config: OpenAIConfig):
        self.config = config

    def summarize(self, emails: list[EmailItem], target_date: date) -> str:
        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(emails, target_date)},
            ],
            "temperature": 0.2,
            "max_tokens": self.config.max_tokens,
        }
        request = urllib.request.Request(
            f"{self.config.base_url}/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"AI API request failed with HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"AI API request failed: {exc}") from exc

        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
        raise RuntimeError("AI API response did not contain summary text.")
