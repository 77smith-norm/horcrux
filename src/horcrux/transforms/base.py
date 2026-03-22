"""Transform protocol."""

from __future__ import annotations

from typing import Protocol


class Transform(Protocol):
    """A text transform applied during diffusion."""

    name: str

    def apply(self, text: str) -> str:
        """Return transformed text."""

