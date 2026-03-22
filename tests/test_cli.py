from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner
import yaml

from horcrux.cli import app

from tests.conftest import fixture_path


def test_diffuse_dry_run_prints_meaningful_output(monkeypatch, tmp_path: Path) -> None:
    profile_data = yaml.safe_load(fixture_path("profiles", "test-agent.yaml").read_text())
    profile_data["output_dir"] = str(tmp_path / "output")
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(yaml.safe_dump(profile_data), encoding="utf-8")

    monkeypatch.setenv("HORCRUX_SOURCE_DIR", str(fixture_path("canonical")))
    monkeypatch.setenv("HORCRUX_REGISTRY_PATH", str(tmp_path / "agents.json"))

    result = CliRunner().invoke(app, ["diffuse", str(profile_path), "--dry-run"])

    assert result.exit_code == 0
    assert "Dry run: TestAgent (openclaw/linux)" in result.stdout
    assert "Runtime workspace: /home/workspace/TestAgent" in result.stdout
    assert "- AGENTS.md <- AGENTS.md [filter, substitute, render-model-routing]" in result.stdout
    assert not (tmp_path / "output" / "AGENTS.md").exists()


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

