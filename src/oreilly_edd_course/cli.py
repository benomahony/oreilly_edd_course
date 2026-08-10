"""Simple CLI for the EDD course: setup, workshop steps, and observability."""

import subprocess
from pathlib import Path

import typer

app = typer.Typer(help="O'Reilly EDD course CLI")

LMS = Path.home() / ".lmstudio" / "bin" / "lms"
MODEL = "meta/muse-glimmer"
WORKSHOP = Path(__file__).parent / "workshop"
OBS_UI = "http://localhost:6006"


def _run(*cmd: str) -> None:
    subprocess.run(cmd, check=True)


@app.command()
def setup() -> None:
    """Install deps, start the model server, and load the model."""
    _run("uv", "sync")
    _run(str(LMS), "server", "start")
    _run(str(LMS), "load", MODEL)


@app.command()
def infer() -> None:
    """Smoke-test inference against the configured provider."""
    _run("uv", "run", "src/oreilly_edd_course/inference.py")


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
    _run("docker", "compose", "up", "-d")
    _run("uv", "run", "src/oreilly_edd_course/observability.py")
    _run("open", OBS_UI)


@app.command()
def obs_down() -> None:
    """Stop the observability stack."""
    _run("docker", "compose", "down")


if __name__ == "__main__":
    app()