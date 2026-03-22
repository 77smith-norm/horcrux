"""Verbatim copy transform."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CopyTransform:
    """Return the text unchanged."""

    name: str = "copy"

    def apply(self, text: str) -> str:
        """Return the source text without modification."""
        return text
