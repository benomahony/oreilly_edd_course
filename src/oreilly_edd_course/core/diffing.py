from difflib import SequenceMatcher
from typing import Literal

from rich.text import Text


def diff_text(expected: str, actual: str, mode: Literal["word", "char"] = "word") -> Text:
    a = expected.split() if mode == "word" else list(expected)
    b = actual.split() if mode == "word" else list(actual)
    sep = " " if mode == "word" else ""
    matcher = SequenceMatcher(None, a, b)
    text = Text()
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            text.append(sep.join(a[i1:i2]) + sep)
        elif tag == "delete":
            text.append(sep.join(a[i1:i2]) + sep, style="red strike")
        elif tag == "insert":
            text.append(sep.join(b[j1:j2]) + sep, style="green")
        elif tag == "replace":
            text.append(sep.join(a[i1:i2]) + sep, style="red strike")
            text.append(sep.join(b[j1:j2]) + sep, style="green")
    return text
