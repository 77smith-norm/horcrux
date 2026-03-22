"""CLI entry point."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import typer

from horcrux.profile import AgentProfile, load_profile
from horcrux.registry import RegistryEntry, load_registry, save_registry, upsert_registry_entry
from horcrux.source import default_source_root, load_canonical_workspace
from horcrux.targets import BaseTarget, DiffusedFile, get_target

app = typer.Typer(help="Diffuse agent identities into harness-specific workspaces.")


def _build_target(profile: AgentProfile) -> BaseTarget:
    source = load_canonical_workspace()
    try:
        target_cls = get_target(profile.harness)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    return target_cls(profile=profile, source=source)


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
) -> str:
    lines = [
        f"Diffused: {profile.name} ({profile.harness}/{profile.os})",
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

    if dry_run:
        from horcrux.differ import run_diffuse_preview

        run_diffuse_preview(
            profile,
            files,
            source_root=default_source_root(),
            runtime_workspace=runtime_workspace,
        )
        return

    typer.echo(_format_diffusion_summary(profile, files, runtime_workspace))
    _write_files(files, profile.output_dir, force=force)
    registry = load_registry()
    entry = RegistryEntry(
        name=profile.name,
        profile=profile_path.resolve(),
        output_dir=profile.output_dir,
        diffused_at=datetime.now(UTC),
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
    target = _build_target(profile)
    files = target.render()
    run_diff(profile, files, verbose=verbose)


@app.command("check")
def check_agent(
    profile_path: Path,
    all_agents: bool = typer.Option(False, "--all", help="Check all registered agents."),
) -> None:
    """Check an agent's identity files for structural issues and tone drift."""
    from horcrux.check import run_structural_check

    if all_agents:
        registry = load_registry()
        if not registry.agents:
            typer.echo("No agents registered.")
            raise typer.Exit()
        for entry in registry.agents:
            report = run_structural_check(entry.output_dir, entry.name)
            typer.echo(str(report))
        return

    profile = load_profile(profile_path)
    report = run_structural_check(profile.output_dir, profile.name, harness=profile.harness)
    typer.echo(str(report))
    if report.errors:
        raise typer.Exit(code=1)


@app.command("fix")
def fix_agent(
    profile_path: Path,
    auto: bool = typer.Option(
        False,
        "--auto",
        help="Apply safe auto-fixes without interactive prompts.",
    ),
) -> None:
    """Interactively apply fix suggestions from `horcrux check`."""
    from horcrux.check import run_structural_check
    from horcrux.fix import run_fix

    profile = load_profile(profile_path)
    report = run_structural_check(profile.output_dir, profile.name)

    if report.ok:
        typer.echo("No issues found — nothing to fix.")
        return

    typer.echo(str(report))
    count = run_fix(report, auto=auto)
    if count:
        typer.echo(f"\n{count} fix(es) applied.")
    else:
        typer.echo("\nNo fixes applied.")


@app.command("list")
def list_agents() -> None:
    """List registered horcrux agents."""

    registry = load_registry()
    if not registry.agents:
        typer.echo("No agents registered.")
        return

    for entry in registry.agents:
        typer.echo(f"{entry.name}\t{entry.output_dir}\t{entry.diffused_at.isoformat()}")
