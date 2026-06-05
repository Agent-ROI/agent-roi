# Security Policy

[繁體中文](#中文)

Agent-ROI is **local-first**: it reads logs that AI coding tools already write
on your machine, stores everything in a single local SQLite file, and never
sends your data anywhere. There is no server component and no telemetry. That
design removes a whole class of risks — but the project still parses untrusted
log files and ships a local web server, so we take security reports seriously.

## Supported versions

Only the latest released version on PyPI receives security fixes. Please
upgrade (`agent-roi update` or `pipx upgrade agent-roi-tracker`) before
reporting.

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Use GitHub's private vulnerability reporting:

1. Go to the repository's **Security** tab → **Report a vulnerability**, or
2. email **asce55123@gmail.com** with the details.

Include, where possible:

- the version (`agent-roi --version`) and OS,
- steps to reproduce or a proof of concept,
- the impact you foresee (e.g. arbitrary file read, code execution).

We aim to acknowledge a report within **72 hours** and to ship a fix or a
mitigation plan within **30 days**, coordinating a disclosure date with you.

## Scope

Things especially in scope:

- log parsers (`collectors/`) crashing or executing code on a crafted log file,
- the local API/web server (`agent-roi serve`) exposing data beyond `127.0.0.1`
  or accepting unexpected cross-origin requests,
- any path that would cause data to leave the machine.

Out of scope: the security of the upstream AI tools whose logs we read, and
issues that require an already-compromised local account.

---

<a name="中文"></a>

# 安全政策

Agent-ROI 採 **local-first** 設計：只讀取 AI coding 工具本來就寫在你機器上的
log，全部存進單一本地 SQLite 檔，**資料永不外傳**，沒有伺服器端、沒有任何
遙測。這個設計消除了一整類風險——但專案仍會解析不受信任的 log 檔、並啟動一個
本地 web server，因此我們仍嚴肅看待安全回報。

## 支援版本

只有 PyPI 上的最新發行版會收到安全修補。回報前請先升級
（`agent-roi update` 或 `pipx upgrade agent-roi-tracker`）。

## 回報漏洞

**請勿為安全問題開公開 issue。**

請使用 GitHub 的私密漏洞回報：

1. 到 repo 的 **Security** 分頁 →「Report a vulnerability」，或
2. 寄信到 **asce55123@gmail.com**。

盡量附上：

- 版本（`agent-roi --version`）與作業系統，
- 重現步驟或 PoC，
- 你預期的影響（如任意檔案讀取、程式碼執行）。

我們會在 **72 小時內** 回覆確認，並在 **30 天內** 提供修補或緩解方案，並與你
協調揭露時程。
