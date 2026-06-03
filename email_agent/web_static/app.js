const state = {
  result: null,
  status: null,
  selectedIndex: 0,
  showingMarkdown: false,
};

const els = {
  form: document.querySelector("#summaryForm"),
  dateInput: document.querySelector("#dateInput"),
  todayButton: document.querySelector("#todayButton"),
  noAiInput: document.querySelector("#noAiInput"),
  runButton: document.querySelector("#runButton"),
  mailStatus: document.querySelector("#mailStatus"),
  modelStatus: document.querySelector("#modelStatus"),
  statusDot: document.querySelector(".status-dot"),
  subtitle: document.querySelector("#subtitle"),
  emailCount: document.querySelector("#emailCount"),
  accountCount: document.querySelector("#accountCount"),
  taskCount: document.querySelector("#taskCount"),
  riskCount: document.querySelector("#riskCount"),
  savedPath: document.querySelector("#savedPath"),
  overview: document.querySelector("#overview"),
  tasks: document.querySelector("#tasks"),
  risks: document.querySelector("#risks"),
  emailRows: document.querySelector("#emailRows"),
  selectedEmail: document.querySelector("#selectedEmail"),
  suggestedReply: document.querySelector("#suggestedReply"),
  markdownToggle: document.querySelector("#markdownToggle"),
  settingsButton: document.querySelector("#settingsButton"),
  settingsDrawer: document.querySelector("#settingsDrawer"),
  accountList: document.querySelector("#accountList"),
  accountSummary: document.querySelector("#accountSummary"),
  addAccountForm: document.querySelector("#addAccountForm"),
  addAccountButton: document.querySelector("#addAccountButton"),
  providerInput: document.querySelector("#providerInput"),
  labelInput: document.querySelector("#labelInput"),
  addressInput: document.querySelector("#addressInput"),
  authCodeInput: document.querySelector("#authCodeInput"),
  toast: document.querySelector("#toast"),
};

const providerNames = {
  qq: "QQ邮箱",
  "163": "网易163",
  "126": "网易126",
  yeah: "网易yeah.net",
  custom: "自定义IMAP",
  imap: "IMAP",
};

