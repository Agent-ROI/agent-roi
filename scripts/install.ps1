# Agent-ROI one-line installer for Windows (PowerShell).
#
#   irm https://raw.githubusercontent.com/Agent-ROI/agent-roi/main/scripts/install.ps1 | iex
#
# Installs `uv` if needed, then installs Agent-ROI as a uv tool.
# Requires PowerShell 5.1+ (ships with Windows 10/11).
[CmdletBinding()]
param(
    [string]$Package = "agent-roi-tracker",
    [switch]$FromGit
)

$Repo = if ($env:AGENT_ROI_REPO) { $env:AGENT_ROI_REPO } else { "https://github.com/Agent-ROI/agent-roi" }
if ($env:AGENT_ROI_FROM_GIT -eq "1" -or $FromGit) {
    $Package = "git+$Repo.git"
}

# ── colours ──────────────────────────────────────────────────────────────────
function Write-Step  { param($msg) Write-Host "  -> " -ForegroundColor Blue -NoNewline; Write-Host $msg -ForegroundColor White }
function Write-Ok    { param($msg) Write-Host "  v " -ForegroundColor Green -NoNewline; Write-Host $msg }
function Write-Err   { param($msg) Write-Host "  x " -ForegroundColor Red -NoNewline; Write-Host $msg -ForegroundColor Red }

# ── banner ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  Agent-ROI  " -ForegroundColor White -NoNewline
Write-Host "AI coding cost & ROI tracker" -ForegroundColor DarkGray
Write-Host "  -----------------------------------------" -ForegroundColor DarkGray
Write-Host ""

# ── 1. Ensure uv ─────────────────────────────────────────────────────────────
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Step "Installing uv (Python tool manager)"
    Write-Host "  ... Downloading uv" -ForegroundColor DarkGray
    try {
        $uvInstall = (Invoke-RestMethod "https://astral.sh/uv/install.ps1")
        Invoke-Expression $uvInstall
    } catch {
        Write-Err "uv installation failed — install manually: https://docs.astral.sh/uv/"
        exit 1
    }
    # Refresh PATH so uv is available in this session.
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") +
                ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Err "uv not found after install — restart your terminal and re-run."
    exit 1
}

Write-Ok "uv ready"

# ── 2. Install Agent-ROI ─────────────────────────────────────────────────────
Write-Step "Installing Agent-ROI"
Write-Host "  ... Fetching $Package" -ForegroundColor DarkGray

$result = & uv tool install --upgrade --force $Package 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Err "Installation failed:"
    Write-Host $result
    exit 1
}

Write-Ok "agent-roi installed"
Write-Host ""
Write-Host "  -----------------------------------------" -ForegroundColor DarkGray

# ── 3. Next steps ────────────────────────────────────────────────────────────
$agentRoi = Get-Command agent-roi -ErrorAction SilentlyContinue
if ($agentRoi) {
    $installedVersion = & agent-roi --version 2>$null
    if ($installedVersion) {
        $ver = ($installedVersion -split "\s+")[-1]
        Write-Ok "agent-roi $ver"
    }
    Write-Host "  Done!  Run:" -ForegroundColor Green
} else {
    # uv tool shims land in %USERPROFILE%\.local\bin — may need a new terminal.
    $shimPath = Join-Path $env:USERPROFILE ".local\bin"
    if ($env:PATH -notlike "*$shimPath*") {
        Write-Host "  Done!  " -ForegroundColor Green -NoNewline
        Write-Host "Restart your terminal so " -NoNewline
        Write-Host "agent-roi" -ForegroundColor White -NoNewline
        Write-Host " is on PATH, then run:"
    } else {
        Write-Host "  Done!  Run:" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "    agent-roi ingest   " -ForegroundColor White -NoNewline
Write-Host "# collect logs from your AI tools" -ForegroundColor DarkGray
Write-Host "    agent-roi serve    " -ForegroundColor White -NoNewline
Write-Host "# open the web dashboard" -ForegroundColor DarkGray
Write-Host ""
