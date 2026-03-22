"""Interactive interview flow for generating agent profile YAML."""

from __future__ import annotations

import typer


_HARNESSESS = ["openclaw", "hermes"]
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


def run_init_interview() -> str:
    """Run the interview and return a YAML string for the profile."""
    typer.echo("\n── Horcrux Agent Profile Generator ──\n")

    name = _prompt("Agent name")

    typer.echo(f"\nHarness options: {', '.join(_HARNESSESS)}")
    while True:
        harness = _prompt("Harness", default="openclaw")
        if harness in _HARNESSESS:
            break
        typer.echo(f"  Unknown harness '{harness}'. Choose from: {', '.join(_HARNESSESS)}")

    typer.echo(f"\nOS options: {', '.join(_OSES)}")
    while True:
        os_val = _prompt("OS", default="linux")
        if os_val in _OSES:
            break
        typer.echo(f"  Unknown OS '{os_val}'. Choose from: {', '.join(_OSES)}")

    output_dir = _prompt("Output directory (absolute path)", default=f"~/agents/{name}")
    model = _prompt("Model", default="openrouter/minimax/minimax-m2.7")
    voice_notes = _prompt("Voice notes (describe the agent's character in 1–3 sentences)")
    platform_notes = _prompt("Platform notes (hardware, OS version, constraints)", required=False)

    capabilities = _prompt_list(
        "\nCapabilities",
        "(e.g. terminal, git, web, python):",
    )
    exclude_tools = _prompt_list(
        "\nExclude tools",
        "(e.g. mdfind, applcal, applpass):",
    )

    # Build YAML manually — cleaner than dumping pydantic's dict for a config file
    lines = [
        f"name: {name}",
        f"harness: {harness}",
        f"os: {os_val}",
        f"output_dir: {output_dir}",
        f"model: {model}",
        f'voice_notes: >',
        f'  {voice_notes}',
    ]

    if capabilities:
        lines.append("capabilities:")
        for cap in capabilities:
            lines.append(f"  - {cap}")
    else:
        lines.append("capabilities: []")

    if exclude_tools:
        lines.append("exclude_tools:")
        for tool in exclude_tools:
            lines.append(f"  - {tool}")
    else:
        lines.append("exclude_tools: []")

    if platform_notes:
        lines.append(f'platform_notes: "{platform_notes}"')
    else:
        lines.append('platform_notes: ""')

    return "\n".join(lines) + "\n"
