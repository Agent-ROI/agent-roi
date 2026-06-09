"""Agent-ROI command-line interface."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from agent_roi import __version__
from agent_roi.core.platform import platform_label
from agent_roi.core.service import Service
from agent_roi.core.timeframe import parse_since
from agent_roi.storage.db import Database

app = typer.Typer(
    name="agent-roi",
    help="Track the cost, usage, and ROI of your AI coding agents across every tool.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"agent-roi {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show the installed version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Track the cost, usage, and ROI of your AI coding agents across every tool."""


def _parse_since(value: str) -> datetime | None:
    try:
        return parse_since(value)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc


@app.command()
def ingest(
    classify: bool = typer.Option(True, help="Also discover topics after ingesting (recommended)."),
) -> None:
    """Collect interactions from all enabled tools, then discover topics."""
    service = Service()
    with console.status("Ingesting logs..."):
        count = service.ingest()
    console.print(f"[green]Ingested {count} interactions.[/green]")
    if classify:
        with console.status("Discovering topics..."):
            labeled = service.classify()
        console.print(f"[green]Classified {labeled} interactions into topics.[/green]")


@app.command()
def classify(
    limit: int = typer.Option(0, help="Max sessions to classify (0 = all)."),
) -> None:
    """Re-discover topics across all sessions."""
    service = Service()
    with console.status("Discovering topics..."):
        count = service.classify(limit=limit or None)
    console.print(f"[green]Classified {count} interactions.[/green]")


@app.command()
def report(
    by: str = typer.Option("topic", help="Grouping dimension: topic | tool | model | project."),
    since: str = typer.Option(
        "", help="Time window start: a date (YYYY-MM-DD) or shorthand like 7d, 24h, today."
    ),
) -> None:
    """Show a token/cost breakdown, grouped and optionally time-windowed."""
    if by not in Database.VALID_DIMENSIONS:
        valid = "|".join(sorted(Database.VALID_DIMENSIONS))
        console.print(f"[red]Unsupported grouping: {by} (use {valid})[/red]")
        raise typer.Exit(1)

    start = _parse_since(since)
    service = Service()
    rollups = service.report(dimension=by, start=start)
    if not rollups:
        console.print("[yellow]No data in range. Run 'agent-roi ingest' first.[/yellow]")
        return

    title = f"Token Cost by {by.capitalize()}"
    if start is not None:
        title += f"  (since {start.date()})"
    table = Table(title=title)
    table.add_column(by.capitalize(), style="cyan", no_wrap=True)
    table.add_column("Interactions", justify="right")
    table.add_column("Input", justify="right")
    table.add_column("Output", justify="right")
    # Cache reads dominate the total for tools with prompt caching (often >80%),
    # so break them out — otherwise "Total" looks inexplicably huge next to a
    # tiny "Input". See TokenComposition for the same split in the UI.
    table.add_column("Cached", justify="right", style="dim")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Cost (USD)", justify="right", style="green")
    table.add_column("Src", justify="center")

    for r in rollups:
        table.add_row(
            r.key,
            str(r.interactions),
            f"{r.input_tokens:,}",
            f"{r.output_tokens:,}",
            f"{r.cache_read_tokens:,}",
            f"{r.total_tokens:,}",
            f"${r.cost_usd:,.4f}",
            "~est" if r.estimated else "exact",
        )
    console.print(table)
    console.print(
        "[dim]Cached = tokens served from the prompt cache (re-sent context, "
        "billed cheap); included in Total.[/dim]"
    )
    if any(r.estimated for r in rollups):
        console.print("[dim]~est = token counts estimated (tool doesn't report usage).[/dim]")


@app.command()
def topic(
    name: str = typer.Argument(..., help="Topic to drill into."),
    since: str = typer.Option("", help="Time window start (date or 7d/24h/today)."),
) -> None:
    """Drill into one topic: how its tokens split across tools and models."""
    start = _parse_since(since)
    service = Service()
    bd = service.topic_breakdown(name, start=start)
    if bd.total.interactions == 0:
        console.print(f"[yellow]No interactions for topic '{name}' in range.[/yellow]")
        return

    console.print(
        f"[bold]{name}[/bold] — {bd.total.interactions} interactions, "
        f"{bd.total.total_tokens:,} tokens, [green]${bd.total.cost_usd:,.4f}[/green]"
    )

    for label, rows in (("By Tool", bd.by_tool), ("By Model", bd.by_model)):
        table = Table(title=label)
        table.add_column(label.split()[-1], style="cyan")
        table.add_column("Interactions", justify="right")
        table.add_column("Total Tokens", justify="right")
        table.add_column("Cost (USD)", justify="right", style="green")
        table.add_column("Share", justify="right")
        for r in rows:
            share = (r.cost_usd / bd.total.cost_usd * 100) if bd.total.cost_usd else 0.0
            table.add_row(
                r.key,
                str(r.interactions),
                f"{r.total_tokens:,}",
                f"${r.cost_usd:,.4f}",
                f"{share:.0f}%",
            )
        console.print(table)


