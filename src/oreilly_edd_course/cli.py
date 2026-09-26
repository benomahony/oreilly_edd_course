"""Simple CLI for the EDD course: run the worked example and open its telemetry."""

import json
import os
import subprocess
from pathlib import Path

import typer

from oreilly_edd_course.providers import Settings

app = typer.Typer(help="Eval-Driven Development for Reliable Agents (O'Reilly course)", no_args_is_help=True)

LOGFIRE_CREDENTIALS = Path(".logfire") / "logfire_credentials.json"
EXAMPLE = Path(__file__).parent / "example.py"


@app.command()
def run(
    fresh: bool = typer.Option(False, "--fresh", help="Reset the agent to the naive prompt first."),
) -> None:
    """Run the evals and the improvement loop against the current agent."""
    provider = Settings().provider
    if provider == "google" and not os.environ.get("GOOGLE_API_KEY"):
        raise typer.BadParameter("Set GOOGLE_API_KEY first (or PROVIDER=lmstudio for a local model).")
    typer.echo(f"Running {EXAMPLE.name} with {provider} provider...")
    subprocess.run(["uv", "run", str(EXAMPLE), *(["--fresh"] if fresh else [])], check=True)


@app.command()
def obs() -> None:
    """Open your Logfire project (traces and online eval results)."""
    if not LOGFIRE_CREDENTIALS.exists():
        raise typer.BadParameter("No Logfire project yet: uv run logfire auth && uv run logfire projects new")
    subprocess.run(["open", json.loads(LOGFIRE_CREDENTIALS.read_text())["project_url"]], check=True)


if __name__ == "__main__":
    app()
