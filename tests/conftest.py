from __future__ import annotations

import re
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def fixture_path(*parts: str) -> Path:
    return FIXTURES.joinpath(*parts)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text (for CI-safe output assertions)."""
    return _ANSI_ESCAPE.sub("", text)

