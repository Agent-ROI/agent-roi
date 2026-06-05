# 設定

> English version: [configuration.md](./configuration.md)

Agent-ROI 在零設定下即可運作。若要自訂，請在以下位置建立一個 TOML 檔：

- **Linux/macOS：** `~/.config/agent-roi/config.toml`
- **Windows：** `%APPDATA%\agent-roi\config.toml`

可用環境變數 `AGENT_ROI_CONFIG` 覆寫此路徑。

## 完整範例

```toml
[classifier]
similarity_threshold = 0.18   # 越高 = 主題越多、越細
label_terms = 3               # 每個主題名稱用幾個詞

[collectors]
enabled = ["claude_code", "codex", "copilot", "gemini", "hermes"]

[budget]
daily_usd = 5.0      # 選填 — 省略某行即代表該區間不設預算
weekly_usd = 25.0
monthly_usd = 100.0
```

## 選項

### `[classifier]`

分類器是免模型的：它以 TF-IDF 向量與餘弦相似度將 session 依語意分群。不需要任何
模型、API 金鑰或網路連線。

| 鍵 | 預設 | 說明 |
|----|------|------|
| `similarity_threshold` | `0.18` | 兩個 session 的餘弦相似度達到此值以上，即歸為同一主題。調高得到更多、更細的主題；調低得到更少、更廣的主題。 |
| `label_terms` | `3` | 每個自動歸納的主題名稱包含幾個關鍵詞。 |

### `[collectors]`

| 鍵 | 預設 | 說明 |
|----|------|------|
| `enabled` | `["claude_code", "codex", "copilot", "gemini", "hermes"]` | ingest 時要執行哪些工具採集器。 |

### `[budget]`

各區間的選填花費上限（美元）。設定後，`agent-roi budget` 與儀表板的 Overview
會顯示相對上限的花費，並在超支時標示。每個上限皆為選填——省略某行即代表該區間
不設預算。週以週一為起點，月在每月 1 號重置。

| 鍵 | 預設 | 說明 |
|----|------|------|
| `daily_usd` | _(無)_ | 當天的花費上限。 |
| `weekly_usd` | _(無)_ | 本週（自週一起）的花費上限。 |
| `monthly_usd` | _(無)_ | 當月的花費上限。 |

### 資料庫位置

預設情況下，SQLite 資料庫位於平台的資料目錄（Linux 上為
`~/.local/share/agent-roi/agent_roi.db`）。如有需要，可在設定中以 `db_path` 覆寫。

## 環境變數

| 變數 | 用途 |
|------|------|
| `AGENT_ROI_CONFIG` | 自訂設定檔的路徑。 |
| `WIN_USER` | （WSL）Windows 使用者名稱，用以定位 Windows 側的工具 log。 |
