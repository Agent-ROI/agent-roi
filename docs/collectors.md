# Collectors

> 繁體中文版：[collectors.zh.md](./collectors.zh.md)

A **collector** knows how to find one AI tool's local logs and turn each
request/response turn into a normalized `Interaction`. Collectors are read-only
and idempotent.

## Built-in collectors

| Collector | Tool | Log location |
|-----------|------|--------------|
| `claude_code` | Claude Code | `~/.claude/projects/**/<session>.jsonl` |
| `codex` | OpenAI Codex CLI | `~/.codex/sessions/**/*.jsonl` |

Under WSL, collectors also search the mounted Windows home(s) at
`/mnt/c/Users/<name>/...`, so logs written by tools running on the Windows side
are picked up automatically.

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
- **Keep `summary` short.** It feeds the classifier and may be sent to a cloud
  model — never put full prompt bodies in it.
- **Use `find_tool_dirs`.** This is what makes collectors work across Windows,
  macOS, Linux, and WSL.