@app.command()
def sessions(
    topic: str = typer.Option("", help="Only sessions in this topic."),
    since: str = typer.Option("", help="Time window start (date or 7d/24h/today)."),
    search: str = typer.Option("", help="Filter by text in the session summary."),
    limit: int = typer.Option(30, help="Max sessions to show (most recent first)."),
) -> None:
    """List individual agent sessions: the unit a topic is made of."""
    start = _parse_since(since)
    service = Service()
    rows = service.sessions(
        topic=topic or None,
        start=start,
        search=search or None,
        limit=limit,
    )
    if not rows:
        console.print("[yellow]No sessions in range. Run 'agent-roi ingest' first.[/yellow]")
        return

    title = "Sessions"
    if topic:
        title += f" · {topic}"
    if start is not None:
        title += f"  (since {start.date()})"
    table = Table(title=title)
    table.add_column("Started", justify="right", style="dim", no_wrap=True)
    table.add_column("Topic", style="cyan")
    table.add_column("Project")
    table.add_column("Tools")
    table.add_column("Calls", justify="right")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Cost (USD)", justify="right", style="green")
    table.add_column("Src", justify="center")

    for s in rows:
        table.add_row(
            s.started.strftime("%Y-%m-%d %H:%M"),
            s.topic,
            s.project or "—",
            ", ".join(s.tools),
            str(s.interactions),
            f"{s.total_tokens:,}",
            f"${s.cost_usd:,.4f}",
            "~est" if s.estimated else "exact",
        )
    console.print(table)
    if any(s.estimated for s in rows):
        console.print("[dim]~est = token counts estimated (tool doesn't report usage).[/dim]")


@app.command()
def pricing() -> None:
    """Show the pricing table behind every cost figure (USD per 1M tokens)."""
    service = Service()
    table = Table(title="Model Pricing (USD per 1M tokens)")
    table.add_column("Model", style="cyan")
    table.add_column("From", justify="right", style="dim")
    table.add_column("Input", justify="right")
    table.add_column("Output", justify="right")
    table.add_column("Cache Read", justify="right")
    table.add_column("Cache Write", justify="right")
    for p in service.pricing():
        table.add_row(
            p.model,
            p.effective_from,
            f"${p.input}",
            f"${p.output}",
            f"${p.cache_read}",
            f"${p.cache_write}",
        )
    console.print(table)
    console.print("[dim]cost = (input x in + output x out + cache_read x cr + ...) / 1e6[/dim]")


@app.command()
def budget() -> None:
    """Show spend so far this day/week/month against your configured limits.

    Set limits in ``~/.config/agent-roi/config.toml`` under ``[budget]`` (or in
    the web Settings page): daily_usd, weekly_usd, monthly_usd.
    """
    service = Service()
    status = service.budget_status()
    table = Table(title="Budget")
    table.add_column("Period", style="cyan")
    table.add_column("Since", justify="right", style="dim")
    table.add_column("Spent (USD)", justify="right", style="green")
    table.add_column("Limit (USD)", justify="right")
    table.add_column("Used", justify="right")
    table.add_column("Status", justify="center")

    for p in status.periods:
        if p.limit_usd is None:
            limit, used, state = "—", "—", "[dim]no budget[/dim]"
        else:
            limit = f"${p.limit_usd:,.2f}"
            used = f"{p.pct:.0f}%" if p.pct is not None else "—"
            state = "[red]OVER[/red]" if p.over else "[green]ok[/green]"
        table.add_row(
            p.period.capitalize(),
            str(p.start.date()),
            f"${p.spent_usd:,.4f}",
            limit,
            used,
            state,
        )
    console.print(table)
    if status.any_over:
        console.print("[red]⚠ You are over budget for at least one period.[/red]")
    if all(p.limit_usd is None for p in status.periods):
        console.print(
            "[dim]No budgets set. Add [budget] daily_usd/weekly_usd/monthly_usd to config.[/dim]"
        )


@app.command()
def doctor() -> None:
    """Show which tools were detected, where Agent-ROI looked, and what it found."""
    service = Service()
    console.print(f"[bold]Platform:[/bold] {platform_label()}")
    table = Table(title="Data Sources")
    table.add_column("Tool", style="cyan")
    table.add_column("Detected", justify="center")
    table.add_column("Log Files", justify="right")
    table.add_column("Interactions", justify="right")
    table.add_column("Cost (USD)", justify="right", style="green")
    table.add_column("Notes")
    for s in service.sources():
        table.add_row(
            s.name,
            "[green]yes[/green]" if s.available else "[red]no[/red]",
            str(s.log_files),
            f"{s.interactions:,}",
            f"${s.cost_usd:,.2f}",
            s.note,
        )
    console.print(table)
    for s in service.sources():
        if s.search_paths:
            console.print(f"[dim]{s.name} searched:[/dim] {', '.join(s.search_paths)}")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host."),
    port: int = typer.Option(8000, help="Bind port."),
) -> None:
    """Run the REST API (and serve the built web UI if present)."""
    # Imported lazily: uvicorn (+ its event-loop machinery) is a heavy import we
    # only need for `serve`, so keeping it out of module scope keeps every other
    # command's startup fast. This is the one deliberate in-function import.
    import uvicorn

    uvicorn.run("agent_roi.api.app:create_app", host=host, port=port, factory=True)


