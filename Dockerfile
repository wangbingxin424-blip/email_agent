FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY email_agent ./email_agent

RUN pip install --no-cache-dir .

EXPOSE 8765

ENTRYPOINT ["email-agent"]
CMD ["summarize", "--date", "today"]
