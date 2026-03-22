"""Token substitution transform."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubstituteTransform:
    """Apply ordered string substitutions."""

    replacements: tuple[tuple[str, str], ...]
    name: str = "substitute"

    def apply(self, text: str) -> str:
        rendered = text
        for old, new in self.replacements:
            if not old:
                raise ValueError("substitution source must not be empty")
            rendered = rendered.replace(old, new)
        return rendered

