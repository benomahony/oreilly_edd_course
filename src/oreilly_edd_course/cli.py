"""Simple CLI for the EDD course: setup, workshop steps, and observability."""

import os
import shutil
import subprocess
from pathlib import Path

import typer
from InquirerPy import inquirer

from oreilly_edd_course.providers import Settings

app = typer.Typer(help="O'Reilly EDD course CLI", no_args_is_help=True)

LMS = Path.home() / ".lmstudio" / "bin" / "lms"
MODEL = "meta/muse-glimmer"
WORKSHOP = Path(__file__).parent / "workshop"
OBS_UI = "http://localhost:6006"
CONFIG = Path(".env")

EXERCISES = [
    "Structured extraction & evals",
    "Self-improving agent",
    "CI pipeline evals",
    "Production evals",
]
EXERCISE_SCRIPTS = {
    "Structured extraction & evals": "step1_evals.py",
    "Self-improving agent": "step2_improver.py",
    "CI pipeline evals": "step3_ci_pipeline.py",
    "Production evals": "step4_production.py",
}

SOLUTIONS = [
    "Structured extraction & evals",
    "Self-improving agent",
    "CI pipeline evals",
    "Production evals",
]
SOLUTION_SCRIPTS = {
    "Structured extraction & evals": "step1_evals_solution.py",
    "Self-improving agent": "step2_improver_solution.py",
    "CI pipeline evals": "step3_ci_pipeline_solution.py",
    "Production evals": "step4_production_solution.py",
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
    """Install deps, configure the provider, and start Phoenix."""
    _require("uv")
    _run("uv", "sync")

    provider = inquirer.select(
        message="Select provider:", choices=["lmstudio", "google"], default="google"
    ).execute()
    if provider == "google":
        _check_google()
    _set_provider(provider)
    typer.echo(f"Configured provider: {provider}")

    _require("docker")
    _run("docker", "compose", "up", "-d")
    typer.echo(f"Phoenix running at {OBS_UI}")

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
def solutions() -> None:
    """Run a workshop solution with the configured provider."""
    choice = inquirer.select(
        message="Select solution:", choices=SOLUTIONS, default=SOLUTIONS[0]
    ).execute()
    script = SOLUTION_SCRIPTS[choice]
    provider = _provider()
    if provider == "google":
        _check_google()
    typer.echo(f"Running {script} with {provider} provider...")
    _run_with_provider(provider, "uv", "run", str(WORKSHOP / script))


@app.command()
def exercise() -> None:
    """Run a workshop exercise with the configured provider."""
    choice = inquirer.select(
        message="Select exercise:", choices=EXERCISES, default=EXERCISES[0]
    ).execute()
    script = EXERCISE_SCRIPTS[choice]
    provider = _provider()
    if provider == "google":
        _check_google()
    typer.echo(f"Running {script} with {provider} provider...")
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