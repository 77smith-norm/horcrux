"""CLI entry point."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer

from horcrux.profile import AgentProfile, load_profile
from horcrux.registry import RegistryEntry, load_registry, save_registry, upsert_registry_entry
from horcrux.source import default_source_root, load_canonical_workspace
from horcrux.targets.hermes import HermesTarget
from horcrux.targets.openclaw import DiffusedFile, OpenClawTarget


app = typer.Typer(help="Diffuse agent identities into harness-specific workspaces.")


def _build_target(profile: AgentProfile) -> OpenClawTarget | HermesTarget:
    source = load_canonical_workspace()
    if profile.harness == "openclaw":
        return OpenClawTarget(profile, source)
    if profile.harness == "hermes":
        return HermesTarget(profile, source)
    raise typer.BadParameter(f"unsupported harness: {profile.harness}")


def _write_files(files: list[DiffusedFile], output_dir: Path, *, force: bool) -> None:
    for file in files:
        destination = output_dir / file.relative_path
        if destination.exists() and not force:
            raise typer.BadParameter(
                f"{destination} already exists. Re-run with --force to overwrite managed files."
            )
    for file in files:
        destination = output_dir / file.relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(file.content, encoding="utf-8")


def _format_diffusion_summary(
    profile: AgentProfile,
    files: list[DiffusedFile],
    runtime_workspace: Path,
    *,
    dry_run: bool,
) -> str:
    header = "Dry run" if dry_run else "Diffused"
    lines = [
        f"{header}: {profile.name} ({profile.harness}/{profile.os})",
        f"Source root: {default_source_root()}",
        f"Output dir: {profile.output_dir}",
        f"Runtime workspace: {runtime_workspace}",
        f"Files: {len(files)}",
        "",
    ]
    for file in files:
        source_label = str(file.source_path) if file.source_path is not None else "generated"
        transform_label = ", ".join(file.transforms)
        lines.append(f"- {file.relative_path} <- {source_label} [{transform_label}]")
    return "\n".join(lines)


@app.command()
def diffuse(
    profile_path: Path,
    dry_run: bool = typer.Option(False, "--dry-run", help="Render without writing files."),
    force: bool = typer.Option(False, "--force", help="Overwrite managed files."),
) -> None:
    """Diffuse a canonical workspace into a target agent workspace."""

    profile = load_profile(profile_path)
    target = _build_target(profile)
    files = target.render()
    runtime_workspace = getattr(target, "runtime_workspace", profile.output_dir)
    typer.echo(_format_diffusion_summary(profile, files, runtime_workspace, dry_run=dry_run))

    if dry_run:
        return

    _write_files(files, profile.output_dir, force=force)
    registry = load_registry()
    entry = RegistryEntry(
        name=profile.name,
        profile=profile_path.resolve(),
        output_dir=profile.output_dir,
        diffused_at=datetime.now(timezone.utc),
    )
    save_registry(upsert_registry_entry(registry, entry))


@app.command("init")
def init_profile(
    output: Path = typer.Option(None, "--output", "-o", help="Write profile to this path."),
) -> None:
    """Interview flow to generate an agent profile YAML."""
    from horcrux.init_flow import run_init_interview

    result = run_init_interview()
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result, encoding="utf-8")
        typer.echo(f"Profile written to {output}")
    else:
        typer.echo(result)


@app.command("diff")
def diff_agent(
    profile_path: Path,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full content diffs."),
) -> None:
    """Show structural diff between current output_dir and what diffuse would produce."""
    from horcrux.differ import run_diff

    profile = load_profile(profile_path)
    source = load_canonical_workspace()
    target = _build_target(profile)
    files = target.render()
    run_diff(profile, files, verbose=verbose)


@app.command("list")
def list_agents() -> None:
    """List registered horcrux agents."""

    registry = load_registry()
    if not registry.agents:
        typer.echo("No agents registered.")
        return

    for entry in registry.agents:
        typer.echo(f"{entry.name}\t{entry.output_dir}\t{entry.diffused_at.isoformat()}")
