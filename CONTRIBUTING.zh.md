# 貢獻 Agent-ROI

感謝你有興趣改善 Agent-ROI！本指南帶你完成環境設定，並說明我們的協作方式。

> English version: [CONTRIBUTING.md](./CONTRIBUTING.md)

## 開發環境設定

Agent-ROI 有一個 Python 後端（以 [uv](https://docs.astral.sh/uv/) 管理）與一個
React 前端（以 npm 管理）。

```bash
# 後端
uv sync --extra dev
uv run pytest          # 跑測試
uv run ruff check src  # lint
uv run mypy            # 型別檢查

# 前端
cd web
npm install
npm run build
```

## 專案結構

```
src/agent_roi/
  collectors/   # 解析各工具的本地 log -> Interaction
  classify/     # 免模型的語意主題歸納（TF-IDF + 餘弦相似度分群）
  storage/      # SQLite 持久化 + 彙總
  core/         # 領域模型、設定、定價、平台、服務
  api/          # FastAPI REST 層
  cli/          # Typer 命令列介面
web/            # React + Vite 儀表板
design/         # DESIGN.md 設計系統（Linear）— 改 UI 前請先閱讀
docs/           # 英文文件 (*.md) + 中文翻譯 (*.zh.md)
tests/          # pytest 測試
```

前端遵循 [`design/DESIGN.md`](./design/DESIGN.md)（Notion）的設計系統。其 token 已
鏡射為 `web/src/index.css` 的 CSS 變數；改動 UI 樣式前請先閱讀，讓外觀維持一致。

### 建置發佈版本

web UI 會被打包進 Python 套件，讓一般安裝後 `agent-roi serve` 也能運作。建置 wheel 前：

```bash
./scripts/build_web.sh   # 建置 web/ 並複製進 src/agent_roi/webui
uv build                 # 產生 wheel/sdist（含 web UI）
```

## 新增採集器

新的工具整合就是一個 `Collector` 子類：

1. 建立 `src/agent_roi/collectors/<tool>.py`，繼承 `Collector`。
2. 實作 `is_available()` 與 `collect()`（參考既有採集器）。
3. 使用 `core.platform.find_tool_dirs(...)` 定位 log，讓 Windows/macOS/Linux 與
   WSL 都能運作。
4. 在 `collectors/__init__.py` 中註冊。
5. 在 `tests/` 下新增以 fixture 為基礎的測試。

完整指南見 [docs/collectors.zh.md](./docs/collectors.zh.md)。

## Pull Request

- 保持 PR 聚焦；一個 PR 一個邏輯變更。
- 行為變更請新增或更新測試。
- push 前請執行 `uv run ruff check src tests` 與 `uv run pytest`。
- 變更文件時，請同時更新英文文件與其 `.zh.md` 翻譯。

## 行為準則

參與本專案即表示你同意我們的[行為準則](./CODE_OF_CONDUCT.md)。
