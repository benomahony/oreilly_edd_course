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

STEPS = [
    "Step 1: Structured extraction & evals",
    "Step 2: Self-improving agent",
    "Step 3: CI pipeline evals",
    "Step 4: Production evals",
]
STEP_SCRIPTS = {
    "Step 1: Structured extraction & evals": "step1_evals.py",
    "Step 2: Self-improving agent": "step2_improver.py",
    "Step 3: CI pipeline evals": "step3_ci_pipeline.py",
    "Step 4: Production evals": "step4_production.py",
}


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
def step() -> None:
    """Run a workshop exercise."""
    choice = inquirer.select(message="Select exercise:", choices=STEPS, default=STEPS[0]).execute()
    script = STEP_SCRIPTS[choice]
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