function todayIso() {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  const local = new Date(now.getTime() - offset * 60000);
  return local.toISOString().slice(0, 10);
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => {
    els.toast.hidden = true;
  }, 4200);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function inlineMarkdown(text) {
  return escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

function markdownToHtml(markdown) {
  const lines = String(markdown || "").split(/\r?\n/);
  const html = [];
  let inList = false;
  let inTable = false;
  let tableRows = [];

  const closeList = () => {
    if (inList) {
      html.push("</ul>");
      inList = false;
    }
  };
  const closeTable = () => {
    if (!inTable) return;
    html.push("<table>");
    tableRows.forEach((row, index) => {
      if (/^\s*\|?\s*:?-{3,}/.test(row)) return;
      const cells = row.replace(/^\||\|$/g, "").split("|").map((cell) => inlineMarkdown(cell.trim()));
      const tag = index === 0 ? "th" : "td";
      html.push("<tr>" + cells.map((cell) => `<${tag}>${cell}</${tag}>`).join("") + "</tr>");
    });
    html.push("</table>");
    tableRows = [];
    inTable = false;
  };

  for (const line of lines) {
    if (/^\s*\|.*\|\s*$/.test(line)) {
      closeList();
      inTable = true;
      tableRows.push(line);
      continue;
    }
    closeTable();
    const trimmed = line.trim();
    if (!trimmed) {
      closeList();
      continue;
    }
    if (/^[-*]\s+/.test(trimmed)) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${inlineMarkdown(trimmed.replace(/^[-*]\s+/, ""))}</li>`);
    } else if (/^#{1,4}\s+/.test(trimmed)) {
      closeList();
      html.push(`<h4>${inlineMarkdown(trimmed.replace(/^#{1,4}\s+/, ""))}</h4>`);
    } else if (/^---+$/.test(trimmed)) {
      closeList();
    } else {
      closeList();
      html.push(`<p>${inlineMarkdown(trimmed.replace(/^>\s*/, ""))}</p>`);
    }
  }
  closeTable();
  closeList();
  return html.join("");
}

function countLines(section, keywords) {
  if (!section) return 0;
  const lines = section.split(/\r?\n/).filter((line) => line.trim());
  const matched = lines.filter((line) => keywords.some((keyword) => line.includes(keyword)));
  return Math.max(matched.length, Math.min(lines.length, section.length > 20 ? 1 : 0));
}

function classifyEmail(email) {
  const text = `${email.subject} ${email.sender} ${email.snippet}`;
  if (/风险|异常|支付|付款|安全|验证码|账单|投诉|逾期|OpenAI|IB/i.test(text)) return ["风险", "risk"];
  if (/审核|邀请|deadline|截止|会议|重要|Policy|Submission|合同|报价/i.test(text)) return ["重要", "important"];
  return ["通知", ""];
}

function renderResult(result) {
  state.result = result;
  state.selectedIndex = 0;
  state.showingMarkdown = false;

  els.emailCount.textContent = result.email_count ?? result.emails?.length ?? els.emailCount.textContent ?? "-";
  els.accountCount.textContent = result.account_count ?? state.status?.mail?.count ?? result.accounts?.length ?? "-";
  els.taskCount.textContent = countLines(result.sections?.tasks, ["|", "-", "任务", "高", "中", "回复", "确认"]) || "-";
  els.riskCount.textContent = /无高风险|暂无|无风险/.test(result.sections?.risks || "")
    ? "0"
    : countLines(result.sections?.risks, ["-", "风险", "异常", "逾期"]) || "0";
  els.savedPath.textContent = result.output_path ? `已保存 ${result.output_path}` : "已生成";
  els.subtitle.textContent = result.email_count == null
    ? `${result.date || "最近"} 的已保存简报。点击按钮可重新读取邮件。`
    : `${result.date} 的邮件简报，共读取 ${result.email_count} 封邮件。`;

  els.overview.className = "rich-text";
  els.tasks.className = "rich-text";
  els.risks.className = "rich-text";
  els.overview.innerHTML = markdownToHtml(result.sections?.overview || result.markdown || "没有可总结邮件。");
  els.tasks.innerHTML = markdownToHtml(result.sections?.tasks || "暂无待办。");
  els.risks.innerHTML = markdownToHtml(result.sections?.risks || "暂无风险。");

  renderRows(result.emails || []);
  renderSelectedEmail();
  renderSuggestedReply();
}

function renderRows(emails) {
  if (!emails.length) {
    els.emailRows.innerHTML = '<tr><td colspan="5" class="empty-row">没有读取到当天邮件。</td></tr>';
    return;
  }
  els.emailRows.innerHTML = emails
    .map((email, index) => {
      const [label, kind] = classifyEmail(email);
      const selected = index === state.selectedIndex ? "selected" : "";
      const time = email.sent_at ? new Date(email.sent_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }) : "-";
      return `<tr class="${selected}" data-index="${index}">
        <td><div class="sender">${escapeHtml(email.account || "未知账号")}</div></td>
        <td><div class="sender">${escapeHtml(email.sender || "未知")}</div></td>
        <td><div class="subject">${escapeHtml(email.subject || "无主题")}</div></td>
        <td>${escapeHtml(time)}</td>
        <td><span class="tag ${kind}">${label}</span></td>
      </tr>`;
    })
    .join("");
}

function renderSelectedEmail() {
  const emails = state.result?.emails || [];
  const email = emails[state.selectedIndex];
  if (!email) {
    els.selectedEmail.className = "selected-email empty";
    els.selectedEmail.textContent = "选择一封邮件查看摘要片段。";
    return;
  }
  els.selectedEmail.className = "selected-email";
  els.selectedEmail.innerHTML = `<h4>${escapeHtml(email.subject || "无主题")}</h4>
    <dl>
      <dt>邮箱账号</dt><dd>${escapeHtml(email.account || "未知账号")}</dd>
      <dt>发件人</dt><dd>${escapeHtml(email.sender || "未知")}</dd>
      <dt>时间</dt><dd>${escapeHtml(email.sent_at ? new Date(email.sent_at).toLocaleString("zh-CN") : "未知")}</dd>
      <dt>内容片段</dt><dd>${escapeHtml(email.snippet || "无正文")}</dd>
    </dl>`;
}

function renderSuggestedReply() {
  const text = state.result?.sections?.reply || "没有识别到需要回复的邮件。";
  els.suggestedReply.className = "rich-text";
  els.suggestedReply.innerHTML = markdownToHtml(text);
}

function renderSettings(status) {
  const accounts = status.mail?.accounts || [];
  els.accountSummary.textContent = accounts.length ? `${accounts.length} 个邮箱` : "未配置";
  els.accountList.innerHTML = accounts.length
    ? accounts.map((account) => `<article>
        <strong>${escapeHtml(account.label || account.address)}</strong>
        <span>${escapeHtml(providerNames[account.provider] || account.provider || "IMAP")} · ${escapeHtml(account.address)}</span>
        <small>${escapeHtml(account.host)} · ${escapeHtml(account.mailbox)}</small>
      </article>`).join("")
    : `<p class="empty">还没有配置邮箱账号。</p>`;
}

async function loadStatus() {
  const response = await fetch("/api/status");
  const status = await response.json();
  state.status = status;
  const accountCount = status.mail?.count || 0;
  els.mailStatus.textContent = status.mail?.configured ? `已连接 ${accountCount} 个邮箱` : "邮箱未配置";
  els.modelStatus.textContent = status.ai?.configured ? "AI 简报已配置" : "AI 简报未配置";
  els.accountCount.textContent = accountCount || "-";
  els.statusDot.classList.toggle("ready", Boolean(status.mail?.configured && status.ai?.configured));
  renderSettings(status);
}

async function loadLatest() {
  const response = await fetch("/api/latest");
  const latest = await response.json();
  if (latest.found) {
    renderResult(latest);
    els.savedPath.textContent = `最近简报 ${latest.output_path}`;
  }
}

async function summarize(event) {
  event.preventDefault();
  els.runButton.disabled = true;
  els.runButton.textContent = "生成中...";
  showToast("正在并发读取所有邮箱并生成简报。");
  try {
    const response = await fetch("/api/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        date: els.dateInput.value || "today",
        no_ai: els.noAiInput.checked,
      }),
    });
    const payload = await response.json();
    if (!response.ok || payload.error) throw new Error(payload.error || "生成失败");
    renderResult(payload);
    showToast("今日简报已生成。");
  } catch (error) {
    showToast(error.message);
  } finally {
    els.runButton.disabled = false;
    els.runButton.textContent = "生成今日简报";
  }
}

