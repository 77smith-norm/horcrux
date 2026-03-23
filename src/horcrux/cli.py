"""CLI entry point."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from horcrux.profile import AgentProfile, load_profile
from horcrux.registry import RegistryEntry, load_registry, save_registry, upsert_registry_entry
from horcrux.source import apply_overrides, load_canonical_workspace, resolve_source_root
from horcrux.targets import BaseTarget, DiffusedFile, get_target

app = typer.Typer(help="Diffuse agent identities into harness-specific workspaces.")
_INIT_HARNESSES = ("openclaw", "hermes")
_INIT_OSES = ("linux", "macos")
_INIT_REQUIRED_FLAGS = (
    "--name",
    "--harness",
    "--os",
    "--output-dir",
    "--model",
    "--voice-notes",
)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped


def _validate_init_choice(
    value: str | None,
    label: str,
    *,
    choices: tuple[str, ...],
) -> str | None:
    if value is None:
        return None
    if value in choices:
        return value
    raise typer.BadParameter(f"{label} must be one of: {', '.join(choices)}")


def _missing_init_required_fields(
    *,
    name: str | None,
    harness: str | None,
    os_val: str | None,
    output_dir: str | None,
    model: str | None,
    voice_notes: str | None,
) -> list[str]:
    required_values = {
        "--name": _normalize_optional_text(name),
        "--harness": _normalize_optional_text(harness),
        "--os": _normalize_optional_text(os_val),
        "--output-dir": _normalize_optional_text(output_dir),
        "--model": _normalize_optional_text(model),
        "--voice-notes": _normalize_optional_text(voice_notes),
    }
    return [flag for flag, value in required_values.items() if value is None]


def _stdin_supports_prompts() -> bool:
    """Allow interactive prompts on real TTYs and Typer's test stdin wrapper."""

    return sys.stdin.isatty() or sys.stdin.__class__.__module__ == "click.testing"


