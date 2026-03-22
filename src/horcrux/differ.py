"""Structural diff between current output_dir and freshly-rendered files."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

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


@dataclass(frozen=True)
class ManagedFileDiff:
    """Rendered file compared against the current output directory."""

    file: DiffusedFile
    status: Literal["new", "changed", "unchanged"]
    existing_text: str | None = None

    @property
    def path(self) -> Path:
        return self.file.relative_path

    @property
    def rendered_text(self) -> str:
        return self.file.content


@dataclass(frozen=True)
class DiffReport:
    """Comparison between rendered files and an output directory."""

    output_dir: Path
    files: tuple[ManagedFileDiff, ...]
    extra_paths: tuple[Path, ...] = ()

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def new_files(self) -> tuple[ManagedFileDiff, ...]:
        return tuple(file for file in self.files if file.status == "new")

    @property
    def changed_files(self) -> tuple[ManagedFileDiff, ...]:
        return tuple(file for file in self.files if file.status == "changed")

    @property
    def unchanged_files(self) -> tuple[ManagedFileDiff, ...]:
        return tuple(file for file in self.files if file.status == "unchanged")


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
    report = build_diff_report(profile.output_dir, rendered_files)

    printer.print(f"\nDiff: {profile.name} ({profile.harness}/{profile.os})", style="bold")
    printer.print(f"Output dir: {report.output_dir}")
    printer.print()
    _print_diff_report(printer, report, verbose=verbose, show_match_message=True)
    printer.print()


def run_diffuse_preview(
    profile: AgentProfile,
    rendered_files: list[DiffusedFile],
    *,
    source_root: Path,
    runtime_workspace: Path,
) -> None:
    """Show a dry-run preview of what diffuse would write."""
    printer = _Printer()
    report = build_diff_report(profile.output_dir, rendered_files)

    printer.print(f"Dry run: {profile.name} ({profile.harness}/{profile.os})", style="bold")
    printer.print(f"Source root: {source_root}")
    printer.print(f"Output dir: {report.output_dir}")
    printer.print(f"Runtime workspace: {runtime_workspace}")
    printer.print()
    _print_diff_report(printer, report, verbose=False, show_match_message=False)
    printer.print(
        (
            f"Would write {report.total_files} files "
            f"({len(report.unchanged_files)} unchanged, {len(report.new_files)} new)."
        ),
        style="bold",
    )
    printer.print()


def build_diff_report(output_dir: Path, rendered_files: list[DiffusedFile]) -> DiffReport:
    """Compare rendered files against an output directory."""
    existing_paths = (
        {
            path.relative_to(output_dir)
            for path in output_dir.rglob("*")
            if path.is_file() and not path.name.startswith(".")
        }
        if output_dir.exists()
        else set()
    )
    rendered_paths = {file.relative_path for file in rendered_files}

    file_diffs: list[ManagedFileDiff] = []
    for file in rendered_files:
        destination = output_dir / file.relative_path
        if not destination.exists():
            file_diffs.append(ManagedFileDiff(file=file, status="new"))
            continue

        existing_text = destination.read_text(encoding="utf-8")
        status: Literal["new", "changed", "unchanged"] = "unchanged"
        if existing_text != file.content:
            status = "changed"
        file_diffs.append(
            ManagedFileDiff(
                file=file,
                status=status,
                existing_text=existing_text,
            )
        )

    return DiffReport(
        output_dir=output_dir,
        files=tuple(file_diffs),
        extra_paths=tuple(sorted(existing_paths - rendered_paths)),
    )


def _print_diff_report(
    printer: _Printer,
    report: DiffReport,
    *,
    verbose: bool,
    show_match_message: bool,
) -> None:
    if report.new_files:
        printer.print("  New files (would be written):", style="green")
        for file in report.new_files:
            printer.print(f"    + {file.path}", style="green")
    if report.extra_paths:
        printer.print("  Extra files (not managed by Horcrux):", style="yellow")
        for path in report.extra_paths:
            printer.print(f"    ? {path}", style="yellow")
    if report.changed_files:
        printer.print("  Changed files:", style="cyan")
        for file in report.changed_files:
            printer.print(f"    ~ {file.path}", style="cyan")
            existing_text = file.existing_text or ""
            _print_section_summary(printer, existing_text, file.rendered_text)
            if verbose:
                diff = difflib.unified_diff(
                    existing_text.splitlines(keepends=True),
                    file.rendered_text.splitlines(keepends=True),
                    fromfile=f"current/{file.path}",
                    tofile=f"rendered/{file.path}",
                    n=3,
                )
                for line in diff:
                    printer.print(
                        "      " + line.rstrip("\n"),
                        style=_diff_line_style(line),
                    )
    if report.unchanged_files:
        printer.print(f"  Unchanged: {len(report.unchanged_files)} file(s)")
    if show_match_message and not report.new_files and not report.changed_files:
        printer.print("  Output dir matches rendered output.", style="green")


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
