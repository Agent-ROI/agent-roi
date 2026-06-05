# 採集器（Collectors）

> English version: [collectors.md](./collectors.md)

**採集器（collector）** 知道如何找到某個 AI 工具的本地 log，並將每一次請求／回應
轉換成正規化的 `Interaction`。採集器是唯讀且冪等的。

## 內建採集器

| 採集器 | 工具 | Log 位置 | Token |
|--------|------|----------|-------|
| `claude_code` | Claude Code | `~/.claude/projects/**/<session>.jsonl` | 精算（工具回報） |
| `codex` | OpenAI Codex CLI | `~/.codex/sessions/**/*.jsonl` | 精算（工具回報） |
| `copilot` | GitHub Copilot Chat (VS Code) | `<VS Code User>/workspaceStorage/**/chatSessions/*` | **估算** |

在 WSL 下，採集器也會搜尋掛載的 Windows home（`/mnt/c/Users/<name>/...`），因此由
Windows 側執行的工具所寫的 log 會被自動納入。Copilot 採集器還會透過
`core.platform.vscode_user_dirs()` 搜尋 VS Code 的分支（Insiders、VSCodium、Cursor）。

### 關於估算 token

有些工具只記錄對話內容，而**不**記錄真實 token 用量 —— GitHub Copilot 是典型案例，
因為它是訂閱制計費而非按 token 計費。對這類工具，採集器會用一個離線啟發式從訊息文字
估算 token 數，並將 `Interaction.estimated` 設為 `True`。報表會以 `estimated` / `exact`
標章呈現，讓兩者絕不被悄悄混在一起。詳見
[`core/tokens.py`](../src/agent_roi/core/tokens.py)。

## 撰寫新的採集器

1. 建立 `src/agent_roi/collectors/<tool>.py`：

   ```python
   from collections.abc import Iterator
   from pathlib import Path

   from agent_roi.collectors.base import Collector
   from agent_roi.core.models import Interaction, Tool
   from agent_roi.core.platform import find_tool_dirs


   class MyToolCollector(Collector):
       tool = Tool.UNKNOWN  # 新增一個 Tool enum 值
       name = "mytool"

       def __init__(self, roots: list[Path] | None = None) -> None:
           self.roots = roots if roots is not None else find_tool_dirs(".mytool", "logs")

       def is_available(self) -> bool:
           return bool(self.roots)

       def collect(self) -> Iterator[Interaction]:
           for root in self.roots:
               for path in root.rglob("*.jsonl"):
                   ...  # 解析並 yield Interaction 物件
   ```

2. 在 `src/agent_roi/collectors/__init__.py` 中註冊。

3. 在 `tests/` 下新增一個以 fixture 為基礎的測試（解析一行範例 log）。

### 準則

- **要防禦性。** 遇到不認得的記錄就跳過，而非拋出例外；工具的 log 格式會隨版本改變。
- **使用穩定的 `id`。** 優先採用工具本身的 message id，讓重複 ingest 冪等。若沒有，
  則退而使用 `<session>:<sequence>`。
- **`summary` 保持簡短。** 它會餵給分類器，也可能被送往雲端模型 — 絕不要把完整的
  prompt 內容放進去。
- **使用 `find_tool_dirs`。** 這是讓採集器能跨 Windows、macOS、Linux 與 WSL 運作的
  關鍵。
