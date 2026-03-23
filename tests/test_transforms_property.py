from __future__ import annotations

from dataclasses import dataclass

from hypothesis import given
from hypothesis import strategies as st

from horcrux.transforms.filter import FilterTransform

ASCII_PRINTABLE = [chr(codepoint) for codepoint in range(32, 127) if chr(codepoint) not in "#<>"]
TEXT_CHUNK = st.text(alphabet=ASCII_PRINTABLE, min_size=0, max_size=24)
HEADING_TITLE = TEXT_CHUNK.map(str.strip).filter(bool)
HEADING_LEVEL = st.integers(min_value=1, max_value=6)


@dataclass(frozen=True)
class FilterSectionCase:
    document: str
    expected: str
    strip_title: str
    drop_fragment: str


def render_heading(level: int, title: str) -> str:
    return f"{'#' * level} {title}\n"


def render_lines(lines: list[str]) -> str:
    return "".join(f"{line}\n" for line in lines)


def tagged_lines(tag: str) -> st.SearchStrategy[list[str]]:
    return st.lists(TEXT_CHUNK, max_size=4).map(
        lambda values: [f"{tag}-{index}:{value}" for index, value in enumerate(values)]
    )


@st.composite
def filter_section_case(draw: st.DrawFn) -> FilterSectionCase:
    strip_title = draw(HEADING_TITLE)
    keep_title = draw(HEADING_TITLE.filter(lambda title: title != strip_title))
    strip_level = draw(HEADING_LEVEL)
    keep_level = draw(st.integers(min_value=1, max_value=strip_level))
    before_lines = draw(tagged_lines("before"))
    stripped_lines = draw(tagged_lines("stripped"))
    kept_lines = draw(tagged_lines("kept"))
    tail_lines = draw(tagged_lines("tail"))
    drop_fragment = f"<<drop-{draw(st.integers(min_value=0, max_value=999_999))}>>"
    dropped_line = f"drop-line:{drop_fragment}"

    nested_heading = ""
    nested_lines: list[str] = []
    if strip_level < 6:
        nested_title = draw(
            HEADING_TITLE.filter(lambda title: title not in {strip_title, keep_title})
        )
        nested_level = draw(st.integers(min_value=strip_level + 1, max_value=6))
        nested_lines = draw(tagged_lines("nested"))
        nested_heading = render_heading(nested_level, nested_title)

    document = (
        render_lines(before_lines)
        + render_heading(strip_level, strip_title)
        + render_lines(stripped_lines)
        + nested_heading
        + render_lines(nested_lines)
        + f"{dropped_line}\n"
        + render_heading(keep_level, keep_title)
        + render_lines(kept_lines)
        + render_lines(tail_lines)
    )
    expected = (
        render_lines(before_lines)
        + render_heading(keep_level, keep_title)
        + render_lines(kept_lines)
        + render_lines(tail_lines)
    )
    return FilterSectionCase(
        document=document,
        expected=expected,
        strip_title=strip_title,
        drop_fragment=drop_fragment,
    )


@st.composite
def drop_line_case(draw: st.DrawFn) -> tuple[str, str]:
    fragment = f"<<drop-{draw(st.integers(min_value=0, max_value=999_999))}>>"
    kept_lines = draw(tagged_lines("keep"))
    dropped_lines = draw(tagged_lines("drop")).copy()
    dropped_lines = [f"{line} {fragment}" for line in dropped_lines]

    all_lines = draw(
        st.permutations(
            [(line, False) for line in kept_lines] + [(line, True) for line in dropped_lines]
        )
    )
    document = render_lines([line for line, _ in all_lines])
    expected = render_lines([line for line, should_drop in all_lines if not should_drop])
    return document, fragment, expected


@given(filter_section_case())
def test_filter_transform_is_idempotent(case: FilterSectionCase) -> None:
    transform = FilterTransform(
        strip_headings=(case.strip_title,),
        drop_if_contains=(case.drop_fragment,),
    )

    once = transform.apply(case.document)

    assert transform.apply(once) == once


@given(filter_section_case())
def test_filter_transform_strips_target_heading_block_without_touching_siblings(
    case: FilterSectionCase,
) -> None:
    rendered = FilterTransform(
        strip_headings=(case.strip_title,),
        drop_if_contains=(case.drop_fragment,),
    ).apply(case.document)

    assert rendered == case.expected


@given(drop_line_case())
def test_filter_transform_drops_only_lines_containing_fragments(
    case: tuple[str, str, str],
) -> None:
    document, fragment, expected = case

    rendered = FilterTransform(drop_if_contains=(fragment,)).apply(document)

    assert rendered == expected


def test_filter_transform_returns_empty_string_for_empty_input() -> None:
    assert FilterTransform().apply("") == ""


@given(tagged_lines("plain"))
def test_filter_transform_leaves_plain_text_unchanged_when_nothing_matches(
    plain_lines: list[str],
) -> None:
    text = render_lines(plain_lines)

    assert FilterTransform(drop_if_contains=("<<absent>>",)).apply(text) == text
