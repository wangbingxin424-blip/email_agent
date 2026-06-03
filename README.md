# email_agent

本地邮件总结 agent。当前先支持 QQ 邮箱：读取指定日期的邮件内容，然后调用 OpenAI 兼容的 Chat Completions 接口生成中文日报，告诉你当天主要发生了什么。可以使用 OpenAI，也可以使用阿里云 DashScope 兼容模式。

## 功能

- 读取 QQ 邮箱 IMAP 邮件
- 默认总结今天的邮件，也可以指定日期
- 提取重要事项、待办任务、会议日程、风险异常和建议回复
- 输出到终端，同时保存为 Markdown 文件
- 代码结构预留了其他邮箱 provider，后续可加 Gmail、Outlook、163 等

## 准备 QQ 邮箱授权码

QQ 邮箱不能直接用登录密码读取 IMAP。你需要在 QQ 邮箱网页端开启 IMAP/SMTP 服务，并生成授权码。

通常路径是：QQ 邮箱设置 -> 账号 -> POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV 服务 -> 开启 IMAP/SMTP 服务 -> 生成授权码。

## 配置

复制配置模板：

```powershell
Copy-Item .env.example .env.local
```

编辑 `.env.local`，填入：

```env
OPENAI_API_KEY=你的API Key
QQ_EMAIL_ADDRESS=你的QQ邮箱地址
QQ_EMAIL_AUTH_CODE=你的QQ邮箱授权码
```

阿里云 DashScope 推荐配置：

```env
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus
```

OpenAI 官方接口配置：

```env
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```

其他可选项：

```env
EMAIL_AGENT_TIMEZONE=Asia/Shanghai
EMAIL_AGENT_MAX_EMAILS=80
```

## 运行

如果你本机已有 Python 3.10+：

```powershell
python -m pip install -e .
python -m email_agent summarize --date today
```

## 使用 Docker 运行

构建镜像：

```powershell
docker build -t email-agent .
```

使用 `.env.local` 运行今天的邮件总结：

```powershell
docker run --rm --env-file .env.local -v "${PWD}/outputs:/app/outputs" email-agent
```

指定日期：

```powershell
docker run --rm --env-file .env.local -v "${PWD}/outputs:/app/outputs" email-agent summarize --date 2026-06-03
```

只读取邮件、不调用 AI：

```powershell
docker run --rm --env-file .env.local -v "${PWD}/outputs:/app/outputs" email-agent summarize --date today --no-ai
```

启动可视化网站：

```powershell
docker run --rm --env-file .env.local -p 8765:8765 -v "${PWD}/outputs:/app/outputs" email-agent web --host 0.0.0.0 --port 8765
```

然后打开：

```text
http://127.0.0.1:8765
```

如果 `python` 命令不可用，也可以用可用的 Python 解释器运行：

```powershell
<python.exe路径> -m email_agent summarize --date today
```

指定日期：

```powershell
python -m email_agent summarize --date 2026-06-03
```

只读取邮件、不调用 AI：

```powershell
python -m email_agent summarize --date today --no-ai
```

不保存 Markdown 文件：

```powershell
python -m email_agent summarize --date today --no-save
```

## 启动可视化网站

```powershell
python -m email_agent web --port 8765
```

打开：

```text
http://127.0.0.1:8765
```

网页中可以选择日期、生成简报、查看待办任务、风险异常、邮件列表和原始 Markdown。

## 输出结构

AI 简报会包含：

- 今日总览
- 重要事项
- 待办任务
- 会议与日程
- 风险与异常
- 可忽略信息
- 建议回复

默认保存到：

```text
outputs/email-summary-YYYY-MM-DD.md
```

## 安全说明

- `.env.local` 和 `.env` 已加入 `.gitignore`，不要把 API Key 或邮箱授权码提交到 GitHub。
- 程序只读取邮件，不会自动发送、删除、移动邮件。
- 邮件正文会发送到你配置的 OpenAI 兼容接口用于总结，请确认你接受该数据流向。
