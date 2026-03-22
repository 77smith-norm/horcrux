"""Runtime registry for harness targets."""

from __future__ import annotations

from horcrux.targets.base import BaseTarget

_REGISTRY: dict[str, type[BaseTarget]] = {}


def register(cls: type[BaseTarget]) -> type[BaseTarget]:
    """Register a target class by its harness identifier."""

    harness_id = getattr(cls, "harness_id", "").strip()
    if not harness_id:
        raise ValueError(f"{cls.__name__} must define a non-empty harness_id")
    _REGISTRY[harness_id] = cls
    return cls


def get_target(harness: str) -> type[BaseTarget]:
    """Look up a target class by harness identifier."""

    if harness not in _REGISTRY:
        raise ValueError(f"Unknown harness: {harness!r}. Known: {sorted(_REGISTRY)}")
    return _REGISTRY[harness]
