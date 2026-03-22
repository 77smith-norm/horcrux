from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from horcrux.cli import app

ZOCOTS_AGENT_DIR = Path("/Users/norm/.openclaw/workspace/agents/Zocots")
ZOCOTS_PROFILE_PATH = ZOCOTS_AGENT_DIR / "profile.yaml"

pytestmark = pytest.mark.smoke


def _require_zocots_profile() -> Path:
    if not ZOCOTS_PROFILE_PATH.exists():
        pytest.skip("Zocots profile not found")
    return ZOCOTS_PROFILE_PATH


def test_smoke_check_zocots_workspace_is_clean() -> None:
    profile_path = _require_zocots_profile()

    result = CliRunner().invoke(app, ["check", str(profile_path)])

    assert result.exit_code == 0, result.stdout
    assert "No issues found." in result.stdout


def test_smoke_diff_zocots_workspace_runs() -> None:
    profile_path = _require_zocots_profile()

    result = CliRunner().invoke(app, ["diff", str(profile_path)])

    assert result.exit_code == 0, result.stdout


def test_smoke_diffuse_dry_run_zocots_profile_does_not_write() -> None:
    profile_path = _require_zocots_profile()
    agents_path = ZOCOTS_AGENT_DIR / "AGENTS.md"
    before_mtime = agents_path.stat().st_mtime_ns

    result = CliRunner().invoke(app, ["diffuse", str(profile_path), "--dry-run"])

    assert result.exit_code == 0, result.stdout
    assert "Dry run:" in result.stdout
    assert "AGENTS.md" in result.stdout
    assert agents_path.stat().st_mtime_ns == before_mtime
