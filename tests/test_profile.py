from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from horcrux.profile import load_profile
from tests.conftest import fixture_path


def _write_profile(tmp_path: Path, **updates: object) -> Path:
    profile_data = yaml.safe_load(fixture_path("profiles", "test-agent.yaml").read_text())
    profile_data.update(updates)
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(yaml.safe_dump(profile_data), encoding="utf-8")
    return profile_path


def test_load_profile_parses_yaml() -> None:
    profile = load_profile(fixture_path("profiles", "test-agent.yaml"))

    assert profile.name == "TestAgent"
    assert profile.harness == "openclaw"
    assert profile.os == "linux"
    assert profile.output_dir.as_posix() == "/tmp/horcrux-test-agent"
    assert profile.capabilities == ["terminal", "python"]
    assert profile.exclude_tools == ["mdfind", "applcal"]


def test_profile_source_root_optional(tmp_path: Path) -> None:
    profile = load_profile(_write_profile(tmp_path))

    assert profile.source_root is None


def test_profile_source_root_expands_tilde(tmp_path: Path) -> None:
    profile = load_profile(_write_profile(tmp_path, source_root="~/source-workspace"))

    assert profile.source_root == Path("~/source-workspace").expanduser()


def test_profile_source_root_absolute(tmp_path: Path) -> None:
    profile = load_profile(_write_profile(tmp_path, source_root="/tmp/workspace"))

    assert profile.source_root == Path("/tmp/workspace")


def test_profile_rejects_unknown_fields(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        load_profile(_write_profile(tmp_path, unexpected="value"))
