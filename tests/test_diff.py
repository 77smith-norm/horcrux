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


def test_diff_default_shows_section_summary_without_unified_diff(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    profile = _make_profile(tmp_path, output_dir=output_dir)

    runner.invoke(app, ["diffuse", str(profile), "--force"])
    agents_file = output_dir / "AGENTS.md"
    agents_file.write_text(
        "\n".join(
            [
                "# AGENTS.md — How TestDiff Operates",
                "",
                "_SOUL.md is who I am. This is how I move through the day._",
                "",
                "---",
                "",
                "## Model Routing",
                "",
                "Changed routing text.",
                "",
                "## Extra Protocol",
                "",
                "Only in the current file.",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["diff", str(profile)])

    assert result.exit_code == 0
    assert "AGENTS.md" in result.output
    assert "Added sections" in result.output
    assert "Removed sections" in result.output
    assert "## Safety (Short Form)" in result.output
    assert "## Extra Protocol" in result.output
    assert "--- current/AGENTS.md" not in result.output
    assert "@@" not in result.output


def test_diff_verbose_shows_unified_diff_for_changed_files(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    profile = _make_profile(tmp_path, output_dir=output_dir)

    runner.invoke(app, ["diffuse", str(profile), "--force"])
    agents_file = output_dir / "AGENTS.md"
    agents_file.write_text(
        agents_file.read_text(encoding="utf-8").replace(
            "## Safety (Short Form)",
            "## Safety (Expanded)",
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["diff", str(profile), "--verbose"])

    assert result.exit_code == 0
    assert "--- current/AGENTS.md" in result.output
    assert "+++ rendered/AGENTS.md" in result.output
