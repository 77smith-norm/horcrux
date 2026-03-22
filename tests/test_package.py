from __future__ import annotations

from enum import StrEnum
from pathlib import Path
import tomllib

import horcrux
from horcrux.check import Severity
from horcrux.transforms import CopyTransform, FilterTransform, SubstituteTransform


def test_package_version_matches_pyproject() -> None:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    project = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))["project"]

    assert "__version__" in horcrux.__all__
    assert horcrux.__version__ == project["version"]


def test_severity_is_a_str_enum() -> None:
    assert issubclass(Severity, StrEnum)


def test_public_transform_apply_methods_have_docstrings() -> None:
    transforms = (
        CopyTransform.apply,
        FilterTransform.apply,
        SubstituteTransform.apply,
    )

    for apply_method in transforms:
        assert apply_method.__doc__
        assert apply_method.__doc__.strip()
