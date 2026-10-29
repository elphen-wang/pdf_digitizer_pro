"""矢量几何工具的单元测试。"""

from __future__ import annotations

from collections import namedtuple

import pytest

from pdf_digitizer.geometry import (
    bezier_points,
    extract_path_points,
    path_min_distance,
    point_segment_distance,
)

Point = namedtuple("Point", "x y")


@pytest.mark.unit
def test_point_segment_distance_uses_perpendicular_projection() -> None:
    assert point_segment_distance(0.5, 1.0, 0.0, 0.0, 1.0, 0.0) == pytest.approx(1.0)


@pytest.mark.unit
def test_point_segment_distance_clamps_beyond_endpoint() -> None:
    assert point_segment_distance(2.0, 0.0, 0.0, 0.0, 1.0, 0.0) == pytest.approx(1.0)


@pytest.mark.unit
def test_point_segment_distance_handles_zero_length_segment() -> None:
    assert point_segment_distance(3.0, 4.0, 0.0, 0.0, 0.0, 0.0) == pytest.approx(5.0)


@pytest.mark.unit
def test_bezier_points_include_both_endpoints() -> None:
    p1, c1, c2, p2 = Point(0, 0), Point(0, 1), Point(1, 1), Point(1, 0)
    points = bezier_points(p1, c1, c2, p2, samples=8)
    assert points[0] == pytest.approx((0.0, 0.0))
    assert points[-1] == pytest.approx((1.0, 0.0))
    assert len(points) == 9


@pytest.mark.unit
def test_path_min_distance_sees_midpoint_of_curve() -> None:
    path = {
        "items": [
            ("c", Point(0, 0), Point(0, 2), Point(2, 2), Point(2, 0)),
        ]
    }
    # 三次贝塞尔在 t=0.5 处位于 (1, 1.5)
    assert path_min_distance(path, 1.0, 1.5) == pytest.approx(0.0, abs=1e-6)


@pytest.mark.unit
def test_path_min_distance_handles_line_items() -> None:
    path = {"items": [("l", Point(0, 0), Point(10, 0))]}
    assert path_min_distance(path, 5.0, 3.0) == pytest.approx(3.0)


@pytest.mark.unit
def test_extract_path_points_keeps_line_endpoints() -> None:
    path = {"items": [("l", Point(0, 0), Point(1, 1))]}
    assert extract_path_points(path) == [(0.0, 0.0), (1.0, 1.0)]
