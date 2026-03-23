"""Interactive interview flow for generating agent profile YAML."""

from __future__ import annotations

import typer
import yaml

_HARNESSES = ["openclaw", "hermes"]
_OSES = ["linux", "macos"]


def _prompt(label: str, default: str = "", required: bool = True) -> str:
    while True:
        value = typer.prompt(label, default=default or None, show_default=bool(default))
        if value or not required:
            return value
        typer.echo("  (required — please enter a value)")


def _prompt_list(label: str, hint: str = "") -> list[str]:
    typer.echo(f"{label} {hint}")
    typer.echo("  Enter one per line. Empty line to finish.")
    items: list[str] = []
    while True:
        value = typer.prompt("  ", default="", show_default=False)
        if not value:
            break
        items.append(value.strip())
    return items


class _FoldedString(str):
    """Marker type for folded YAML scalars."""


class _ProfileDumper(yaml.SafeDumper):
    """YAML dumper with readable indentation for nested lists."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        super().increase_indent(flow, False)


def _represent_folded_string(dumper: yaml.SafeDumper, data: _FoldedString) -> yaml.Node:
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")


_ProfileDumper.add_representer(_FoldedString, _represent_folded_string)


def _resolve_prompt_value(
    value: str | None,
    label: str,
    *,
    default: str = "",
    required: bool = True,
) -> str:
    candidate = value.strip() if value is not None else ""
    if candidate:
        return candidate
    return _prompt(label, default=default, required=required)


def _resolve_choice(
    value: str | None,
    label: str,
    *,
    options: list[str],
    default: str,
) -> str:
    candidate = value.strip() if value is not None else ""
    while True:
        if candidate:
            choice = candidate
            candidate = ""
        else:
            choice = _prompt(label, default=default)
        if choice in options:
            return choice
        typer.echo(f"  Unknown {label.lower()} '{choice}'. Choose from: {', '.join(options)}")


def build_profile_yaml(
    *,
    name: str,
    harness: str,
    os_val: str,
    output_dir: str,
    model: str,
    voice_notes: str,
    capabilities: list[str] | None = None,
    exclude_tools: list[str] | None = None,
    platform_notes: str = "",
) -> str:
    """Build agent profile YAML from Python values."""

    folded_voice_notes = voice_notes if voice_notes.endswith("\n") else f"{voice_notes}\n"
    payload = {
        "name": name,
        "harness": harness,
        "os": os_val,
        "output_dir": output_dir,
        "model": model,
        "voice_notes": _FoldedString(folded_voice_notes),
        "capabilities": capabilities or [],
        "exclude_tools": exclude_tools or [],
        "platform_notes": platform_notes,
    }
    return yaml.dump(payload, Dumper=_ProfileDumper, sort_keys=False, allow_unicode=False)


def run_init_interview(
    *,
    name: str | None = None,
    harness: str | None = None,
    os_val: str | None = None,
    output_dir: str | None = None,
    model: str | None = None,
    voice_notes: str | None = None,
    capabilities: list[str] | None = None,
    exclude_tools: list[str] | None = None,
    platform_notes: str | None = None,
) -> str:
    """Run the interview and return a YAML string for the profile."""
    typer.echo("\n── Horcrux Agent Profile Generator ──\n")

    name = _resolve_prompt_value(name, "Agent name")

    typer.echo(f"\nHarness options: {', '.join(_HARNESSES)}")
    harness = _resolve_choice(
        harness,
        "Harness",
        options=_HARNESSES,
        default="openclaw",
    )

    typer.echo(f"\nOS options: {', '.join(_OSES)}")
    os_val = _resolve_choice(
        os_val,
        "OS",
        options=_OSES,
        default="linux",
    )

    output_dir = _resolve_prompt_value(
        output_dir,
        "Output directory (absolute path)",
        default=f"~/agents/{name}",
    )
    model = _resolve_prompt_value(model, "Model", default="openrouter/minimax/minimax-m2.7")
    voice_notes = _resolve_prompt_value(
        voice_notes,
        "Voice notes (describe the agent's character in 1–3 sentences)",
    )
    platform_notes = _resolve_prompt_value(
        platform_notes,
        "Platform notes (hardware, OS version, constraints)",
        required=False,
    )

    resolved_capabilities = [item.strip() for item in capabilities or [] if item.strip()]
    if not resolved_capabilities:
        resolved_capabilities = _prompt_list(
            "\nCapabilities",
            "(e.g. terminal, git, web, python):",
        )
    resolved_exclude_tools = [item.strip() for item in exclude_tools or [] if item.strip()]
    if not resolved_exclude_tools:
        resolved_exclude_tools = _prompt_list(
            "\nExclude tools",
            "(e.g. mdfind, applcal, applpass):",
        )

    return build_profile_yaml(
        name=name,
        harness=harness,
        os_val=os_val,
        output_dir=output_dir,
        model=model,
        voice_notes=voice_notes,
        capabilities=resolved_capabilities,
        exclude_tools=resolved_exclude_tools,
        platform_notes=platform_notes,
    )
