/**
 * Brand icons for each supported AI coding tool.
 * SVG paths sourced from Simple Icons (simpleicons.org, MIT licence).
 * Each icon is rendered on a rounded-rect badge matching the tool's brand colour.
 */

interface Props {
  tool: string;
  size?: number;
  className?: string;
}

// Anthropic Claude — official mark from simpleicons.org/icons/anthropic
function ClaudeIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect width="24" height="24" rx="5" fill="#D97757" />
      {/* Anthropic logomark — two strokes forming an "A" shape */}
      <path
        d="M13.827 3.785h-3.257L5.094 20.215h3.257l1.224-3.356h5.634l1.224 3.356h3.257zm-3.56 10.591 1.932-5.299 1.932 5.299z"
        fill="#fff"
      />
    </svg>
  );
}

// Google Gemini — four-pointed star from simpleicons.org/icons/googlegemini
function GeminiIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect width="24" height="24" rx="5" fill="#fff" stroke="#e5e3df" strokeWidth="1" />
      <defs>
        <linearGradient id="gem-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4285F4" />
          <stop offset="50%" stopColor="#9B72CB" />
          <stop offset="100%" stopColor="#D96570" />
        </linearGradient>
      </defs>
      {/* Gemini 4-pointed star */}
      <path
        d="M12 2C12 2 10.5 8.5 8 10.5C5.5 12.5 2 12 2 12C2 12 5.5 11.5 8 13.5C10.5 15.5 12 22 12 22C12 22 13.5 15.5 16 13.5C18.5 11.5 22 12 22 12C22 12 18.5 12.5 16 10.5C13.5 8.5 12 2 12 2Z"
        fill="url(#gem-grad)"
      />
    </svg>
  );
}

// GitHub Copilot — official mark from simpleicons.org/icons/githubcopilot
function CopilotIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect width="24" height="24" rx="5" fill="#fff" stroke="#e5e3df" strokeWidth="1" />
      {/* GitHub Copilot helmet silhouette */}
      <path
        d="M12 2.5a5.25 5.25 0 0 0-5.25 5.25v.65a3 3 0 0 0-1.5 2.6v2a3 3 0 0 0 1.5 2.6v.65a1.5 1.5 0 0 0 1.5 1.5h.75a1.5 1.5 0 0 0 1.5-1.5v-.25h3v.25a1.5 1.5 0 0 0 1.5 1.5h.75a1.5 1.5 0 0 0 1.5-1.5v-.65a3 3 0 0 0 1.5-2.6v-2a3 3 0 0 0-1.5-2.6v-.65A5.25 5.25 0 0 0 12 2.5zm-3 7.25a1 1 0 1 1 2 0 1 1 0 0 1-2 0zm4 0a1 1 0 1 1 2 0 1 1 0 0 1-2 0zm-4.5 3.25h7a.5.5 0 0 1 0 1h-7a.5.5 0 0 1 0-1z"
        fill="#24292F"
      />
    </svg>
  );
}

// OpenAI — official bloom/flower mark from simpleicons.org/icons/openai
function CodexIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect width="24" height="24" rx="5" fill="#fff" stroke="#e5e3df" strokeWidth="1" />
      {/* OpenAI logo */}
      <path
        d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.896zm16.597 3.855l-5.843-3.369 2.02-1.168a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.402-.681zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z"
        fill="#10A37F"
      />
    </svg>
  );
}

// Hermes Agent (NousResearch) — winged mark evoking the messenger god
function HermesIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect width="24" height="24" rx="5" fill="#5B4BE0" />
      {/* Stylized winged helmet / "H" with wings */}
      <path
        d="M7.5 7v10M16.5 7v10M7.5 12h9"
        stroke="#fff"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M7.5 8.2c-1.6-.2-3-.1-4.3.6 1.3.3 2.4.8 3.2 1.6M16.5 8.2c1.6-.2 3-.1 4.3.6-1.3.3-2.4.8-3.2 1.6"
        stroke="#C7C0FF"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// Google Antigravity (agy CLI) — official mark: an upward-sweeping plume cut