PACKAGE_NAME = "agent-roi-tracker"


@app.command()
def version() -> None:
    """Show the installed Agent-ROI version."""
    console.print(f"agent-roi {__version__}")


def _latest_pypi_version() -> str | None:
    """Return the newest version of the package on PyPI, or None if unreachable."""
    url = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
            data = json.load(resp)
        return str(data["info"]["version"])
    except Exception:
        return None


def _installed_version() -> str | None:
    """Read the freshly-installed version by querying the package metadata on disk.

    The current process still has the old version imported, so we shell out to a
    fresh interpreter to read the up-to-date installed distribution metadata.
    """
    try:
        out = subprocess.run(
            [
                sys.executable,
                "-c",
                f"from importlib.metadata import version;print(version('{PACKAGE_NAME}'))",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    version = out.stdout.strip()
    return version or None


def _installed_via_uv_tool() -> bool:
    """True if agent-roi is managed by `uv tool` (vs a plain pip/uv pip install)."""
    if shutil.which("uv") is None:
        return False
    try:
        out = subprocess.run(
            ["uv", "tool", "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=15,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return PACKAGE_NAME in out.stdout


@app.command()
def update(
    check: bool = typer.Option(
        False, "--check", help="Only check for a newer version; don't install it."
    ),
    pre: bool = typer.Option(False, "--pre", help="Include pre-release versions."),
) -> None:
    """Upgrade Agent-ROI to the latest release on PyPI."""
    console.print(f"Installed: [bold]{__version__}[/bold]")

    latest = _latest_pypi_version()
    if latest is None:
        console.print("[yellow]Could not reach PyPI to check for updates.[/yellow]")
    else:
        console.print(f"Latest on PyPI: [bold]{latest}[/bold]")
        if not pre and latest == __version__:
            console.print("[green]You're already on the latest version.[/green]")
            return

    if check:
        return

    if _installed_via_uv_tool():
        cmd = ["uv", "tool", "install", "--upgrade", "--force", PACKAGE_NAME]
    else:
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", PACKAGE_NAME]
    if pre:
        cmd.append("--prerelease=allow" if cmd[0] == "uv" else "--pre")

    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
    with console.status("Updating Agent-ROI..."):
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    if result.returncode != 0:
        console.print("[red]Update failed:[/red]")
        console.print((result.stderr or result.stdout or "unknown error").strip())
        raise typer.Exit(1)

    new_version = _installed_version() or latest or "?"
    if new_version == __version__:
        console.print(f"[green]Already up to date at {__version__}.[/green]")
    else:
        console.print(f"[green]Updated {__version__} → [bold]{new_version}[/bold].[/green]")


@app.command(name="mcp-cost")
def mcp_cost(
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip the confirmation prompt and probe immediately."
    ),
) -> None:
    """Estimate each MCP server's per-turn token overhead (its tool schemas).

    This is opt-in and has side effects: it launches each configured stdio MCP
    server to ask for its tool list. Servers are read from Claude Code's
    ``~/.claude.json``; non-stdio servers are skipped (probing them would make
    network calls).
    """
    from agent_roi.mcp import load_mcp_servers, probe_servers

    servers = load_mcp_servers()
    if not servers:
        console.print(
            "[yellow]No MCP servers found in ~/.claude.json.[/yellow]\n"
            "[dim]VS Code MCP servers are registered by extensions and have no "
            "static command to probe.[/dim]"
        )
        return

    names = ", ".join(servers)
    console.print(
        f"[bold]This will launch {len(servers)} MCP server(s) to read their tool "
        f"definitions:[/bold] {names}"
    )
    if not yes and not typer.confirm("Probe them now?", default=False):
        console.print("[dim]Aborted.[/dim]")
        return

    with console.status("Probing MCP servers..."):
        results = probe_servers(servers)

    table = Table(title="MCP Schema Overhead (estimated tokens per turn)")
    table.add_column("Server", style="cyan", no_wrap=True)
    table.add_column("Transport", justify="center")
    table.add_column("Tools", justify="right")
    table.add_column("Est. tokens/turn", justify="right", style="green")
    table.add_column("Note", style="dim")

    total = 0
    for r in results:
        total += r.est_tokens
        table.add_row(
            r.name,
            r.transport,
            str(r.tools) if r.ok else "—",
            f"~{r.est_tokens:,}" if r.ok else "—",
            "" if r.ok else (r.error or ""),
        )
    if len([r for r in results if r.ok]) > 1:
        table.add_section()
        table.add_row("Total", "", "", f"~{total:,}", "")
    console.print(table)
    console.print(
        "[dim]Estimated from each tool's JSON schema; sent once per session and "
        "usually cache-written. Actual cost depends on the model's tokenizer.[/dim]"
    )


if __name__ == "__main__":
    app()
