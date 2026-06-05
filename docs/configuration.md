# Configuration

> 繁體中文版：[configuration.zh.md](./configuration.zh.md)

Agent-ROI works with zero configuration. To customize it, create a TOML file at:

- **Linux/macOS:** `~/.config/agent-roi/config.toml`
- **Windows:** `%APPDATA%\agent-roi\config.toml`

Override the path with the `AGENT_ROI_CONFIG` environment variable.

## Full example

```toml
[classifier]
provider = "ollama"     # "ollama" (local) | "anthropic" (cloud Haiku)
model = "llama3.2"
batch_size = 20

[collectors]
enabled = ["claude_code", "codex"]
```

## Options

### `[classifier]`

| Key | Default | Description |
|-----|---------|-------------|
| `provider` | `"ollama"` | `ollama` runs a local model (offline, private). `anthropic` uses Claude Haiku via the API. |
| `model` | `"llama3.2"` | Model name for the chosen provider (e.g. `qwen2.5`, `claude-haiku-4-5`). |
| `batch_size` | `20` | Max interactions classified per batch. |

For `provider = "anthropic"`, set the `ANTHROPIC_API_KEY` environment variable.
Only short summaries are sent — never full prompt bodies.

### `[collectors]`

| Key | Default | Description |
|-----|---------|-------------|
| `enabled` | `["claude_code", "codex"]` | Which tool collectors to run during ingest. |

### Database location

By default the SQLite database lives in the platform data directory
(`~/.local/share/agent-roi/agent_roi.db` on Linux). Override with `db_path` in
config if needed.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `AGENT_ROI_CONFIG` | Path to a custom config file. |
| `ANTHROPIC_API_KEY` | Required when `classifier.provider = "anthropic"`. |
| `WIN_USER` | (WSL) Windows username, to locate Windows-side tool logs. |
