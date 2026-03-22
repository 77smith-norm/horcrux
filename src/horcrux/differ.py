"""Structural diff between current output_dir and freshly-rendered files."""

from __future__ import annotations

import difflib
from pathlib import Path

import typer

from horcrux.profile import AgentProfile
from horcrux.targets.openclaw import DiffusedFile


def run_diff(
    profile: AgentProfile,
    rendered_files: list[DiffusedFile],
    *,
    verbose: bool = False,
) -> None:
    """Compare rendered files against what's currently in output_dir."""
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
    typer.echo(f"\nDiff: {profile.name} ({profile.harness}/{profile.os})")
    typer.echo(f"Output dir: {output_dir}\n")

    if only_in_rendered:
        typer.echo("  New files (would be written):")
        for p in sorted(only_in_rendered):
            typer.echo(f"    + {p}")
    if only_in_output:
        typer.echo("  Extra files (not managed by Horcrux):")
        for p in sorted(only_in_output):
            typer.echo(f"    ? {p}")
    if changed:
        typer.echo("  Changed files:")
        for p in sorted(changed):
            typer.echo(f"    ~ {p}")
            if verbose:
                existing_text = (output_dir / p).read_text(encoding="utf-8")
                rendered_text = rendered_map[p].content
                diff = difflib.unified_diff(
                    existing_text.splitlines(keepends=True),
                    rendered_text.splitlines(keepends=True),
                    fromfile=f"current/{p}",
                    tofile=f"rendered/{p}",
                    n=3,
                )
                for line in diff:
                    typer.echo("      " + line, nl=False)
    if unchanged:
        typer.echo(f"  Unchanged: {len(unchanged)} file(s)")

    if not only_in_rendered and not changed:
        typer.echo("  ✓ Output dir matches rendered output.")
    typer.echo("")
