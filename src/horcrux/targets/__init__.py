"""Diffusion targets."""

from horcrux.targets.base import BaseTarget, DiffusedFile
from horcrux.targets.hermes import HermesTarget
from horcrux.targets.openclaw import OpenClawTarget
from horcrux.targets.registry import get_target, register

__all__ = [
    "BaseTarget",
    "DiffusedFile",
    "HermesTarget",
    "OpenClawTarget",
    "get_target",
    "register",
]