async function addAccount(event) {
  event.preventDefault();
  els.addAccountButton.disabled = true;
  els.addAccountButton.textContent = "添加中...";
  try {
    const payload = {
      provider: els.providerInput.value,
      label: els.labelInput.value.trim(),
      address: els.addressInput.value.trim(),
      auth_code: els.authCodeInput.value.trim(),
    };
    const response = await fetch("/api/accounts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || "添加失败");
    state.status = data.status;
    renderSettings(data.status);
    els.mailStatus.textContent = `已连接 ${data.status.mail.count} 个邮箱`;
    els.accountCount.textContent = data.status.mail.count || "-";
    els.statusDot.classList.toggle("ready", Boolean(data.status.mail.configured && data.status.ai.configured));
    els.addAccountForm.reset();
    showToast("邮箱已添加，下一次生成简报会一起读取。");
  } catch (error) {
    showToast(error.message);
  } finally {
    els.addAccountButton.disabled = false;
    els.addAccountButton.textContent = "添加邮箱";
  }
}

function openSettings() {
  els.settingsDrawer.hidden = false;
  els.settingsButton.classList.add("active");
}

function closeSettings() {
  els.settingsDrawer.hidden = true;
  els.settingsButton.classList.remove("active");
}

els.form.addEventListener("submit", summarize);
els.addAccountForm.addEventListener("submit", addAccount);
els.todayButton.addEventListener("click", () => {
  els.dateInput.value = todayIso();
});
els.emailRows.addEventListener("click", (event) => {
  const row = event.target.closest("tr[data-index]");
  if (!row) return;
  state.selectedIndex = Number(row.dataset.index);
  renderRows(state.result?.emails || []);
  renderSelectedEmail();
});
els.markdownToggle.addEventListener("click", () => {
  if (!state.result) return;
  state.showingMarkdown = !state.showingMarkdown;
  if (state.showingMarkdown) {
    els.selectedEmail.className = "selected-email";
    els.selectedEmail.innerHTML = `<pre>${escapeHtml(state.result.markdown)}</pre>`;
    els.markdownToggle.textContent = "邮件详情";
  } else {
    els.markdownToggle.textContent = "原始 Markdown";
    renderSelectedEmail();
  }
});
els.settingsButton.addEventListener("click", openSettings);
els.settingsDrawer.addEventListener("click", (event) => {
  if (event.target.matches("[data-close-settings]")) closeSettings();
});
document.querySelectorAll(".nav-item[data-target]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    document.querySelector(`#${button.dataset.target}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

els.dateInput.value = todayIso();
(async function boot() {
  await loadStatus();
  await loadLatest();
  if (window.location.hash === "#settings" || new URLSearchParams(window.location.search).get("panel") === "settings") {
    openSettings();
  }
})().catch((error) => showToast(error.message));
