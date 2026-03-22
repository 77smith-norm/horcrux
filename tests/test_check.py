"""Tests for structural health checks."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from horcrux.check import run_structural_check
from horcrux.cli import app

runner = CliRunner()


def _make_profile(tmp_path: Path, output_dir: Path) -> Path:
    p = tmp_path / "profile.yaml"
    p.write_text(
        f"""\
name: CheckTest
harness: openclaw
os: linux
output_dir: {output_dir}
model: test/model
voice_notes: "Test."
capabilities: []
exclude_tools: []
platform_notes: ""
""",
        encoding="utf-8",
    )
    return p


def _populate_output(output_dir: Path) -> None:
    """Write minimal valid identity files to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "refs").mkdir(exist_ok=True)
    files = {
        "SOUL.md": "# SOUL.md\n\nI am a test agent. I do things. I build things.\n",
        "AGENTS.md": "# AGENTS.md\n\nI operate with care and precision.\n",
        "HEARTBEAT.md": "# HEARTBEAT.md\n\nI run hourly.\n",
        "BOUNDARIES.md": "# BOUNDARIES.md\n\nI protect the system.\n",
        "TOOLS.md": "# TOOLS.md\n\nTools I use.\n",
        "MEMORY.md": "# MEMORY.md\n\nI remember things here.\n",
        "IDENTITY.md": "# IDENTITY.md\n\nI am CheckTest.\n",
        "USER.md": "# USER.md\n\nThe user is Russell.\n",
    }
    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8")


def test_check_missing_output_dir(tmp_path: Path) -> None:
    report = run_structural_check(tmp_path / "nonexistent", "TestAgent")
    assert report.errors
    assert "does not exist" in report.errors[0].message


def test_check_missing_required_file(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    _populate_output(output_dir)
    (output_dir / "SOUL.md").unlink()
    report = run_structural_check(output_dir, "TestAgent")
    missing = [i for i in report.errors if "SOUL.md" in str(i.file)]
    assert missing, "Expected error for missing SOUL.md"


def test_check_all_present_no_issues(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    _populate_output(output_dir)
    report = run_structural_check(output_dir, "TestAgent")
    # Should have no errors; may have warnings for missing optional refs
    assert not report.errors


def test_check_detects_third_person(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    _populate_output(output_dir)
    (output_dir / "SOUL.md").write_text(
        "# SOUL.md\n\nThe agent will respond to all queries.\n" + "x" * 600,
        encoding="utf-8",
    )
    report = run_structural_check(output_dir, "TestAgent")
    tone_issues = [
        i for i in report.warnings
        if "third-person" in i.message.lower() or "passive" in i.message.lower()
    ]
    assert tone_issues, "Expected third-person tone warning"


def test_check_detects_hollow_affirmation(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    _populate_output(output_dir)
    (output_dir / "SOUL.md").write_text(
        "# SOUL.md\n\nI am always happy to help with any task.\n" + "x" * 600,
        encoding="utf-8",
    )
    report = run_structural_check(output_dir, "TestAgent")
    hollow = [i for i in report.warnings if "hollow" in i.message.lower()]
    assert hollow, "Expected hollow affirmation warning"


def test_check_cli_exits_nonzero_on_errors(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    profile = _make_profile(tmp_path, output_dir)
    # output_dir doesn't exist → error
    result = runner.invoke(app, ["check", str(profile)])
    assert result.exit_code == 1


def test_check_cli_exits_zero_when_clean(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    profile = _make_profile(tmp_path, output_dir)
    _populate_output(output_dir)
    result = runner.invoke(app, ["check", str(profile)])
    assert result.exit_code == 0
