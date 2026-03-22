"""Interactive fix application for horcrux check issues."""

from __future__ import annotations

import typer

from horcrux.check import CheckReport


def run_fix(report: CheckReport) -> int:
    """Walk through fixable issues interactively. Returns count of applied fixes."""
    fixable = [i for i in report.issues if i.suggestion and i.line is not None]

    if not fixable:
        typer.echo("No auto-fixable issues found.")
        return 0

    applied = 0
    for issue in fixable:
        typer.echo(f"\n{issue}")
        if not typer.confirm("  Apply this suggestion?", default=False):
            continue

        full_path = report.output_dir / issue.file
        lines = full_path.read_text(encoding="utf-8").splitlines(keepends=True)
        line_idx = (issue.line or 1) - 1

        typer.echo(f"\n  Current line {issue.line}:")
        typer.echo(f"    {lines[line_idx].rstrip()}")
        new_text = typer.prompt("  Replacement text (empty to skip)")
        if not new_text:
            continue

        lines[line_idx] = new_text + "\n"
        full_path.write_text("".join(lines), encoding="utf-8")
        typer.echo("  ✓ Applied.")
        applied += 1

    return applied
