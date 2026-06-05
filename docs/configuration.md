# Configuration

> 繁體中文版：[configuration.zh.md](./configuration.zh.md)

Agent-ROI works with zero configuration. To customize it, create a TOML file at:

- **Linux/macOS:** `~/.config/agent-roi/config.toml`
- **Windows:** `%APPDATA%\agent-roi\config.toml`

Override the path with the `AGENT_ROI_CONFIG` environment variable.

## Full example

```toml
[classifier]
similarity_threshold = 0.18   # higher = more, smaller topics
label_terms = 3               # words used to name each topic

[collectors]
enabled = ["claude_code", "codex", "copilot", "gemini"]
```

## Options

### `[classifier]`

The classifier is model-free: it groups sessions by semantic similarity using
TF-IDF vectors and cosine distance. No model, no API key, no network access
required.

| Key | Default | Description |
|-----|---------|-------------|
| `similarity_threshold` | `0.18` | Cosine similarity at or above which two sessions are merged into one topic. Raise to get more, narrower topics; lower to get fewer, broader ones. |
| `label_terms` | `3` | Number of distinctive words used to name each discovered topic. |

### `[collectors]`

| Key | Default | Description |
|-----|---------|-------------|
| `enabled` | `["claude_code", "codex", "copilot", "gemini"]` | Which tool collectors to run during ingest. |

### Database location

By default the SQLite database lives in the platform data directory
(`~/.local/share/agent-roi/agent_roi.db` on Linux). Override with `db_path` in
config if needed.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `AGENT_ROI_CONFIG` | Path to a custom config file. |
| `WIN_USER` | (WSL) Windows username, to locate Windows-side tool logs. |
