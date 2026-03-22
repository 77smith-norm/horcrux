from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from horcrux.registry import Registry, RegistryEntry, load_registry, save_registry


def _sample_registry() -> Registry:
    return Registry(
        agents=[
            RegistryEntry(
                name="TestAgent",
                profile=Path("/tmp/profile.yaml"),
                output_dir=Path("/tmp/output"),
                diffused_at=datetime(2026, 3, 22, 17, 0, tzinfo=UTC),
            )
        ]
    )


def test_save_registry_creates_missing_parent_directory(tmp_path: Path) -> None:
    registry_path = tmp_path / ".horcrux" / "agents.json"

    saved_path = save_registry(_sample_registry(), registry_path)

    assert saved_path == registry_path
    assert registry_path.exists()
    assert registry_path.parent.is_dir()
    loaded = load_registry(registry_path)
    assert [entry.name for entry in loaded.agents] == ["TestAgent"]


def test_load_registry_raises_clear_error_for_corrupt_json(tmp_path: Path) -> None:
    registry_path = tmp_path / "agents.json"
    registry_path.write_text('{"version": 1, "agents": [', encoding="utf-8")

    with pytest.raises(RuntimeError, match="corrupt"):
        load_registry(registry_path)

