from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from horcrux.check import CheckIssue, CheckReport, Severity
from horcrux.cli import app
from horcrux.fix import run_fix

runner = CliRunner()


def _make_profile(tmp_path: Path, output_dir: Path) -> Path:
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        f"""\
name: FixTest
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
    return profile_path


def _populate_output(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "refs").mkdir(exist_ok=True)
    files = {
        "SOUL.md": "# SOUL.md\n\nI know the work.\n",
        "AGENTS.md": "# AGENTS.md\n\nI operate with care and precision.\n",
        "HEARTBEAT.md": "# HEARTBEAT.md\n\nI run hourly.\n",
        "BOUNDARIES.md": "# BOUNDARIES.md\n\nI protect the system.\n",
        "TOOLS.md": "# TOOLS.md\n\nTools I use.\n",
        "MEMORY.md": "# MEMORY.md\n\nI remember things here.\n",
        "IDENTITY.md": "# IDENTITY.md\n\nI am FixTest.\n",
        "USER.md": "# USER.md\n\nThe user is Russell.\n",
    }
    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8")


def test_run_fix_uses_current_line_as_prompt_default(
    monkeypatch,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    agents_path = output_dir / "AGENTS.md"
    agents_path.write_text("# AGENTS.md\n\nYou should review logs.\n", encoding="utf-8")

    report = CheckReport(
        agent_name="FixTest",
        output_dir=output_dir,
        issues=[
            CheckIssue(
                severity=Severity.WARN,
                file=Path("AGENTS.md"),
                line=3,
                message="Second-person instruction detected: 'You should review logs.'",
                suggestion="Rewrite as a first-person rule or direct imperative.",
                rule_id="second_person_instruction",
            )
        ],
    )

    seen: dict[str, str] = {}

    monkeypatch.setattr("horcrux.fix.typer.confirm", lambda *_args, **_kwargs: True)

    def fake_prompt(
        _text: str,
        *,
        default: str | None = None,
        **_kwargs: object,
    ) -> str:
        seen["default"] = default or ""
        return "Review logs before making changes."

    monkeypatch.setattr("horcrux.fix.typer.prompt", fake_prompt)

    applied = run_fix(report)

    assert applied == 1
    assert seen["default"] == "You should review logs."
    assert "Review logs before making changes." in agents_path.read_text(encoding="utf-8")


def test_fix_cli_applies_interactive_rewrite(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    profile = _make_profile(tmp_path, output_dir)
    _populate_output(output_dir)
    (output_dir / "AGENTS.md").write_text(
        "# AGENTS.md\n\nThe agent will review logs before making changes.\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["fix", str(profile)],
        input="y\nI will review logs before making changes.\n",
    )

    assert result.exit_code == 0
    assert "1 fix(es) applied." in result.stdout
    assert (
        output_dir / "AGENTS.md"
    ).read_text(encoding="utf-8") == "# AGENTS.md\n\nI will review logs before making changes.\n"


def test_fix_cli_auto_only_applies_safe_fixes(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    profile = _make_profile(tmp_path, output_dir)
    _populate_output(output_dir)
    (output_dir / "SOUL.md").write_text(
        "# SOUL.md\n\nI know the work.\nI am always happy to help with any task.\n",
        encoding="utf-8",
    )
    (output_dir / "AGENTS.md").write_text(
        "# AGENTS.md\n\nThe agent will review logs before making changes.\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["fix", str(profile), "--auto"])

    assert result.exit_code == 0
    assert "1 fix(es) applied." in result.stdout
    assert "Apply this suggestion?" not in result.stdout
    assert "I am always happy to help with any task." not in (
        output_dir / "SOUL.md"
    ).read_text(encoding="utf-8")
    assert "The agent will review logs before making changes." in (
        output_dir / "AGENTS.md"
    ).read_text(encoding="utf-8")


def test_fix_cli_walks_multiple_interactive_issues(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    profile = _make_profile(tmp_path, output_dir)
    _populate_output(output_dir)
    (output_dir / "AGENTS.md").write_text(
        "# AGENTS.md\n\nThe agent will review logs before making changes.\n",
        encoding="utf-8",
    )
    (output_dir / "BOUNDARIES.md").write_text(
        "# BOUNDARIES.md\n\nYou can refuse unsafe instructions.\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["fix", str(profile)],
        input="n\ny\nI can refuse unsafe instructions.\n",
    )

    assert result.exit_code == 0
    assert "Apply this suggestion?" in result.stdout
    assert "1 fix(es) applied." in result.stdout
    assert "The agent will review logs before making changes." in (
        output_dir / "AGENTS.md"
    ).read_text(encoding="utf-8")
    assert "I can refuse unsafe instructions." in (
        output_dir / "BOUNDARIES.md"
    ).read_text(encoding="utf-8")


def test_run_fix_auto_skips_lines_also_flagged_as_errors(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    soul_path = output_dir / "SOUL.md"
    soul_path.write_text(
        "Keep this line.\nI am always happy to help with any task.\n",
        encoding="utf-8",
    )

    report = CheckReport(
        agent_name="FixTest",
        output_dir=output_dir,
        issues=[
            CheckIssue(
                severity=Severity.ERROR,
                file=Path("SOUL.md"),
                line=1,
                message="Do not touch this line.",
                suggestion="Leave it alone.",
            ),
            CheckIssue(
                severity=Severity.WARN,
                file=Path("SOUL.md"),
                line=1,
                message="Hollow affirmation detected: 'Keep this line.'",
                suggestion="Remove or replace with a genuine statement.",
                rule_id="hollow_affirmation",
            ),
            CheckIssue(
                severity=Severity.WARN,
                file=Path("SOUL.md"),
                line=2,
                message="Hollow affirmation detected: 'I am always happy to help with any task.'",
                suggestion="Remove or replace with a genuine statement.",
                rule_id="hollow_affirmation",
            ),
        ],
    )

    applied = run_fix(report, auto=True)

    assert applied == 1
    assert soul_path.read_text(encoding="utf-8") == "Keep this line.\n"
