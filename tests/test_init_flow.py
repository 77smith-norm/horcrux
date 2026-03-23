from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from horcrux.cli import app
from horcrux.init_flow import build_profile_yaml

runner = CliRunner()


def test_build_profile_yaml_all_fields() -> None:
    result = build_profile_yaml(
        name="Zocots",
        harness="openclaw",
        os_val="linux",
        output_dir="~/agents/Zocots",
        model="openrouter/minimax/minimax-m2.7",
        voice_notes="Quieter than Norm. Watchful and precise.",
        capabilities=["terminal", "git", "web"],
        exclude_tools=["mdfind"],
        platform_notes="Ubuntu 22.04 VM.",
    )

    assert "voice_notes: >" in result
    assert "capabilities:" in result
    assert "exclude_tools:" in result
    assert yaml.safe_load(result) == {
        "name": "Zocots",
        "harness": "openclaw",
        "os": "linux",
        "output_dir": "~/agents/Zocots",
        "model": "openrouter/minimax/minimax-m2.7",
        "voice_notes": "Quieter than Norm. Watchful and precise.\n",
        "capabilities": ["terminal", "git", "web"],
        "exclude_tools": ["mdfind"],
        "platform_notes": "Ubuntu 22.04 VM.",
    }


def test_build_profile_yaml_empty_lists() -> None:
    result = build_profile_yaml(
        name="Zocots",
        harness="openclaw",
        os_val="linux",
        output_dir="~/agents/Zocots",
        model="openrouter/minimax/minimax-m2.7",
        voice_notes="Quieter than Norm. Watchful and precise.",
        capabilities=[],
        exclude_tools=[],
        platform_notes="",
    )

    assert "capabilities: []" in result
    assert "exclude_tools: []" in result
    assert yaml.safe_load(result)["capabilities"] == []
    assert yaml.safe_load(result)["exclude_tools"] == []


def test_init_cli_writes_profile_from_interactive_answers(tmp_path: Path) -> None:
    output_path = tmp_path / "generated-profile.yaml"
    result = runner.invoke(
        app,
        ["init", "--output", str(output_path)],
        input="\n".join(
            [
                "InitTest",
                "",
                "",
                str(tmp_path / "agents" / "InitTest"),
                "",
                "I work directly and leave a clear trail.",
                "M3 MacBook Pro",
                "terminal",
                "git",
                "",
                "mdfind",
                "",
            ]
        )
        + "\n",
    )

    assert result.exit_code == 0, result.stdout
    assert f"Profile written to {output_path}" in result.stdout

    profile = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert profile == {
        "name": "InitTest",
        "harness": "openclaw",
        "os": "linux",
        "output_dir": str(tmp_path / "agents" / "InitTest"),
        "model": "openrouter/minimax/minimax-m2.7",
        "voice_notes": "I work directly and leave a clear trail.\n",
        "capabilities": ["terminal", "git"],
        "exclude_tools": ["mdfind"],
        "platform_notes": "M3 MacBook Pro",
    }


def test_cli_init_noninteractive(tmp_path: Path) -> None:
    output_path = tmp_path / "generated-profile.yaml"
    result = runner.invoke(
        app,
        [
            "init",
            "--name",
            "Zocots",
            "--harness",
            "openclaw",
            "--os",
            "linux",
            "--output-dir",
            str(tmp_path / "agents" / "Zocots"),
            "--model",
            "openrouter/minimax/minimax-m2.7",
            "--voice-notes",
            "Quieter than Norm. Watchful and precise.",
            "--capabilities",
            "terminal",
            "--capabilities",
            "git",
            "--exclude-tools",
            "mdfind",
            "--platform-notes",
            "Ubuntu 22.04 VM.",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Horcrux Agent Profile Generator" not in result.stdout
    assert "Agent name" not in result.stdout
    assert f"Profile written to {output_path}" in result.stdout
    assert yaml.safe_load(output_path.read_text(encoding="utf-8")) == {
        "name": "Zocots",
        "harness": "openclaw",
        "os": "linux",
        "output_dir": str(tmp_path / "agents" / "Zocots"),
        "model": "openrouter/minimax/minimax-m2.7",
        "voice_notes": "Quieter than Norm. Watchful and precise.\n",
        "capabilities": ["terminal", "git"],
        "exclude_tools": ["mdfind"],
        "platform_notes": "Ubuntu 22.04 VM.",
    }


def test_cli_init_missing_required_noninteractive(monkeypatch, tmp_path: Path) -> None:
    output_path = tmp_path / "generated-profile.yaml"
    monkeypatch.setattr("horcrux.cli._stdin_supports_prompts", lambda: False)

    result = runner.invoke(
        app,
        [
            "init",
            "--harness",
            "openclaw",
            "--os",
            "linux",
            "--output-dir",
            str(tmp_path / "agents" / "Zocots"),
            "--model",
            "openrouter/minimax/minimax-m2.7",
            "--voice-notes",
            "Quieter than Norm. Watchful and precise.",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 1
    assert "horcrux init: missing required fields for non-interactive mode." in result.stdout
    assert "Provide all required flags or run interactively in a terminal." in result.stdout
    assert "\nMissing:\n  --name\n" in result.stdout
    assert (
        "Required flags: --name --harness --os --output-dir --model --voice-notes"
        in result.stdout
    )
    assert not output_path.exists()
