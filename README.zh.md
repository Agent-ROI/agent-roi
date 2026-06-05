<div align="center">

# Agent-ROI

**追蹤你的 AI coding agent 的花費、用量與 ROI — 跨越每一個工具。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/Agent-ROI/agent-roi/actions/workflows/ci.yml/badge.svg)](https://github.com/Agent-ROI/agent-roi/actions/workflows/ci.yml)

[English](./README.md) · [繁體中文](./README.zh.md)

</div>

---

## Agent-ROI 是什麼？

當你同時使用多個 AI coding 工具 — Claude Code、Codex CLI、GitHub Copilot、Cursor
等 — 你的 token 花費四散各處、難以評估。**Agent-ROI** 把這一切統一起來。

它讀取每個工具本來就會寫下的本地 session log，使用**免模型的語意分類器**從 session
對話中自動歸納**主題／任務**，接著呈現**每個主題消耗了多少 token** — 讓你能衡量
agent 的**投資報酬率（ROI）**，而不只是看原始 token 數。

> Agent-ROI 要回答的核心問題：*「為了這個功能／bug／主題，我的 agent 燒了多少
> token — 值得嗎？」*

## 功能特色

- 🔌 **工具無關的採集器** — 解析 Claude Code、Codex CLI、GitHub Copilot 與 Gemini CLI 的本地 log
  （不需 proxy、不改變使用流程）。
- 🧠 **主題分類** — 免模型的語意分類器依主題將 session 分群，讓你看到**每個主題**的
  成本，而非每個請求。完全離線、不花費 token、不需任何外部服務。
- 💰 **花費與 ROI 追蹤** — token 用量對應到各模型定價，可依**主題、工具或模型**彙總，
  並套用**自訂時間區間**。
- 🔎 **下鑽與可信度** — 點任一主題即可看到它的 token 來自哪些工具與模型；每個數字都有
  **可檢視的定價表**佐證，估算值與精算值以標章清楚區分。
- 🖥️ **CLI** — 終端機直接執行 `report`、主題下鑽、與 `pricing` 指令。
- 🌐 **Web UI** — 現代化的 React 儀表板，含維度／時間控制、分解與下鑽。
- 🗄️ **Local-first** — 所有資料留在你的機器上（SQLite）；完全離線；分類器絕不向外傳送任何資料。

## 架構

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  採集器       │──▶│  分類器       │──▶│   儲存層      │
│ (解析 log)    │   │  (語意分群)   │   │  (SQLite)    │
└──────────────┘   └──────────────┘   └──────┬───────┘
                                             │
                          ┌──────────────────┼──────────────────┐
                          ▼                                      ▼
                   ┌────────────┐                        ┌────────────┐
                   │    CLI     │                        │  REST API  │──▶ Web UI (React)
                   └────────────┘                        └────────────┘
```

詳見 [docs/architecture.zh.md](./docs/architecture.zh.md)。

## 安裝

一行搞定（macOS / Linux / WSL）。需要時會自動安裝 `uv`，接著安裝 `agent-roi` 指令：

```bash
curl -LsSf https://raw.githubusercontent.com/Agent-ROI/agent-roi/main/scripts/install.sh | sh
```

<details>
<summary>其他安裝方式</summary>

```bash
# 使用 pipx
pipx install agent-roi-tracker

# 使用 uv
uv tool install agent-roi-tracker
```

若要在尚未發佈前直接從原始碼安裝，執行安裝腳本前設定 `AGENT_ROI_FROM_GIT=1`。
</details>

## 快速開始

```bash
# 從所有偵測到的工具匯入 log
agent-roi ingest

# 從 session 對話中自動歸納主題（免模型，完全本地）
agent-roi classify

# 成本分解 — 依主題、工具或模型彙總，並套用時間區間
agent-roi report --by tool --since 7d

# 下鑽單一主題：它的 token 來自哪些工具／模型？
agent-roi topic "auth refactor"

# 檢視每個成本數字背後的定價表
agent-roi pricing

# 啟動 web 儀表板（API + React UI），接著開啟 http://127.0.0.1:8000
agent-roi serve
```

> 要開發 Agent-ROI 本身？請見 [CONTRIBUTING.zh.md](./CONTRIBUTING.zh.md) —— 本地開發
> 使用 `uv`，前端跑在獨立的 Vite dev server。

## 設定

Agent-ROI 會於 `~/.config/agent-roi/config.toml` 尋找設定。詳見
[docs/configuration.zh.md](./docs/configuration.zh.md)。

```toml
[classifier]
similarity_threshold = 0.18   # 越高 = 主題越多、越細
label_terms = 3               # 每個主題名稱用幾個詞

[collectors]
enabled = ["claude_code", "codex", "copilot", "gemini"]
```

## 文件

| 文件 | English | 繁體中文 |
|------|---------|----------|
| 架構 | [architecture.md](./docs/architecture.md) | [architecture.zh.md](./docs/architecture.zh.md) |
| 設定 | [configuration.md](./docs/configuration.md) | [configuration.zh.md](./docs/configuration.zh.md) |
| 採集器 | [collectors.md](./docs/collectors.md) | [collectors.zh.md](./docs/collectors.zh.md) |
| 貢獻指南 | [CONTRIBUTING.md](./CONTRIBUTING.md) | [CONTRIBUTING.zh.md](./CONTRIBUTING.zh.md) |

## 貢獻

歡迎貢獻！請先閱讀 [CONTRIBUTING.zh.md](./CONTRIBUTING.zh.md) 與我們的
[行為準則](./CODE_OF_CONDUCT.md)。

## 授權

[MIT](./LICENSE) © Agent-ROI contributors
