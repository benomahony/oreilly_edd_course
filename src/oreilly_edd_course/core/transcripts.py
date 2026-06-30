from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_transcript(name: str) -> str:
    """Load a transcript by stem name, e.g. load_transcript("transcript1")."""
    filename = name if name.endswith(".txt") else f"{name}.txt"
    return (DATA_DIR / filename).read_text()
