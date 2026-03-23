"""Runtime registry for harness targets."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

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


def load_plugin(plugin_path: Path) -> None:
    """Load a harness plugin file and allow it to register targets."""

    if not plugin_path.exists():
        raise FileNotFoundError(
            f"harness_plugin not found: {plugin_path}\nCheck the path in your profile YAML."
        )

    module_suffix = hashlib.sha256(str(plugin_path.resolve()).encode("utf-8")).hexdigest()[:12]
    module_name = f"_horcrux_plugin_{module_suffix}"
    spec = importlib.util.spec_from_file_location(module_name, plugin_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load plugin: {plugin_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise ImportError(f"Failed to load harness plugin {plugin_path}: {exc}") from exc
