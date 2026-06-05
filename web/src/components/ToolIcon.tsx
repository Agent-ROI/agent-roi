/**
 * Brand icons for each supported AI coding tool.
 * All SVGs are inlined to avoid network requests and ensure offline use.
 */

interface Props {
  tool: string;
  size?: number;
  className?: string;
}

// Claude / Anthropic — stylised "A" mark
function ClaudeIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect width="24" height="24" rx="6" fill="#D97757" />
      <path
        d="M14.16 5.5 9.04 18.5h2.18l1.08-2.96h4.9l1.08 2.96H20.4L15.28 5.5h-1.12ZM12.9 13.7l1.75-4.84 1.75 4.84H12.9ZM4 18.5h2.1V5.5H4v13Z"
        fill="#fff"
      />
    </svg>
  );
}

// Gemini — Google's two-tone diamond mark
function GeminiIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect width="24" height="24" rx="6" fill="#1A73E8" />
      <path
        d="M12 4C12 4 8.5 9.5 8.5 12C8.5 14.5 12 20 12 20C12 20 15.5 14.5 15.5 12C15.5 9.5 12 4 12 4Z"
        fill="white"
      />
      <path
        d="M4 12C4 12 9.5 8.5 12 8.5C14.5 8.5 20 12 20 12C20 12 14.5 15.5 12 15.5C9.5 15.5 4 12 4 12Z"
        fill="rgba(255,255,255,0.7)"
      />
    </svg>
  );
}

// GitHub Copilot — Copilot silhouette
function CopilotIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect width="24" height="24" rx="6" fill="#24292F" />
      <path
        d="M12 4.5C10.07 4.5 8.5 6.07 8.5 8V9.5C7.67 9.5 7 10.17 7 11V14C7 14.83 7.67 15.5 8.5 15.5H9C9 16.88 10.12 18 11.5 18H12.5C13.88 18 15 16.88 15 15.5H15.5C16.33 15.5 17 14.83 17 14V11C17 10.17 16.33 9.5 15.5 9.5V8C15.5 6.07 13.93 4.5 12 4.5ZM12 6C13.1 6 14 6.9 14 8V9.5H10V8C10 6.9 10.9 6 12 6ZM10.5 11.5C10.5 11.22 10.72 11 11 11C11.28 11 11.5 11.22 11.5 11.5V13C11.5 13.28 11.28 13.5 11 13.5C10.72 13.5 10.5 13.28 10.5 13V11.5ZM13 11C13.28 11 13.5 11.22 13.5 11.5V13C13.5 13.28 13.28 13.5 13 13.5C12.72 13.5 12.5 13.28 12.5 13V11.5C12.5 11.22 12.72 11 13 11Z"
        fill="white"
      />
    </svg>
  );
}

// OpenAI Codex — simple "O" mark
function CodexIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect width="24" height="24" rx="6" fill="#10A37F" />
      <path
        d="M12 5.5C8.41 5.5 5.5 8.41 5.5 12C5.5 15.59 8.41 18.5 12 18.5C15.59 18.5 18.5 15.59 18.5 12C18.5 8.41 15.59 5.5 12 5.5ZM12 7C14.76 7 17 9.24 17 12C17 14.76 14.76 17 12 17C9.24 17 7 14.76 7 12C7 9.24 9.24 7 12 7Z"
        fill="white"
      />
      <circle cx="12" cy="12" r="2.5" fill="white" />
    </svg>
  );
}

// Cursor — triangular cursor mark
function CursorIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect width="24" height="24" rx="6" fill="#7B3FF2" />
      <path d="M6 5.5L18 12L12.5 13.5L10 19L6 5.5Z" fill="white" />
    </svg>
  );
}

// Fallback — generic code terminal icon
function DefaultIcon({ size, tool }: { size: number; tool: string }) {
  const initials = tool.slice(0, 2).toUpperCase();
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect width="24" height="24" rx="6" fill="#787671" />
      <text
        x="12"
        y="16"
        textAnchor="middle"
        fontSize="10"
        fontWeight="600"
        fill="white"
        fontFamily="system-ui, sans-serif"
      >
        {initials}
      </text>
    </svg>
  );
}

export function ToolIcon({ tool, size = 20, className }: Props) {
  const key = tool.toLowerCase();
  const icon = (() => {
    if (key === "claude_code" || key === "claude") return <ClaudeIcon size={size} />;
    if (key === "gemini" || key === "gemini_cli") return <GeminiIcon size={size} />;
    if (key === "copilot" || key === "github_copilot") return <CopilotIcon size={size} />;
    if (key === "codex" || key === "openai_codex") return <CodexIcon size={size} />;
    if (key === "cursor") return <CursorIcon size={size} />;
    return <DefaultIcon size={size} tool={tool} />;
  })();

  return (
    <span className={`tool-icon${className ? ` ${className}` : ""}`} title={tool}>
      {icon}
    </span>
  );
}

/** Human-readable display name for a tool key. */
export function toolDisplayName(tool: string): string {
  const map: Record<string, string> = {
    claude_code: "Claude Code",
    claude: "Claude",
    gemini: "Gemini CLI",
    gemini_cli: "Gemini CLI",
    copilot: "GitHub Copilot",
    github_copilot: "GitHub Copilot",
    codex: "Codex CLI",
    openai_codex: "Codex CLI",
    cursor: "Cursor",
  };
  return map[tool.toLowerCase()] ?? tool;
}
