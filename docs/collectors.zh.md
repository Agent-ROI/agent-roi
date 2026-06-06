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
| `gemini` | Gemini CLI | `~/.gemini/tmp/<projectHash>/chats/session-*.json{,l}` | 精算（工具回報） |
| `hermes` | Hermes Agent（NousResearch） | `~/.hermes/state.db`（SQLite） | 精算（工具回報） |

在 WSL 下，採集器也會搜尋掛載的 Windows home（`/mnt/c/Users/<name>/...`），因此由
Windows 側執行的工具所寫的 log 會被自動納入。Copilot 採集器還會透過
`core.platform.vscode_user_dirs()` 搜尋 VS Code 的分支（Insiders、VSCodium、Cursor）。

Gemini CLI 只記錄 `projectHash`（即 `sha256(cwd)`）而非路徑本身，因此採集器會從新版
CLI 寫在 chats 旁的 `.project_root` 標記檔還原真實的 `project`，若不存在則改以該 hash
反查 `~/.gemini/projects.json` 中記錄過的 cwd。它同時支援舊版單一物件 `.json` 與新版
逐行 `.jsonl` 兩種 session 格式，並將 Gemini 的推理（`thoughts`）token 併入 output。

Hermes 與其他工具有兩點不同。其一，它不是每個 session 一個 log 檔，而是用單一
SQLite 資料庫（`~/.hermes/state.db`，以唯讀開啟）。其二，它是一個**多供應商路由器**：
同一個 agent 會透過 Copilot 訂閱呼叫 Claude、用 OpenRouter 免費層跑 NVIDIA 模型、跑
本地 Ollama 模型等等，因此 model id 形態各異（`anthropic/claude-opus-4.6`、
`claude-sonnet-4.6`、`gpt-oss:20b`、`nvidia/…:free`）。採集器會剝除供應商前綴並把
`.` 正規化為 `-`，讓共用定價表能對應；未知、免費與本地模型計為 $0，這對它們而言是正確的。

關鍵在於，Hermes 的 `sessions` 表**已經在 session 層級彙總了精確的 token 用量**——
`input_tokens`、`output_tokens`、`cache_read_tokens`、`cache_write_tokens` 與
`reasoning_tokens`。採集器直接從這些欄位**每個 session 產生一筆 interaction**
（reasoning 併入 output，與 Gemini 一致），而非從逐筆訊息的總數去猜 input/output 的拆分。
這很重要：cache 讀取的計價比全新 input 低約 10 倍，且在 agent 工作負載中佔比極大，
若用猜的會嚴重失真。這些是真實數字，因此 Hermes 的 interaction 是 `exact` 而非估算。session 的 `title`
會餵給分類器；沒有 title 的 session 則退回用第一則 user 訊息，讓它仍能歸入某個主題。
較舊、尚無這些欄位的資料庫，則退回逐筆 `token_count` 加總（依 role 歸屬）。欄位名稱以
`PRAGMA table_info` 防禦性地探測，因此 Hermes 跨版本的 schema 變動不會中斷 ingest。

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
- **`summary` 保持簡短。** 它會餵給分類器（用來歸納主題）— 維持精簡片段即可，
  絕不要把完整的 prompt 內容放進去。
- **使用 `find_tool_dirs`。** 這是讓採集器能跨 Windows、macOS、Linux 與 WSL 運作的
  關鍵。
