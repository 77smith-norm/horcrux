from __future__ import annotations

from pathlib import Path
from shutil import copytree

import yaml
from typer.testing import CliRunner

from horcrux.check import CheckReport
from horcrux.cli import app
from horcrux.profile import load_profile
from horcrux.registry import Registry, RegistryEntry
from horcrux.source import load_canonical_workspace
from horcrux.targets.openclaw import OpenClawTarget
from tests.conftest import fixture_path


def _write_profile(tmp_path: Path) -> Path:
    profile_data = yaml.safe_load(fixture_path("profiles", "test-agent.yaml").read_text())
    profile_data["output_dir"] = str(tmp_path / "output")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(yaml.safe_dump(profile_data), encoding="utf-8")
    return profile_path


def _write_source_workspace(tmp_path: Path, name: str, soul_text: str) -> Path:
    source_root = tmp_path / name
    copytree(fixture_path("canonical"), source_root)
    (source_root / "SOUL.md").write_text(soul_text, encoding="utf-8")
    return source_root


def _expected_render_count(profile_path: Path) -> int:
    profile = load_profile(profile_path)
    source = load_canonical_workspace(fixture_path("canonical"))
    return len(OpenClawTarget(profile, source).render())


def test_diffuse_dry_run_prints_meaningful_output(monkeypatch, tmp_path: Path) -> None:
    profile_path = _write_profile(tmp_path)

    monkeypatch.setenv("HORCRUX_SOURCE_DIR", str(fixture_path("canonical")))
    monkeypatch.setenv("HORCRUX_REGISTRY_PATH", str(tmp_path / "agents.json"))

    result = CliRunner().invoke(app, ["diffuse", str(profile_path), "--dry-run"])
    expected_count = _expected_render_count(profile_path)

    assert result.exit_code == 0
    assert "Dry run: TestAgent (openclaw/linux)" in result.stdout
    assert "Runtime workspace: /home/workspace/TestAgent" in result.stdout
    assert "New files (would be written):" in result.stdout
    assert "+ AGENTS.md" in result.stdout
    assert (
        f"Would write {expected_count} files (0 unchanged, {expected_count} new)."
        in result.stdout
    )
    assert not (tmp_path / "output" / "AGENTS.md").exists()


def test_diffuse_dry_run_shows_compact_diff_for_existing_output(
    monkeypatch,
    tmp_path: Path,
) -> None:
    profile_path = _write_profile(tmp_path)
    output_dir = tmp_path / "output"

    monkeypatch.setenv("HORCRUX_SOURCE_DIR", str(fixture_path("canonical")))
    monkeypatch.setenv("HORCRUX_REGISTRY_PATH", str(tmp_path / "agents.json"))

    runner = CliRunner()
    diffuse_result = runner.invoke(app, ["diffuse", str(profile_path), "--force"])
    assert diffuse_result.exit_code == 0, diffuse_result.stdout

    agents_file = output_dir / "AGENTS.md"
    agents_file.write_text(
        agents_file.read_text(encoding="utf-8").replace(
            "## Safety (Short Form)",
            "## Safety (Expanded)",
        ),
        encoding="utf-8",
    )
    (output_dir / "USER.md").unlink()

    result = runner.invoke(app, ["diffuse", str(profile_path), "--dry-run"])
    expected_count = _expected_render_count(profile_path)

    assert result.exit_code == 0
    assert "~ AGENTS.md" in result.stdout
    assert "Added sections" in result.stdout
    assert "Removed sections" in result.stdout
    assert "## Safety (Short Form)" in result.stdout
    assert "## Safety (Expanded)" in result.stdout
    assert "+ USER.md" in result.stdout
    assert f"Would write {expected_count} files (11 unchanged, 1 new)." in result.stdout


