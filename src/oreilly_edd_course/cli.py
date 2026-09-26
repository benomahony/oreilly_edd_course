"""Simple CLI for the EDD course: setup, the worked example, and observability."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import typer
from InquirerPy import inquirer


app = typer.Typer(help="Eval-Driven Development for Reliable Agents (O'Reilly course)", no_args_is_help=True)

LMS = Path.home() / ".lmstudio" / "bin" / "lms"
MODEL = "meta/muse-glimmer"
LOGFIRE_CREDENTIALS = Path(".logfire") / "logfire_credentials.json"
CONFIG = Path(".env")

EXAMPLE = Path(__file__).parent / "example.py"


def _require(name: str) -> None:
    """Fail with a clear message if a prerequisite is missing on PATH."""
    if shutil.which(name) is None:
        raise typer.BadParameter(f"Prerequisite '{name}' not found on PATH. Install it first.")


def _run(*cmd: str) -> None:
    subprocess.run(cmd, check=True)


def _run_with_provider(provider: str, *cmd: str) -> None:
    """Run a command with the selected provider set in its environment."""
    env = {**os.environ, "PROVIDER": provider}
    subprocess.run(cmd, check=True, env=env)


def _provider() -> str:
    """Read the configured provider from .env, defaulting to lmstudio."""
    if CONFIG.exists():
        for line in CONFIG.read_text().splitlines():
            if line.strip().startswith("PROVIDER="):
                return line.split("=", 1)[1].strip()
    return "lmstudio"


def _set_provider(provider: str) -> None:
    """Persist the provider to .env, preserving other settings."""
    lines = CONFIG.read_text().splitlines() if CONFIG.exists() else []
    lines = [ln for ln in lines if not ln.strip().startswith("PROVIDER=")]
    lines.append(f"PROVIDER={provider}")
    CONFIG.write_text("\n".join(lines) + "\n")


def _check_google() -> None:
    """Fail with a clear message if the Google key is missing."""
    if not os.environ.get("GOOGLE_API_KEY"):
        raise typer.BadParameter(
            "Google provider needs GOOGLE_API_KEY. Set it first:\n"
            "    export GOOGLE_API_KEY=your-key"
        )


@app.command()
def setup() -> None:
    """Install deps and configure the provider."""
    _require("uv")
    _run("uv", "sync")

    provider = inquirer.select(
        message="Select provider:", choices=["lmstudio", "google"], default="google"
    ).execute()
    if provider == "google":
        _check_google()
    _set_provider(provider)
    typer.echo(f"Configured provider: {provider}")

    if LOGFIRE_CREDENTIALS.exists():
        typer.echo("Logfire already configured:")
        _run("uv", "run", "logfire", "whoami")
    else:
        typer.echo("Log in to Logfire, then create (or pick) a project for this course.")
        _run("uv", "run", "logfire", "auth")
        _run("uv", "run", "logfire", "projects", "new")

    if provider == "lmstudio":
        if not LMS.exists():
            typer.echo(f"LM Studio CLI not found at {LMS}. Install LM Studio first.")
            raise typer.Exit(1)
        _run(str(LMS), "server", "start")
        try:
            _run(str(LMS), "load", MODEL)
        except subprocess.CalledProcessError:
            typer.echo(
                f"Couldn't load {MODEL} locally (likely insufficient memory).\n"
                "Re-run setup and pick Google instead."
            )
            raise typer.Exit(1)


@app.command()
def run(
    fresh: bool = typer.Option(False, "--fresh", help="Reset the agent to the naive prompt first."),
) -> None:
    """Run the evals and the improvement loop against the current agent."""
    provider = _provider()
    if provider == "google":
        _check_google()
    typer.echo(f"Running {EXAMPLE.name} with {provider} provider...")
    _run_with_provider(provider, "uv", "run", str(EXAMPLE), *(["--fresh"] if fresh else []))


@app.command()
def obs() -> None:
    """Open your Logfire project (traces and online eval results)."""
    if not LOGFIRE_CREDENTIALS.exists():
        raise typer.BadParameter("No Logfire project yet. Run `edd setup` first.")
    _run("open", json.loads(LOGFIRE_CREDENTIALS.read_text())["project_url"])


if __name__ == "__main__":
    app()