from __future__ import annotations

from pathlib import Path

from horcrux.profile import load_profile
from horcrux.source import load_canonical_workspace
from horcrux.targets.openclaw import OpenClawTarget

from tests.conftest import fixture_path


def test_openclaw_target_renders_linux_specific_output() -> None:
    profile = load_profile(fixture_path("profiles", "test-agent.yaml"))
    source = load_canonical_workspace(fixture_path("canonical"))

    rendered = {
        file.relative_path: file
        for file in OpenClawTarget(profile, source).render()
    }

    assert Path("AGENTS.md") in rendered
    assert "# AGENTS.md — How TestAgent Operates" in rendered[Path("AGENTS.md")].content
    assert "## Tools" not in rendered[Path("AGENTS.md")].content
    assert "## Heartbeats" not in rendered[Path("AGENTS.md")].content
    assert "grep -R" in rendered[Path("AGENTS.md")].content
    assert "/home/workspace/TestAgent/dev" in rendered[Path("BOUNDARIES.md")].content
    assert 'find /home/workspace/TestAgent/memory -name "*plan*"' in rendered[
        Path("refs/HANDOFF.md")
    ].content
    assert "mdfind" not in rendered[Path("refs/HANDOFF.md")].content
    assert "`terminal`" in rendered[Path("TOOLS.md")].content
    assert "`mdfind`" in rendered[Path("TOOLS.md")].content

