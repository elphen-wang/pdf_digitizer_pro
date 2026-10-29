"""数据筛选与导出的单元测试。"""

from __future__ import annotations

import pytest

from pdf_digitizer.filters import (
    apply_stride,
    filter_points,
    format_clipboard,
    parse_optional_float,
    separator_from_index,
    sort_points,
    write_export,
)

SAMPLE = [(0.0, 10.0), (1.0, 20.0), (2.0, 30.0), (3.0, 40.0)]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("text", "expected"),
    [("1.5", 1.5), ("", None), ("   ", None), ("abc", None), ("-2", -2.0)],
)
def test_parse_optional_float(text: str, expected: float | None) -> None:
    assert parse_optional_float(text) == expected


@pytest.mark.unit
def test_filter_points_applies_inclusive_bounds() -> None:
    assert filter_points(SAMPLE, xmin=1.0, xmax=2.0) == [(1.0, 20.0), (2.0, 30.0)]


@pytest.mark.unit
def test_filter_points_ignores_none_bounds() -> None:
    assert filter_points(SAMPLE) == SAMPLE


@pytest.mark.unit
def test_apply_stride_takes_every_nth_point() -> None:
    assert apply_stride(SAMPLE, 2) == [(0.0, 10.0), (2.0, 30.0)]


@pytest.mark.unit
def test_apply_stride_treats_non_positive_as_one() -> None:
    assert apply_stride(SAMPLE, 0) == SAMPLE
    assert apply_stride(SAMPLE, -5) == SAMPLE


@pytest.mark.unit
def test_sort_points_by_y_descending() -> None:
    assert sort_points(SAMPLE, column=2, descending=True)[0] == (3.0, 40.0)


@pytest.mark.unit
def test_sort_points_returns_new_list() -> None:
    original = list(SAMPLE)
    sort_points(SAMPLE, column=1)
    assert SAMPLE == original


@pytest.mark.unit
@pytest.mark.parametrize(
    ("index", "expected"),
    [(0, "\t"), (1, ","), (2, " "), (None, "\t"), (99, "\t")],
)
def test_separator_from_index(index: int | None, expected: str) -> None:
    assert separator_from_index(index) == expected


@pytest.mark.unit
def test_format_clipboard_includes_header() -> None:
    assert format_clipboard(SAMPLE[:2], ",") == "X,Y\n0.0,10.0\n1.0,20.0"


@pytest.mark.unit
def test_write_export_txt_uses_separator(tmp_path) -> None:
    target = tmp_path / "out.txt"
    write_export(SAMPLE[:2], target, "\t")
    assert target.read_text(encoding="utf-8") == "X\tY\n0.0\t10.0\n1.0\t20.0\n"


@pytest.mark.unit
def test_write_export_csv_forces_comma(tmp_path) -> None:
    target = tmp_path / "out.csv"
    write_export(SAMPLE[:2], target, "\t")
    assert target.read_text(encoding="utf-8").splitlines() == ["X,Y", "0.0,10.0", "1.0,20.0"]
