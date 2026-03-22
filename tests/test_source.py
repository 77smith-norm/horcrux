from __future__ import annotations

from horcrux.source import load_canonical_workspace

from tests.conftest import fixture_path


def test_load_canonical_workspace_reads_root_docs_and_refs() -> None:
    workspace = load_canonical_workspace(fixture_path("canonical"))

    assert workspace.root == fixture_path("canonical")
    assert workspace.has_document("SOUL.md")
    assert workspace.has_document("refs/HANDOFF.md")
    assert "Test soul." in workspace.read_text("SOUL.md")

