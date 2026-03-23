from __future__ import annotations

from horcrux.transforms.copy import CopyTransform
from horcrux.transforms.filter import FilterTransform
from horcrux.transforms.substitute import SubstituteTransform


def test_copy_transform_returns_same_text() -> None:
    text = "keep me"
    assert CopyTransform().apply(text) == text


def test_filter_transform_strips_named_section_and_matching_lines() -> None:
    text = """# Doc

## Keep
alpha
remove-me

## Drop
beta

## Tail
gamma
"""
    rendered = FilterTransform(
        strip_headings=("Drop",),
        drop_if_contains=("remove-me",),
    ).apply(text)

    assert "## Drop" not in rendered
    assert "beta" not in rendered
    assert "remove-me" not in rendered
    assert "## Tail" in rendered
    assert "gamma" in rendered


def test_filter_transform_strips_indented_markdown_heading() -> None:
    text = """# Doc

   ## Drop
beta

## Keep
gamma
"""
    rendered = FilterTransform(strip_headings=("Drop",)).apply(text)

    assert "   ## Drop" not in rendered
    assert "beta" not in rendered
    assert "## Keep" in rendered
    assert "gamma" in rendered


def test_substitute_transform_applies_ordered_replacements() -> None:
    rendered = SubstituteTransform(
        replacements=(("alpha", "beta"), ("beta beta", "done"))
    ).apply("alpha alpha")

    assert rendered == "done"
