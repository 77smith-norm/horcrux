from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

import horcrux.targets.registry as target_registry
from horcrux.targets.base import BaseTarget, DiffusedFile
from horcrux.targets.hermes import HermesTarget
from horcrux.targets.openclaw import OpenClawTarget


def test_existing_targets_are_registered() -> None:
    assert target_registry.get_target("openclaw") is OpenClawTarget
    assert target_registry.get_target("hermes") is HermesTarget


def test_register_adds_mock_target(monkeypatch) -> None:
    monkeypatch.setattr(target_registry, "_REGISTRY", {})

    @target_registry.register
    class MockTarget(BaseTarget):
        harness_id: ClassVar[str] = "mock"

        def render(self) -> list[DiffusedFile]:
            return []

    assert target_registry.get_target("mock") is MockTarget


def test_get_target_raises_for_unknown_harness(monkeypatch) -> None:
    monkeypatch.setattr(target_registry, "_REGISTRY", {"openclaw": OpenClawTarget})

    with pytest.raises(ValueError, match=r"Unknown harness: 'codex'. Known: \['openclaw'\]"):
        target_registry.get_target("codex")


def test_load_plugin_registers_harness(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(target_registry, "_REGISTRY", {})
    plugin_path = tmp_path / "blob_plugin.py"
    plugin_path.write_text(
        """
from typing import ClassVar

from horcrux.targets.base import BaseTarget, DiffusedFile
from horcrux.targets.registry import register


@register
class BlobHarnessTarget(BaseTarget):
    harness_id: ClassVar[str] = "blob"

    def render(self) -> list[DiffusedFile]:
        return []
""".strip(),
        encoding="utf-8",
    )

    target_registry.load_plugin(plugin_path)

    assert target_registry.get_target("blob").__name__ == "BlobHarnessTarget"


def test_load_plugin_missing_file_raises(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing_plugin.py"

    with pytest.raises(FileNotFoundError, match=rf"harness_plugin not found: {missing_path}"):
        target_registry.load_plugin(missing_path)


def test_load_plugin_invalid_python_raises(tmp_path: Path) -> None:
    plugin_path = tmp_path / "broken_plugin.py"
    plugin_path.write_text("def broken(:\n", encoding="utf-8")

    with pytest.raises(ImportError, match=r"Failed to load harness plugin"):
        target_registry.load_plugin(plugin_path)
