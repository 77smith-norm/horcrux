"""Section and line filtering transform."""

from __future__ import annotations

from dataclasses import dataclass, field
import re


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)(?:\s+#+\s*)?$")


@dataclass(frozen=True)
class FilterTransform:
    """Strip markdown sections or lines matching configured rules."""

    strip_headings: tuple[str, ...] = ()
    drop_if_contains: tuple[str, ...] = field(default_factory=tuple)
    name: str = "filter"

    def apply(self, text: str) -> str:
        lines = text.splitlines(keepends=True)
        filtered: list[str] = []
        skip_level: int | None = None

        for line in lines:
            match = HEADING_RE.match(line)
            if skip_level is not None:
                if match is None or len(match.group(1)) > skip_level:
                    continue
                skip_level = None

            if match is not None:
                title = match.group(2).strip()
                if title in self.strip_headings:
                    skip_level = len(match.group(1))
                    continue

            if any(fragment in line for fragment in self.drop_if_contains):
                continue

            filtered.append(line)

        return "".join(filtered)

