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


def _write_plugin(tmp_path: Path, *, harness_id: str = "blob") -> Path:
    plugin_path = tmp_path / "blob_plugin.py"
    plugin_path.write_text(
        """
from pathlib import Path
from typing import ClassVar

from horcrux.targets.base import BaseTarget, DiffusedFile
from horcrux.targets.registry import register


@register
class BlobHarnessTarget(BaseTarget):
    harness_id: ClassVar[str] = "%s"

    def render(self) -> list[DiffusedFile]:
        return [
            DiffusedFile(
                relative_path=Path("PLUGIN.md"),
                content=self.source.read_text(Path("SOUL.md")),
                source_path=Path("SOUL.md"),
                transforms=("plugin-copy",),
            )
        ]
""".strip()
        % harness_id,
        encoding="utf-8",
    )
    return plugin_path


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

    def fake_run_structural_check(
        _output_dir: Path,
        _agent_name: str,
        harness: str = "openclaw",
    ) -> CheckReport:
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

    result = CliRunner().invoke(app, ["check", "--all"])

    assert result.exit_code == 0
    assert "No agents registered." in result.stdout


def test_check_requires_profile_path_without_all() -> None:
    result = CliRunner().invoke(app, ["check"])

    assert result.exit_code == 2
    assert "PROFILE_PATH is required unless --all is used." in result.output


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

    result = CliRunner().invoke(app, ["check", "--all"])

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


def test_diffuse_missing_profile_reports_clear_error(tmp_path: Path) -> None:
    missing_profile = tmp_path / "missing.yaml"

    result = CliRunner().invoke(app, ["diffuse", str(missing_profile)])

    assert result.exit_code == 2
    assert "Profile not found:" in result.output
    assert missing_profile.name in result.output


def test_diffuse_invalid_profile_mapping_reports_clear_error(tmp_path: Path) -> None:
    invalid_profile = tmp_path / "invalid-profile.yaml"
    invalid_profile.write_text("- not-a-mapping\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["diffuse", str(invalid_profile)])

    assert result.exit_code == 2
    assert "Failed to load profile" in result.output
    assert "YAML" in result.output
    assert "mapping" in result.output


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


def test_diffuse_with_harness_plugin(monkeypatch, tmp_path: Path) -> None:
    profile_path = _write_profile(tmp_path)
    plugin_path = _write_plugin(tmp_path)
    source_root = _write_source_workspace(
        tmp_path,
        "plugin-source",
        "# SOUL.md\n\nPlugin-loaded source.\n",
    )

    profile_data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile_data["harness"] = "blob"
    profile_data["harness_plugin"] = str(plugin_path)
    profile_data["source_root"] = str(source_root)
    profile_path.write_text(yaml.safe_dump(profile_data), encoding="utf-8")

    monkeypatch.setenv("HORCRUX_REGISTRY_PATH", str(tmp_path / "agents.json"))

    result = CliRunner().invoke(app, ["diffuse", str(profile_path), "--force"])

    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "output" / "PLUGIN.md").read_text(encoding="utf-8") == (
        "# SOUL.md\n\nPlugin-loaded source.\n"
    )


def test_diffuse_missing_harness_plugin_reports_clear_error(tmp_path: Path) -> None:
    profile_path = _write_profile(tmp_path)
    missing_plugin = tmp_path / "missing_plugin.py"

    profile_data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile_data["harness_plugin"] = str(missing_plugin)
    profile_path.write_text(yaml.safe_dump(profile_data), encoding="utf-8")

    result = CliRunner().invoke(app, ["diffuse", str(profile_path)])

    assert result.exit_code == 2
    assert "harness_plugin not found:" in result.output
    assert missing_plugin.name in result.output


def test_profile_commands_reject_output_dir_with_clear_error(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    runner = CliRunner()

    for command in ("check", "diff", "fix"):
        result = runner.invoke(app, [command, str(output_dir)])

        assert result.exit_code == 2
        assert "YAML" in result.output
        assert "profile" in result.output
        assert "output_dir" in result.output
        assert output_dir.name in result.output


def test_diffuse_missing_source_root_reports_clear_error(tmp_path: Path) -> None:
    profile_path = _write_profile(tmp_path)
    missing_source = tmp_path / "missing-source"

    profile_data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile_data["source_root"] = str(missing_source)
    profile_path.write_text(yaml.safe_dump(profile_data), encoding="utf-8")

    result = CliRunner().invoke(app, ["diffuse", str(profile_path)])

    assert result.exit_code == 2
    assert "Source root not found:" in result.output
    assert missing_source.name in result.output


def test_diffuse_existing_files_reports_error_without_success_summary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    profile_path = _write_profile(tmp_path)

    monkeypatch.setenv("HORCRUX_SOURCE_DIR", str(fixture_path("canonical")))
    monkeypatch.setenv("HORCRUX_REGISTRY_PATH", str(tmp_path / "agents.json"))

    runner = CliRunner()
    first = runner.invoke(app, ["diffuse", str(profile_path), "--force"])
    assert first.exit_code == 0, first.output

    second = runner.invoke(app, ["diffuse", str(profile_path)])

    assert second.exit_code == 2
    assert "already exists." in second.output
    assert "--force" in second.output
    assert "Diffused:" not in second.output


def test_diffuse_harness_plugin_mismatch_reports_clear_error(tmp_path: Path) -> None:
    profile_path = _write_profile(tmp_path)
    plugin_path = _write_plugin(tmp_path, harness_id="mismatch-blub")
    source_root = _write_source_workspace(
        tmp_path,
        "plugin-source",
        "# SOUL.md\n\nPlugin-loaded source.\n",
    )

    profile_data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile_data["harness"] = "mismatch-blob"
    profile_data["harness_plugin"] = str(plugin_path)
    profile_data["source_root"] = str(source_root)
    profile_path.write_text(yaml.safe_dump(profile_data), encoding="utf-8")

    result = CliRunner().invoke(app, ["diffuse", str(profile_path)])

    assert result.exit_code == 2
    assert "did not register" in result.output
    assert "profile harness" in result.output
    assert "mismatch-blob" in result.output
    assert "mismatch-blub" in result.output


def test_list_exits_cleanly_when_registry_is_empty(monkeypatch) -> None:
    monkeypatch.setattr("horcrux.cli.load_registry", lambda: Registry())

    result = CliRunner().invoke(app, ["list"])

    assert result.exit_code == 0
    assert "No agents registered." in result.output


def test_init_prints_profile_yaml_to_stdout() -> None:
    result = CliRunner().invoke(
        app,
        [
            "init",
            "--name",
            "StdoutInit",
            "--harness",
            "openclaw",
            "--os",
            "linux",
            "--output-dir",
            "/tmp/stdout-init",
            "--model",
            "test/model",
            "--voice-notes",
            "Lean and direct.",
        ],
    )

    assert result.exit_code == 0
    assert "name: StdoutInit" in result.output
    assert "voice_notes: >" in result.output


def test_init_rejects_invalid_harness_choice() -> None:
    result = CliRunner().invoke(app, ["init", "--harness", "blob"])

    assert result.exit_code == 2
    assert "harness must be one of: openclaw, hermes" in result.output
