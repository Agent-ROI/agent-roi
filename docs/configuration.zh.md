# 設定

> English version: [configuration.md](./configuration.md)

Agent-ROI 在零設定下即可運作。若要自訂，請在以下位置建立一個 TOML 檔：

- **Linux/macOS：** `~/.config/agent-roi/config.toml`
- **Windows：** `%APPDATA%\agent-roi\config.toml`

可用環境變數 `AGENT_ROI_CONFIG` 覆寫此路徑。

## 完整範例

```toml
[classifier]
provider = "ollama"     # "ollama"（本地） | "anthropic"（雲端 Haiku）
model = "llama3.2"
batch_size = 20

[collectors]
enabled = ["claude_code", "codex", "copilot"]
```

## 選項

### `[classifier]`

| 鍵 | 預設 | 說明 |
|----|------|------|
| `provider` | `"ollama"` | `ollama` 跑本地模型（離線、隱私）。`anthropic` 透過 API 使用 Claude Haiku。 |
| `model` | `"llama3.2"` | 所選 provider 的模型名稱（例如 `qwen2.5`、`claude-haiku-4-5`）。 |
| `batch_size` | `20` | 每批分類的最大 interaction 數。 |

當 `provider = "anthropic"` 時，需設定環境變數 `ANTHROPIC_API_KEY`。只會送出簡短摘要 —
絕不送出完整的 prompt 內容。

### `[collectors]`

| 鍵 | 預設 | 說明 |
|----|------|------|
| `enabled` | `["claude_code", "codex", "copilot"]` | ingest 時要執行哪些工具採集器。 |

### 資料庫位置

預設情況下，SQLite 資料庫位於平台的資料目錄（Linux 上為
`~/.local/share/agent-roi/agent_roi.db`）。如有需要，可在設定中以 `db_path` 覆寫。

## 環境變數

| 變數 | 用途 |
|------|------|
| `AGENT_ROI_CONFIG` | 自訂設定檔的路徑。 |
| `ANTHROPIC_API_KEY` | 當 `classifier.provider = "anthropic"` 時必須設定。 |
| `WIN_USER` | （WSL）Windows 使用者名稱，用以定位 Windows 側的工具 log。 |
