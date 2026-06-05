# 架構

> English version: [architecture.md](./architecture.md)

Agent-ROI 是一條 local-first 的處理流程，將你的 AI coding 工具本來就會寫下的 log，
轉換成「依主題分類」的 token 花費與 ROI 視圖。

## 處理流程

```
Collectors ──▶ Storage ──▶ Classifier ──▶ Storage ──▶ 報表 (CLI / API / Web)
 (解析 log)     (SQLite)    (小模型)        (主題)
```

1. **Collectors（採集器）** 讀取各工具的本地 session log，將每一次請求／回應
   正規化成一個 `Interaction`（工具、session、時間戳、模型、token 數、簡短摘要）。
   採集器是唯讀的 — 絕不修改原始 log。
2. **Storage（儲存層）** 以穩定的 id 為鍵將 interaction upsert 進 SQLite，因此重複
   執行 ingest 是冪等的（不會重複計算）。每筆 interaction 的美金成本會在寫入時依
   定價表計算。
3. **Classifier（分類器）** 讀取每筆 interaction 的簡短 `summary`，指派一個精簡的
   **主題**（例如 `auth refactor`、`flaky ci test`）。這正是讓成本能「依主題」而非
   「依請求」彙總的關鍵 — 也是衡量 ROI 的核心。
4. **報表** 依主題彙總，並透過 CLI、REST API 與 React web 儀表板呈現。

## 元件

| 層級 | 模組 | 職責 |
|------|------|------|
| Collectors | `agent_roi.collectors` | 解析工具 log → `Interaction` |
| Classifier | `agent_roi.classify` | 可插拔的小模型主題標註 |
| Storage | `agent_roi.storage` | SQLite 持久化 + 彙總 |
| Core | `agent_roi.core` | 模型、設定、定價、平台、服務 |
| API | `agent_roi.api` | FastAPI REST 層 + 靜態 web 託管 |
| CLI | `agent_roi.cli` | Typer 命令列介面 |
| Web | `web/` | React + Vite 儀表板 |

## 關鍵設計決策

- **Local-first。** 所有資料都存在使用者本機的單一 SQLite 檔。雲端分類是選用的，
  而且只會送出簡短摘要，絕不送出完整的 prompt 內容。
- **以 collector 達成工具無關。** 支援新工具只需寫一個 `Collector` 子類 — 不需更動
  系統其他部分。
- **可插拔分類器。** 小模型由設定決定：本地 Ollama（預設，完全離線）或雲端
  Anthropic Haiku。
- **冪等的 ingest。** 穩定的 interaction id 讓你可以隨意重複執行 `ingest`；分類結果
  會在重複 ingest 間被保留。
- **跨平台。** Log 探索會處理 Windows、macOS、Linux 與 WSL（工具可能跑在 Windows
  側）。詳見 [`core/platform.py`](../src/agent_roi/core/platform.py)。

## 資料模型

核心單位是 `Interaction`，彙總結果會產生 `TopicRollup` 物件。詳見
[`core/models.py`](../src/agent_roi/core/models.py)。
