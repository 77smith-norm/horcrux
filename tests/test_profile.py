from __future__ import annotations

from horcrux.profile import load_profile

from tests.conftest import fixture_path


def test_load_profile_parses_yaml() -> None:
    profile = load_profile(fixture_path("profiles", "test-agent.yaml"))

    assert profile.name == "TestAgent"
    assert profile.harness == "openclaw"
    assert profile.os == "linux"
    assert profile.output_dir.as_posix() == "/tmp/horcrux-test-agent"
    assert profile.capabilities == ["terminal", "python"]
    assert profile.exclude_tools == ["mdfind", "applcal"]