// from a multi-colour (Google brand) blurred gradient. Paths/filters are the
// official artwork (via LobeHub icon set); ids are suffixed to stay unique when
// several icons render on one page, and it sits on a white badge like the other
// Google-family marks.
function AntigravityIcon({ size }: { size: number }) {
  const u = "agy"; // unique id prefix for this component's defs
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect width="24" height="24" rx="5" fill="#fff" stroke="#e5e3df" strokeWidth="1" />
      <mask id={`${u}-m`} maskUnits="userSpaceOnUse" x="0" y="1" width="24" height="23">
        <path
          d="M21.751 22.607c1.34 1.005 3.35.335 1.508-1.508C17.73 15.74 18.904 1 12.037 1 5.17 1 6.342 15.74.815 21.1c-2.01 2.009.167 2.511 1.507 1.506 5.192-3.517 4.857-9.714 9.715-9.714 4.857 0 4.522 6.197 9.714 9.715z"
          fill="#fff"
        />
      </mask>
      <g mask={`url(#${u}-m)`}>
        <g filter={`url(#${u}-f1)`}>
          <path
            d="M-1.018-3.992c-.408 3.591 2.686 6.89 6.91 7.37 4.225.48 7.98-2.043 8.387-5.633.408-3.59-2.686-6.89-6.91-7.37-4.225-.479-7.98 2.043-8.387 5.633z"
            fill="#FFE432"
          />
        </g>
        <g filter={`url(#${u}-f2)`}>
          <path
            d="M15.269 7.747c1.058 4.557 5.691 7.374 10.348 6.293 4.657-1.082 7.575-5.653 6.516-10.21-1.058-4.556-5.691-7.374-10.348-6.292-4.657 1.082-7.575 5.653-6.516 10.21z"
            fill="#FC413D"
          />
        </g>
        <g filter={`url(#${u}-f3)`}>
          <path
            d="M-12.443 10.804c1.338 4.703 7.36 7.11 13.453 5.378 6.092-1.733 9.947-6.95 8.61-11.652C8.282-.173 2.26-2.58-3.833-.848-9.925.884-13.78 6.1-12.443 10.804z"
            fill="#00B95C"
          />
        </g>
        <g filter={`url(#${u}-f4)`}>
          <path
            d="M-7.608 14.703c3.352 3.424 9.126 3.208 12.896-.483 3.77-3.69 4.108-9.459.756-12.883C2.69-2.087-3.083-1.871-6.853 1.82c-3.77 3.69-4.108 9.458-.755 12.883z"
            fill="#00B95C"
          />
        </g>
        <g filter={`url(#${u}-f5)`}>
          <path
            d="M9.932 27.617c1.04 4.482 5.384 7.303 9.7 6.3 4.316-1.002 6.971-5.448 5.93-9.93-1.04-4.483-5.384-7.304-9.7-6.301-4.316 1.002-6.971 5.448-5.93 9.93z"
            fill="#3186FF"
          />
        </g>
        <g filter={`url(#${u}-f6)`}>
          <path
            d="M2.572-8.185C.392-3.329 2.778 2.472 7.9 4.771c5.122 2.3 11.042.227 13.222-4.63 2.18-4.855-.205-10.656-5.327-12.955-5.122-2.3-11.042-.227-13.222 4.63z"
            fill="#FBBC04"
          />
        </g>
        <g filter={`url(#${u}-f7)`}>
          <path
            d="M-3.267 38.686c-5.277-2.072 3.742-19.117 5.984-24.83 2.243-5.712 8.34-8.664 13.616-6.592 5.278 2.071 11.533 13.482 9.29 19.195-2.242 5.713-23.613 14.298-28.89 12.227z"
            fill="#3186FF"
          />
        </g>
        <g filter={`url(#${u}-f8)`}>
          <path
            d="M18.163 9.077c5.81 3.93 12.502 4.19 14.946.577 2.443-3.612-.287-9.727-6.098-13.658-5.81-3.931-12.502-4.19-14.946-.577-2.443 3.612.287 9.727 6.098 13.658z"
            fill="#FC413D"
          />
        </g>
        <g filter={`url(#${u}-f9)`}>
          <path
            d="M-.915 2.684c-1.44 3.473-.97 6.967 1.05 7.804 2.02.837 4.824-1.3 6.264-4.772 1.44-3.473.97-6.967-1.05-7.804-2.02-.837-4.824 1.3-6.264 4.772z"
            fill="#FFEE48"
          />
        </g>
      </g>
      <defs>
        {[
          { id: "f1", sd: 1.117 },
          { id: "f2", sd: 5.4 },
          { id: "f3", sd: 4.591 },
          { id: "f4", sd: 4.591 },
          { id: "f5", sd: 4.363 },
          { id: "f6", sd: 3.954 },
          { id: "f7", sd: 3.531 },
          { id: "f8", sd: 2.669 },
          { id: "f9", sd: 3.303 },
        ].map((f) => (
          <filter
            key={f.id}
            id={`${u}-${f.id}`}
            x="-50%"
            y="-50%"
            width="200%"
            height="200%"
            colorInterpolationFilters="sRGB"
          >
            <feGaussianBlur stdDeviation={f.sd} />
          </filter>
        ))}
      </defs>
    </svg>
  );
}

// Cursor — official mark
function CursorIcon({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect width="24" height="24" rx="5" fill="#fff" stroke="#e5e3df" strokeWidth="1" />
      <path
        d="M13.5 2 L22 12 L13.5 22 L13.5 13.5 L2 12 L13.5 10.5 Z"
        fill="#000"
      />
    </svg>
  );
}

// Fallback
function DefaultIcon({ size, tool }: { size: number; tool: string }) {
  const initials = tool.slice(0, 2).toUpperCase();
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect width="24" height="24" rx="5" fill="#787671" />
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
    if (key === "hermes" || key === "hermes_agent") return <HermesIcon size={size} />;
    if (key === "antigravity" || key === "agy") return <AntigravityIcon size={size} />;
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
    hermes: "Hermes Agent",
    hermes_agent: "Hermes Agent",
    antigravity: "Antigravity",
    agy: "Antigravity",
    cursor: "Cursor",
  };
  return map[tool.toLowerCase()] ?? tool;
}
