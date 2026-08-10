"""Simple CLI for the EDD course: setup, workshop steps, and observability."""

import os
import shutil
import subprocess
from pathlib import Path

import typer
from InquirerPy import inquirer

app = typer.Typer(help="O'Reilly EDD course CLI", no_args_is_help=True)

LMS = Path.home() / ".lmstudio" / "bin" / "lms"
MODEL = "meta/muse-glimmer"
WORKSHOP = Path(__file__).parent / "workshop"
OBS_UI = "http://localhost:6006"


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


def _select_provider() -> str:
    """Prompt the user to pick a provider via an interactive dropdown."""
    return inquirer.select(
        message="Select provider:",
        choices=["lmstudio", "google"],
        default="google",
    ).execute()


@app.command()
def setup() -> None:
    """Install deps and prepare the selected provider."""
    _require("uv")
    _run("uv", "sync")

    provider = _select_provider()
    if provider == "google":
        typer.echo("Using Google provider - no local model needed.")
        return

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
def step(number: int = typer.Argument(..., help="Workshop step 1-4")) -> None:
    """Run a workshop step."""
    scripts = {
        1: "step1_evals.py",
        2: "step2_improver.py",
        3: "step3_ci_pipeline.py",
        4: "step4_production.py",
    }
    script = scripts.get(number)
    if script is None:
        raise typer.BadParameter("step must be 1-4")
    provider = _select_provider()
    _run_with_provider(provider, "uv", "run", str(WORKSHOP / script))


@app.command()
def obs() -> None:
    """Start Phoenix and open the UI."""
    _require("docker")
    _run("docker", "compose", "up", "-d")
    _run("open", OBS_UI)


@app.command()
def obs_down() -> None:
    """Stop the observability stack."""
    _run("docker", "compose", "down")


if __name__ == "__main__":
    app()