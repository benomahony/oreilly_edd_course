"""Simple CLI for the EDD course: run the worked example and open its telemetry."""

import asyncio
import json
import os
from pathlib import Path
from typing import Annotated, cast
import uvicorn

import typer

app = typer.Typer(
    help="Eval-Driven Development for Reliable Agents (O'Reilly course)",
    no_args_is_help=True,
)

LOGFIRE_CREDENTIALS = Path(".logfire") / "logfire_credentials.json"


@app.command()
def run(
    fresh: Annotated[
        bool, typer.Option("--fresh", help="Reset the agent to the naive prompt first.")
    ] = False,
) -> None:
    """Run the evals and the improvement loop against the current agent."""
    if not os.environ.get("GOOGLE_API_KEY"):
        raise typer.BadParameter("Set GOOGLE_API_KEY first.")
    # Imported here: example.py builds its agents at import time, so check the key first.
    from oreilly_edd_course.example import main
    from oreilly_edd_course.telemetry import init_telemetry

    init_telemetry(service_name="meeting-todos")
    asyncio.run(main(fresh=fresh))


@app.command()
def obs() -> None:
    """Open your Logfire project (traces and online eval results)."""
    if not LOGFIRE_CREDENTIALS.exists():
        raise typer.BadParameter(
            "No Logfire project yet: uv run logfire auth && uv run logfire projects new"
        )
    credentials = cast(dict[str, str], json.loads(LOGFIRE_CREDENTIALS.read_text()))
    project_url = credentials["project_url"]
    _ = typer.launch(project_url)


@app.command()
def web() -> None:
    """Run the agent as a web frontend."""
    if not os.environ.get("GOOGLE_API_KEY"):
        raise typer.BadParameter("Set GOOGLE_API_KEY first.")
    # Imported here: example.py builds its agents at import time, so check the key first.
    from oreilly_edd_course.example import extractor_agent
    from oreilly_edd_course.telemetry import init_telemetry

    init_telemetry(service_name="meeting-todos")
    uvicorn.run(extractor_agent.to_web())


if __name__ == "__main__":
    app()