def test_list_reads_registry(monkeypatch, tmp_path: Path) -> None:
    registry_path = tmp_path / "agents.json"
    registry_path.write_text(
        """{
  "version": 1,
  "agents": [
    {
      "name": "TestAgent",
      "profile": "/tmp/profile.yaml",
      "output_dir": "/tmp/output",
      "diffused_at": "2026-03-22T17:00:00Z",
      "checked_at": null,
      "soul_reviewed": false
    }
  ]
}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("HORCRUX_REGISTRY_PATH", str(registry_path))

    result = CliRunner().invoke(app, ["list"])

    assert result.exit_code == 0
    assert "TestAgent" in result.stdout
    assert "/tmp/output" in result.stdout


def test_fix_exits_early_when_report_is_clean(monkeypatch, tmp_path: Path) -> None:
    profile_path = _write_profile(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    def fake_run_structural_check(_output_dir: Path, _agent_name: str) -> CheckReport:
        return CheckReport(agent_name="TestAgent", output_dir=output_dir)

    monkeypatch.setattr("horcrux.check.run_structural_check", fake_run_structural_check)

    result = CliRunner().invoke(app, ["fix", str(profile_path)])

    assert result.exit_code == 0
    assert "No issues found — nothing to fix." in result.stdout


def test_fix_reports_empty_agent_dir_without_crashing(tmp_path: Path) -> None:
    profile_path = _write_profile(tmp_path)

    result = CliRunner().invoke(app, ["fix", str(profile_path)])

    assert result.exit_code == 0
    assert "Output directory does not exist." in result.stdout
    assert "No fixable issues found." in result.stdout
    assert "No fixes applied." in result.stdout


def test_check_all_exits_cleanly_when_registry_is_empty(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("horcrux.cli.load_registry", lambda: Registry())

    result = CliRunner().invoke(app, ["check", str(tmp_path / "unused.yaml"), "--all"])

    assert result.exit_code == 0
    assert "No agents registered." in result.stdout


def test_check_all_prints_each_registered_agent_report(monkeypatch, tmp_path: Path) -> None:
    output_dir = tmp_path / "agent-output"
    registry = Registry(
        agents=[
            RegistryEntry(
                name="TestAgent",
                profile=tmp_path / "profile.yaml",
                output_dir=output_dir,
                diffused_at="2026-03-22T17:00:00Z",
            )
        ]
    )

    def fake_run_structural_check(agent_output_dir: Path, agent_name: str) -> CheckReport:
        return CheckReport(agent_name=agent_name, output_dir=agent_output_dir)

    monkeypatch.setattr("horcrux.cli.load_registry", lambda: registry)
    monkeypatch.setattr("horcrux.check.run_structural_check", fake_run_structural_check)

    result = CliRunner().invoke(app, ["check", str(tmp_path / "unused.yaml"), "--all"])

    assert result.exit_code == 0
    assert "Check: TestAgent" in result.stdout
    assert f"Output dir: {output_dir}" in result.stdout
    assert "No issues found." in result.stdout


def test_diffuse_respects_source_root_in_profile(monkeypatch, tmp_path: Path) -> None:
    profile_path = _write_profile(tmp_path)
    custom_source = _write_source_workspace(
        tmp_path,
        "custom-source",
        "# SOUL.md\n\nProfile-specific source root.\n",
    )

    profile_data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile_data["source_root"] = str(custom_source)
    profile_path.write_text(yaml.safe_dump(profile_data), encoding="utf-8")

    monkeypatch.setenv("HORCRUX_SOURCE_DIR", str(fixture_path("canonical")))
    monkeypatch.setenv("HORCRUX_REGISTRY_PATH", str(tmp_path / "agents.json"))

    result = CliRunner().invoke(app, ["diffuse", str(profile_path), "--force"])

    assert result.exit_code == 0, result.stdout
    assert f"Source root: {custom_source}" in result.stdout
    assert (tmp_path / "output" / "SOUL.md").read_text(encoding="utf-8") == (
        "# SOUL.md\n\nProfile-specific source root.\n"
    )


def test_diffuse_source_flag_overrides_profile(monkeypatch, tmp_path: Path) -> None:
    profile_path = _write_profile(tmp_path)
    profile_source = _write_source_workspace(
        tmp_path,
        "profile-source",
        "# SOUL.md\n\nProfile source root.\n",
    )
    cli_source = _write_source_workspace(
        tmp_path,
        "cli-source",
        "# SOUL.md\n\nCLI source root.\n",
    )

    profile_data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile_data["source_root"] = str(profile_source)
    profile_path.write_text(yaml.safe_dump(profile_data), encoding="utf-8")

    monkeypatch.setenv("HORCRUX_REGISTRY_PATH", str(tmp_path / "agents.json"))

    result = CliRunner().invoke(
        app,
        ["diffuse", str(profile_path), "--force", "--source", str(cli_source)],
    )

    assert result.exit_code == 0, result.stdout
    assert f"Source root: {cli_source}" in result.stdout
    assert (tmp_path / "output" / "SOUL.md").read_text(encoding="utf-8") == (
        "# SOUL.md\n\nCLI source root.\n"
    )


def test_diffuse_override_replaces_user_md(monkeypatch, tmp_path: Path) -> None:
    profile_path = _write_profile(tmp_path)
    override_path = tmp_path / "USER.override.md"
    override_path.write_text("# USER.md\n\nOverride user document.\n", encoding="utf-8")

    profile_data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile_data["overrides"] = {"USER.md": str(override_path)}
    profile_path.write_text(yaml.safe_dump(profile_data), encoding="utf-8")

    monkeypatch.setenv("HORCRUX_SOURCE_DIR", str(fixture_path("canonical")))
    monkeypatch.setenv("HORCRUX_REGISTRY_PATH", str(tmp_path / "agents.json"))

    result = CliRunner().invoke(app, ["diffuse", str(profile_path), "--force"])

    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "output" / "USER.md").read_text(encoding="utf-8") == (
        "# USER.md\n\nOverride user document.\n"
    )
