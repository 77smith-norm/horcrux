"""Tests for horcrux diff command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from horcrux.cli import app

runner = CliRunner()


def _make_profile(tmp_path: Path, output_dir: Path | None = None) -> Path:
    profile = tmp_path / "agent.yaml"
    out = str(output_dir or tmp_path / "output")
    profile.write_text(
        f"""\
name: TestDiff
harness: openclaw
os: linux
output_dir: {out}
model: test/model
voice_notes: "Test voice."
capabilities: []
exclude_tools: []
platform_notes: ""
""",
        encoding="utf-8",
    )
    return profile


def test_diff_missing_output_dir(tmp_path: Path) -> None:
    profile = _make_profile(tmp_path)
    result = runner.invoke(app, ["diff", str(profile)])
    assert result.exit_code == 0
    assert "TestDiff" in result.output


def test_diff_shows_unchanged_when_files_match(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    profile = _make_profile(tmp_path, output_dir=output_dir)

    # First diffuse to output_dir
    result = runner.invoke(app, ["diffuse", str(profile), "--force"])
    assert result.exit_code == 0, result.output

    # Now diff — should show all unchanged
    result = runner.invoke(app, ["diff", str(profile)])
    assert result.exit_code == 0
    assert "matches rendered output" in result.output or "Unchanged" in result.output


def test_diff_shows_changed_when_file_modified(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    profile = _make_profile(tmp_path, output_dir=output_dir)

    runner.invoke(app, ["diffuse", str(profile), "--force"])
    soul_file = output_dir / "SOUL.md"
    soul_file.write_text(soul_file.read_text() + "\n## EXTRA SECTION\ninjected content\n")

    result = runner.invoke(app, ["diff", str(profile)])
    assert result.exit_code == 0
    assert "SOUL.md" in result.output
    assert "~" in result.output
