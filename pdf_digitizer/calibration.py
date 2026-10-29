"""坐标定标：图像相对坐标 -> 数据坐标映射。"""

from __future__ import annotations

import math
from collections.abc import Mapping

CALIBRATION_FIELDS = ("x1", "x2", "y1", "y2")

DEFAULT_CALIBRATION_VALUES: dict[str, float] = {
    "x1": 0.0,
    "x2": 100.0,
    "y1": 0.0,
    "y2": 100.0,
}

CalibrationPoint = tuple[float, float]


def map_axis_value(
    value: float,
    pixel_start: float,
    pixel_end: float,
    value_start: float,
    value_end: float,
    is_log: bool,
) -> float:
    """把一个轴上两定标点之间的位置线性（或对数）映射为数据值。"""
    if abs(pixel_end - pixel_start) < 1e-9:
        return value_start
    ratio = (value - pixel_start) / (pixel_end - pixel_start)
    if not is_log:
        return value_start + ratio * (value_end - value_start)
    try:
        log_start, log_end = math.log10(value_start), math.log10(value_end)
        return 10 ** (log_start + ratio * (log_end - log_start))
    except (ValueError, ZeroDivisionError):
        return value_start


def map_point(
    rel_x: float,
    rel_y: float,
    points: Mapping[str, CalibrationPoint | None],
    values: Mapping[str, float],
    is_log_x: bool,
    is_log_y: bool,
) -> tuple[float, float]:
    """把图像相对坐标 (0-1) 映射为数据坐标。

    X 轴只使用两个定标点的 x 分量，Y 轴只使用 y 分量，与原程序一致。
    """
    x = map_axis_value(
        rel_x,
        points["x1"][0],  # type: ignore[index]
        points["x2"][0],  # type: ignore[index]
        values["x1"],
        values["x2"],
        is_log_x,
    )
    y = map_axis_value(
        rel_y,
        points["y1"][1],  # type: ignore[index]
        points["y2"][1],  # type: ignore[index]
        values["y1"],
        values["y2"],
        is_log_y,
    )
    return x, y
