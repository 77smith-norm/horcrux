from __future__ import annotations

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
