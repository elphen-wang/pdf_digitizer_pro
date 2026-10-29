"""坐标定标映射的单元测试。"""

from __future__ import annotations

import pytest

from pdf_digitizer.calibration import map_axis_value, map_point


@pytest.mark.unit
def test_linear_mapping_maps_endpoints_exactly() -> None:
    assert map_axis_value(0.25, 0.25, 0.75, 0.0, 100.0, False) == pytest.approx(0.0)
    assert map_axis_value(0.75, 0.25, 0.75, 0.0, 100.0, False) == pytest.approx(100.0)


@pytest.mark.unit
def test_linear_mapping_interpolates_midpoint() -> None:
    assert map_axis_value(0.5, 0.25, 0.75, 0.0, 100.0, False) == pytest.approx(50.0)


@pytest.mark.unit
def test_log_mapping_uses_decades() -> None:
    # 1 与 100 在对数轴上的中点即几何平均 10
    assert map_axis_value(0.5, 0.0, 1.0, 1.0, 100.0, True) == pytest.approx(10.0)


@pytest.mark.unit
def test_log_mapping_rejects_non_positive_values() -> None:
    assert map_axis_value(0.5, 0.0, 1.0, 0.0, 100.0, True) == pytest.approx(0.0)


@pytest.mark.unit
def test_degenerate_pixel_range_returns_start_value() -> None:
    assert map_axis_value(0.5, 0.4, 0.4, 7.0, 9.0, False) == pytest.approx(7.0)


@pytest.mark.unit
def test_map_point_uses_x_component_for_x_and_y_component_for_y() -> None:
    points = {
        "x1": (0.10, 0.90),
        "x2": (0.60, 0.20),
        "y1": (0.90, 0.20),
        "y2": (0.30, 0.80),
    }
    values = {"x1": 10.0, "x2": 20.0, "y1": 100.0, "y2": 200.0}

    x, y = map_point(0.35, 0.50, points, values, is_log_x=False, is_log_y=False)

    assert x == pytest.approx(15.0)
    assert y == pytest.approx(150.0)
