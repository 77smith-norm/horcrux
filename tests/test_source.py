from __future__ import annotations

from pathlib import Path
from shutil import copytree

import pytest

from horcrux.source import load_canonical_workspace
from tests.conftest import fixture_path


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
