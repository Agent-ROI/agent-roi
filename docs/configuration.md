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
min_topic_sessions = 2        # smaller clusters fold into a shared "misc" topic

[collectors]
enabled = ["claude_code", "codex", "copilot", "gemini", "hermes"]

[budget]
daily_usd = 5.0      # optional — omit a line to leave that period unbudgeted
weekly_usd = 25.0
monthly_usd = 100.0
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
| `min_topic_sessions` | `2` | Clusters with fewer than this many sessions fold into a single `misc` topic, so the report isn't buried under one-off, single-session labels. Set to `1` to keep every cluster as its own topic. |

### `[collectors]`

| Key | Default | Description |
|-----|---------|-------------|
| `enabled` | `["claude_code", "codex", "copilot", "gemini", "hermes"]` | Which tool collectors to run during ingest. |

### `[budget]`

Optional spend limits (USD) per rolling period. When set, `agent-roi budget`
and the dashboard's Overview show spend against the limit and flag when a period
is over budget. Every limit is optional — omit a line to leave that period
unbudgeted. Weeks start on Monday; months reset on the 1st.

| Key | Default | Description |
|-----|---------|-------------|
| `daily_usd` | _(none)_ | Spend limit for the current day. |
| `weekly_usd` | _(none)_ | Spend limit for the current week (since Monday). |
| `monthly_usd` | _(none)_ | Spend limit for the current calendar month. |

### Database location

By default the SQLite database lives in the platform data directory
(`~/.local/share/agent-roi/agent_roi.db` on Linux). Override with `db_path` in
config if needed.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `AGENT_ROI_CONFIG` | Path to a custom config file. |
| `WIN_USER` | (WSL) Windows username, to locate Windows-side tool logs. |
