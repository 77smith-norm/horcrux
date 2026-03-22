"""Structural diff between current output_dir and freshly-rendered files."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path

import typer

from horcrux.profile import AgentProfile
from horcrux.targets.openclaw import DiffusedFile

try:
    from rich.console import Console
except ImportError:  # pragma: no cover - typer pulls rich in normal installs
    Console = None

_HEADING_PATTERN = re.compile(r"^(#{1,6}\s+.+)$")


@dataclass(frozen=True)
class SectionSummary:
    """Heading-level summary for a changed markdown file."""

    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    modified: tuple[str, ...] = ()

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed or self.modified)


class _Printer:
    """Small output shim that uses rich styling when available."""

    def __init__(self) -> None:
        self._console = Console() if Console is not None else None

    def print(self, text: str = "", *, style: str | None = None, nl: bool = True) -> None:
        if self._console is not None:
            self._console.print(text, style=style, end="\n" if nl else "", highlight=False)
            return
        typer.echo(text, nl=nl)


def run_diff(
    profile: AgentProfile,
    rendered_files: list[DiffusedFile],
    *,
    verbose: bool = False,
) -> None:
    """Compare rendered files against what's currently in output_dir."""
    printer = _Printer()
    output_dir = profile.output_dir
    rendered_map = {f.relative_path: f for f in rendered_files}
    existing_paths = {
        p.relative_to(output_dir)
        for p in output_dir.rglob("*")
        if p.is_file() and not p.name.startswith(".")
    } if output_dir.exists() else set()

    rendered_paths = set(rendered_map.keys())
    only_in_rendered = rendered_paths - existing_paths
    only_in_output = existing_paths - rendered_paths
    in_both = rendered_paths & existing_paths

    changed: list[Path] = []
    unchanged: list[Path] = []

    for path in sorted(in_both):
        existing_text = (output_dir / path).read_text(encoding="utf-8")
        rendered_text = rendered_map[path].content
        if existing_text == rendered_text:
            unchanged.append(path)
        else:
            changed.append(path)

    # Summary header
    printer.print(f"\nDiff: {profile.name} ({profile.harness}/{profile.os})", style="bold")
    printer.print(f"Output dir: {output_dir}")
    printer.print()

    if only_in_rendered:
        printer.print("  New files (would be written):", style="green")
        for p in sorted(only_in_rendered):
            printer.print(f"    + {p}", style="green")
    if only_in_output:
        printer.print("  Extra files (not managed by Horcrux):", style="yellow")
        for p in sorted(only_in_output):
            printer.print(f"    ? {p}", style="yellow")
    if changed:
        printer.print("  Changed files:", style="cyan")
        for p in sorted(changed):
            printer.print(f"    ~ {p}", style="cyan")
            existing_text = (output_dir / p).read_text(encoding="utf-8")
            rendered_text = rendered_map[p].content
            _print_section_summary(printer, existing_text, rendered_text)
            if verbose:
                diff = difflib.unified_diff(
                    existing_text.splitlines(keepends=True),
                    rendered_text.splitlines(keepends=True),
                    fromfile=f"current/{p}",
                    tofile=f"rendered/{p}",
                    n=3,
                )
                for line in diff:
                    printer.print(
                        "      " + line.rstrip("\n"),
                        style=_diff_line_style(line),
                    )
    if unchanged:
        printer.print(f"  Unchanged: {len(unchanged)} file(s)")

    if not only_in_rendered and not changed:
        printer.print("  Output dir matches rendered output.", style="green")
    printer.print()


def _print_section_summary(printer: _Printer, existing_text: str, rendered_text: str) -> None:
    summary = _summarize_sections(existing_text, rendered_text)
    if summary.has_changes:
        _print_section_group(printer, "Added sections", summary.added, "+", "green")
        _print_section_group(printer, "Removed sections", summary.removed, "-", "red")
        _print_section_group(printer, "Changed sections", summary.modified, "~", "yellow")
        return
    printer.print("      ~ Content changed (no heading-level summary available).", style="yellow")


def _print_section_group(
    printer: _Printer,
    label: str,
    headings: tuple[str, ...],
    prefix: str,
    style: str,
) -> None:
    if not headings:
        return
    printer.print(f"      {label}:", style=style)
    for heading in headings:
        printer.print(f"        {prefix} {heading}", style=style)


def _summarize_sections(existing_text: str, rendered_text: str) -> SectionSummary:
    existing_sections = _extract_sections(existing_text)
    rendered_sections = _extract_sections(rendered_text)

    existing_headings = set(existing_sections)
    rendered_headings = set(rendered_sections)

    return SectionSummary(
        added=tuple(sorted(rendered_headings - existing_headings)),
        removed=tuple(sorted(existing_headings - rendered_headings)),
        modified=tuple(sorted(
            heading
            for heading in existing_headings & rendered_headings
            if existing_sections[heading] != rendered_sections[heading]
        )),
    )


def _extract_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None

    for line in text.splitlines():
        heading_match = _HEADING_PATTERN.match(line)
        if heading_match:
            current_heading = heading_match.group(1).strip()
            sections[current_heading] = []
            continue
        if current_heading is not None:
            sections[current_heading].append(line.rstrip())

    return {
        heading: "\n".join(body).rstrip()
        for heading, body in sections.items()
    }


def _diff_line_style(line: str) -> str | None:
    if line.startswith(("+++", "+")) and not line.startswith("+++"):
        return "green"
    if line.startswith("---"):
        return "red"
    if line.startswith("-") and not line.startswith("---"):
        return "red"
    if line.startswith("@@"):
        return "cyan"
    return None