def _build_target(
    profile: AgentProfile,
    *,
    source_root: Path | None = None,
) -> tuple[BaseTarget, Path]:
    try:
        target_cls = get_target(profile.harness)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    resolved_source_root = resolve_source_root(profile, cli_override=source_root)
    source = load_canonical_workspace(resolved_source_root)
    source = apply_overrides(source, profile.overrides)
    return target_cls(profile=profile, source=source), resolved_source_root


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
    source_root: Path,
    runtime_workspace: Path,
) -> str:
    lines = [
        f"Diffused: {profile.name} ({profile.harness}/{profile.os})",
        f"Source root: {source_root}",
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
    source_root: Annotated[
        Path | None,
        typer.Option("--source", "-s", help="Override canonical source workspace root."),
    ] = None,
    dry_run: bool = typer.Option(False, "--dry-run", help="Render without writing files."),
    force: bool = typer.Option(False, "--force", help="Overwrite managed files."),
) -> None:
    """Diffuse a canonical workspace into a target agent workspace."""

    profile = load_profile(profile_path)
    target, resolved_source_root = _build_target(profile, source_root=source_root)
    files = target.render()
    runtime_workspace = getattr(target, "runtime_workspace", profile.output_dir)

    if dry_run:
        from horcrux.differ import run_diffuse_preview

        run_diffuse_preview(
            profile,
            files,
            source_root=resolved_source_root,
            runtime_workspace=runtime_workspace,
        )
        return

    typer.echo(_format_diffusion_summary(profile, files, resolved_source_root, runtime_workspace))
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
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Write profile to this path."),
    ] = None,
    name: Annotated[
        str | None,
        typer.Option("--name", help="Agent name."),
    ] = None,
    harness: Annotated[
        str | None,
        typer.Option("--harness", help="Harness: openclaw or hermes."),
    ] = None,
    os_val: Annotated[
        str | None,
        typer.Option("--os", help="Target OS: linux or macos."),
    ] = None,
    output_dir: Annotated[
        str | None,
        typer.Option("--output-dir", help="Agent output directory."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option("--model", help="Model string for the agent."),
    ] = None,
    voice_notes: Annotated[
        str | None,
        typer.Option("--voice-notes", help="1–3 sentences describing the agent's character."),
    ] = None,
    capabilities: list[str] = typer.Option(
        default_factory=list,
        help="Repeatable capability flag, e.g. --capabilities terminal.",
    ),
    exclude_tools: list[str] = typer.Option(
        default_factory=list,
        help="Repeatable tool exclusion flag.",
    ),
    platform_notes: Annotated[
        str | None,
        typer.Option("--platform-notes", help="Platform notes or constraints."),
    ] = None,
) -> None:
    """Generate an agent profile YAML via flags or interview."""
    from horcrux.init_flow import build_profile_yaml, run_init_interview

    name = _normalize_optional_text(name)
    harness = _validate_init_choice(
        _normalize_optional_text(harness),
        "harness",
        choices=_INIT_HARNESSES,
    )
    os_val = _validate_init_choice(
        _normalize_optional_text(os_val),
        "os",
        choices=_INIT_OSES,
    )
    output_dir = _normalize_optional_text(output_dir)
    model = _normalize_optional_text(model)
    voice_notes = _normalize_optional_text(voice_notes)
    platform_notes = _normalize_optional_text(platform_notes)

    missing_required = _missing_init_required_fields(
        name=name,
        harness=harness,
        os_val=os_val,
        output_dir=output_dir,
        model=model,
        voice_notes=voice_notes,
    )
    if missing_required and not _stdin_supports_prompts():
        typer.echo("horcrux init: missing required fields for non-interactive mode.")
        typer.echo("Provide all required flags or run interactively in a terminal.")
        typer.echo("")
        typer.echo("Missing:")
        for flag in missing_required:
            typer.echo(f"  {flag}")
        typer.echo("")
        typer.echo(f"Required flags: {' '.join(_INIT_REQUIRED_FLAGS)}")
        raise typer.Exit(code=1)

    if not missing_required:
        assert name is not None
        assert harness is not None
        assert os_val is not None
        assert output_dir is not None
        assert model is not None
        assert voice_notes is not None
        result = build_profile_yaml(
            name=name,
            harness=harness,
            os_val=os_val,
            output_dir=output_dir,
            model=model,
            voice_notes=voice_notes,
            capabilities=capabilities,
            exclude_tools=exclude_tools,
            platform_notes=platform_notes or "",
        )
    else:
        result = run_init_interview(
            name=name,
            harness=harness,
            os_val=os_val,
            output_dir=output_dir,
            model=model,
            voice_notes=voice_notes,
            capabilities=capabilities,
            exclude_tools=exclude_tools,
            platform_notes=platform_notes,
        )

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result, encoding="utf-8")
        typer.echo(f"Profile written to {output}")
    else:
        typer.echo(result)


@app.command("diff")
def diff_agent(
    profile_path: Path,
    source_root: Annotated[
        Path | None,
        typer.Option("--source", "-s", help="Override canonical source workspace root."),
    ] = None,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full content diffs."),
) -> None:
    """Show structural diff between current output_dir and what diffuse would produce."""
    from horcrux.differ import run_diff

    profile = load_profile(profile_path)
    target, _ = _build_target(profile, source_root=source_root)
    files = target.render()
    run_diff(profile, files, verbose=verbose)


@app.command("check")
def check_agent(
    profile_path: Path,
    source_root: Annotated[
        Path | None,
        typer.Option("--source", "-s", help="Override canonical source workspace root."),
    ] = None,
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
    resolve_source_root(profile, cli_override=source_root)
    report = run_structural_check(profile.output_dir, profile.name, harness=profile.harness)
    typer.echo(str(report))
    if report.errors:
        raise typer.Exit(code=1)


@app.command("fix")
def fix_agent(
    profile_path: Path,
    source_root: Annotated[
        Path | None,
        typer.Option("--source", "-s", help="Override canonical source workspace root."),
    ] = None,
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
    resolve_source_root(profile, cli_override=source_root)
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
