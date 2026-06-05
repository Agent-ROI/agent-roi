"""Agent-ROI command-line interface."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from agent_roi.core.service import Service

app = typer.Typer(
    name="agent-roi",
    help="Track the cost, usage, and ROI of your AI coding agents across every tool.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.command()
def ingest() -> None:
    """Collect interactions from all enabled tools into the local database."""
    service = Service()
    with console.status("Ingesting logs..."):
        count = service.ingest()
    console.print(f"[green]Ingested {count} interactions.[/green]")


@app.command()
def classify(
    limit: int = typer.Option(0, help="Max interactions to classify (0 = all)."),
) -> None:
    """Assign a topic to interactions that don't have one yet."""
    service = Service()
    with console.status("Classifying topics..."):
        count = service.classify(limit=limit or None)
    console.print(f"[green]Classified {count} interactions.[/green]")


@app.command()
def report(
    by: str = typer.Option("topic", help="Grouping dimension. Currently: 'topic'."),
) -> None:
    """Show a token/cost breakdown."""
    if by != "topic":
        console.print(f"[red]Unsupported grouping: {by}[/red]")
        raise typer.Exit(1)

    service = Service()
    rollups = service.report_by_topic()
    if not rollups:
        console.print("[yellow]No data yet. Run 'agent-roi ingest' first.[/yellow]")
        return

    table = Table(title="Token Cost by Topic")
    table.add_column("Topic", style="cyan", no_wrap=True)
    table.add_column("Interactions", justify="right")
    table.add_column("Total Tokens", justify="right")
    table.add_column("Cost (USD)", justify="right", style="green")

    for r in rollups:
        table.add_row(
            r.topic,
            str(r.interactions),
            f"{r.total_tokens:,}",
            f"${r.cost_usd:,.4f}",
        )
    console.print(table)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host."),
    port: int = typer.Option(8000, help="Bind port."),
) -> None:
    """Run the REST API (and serve the built web UI if present)."""
    import uvicorn

    uvicorn.run("agent_roi.api.app:create_app", host=host, port=port, factory=True)


if __name__ == "__main__":
    app()
