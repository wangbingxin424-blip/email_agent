# email_agent

本地邮件简报 Agent。它会只读读取当天邮件，并调用 OpenAI 兼容的 Chat Completions 接口生成中文简报，帮助你快速知道今天主要发生了什么。

## 功能

- 支持 QQ 邮箱、网易 163/126/yeah.net 邮箱，也支持自定义 IMAP。
- 支持一次读取多个邮箱账号。
- 可以在本地网页的设置面板新增邮箱。
- 多邮箱并发读取，IMAP 批量拉取邮件，减少等待时间。
- 可生成今日总览、重要事项、待办任务、会议日程、风险异常和建议回复。
- 提供命令行和本地可视化网页。
- 输出会保存为 Markdown 文件。

## 配置

复制配置模板：

```powershell
Copy-Item .env.example .env.local
```

最小配置：

```env
OPENAI_API_KEY=你的API Key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus

QQ_EMAIL_ADDRESS=你的QQ邮箱地址
QQ_EMAIL_AUTH_CODE=你的QQ邮箱授权码
```

QQ 邮箱不能直接用登录密码读取 IMAP。需要在 QQ 邮箱网页端开启 IMAP/SMTP 服务，并生成授权码。

## 多邮箱

如果要一次读取多个邮箱，可以直接在网页设置面板添加 QQ 或网易邮箱。也可以手动在 `.env.local` 使用 `EMAIL_ACCOUNT_N_*`：

```env
EMAIL_ACCOUNT_1_LABEL=我的QQ邮箱
EMAIL_ACCOUNT_1_ADDRESS=you@qq.com
EMAIL_ACCOUNT_1_AUTH_CODE=邮箱授权码
EMAIL_ACCOUNT_1_PROVIDER=qq
EMAIL_ACCOUNT_1_IMAP_HOST=imap.qq.com
EMAIL_ACCOUNT_1_IMAP_PORT=993
EMAIL_ACCOUNT_1_MAILBOX=INBOX

EMAIL_ACCOUNT_2_LABEL=客户邮箱
EMAIL_ACCOUNT_2_ADDRESS=client@163.com
EMAIL_ACCOUNT_2_AUTH_CODE=邮箱授权码
EMAIL_ACCOUNT_2_PROVIDER=163
EMAIL_ACCOUNT_2_IMAP_HOST=imap.163.com
EMAIL_ACCOUNT_2_IMAP_PORT=993
EMAIL_ACCOUNT_2_MAILBOX=INBOX
```

只要配置了 `EMAIL_ACCOUNT_1_ADDRESS`，程序就会读取账号列表，而不是单独的 `QQ_EMAIL_*` 配置。

## 本地网页

```powershell
python -m email_agent web --port 8765
```

打开：

```text
http://127.0.0.1:8765
```

网页里可以选择日期、生成简报、查看邮件列表、查看原始 Markdown，也可以在设置面板新增或删除 QQ / 网易邮箱。新增后，下一次生成简报会同时读取所有已添加邮箱。

## 网易邮箱排错

网易邮箱需要在网页端开启 IMAP/SMTP，并使用“客户端授权码”，不能使用邮箱登录密码。

常见错误：

- `LOGIN Login error or password error`：授权码不正确，或该邮箱未开启 IMAP/SMTP。
- `EXAMINE Unsafe Login`：网易拒绝当前第三方客户端登录。先确认 IMAP/SMTP 已开启，并按网易邮箱安全提示处理第三方客户端登录限制。

## 命令行

安装开发包：

```powershell
python -m pip install -e .
```

生成今天的简报：

```powershell
python -m email_agent summarize --date today
```

只读取邮件，不调用 AI：

```powershell
python -m email_agent summarize --date today --no-ai
```

指定日期：

```powershell
python -m email_agent summarize --date 2026-06-03
```

## Docker

构建镜像：

```powershell
docker build -t email-agent .
```

运行网页：

```powershell
docker run --rm --env-file .env.local -p 8765:8765 -v "${PWD}/outputs:/app/outputs" email-agent web --host 0.0.0.0 --port 8765
```

运行命令行简报：

```powershell
docker run --rm --env-file .env.local -v "${PWD}/outputs:/app/outputs" email-agent summarize --date today
```

## 可调参数

```env
EMAIL_AGENT_TIMEZONE=Asia/Shanghai
EMAIL_AGENT_MAX_EMAILS=80
EMAIL_AGENT_FETCH_WORKERS=4
EMAIL_AGENT_OUTPUT_DIR=outputs
OPENAI_MAX_TOKENS=1800
```

## 安全说明

- `.env.local` 和 `.env` 已加入 `.gitignore`，不要把 API Key 或邮箱授权码提交到 GitHub。
- 程序只读取邮件，不会自动发送、删除或移动邮件。
- 邮件正文会发送到你配置的 OpenAI 兼容接口用于总结，请确认你接受该数据流向。
