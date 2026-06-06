# Collectors

> 繁體中文版：[collectors.zh.md](./collectors.zh.md)

A **collector** knows how to find one AI tool's local logs and turn each
request/response turn into a normalized `Interaction`. Collectors are read-only
and idempotent.

## Built-in collectors

| Collector | Tool | Log location | Tokens |
|-----------|------|--------------|--------|
| `claude_code` | Claude Code | `~/.claude/projects/**/<session>.jsonl` | exact (reported) |
| `codex` | OpenAI Codex CLI | `~/.codex/sessions/**/*.jsonl` | exact (reported) |
| `copilot` | GitHub Copilot Chat (VS Code) | `<VS Code User>/workspaceStorage/**/chatSessions/*` | **estimated** |
| `gemini` | Gemini CLI | `~/.gemini/tmp/<projectHash>/chats/session-*.json{,l}` | exact (reported) |
| `hermes` | Hermes Agent (NousResearch) | `~/.hermes/state.db` (SQLite) | exact (reported) |

Under WSL, collectors also search the mounted Windows home(s) at
`/mnt/c/Users/<name>/...`, so logs written by tools running on the Windows side
are picked up automatically. The Copilot collector additionally searches VS Code
forks (Insiders, VSCodium, Cursor) via `core.platform.vscode_user_dirs()`.

The Gemini CLI logs only a `projectHash` (which is `sha256(cwd)`), not the path
itself, so the collector recovers a real `project` from the `.project_root`
marker newer CLI versions write next to the chats, falling back to a reverse
lookup of the hash against the cwds recorded in `~/.gemini/projects.json`. It
reads both the older single-object `.json` and the newer line-delimited `.jsonl`
session shapes, and folds Gemini's reasoning (`thoughts`) tokens into output.

Hermes is different from the others in two ways. First, instead of per-session
log files it keeps a single SQLite database (`~/.hermes/state.db`, opened
read-only). Second, it is a **multi-provider router**: the same agent calls Claude
through a Copilot subscription, NVIDIA models via OpenRouter's free tier, local
Ollama models, and so on, so model ids vary in shape (`anthropic/claude-opus-4.6`,
`claude-sonnet-4.6`, `gpt-oss:20b`, `nvidia/…:free`). The collector strips any
provider prefix and normalizes `.` to `-` so the shared pricing table resolves
them; unknown, free, and local models price at $0, which is correct for them.

Crucially, Hermes's `sessions` table already **aggregates exact token usage per
session** — `input_tokens`, `output_tokens`, `cache_read_tokens`,
`cache_write_tokens`, and `reasoning_tokens`. The collector emits **one
interaction per session** straight from these columns (reasoning folded into
output, matching Gemini) rather than guessing an input/output split from
per-message totals. This matters because cache reads — priced ~10× lower than
fresh input — dominate agent workloads and would be badly mis-costed otherwise.
The counts are real, so Hermes interactions are `exact`, not estimated. The
session `title` feeds the classifier; sessions without one fall back to their
first user message so they still cluster into a topic. Older databases that
predate the per-session token columns fall back to summing the per-message
`token_count` (attributed by role). Column names are discovered defensively
(`PRAGMA table_info`) so schema shifts across Hermes versions don't break ingest.

### A note on estimated tokens

Some tools log the conversation but **not** real token usage — GitHub Copilot is
the notable case, because it's subscription-billed rather than per-token. For
these, the collector estimates token counts from the message text with an
offline heuristic and sets `Interaction.estimated = True`. Reports surface this
with an `estimated` / `exact` badge so the two are never silently mixed. See
[`core/tokens.py`](../src/agent_roi/core/tokens.py).

## Writing a new collector

1. Create `src/agent_roi/collectors/<tool>.py`:

   ```python
   from collections.abc import Iterator
   from pathlib import Path

   from agent_roi.collectors.base import Collector
   from agent_roi.core.models import Interaction, Tool
   from agent_roi.core.platform import find_tool_dirs


   class MyToolCollector(Collector):
       tool = Tool.UNKNOWN  # add a new Tool enum value
       name = "mytool"

       def __init__(self, roots: list[Path] | None = None) -> None:
           self.roots = roots if roots is not None else find_tool_dirs(".mytool", "logs")

       def is_available(self) -> bool:
           return bool(self.roots)

       def collect(self) -> Iterator[Interaction]:
           for root in self.roots:
               for path in root.rglob("*.jsonl"):
                   ...  # parse and yield Interaction objects
   ```

2. Register it in `src/agent_roi/collectors/__init__.py`.

3. Add a fixture-based test (parse a sample log line) under `tests/`.

### Guidelines

- **Be defensive.** Skip records you don't recognize instead of raising; tool log
  formats change across versions.
- **Use a stable `id`.** Prefer the tool's own message id so re-ingest is
  idempotent. Fall back to `<session>:<sequence>` if none exists.
- **Keep `summary` short.** It feeds the classifier (used to discover topics) —
  keep it to a concise snippet, never full prompt bodies.
- **Use `find_tool_dirs`.** This is what makes collectors work across Windows,
  macOS, Linux, and WSL.
