"""Tests for the Hermes harness target."""

from __future__ import annotations

from pathlib import Path

from horcrux.profile import load_profile
from horcrux.source import load_canonical_workspace
from horcrux.targets.hermes import HermesTarget
from tests.conftest import fixture_path


def _render_map(profile_file: str) -> dict[Path, object]:
    profile = load_profile(fixture_path("profiles", profile_file))
    source = load_canonical_workspace(fixture_path("canonical"))
    files = HermesTarget(profile, source).render()
    return {f.relative_path: f for f in files}


def test_hermes_renders_four_files(tmp_path: Path) -> None:
    profile_path = tmp_path / "hermes-agent.yaml"
    profile_path.write_text(
        """\
name: TestHermes
harness: hermes
os: linux
output_dir: /tmp/test-hermes
model: some/model
voice_notes: "Lean and direct."
capabilities:
  - terminal
exclude_tools:
  - mdfind
platform_notes: ""
""",
        encoding="utf-8",
    )
    from horcrux.profile import load_profile
    from horcrux.source import load_canonical_workspace

    profile = load_profile(profile_path)
    source = load_canonical_workspace(fixture_path("canonical"))
    files = HermesTarget(profile, source).render()
    paths = {f.relative_path for f in files}

    assert Path("SOUL.md") in paths
    assert Path("AGENTS.md") in paths
    assert Path("IDENTITY.md") in paths
    assert Path("MEMORY.md") in paths
    # Hermes does not include HEARTBEAT.md or refs/
    assert Path("HEARTBEAT.md") not in paths
    assert Path("refs/BIO.md") not in paths


def test_hermes_agents_md_contains_identity(tmp_path: Path) -> None:
    profile_path = tmp_path / "h.yaml"
    profile_path.write_text(
        """\
name: Aria
harness: hermes
os: linux
output_dir: /tmp/aria
model: test/model
voice_notes: "Thoughtful and precise."
capabilities: []
exclude_tools: []
platform_notes: "Test box."
""",
        encoding="utf-8",
    )
    from horcrux.profile import load_profile
    from horcrux.source import load_canonical_workspace

    profile = load_profile(profile_path)
    source = load_canonical_workspace(fixture_path("canonical"))
    files = {f.relative_path: f for f in HermesTarget(profile, source).render()}

    agents = files[Path("AGENTS.md")].content
    assert "Aria" in agents
    assert "test/model" in agents
    assert "Thoughtful and precise." in agents
    assert "Install note" in agents


def test_hermes_soul_is_verbatim_copy(tmp_path: Path) -> None:
    profile_path = tmp_path / "h.yaml"
    profile_path.write_text(
        """\
name: Aria
harness: hermes
os: linux
output_dir: /tmp/aria
model: test/model
voice_notes: "Thoughtful."
capabilities: []
exclude_tools: []
platform_notes: ""
""",
        encoding="utf-8",
    )
    from horcrux.profile import load_profile
    from horcrux.source import load_canonical_workspace

    profile = load_profile(profile_path)
    source = load_canonical_workspace(fixture_path("canonical"))
    files = {f.relative_path: f for f in HermesTarget(profile, source).render()}

    canonical_soul = source.read_text(Path("SOUL.md"))
    assert files[Path("SOUL.md")].content == canonical_soul


def test_llm_transform_raises_without_api_key(monkeypatch: object) -> None:
    """LLMTransform should raise RuntimeError if no API key is set."""

    import pytest

    from horcrux.transforms.llm import LLMTransform

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)  # type: ignore[attr-defined]

    transform = LLMTransform(
        agent_name="Test",
        agent_os="linux",
        agent_harness="hermes",
        agent_model="some/model",
        voice_notes="Lean.",
        platform_notes="",
    )
    with pytest.raises(RuntimeError, match="openai package|OPENROUTER_API_KEY"):
        transform.apply("# SOUL.md content")
