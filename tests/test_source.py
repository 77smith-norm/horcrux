from __future__ import annotations

from pathlib import Path
from shutil import copytree

import pytest

from horcrux.profile import AgentProfile
from horcrux.source import apply_overrides, load_canonical_workspace, resolve_source_root
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


def test_load_canonical_workspace_missing_root_raises_clear_error(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing-canonical"

    with pytest.raises(FileNotFoundError, match=rf"Source root not found: {missing_root}"):
        load_canonical_workspace(missing_root)


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


def test_apply_overrides_replaces_document(tmp_path: Path) -> None:
    workspace = load_canonical_workspace(fixture_path("canonical"))
    override_path = tmp_path / "USER.md"
    override_path.write_text("# USER.md\n\nOverride content.\n", encoding="utf-8")

    updated = apply_overrides(workspace, {"USER.md": override_path})

    assert updated.read_text("USER.md") == "# USER.md\n\nOverride content.\n"
    assert workspace.read_text("USER.md") != updated.read_text("USER.md")


def test_apply_overrides_adds_new_document(tmp_path: Path) -> None:
    workspace = load_canonical_workspace(fixture_path("canonical"))
    override_path = tmp_path / "CUSTOM.md"
    override_path.write_text("# CUSTOM.md\n\nOverride content.\n", encoding="utf-8")

    updated = apply_overrides(workspace, {"refs/CUSTOM.md": override_path})

    assert updated.has_document("refs/CUSTOM.md")
    assert updated.read_text("refs/CUSTOM.md") == "# CUSTOM.md\n\nOverride content.\n"


def test_apply_overrides_empty_overrides_returns_same_workspace() -> None:
    workspace = load_canonical_workspace(fixture_path("canonical"))

    updated = apply_overrides(workspace, {})

    assert updated is workspace


def test_apply_overrides_missing_file_raises(tmp_path: Path) -> None:
    workspace = load_canonical_workspace(fixture_path("canonical"))
    missing_override = tmp_path / "missing.md"

    with pytest.raises(
        FileNotFoundError,
        match=rf"Override for USER\.md not found: {missing_override}",
    ):
        apply_overrides(workspace, {"USER.md": missing_override})
