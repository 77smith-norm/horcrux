"""Horcrux package."""

from importlib.metadata import PackageNotFoundError, version


__all__ = ["__version__"]


try:
    __version__ = version("horcrux")
except PackageNotFoundError:  # pragma: no cover - local source checkout
    __version__ = "0.1.0"
