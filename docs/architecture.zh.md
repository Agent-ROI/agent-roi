# 架構

> English version: [architecture.md](./architecture.md)

Agent-ROI 是一條 local-first 的處理流程，將你的 AI coding 工具本來就會寫下的 log，
轉換成「依主題分類」的 token 花費與 ROI 視圖。

## 處理流程

```
Collectors ──▶ Storage ──▶ Classifier ──▶ Storage ──▶ 報表 (CLI / API / Web)
 (解析 log)     (SQLite)    (語意分群)      (主題)
```

1. **Collectors（採集器）** 讀取各工具的本地 session log，將每一次請求／回應
   正規化成一個 `Interaction`（工具、session、時間戳、模型、token 數、簡短摘要）。
   同時抽取每輪的具體**活動**（工具呼叫、MCP server 呼叫、檔案編輯），讓成本之後
   能對應到實際做了什麼。採集器是唯讀的 — 絕不修改原始 log。
2. **Storage（儲存層）** 以穩定的 id 為鍵將 interaction upsert 進 SQLite，因此重複
   執行 ingest 是冪等的（不會重複計算）。每筆 interaction 的美金成本會在寫入時依
   定價表計算；活動存在獨立資料表，並以 interaction 為單位整批替換，讓重複 ingest
   仍維持冪等。
3. **Classifier（分類器）** 以整個 *session* 為單位，一次看所有 session，把語意
   相近的 session 歸入同一個**主題**（例如 `auth jwt session`、`ci pipeline test`）。
   使用 TF-IDF 向量與餘弦相似度分群 — 不需模型、不需 API 金鑰、完全離線。
4. **報表** 依主題、工具、模型彙總，並再加上兩個視圖：**權杖組成**（固定開銷／快取／
   實際對話 — 看 token 真正花在哪）與**活動分析**（呼叫了哪些工具與 MCP server、各
   回傳了什麼）。全部透過 CLI、REST API 與 React web 儀表板呈現。

## 元件

| 層級 | 模組 | 職責 |
|------|------|------|
| Collectors | `agent_roi.collectors` | 解析工具 log → `Interaction` |
| Classifier | `agent_roi.classify` | 免模型的語意主題歸納 |
| Storage | `agent_roi.storage` | SQLite 持久化 + 彙總 |
| Core | `agent_roi.core` | 模型、設定、定價、平台、服務 |
| API | `agent_roi.api` | FastAPI REST 層 + 靜態 web 託管 |
| CLI | `agent_roi.cli` | Typer 命令列介面 |
| Web | `web/` | React + Vite 儀表板 |

## 關鍵設計決策

- **Local-first。** 所有資料都存在使用者本機的單一 SQLite 檔。分類完全離線，
  絕不向外傳送任何資料。
- **以 collector 達成工具無關。** 支援新工具只需寫一個 `Collector` 子類 — 不需更動
  系統其他部分。
- **免模型分類器。** 主題直接從 session 文本以 TF-IDF 向量與餘弦相似度分群歸納。
  不需模型、不需 API 金鑰、不需額外依賴，開箱即用。
- **冪等的 ingest。** 穩定的 interaction id 讓你可以隨意重複執行 `ingest`；分類結果
  會在重複 ingest 間被保留。
- **跨平台。** Log 探索會處理 Windows、macOS、Linux 與 WSL（工具可能跑在 Windows
  側）。詳見 [`core/platform.py`](../src/agent_roi/core/platform.py)。

## 資料模型

核心單位是 `Interaction`，它帶有一組 `Activity` 紀錄（該輪的工具／MCP／檔案動作）。
彙總結果會產生 `Rollup`、`TokenComposition` 與 `ActivityReport` 物件。詳見
[`core/models.py`](../src/agent_roi/core/models.py)。

## MCP schema 成本（opt-in）

權杖組成能顯示 MCP／工具的整體開銷，但每個 MCP server 每輪注入的 schema 不在任何
log 裡 — 它是 server 在執行時才產生的。`agent-roi mcp-cost`
（[`mcp/probe.py`](../src/agent_roi/mcp/probe.py)）會啟動每個設定的 stdio server、
完成 MCP 握手、請求其 `tools/list`，再估算這些 schema 的 token 大小。由於會執行外部
程式，它是**僅限 opt-in**，絕不屬於 `ingest` 或 `serve` 的一部分。
