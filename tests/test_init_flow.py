from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from horcrux.cli import app


def test_init_cli_writes_profile_from_interactive_answers(tmp_path: Path) -> None:
    output_path = tmp_path / "generated-profile.yaml"
    result = CliRunner().invoke(
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
