"""Simple CLI for the EDD course: setup, workshop steps, and observability."""

import os
import shutil
import subprocess
from pathlib import Path

import typer

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


def _using_google() -> bool:
    return os.environ.get("PROVIDER", "lmstudio") == "google"


@app.command()
def setup() -> None:
    """Install deps; start the model server and load the model (skipped for Google)."""
    _require("uv")
    _run("uv", "sync")

    if _using_google():
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
            "Switch to Google instead:\n"
            "    PROVIDER=google edd setup\n"
            "    PROVIDER=google edd run"
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
    _run("uv", "run", str(WORKSHOP / script))


@app.command()
def run() -> None:
    """Start Phoenix, run a traced inference, and open the UI."""
    _require("docker")
    _run("docker", "compose", "up", "-d")
    _run("uv", "run", "src/oreilly_edd_course/observability.py")
    _run("open", OBS_UI)


@app.command()
def obs_down() -> None:
    """Stop the observability stack."""
    _run("docker", "compose", "down")


if __name__ == "__main__":
    app()