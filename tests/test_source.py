from __future__ import annotations

from pathlib import Path
from shutil import copytree

import pytest

from horcrux.profile import AgentProfile
from horcrux.source import load_canonical_workspace, resolve_source_root
from tests.conftest import fixture_path


def _build_profile(*, source_root: Path | None = None) -> AgentProfile:
    return AgentProfile(
        name="TestAgent",
        harness="openclaw",
        os="linux",
        output_dir=Path("/tmp/horcrux-test-agent"),
        source_root=source_root,
        model="openrouter/example/test-model",
        voice_notes="Quiet, direct, technical.",
    )


def test_load_canonical_workspace_reads_root_docs_and_refs() -> None:
    workspace = load_canonical_workspace(fixture_path("canonical"))

    assert workspace.root == fixture_path("canonical")
    assert workspace.has_document("SOUL.md")
    assert workspace.has_document("refs/HANDOFF.md")
    assert "Test soul." in workspace.read_text("SOUL.md")


@pytest.mark.parametrize("missing_name", ["AGENTS.md", "SOUL.md"])
def test_load_canonical_workspace_raises_for_missing_root_document(
    tmp_path: Path,
    missing_name: str,
) -> None:
    workspace_root = tmp_path / "canonical"
    copytree(fixture_path("canonical"), workspace_root)
    (workspace_root / missing_name).unlink()

    with pytest.raises(FileNotFoundError, match=missing_name):
        load_canonical_workspace(workspace_root)


def test_resolve_source_root_cli_override_wins() -> None:
    profile = _build_profile(source_root=Path("/tmp/profile-source"))

    resolved = resolve_source_root(profile, cli_override=Path("/tmp/cli-source"))

    assert resolved == Path("/tmp/cli-source")


def test_resolve_source_root_profile_wins_over_default(monkeypatch) -> None:
    monkeypatch.setattr("horcrux.source.default_source_root", lambda: Path("/tmp/default-source"))
    profile = _build_profile(source_root=Path("/tmp/profile-source"))

    resolved = resolve_source_root(profile)

    assert resolved == Path("/tmp/profile-source")


def test_resolve_source_root_falls_back_to_default(monkeypatch) -> None:
    monkeypatch.setattr("horcrux.source.default_source_root", lambda: Path("/tmp/default-source"))
    profile = _build_profile()

    resolved = resolve_source_root(profile)

    assert resolved == Path("/tmp/default-source")
