"""矢量几何工具：点到线段距离、贝塞尔采样、路径点提取。

PDF 路径中的点由 PyMuPDF 提供，只需具备 ``x`` / ``y`` 属性即可，
因此这里只做鸭子类型处理，不直接依赖 fitz。
"""

from __future__ import annotations

import math
from typing import Any


def point_segment_distance(
    px: float, py: float, ax: float, ay: float, bx: float, by: float
) -> float:
    """点 (px, py) 到线段 (ax, ay)-(bx, by) 的最短距离。"""
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / length_sq
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def bezier_points(
    p1: Any, c1: Any, c2: Any, p2: Any, samples: int = 20
) -> list[tuple[float, float]]:
    """三次贝塞尔曲线离散采样。"""
    points: list[tuple[float, float]] = []
    for i in range(samples + 1):
        t = i / samples
        mt = 1 - t
        x = mt**3 * p1.x + 3 * mt * mt * t * c1.x + 3 * mt * t * t * c2.x + t**3 * p2.x
        y = mt**3 * p1.y + 3 * mt * mt * t * c1.y + 3 * mt * t * t * c2.y + t**3 * p2.y
        points.append((x, y))
    return points


def path_min_distance(path: Any, px: float, py: float) -> float:
    """点击点到整条矢量路径（含曲线中间）的最小距离。"""
    best = math.inf
    for item in path["items"]:
        op = item[0]
        if op == "l":
            a, b = item[1], item[2]
            best = min(best, point_segment_distance(px, py, a.x, a.y, b.x, b.y))
        elif op == "c":
            p1, c1, c2, p2 = item[1], item[2], item[3], item[4]
            for x, y in bezier_points(p1, c1, c2, p2):
                best = min(best, math.hypot(px - x, py - y))
        elif op in ("m", "re"):
            point = item[-1]
            if hasattr(point, "x"):
                best = min(best, math.hypot(px - point.x, py - point.y))
    return best


def extract_path_points(
    path: Any, curve_samples: int = 24
) -> list[tuple[float, float]]:
    """从路径提取 (x, y) 数据点，曲线按采样点展开。"""
    points: list[tuple[float, float]] = []
    for item in path["items"]:
        op = item[0]
        if op == "l":
            p1, p2 = item[1], item[2]
            if not points or abs(points[-1][0] - p1.x) > 1e-9 or abs(points[-1][1] - p1.y) > 1e-9:
                points.append((p1.x, p1.y))
            points.append((p2.x, p2.y))
        elif op == "c":
            p1, c1, c2, p2 = item[1], item[2], item[3], item[4]
            if not points or abs(points[-1][0] - p1.x) > 1e-9 or abs(points[-1][1] - p1.y) > 1e-9:
                points.append((p1.x, p1.y))
            points.extend(bezier_points(p1, c1, c2, p2, curve_samples)[1:])
    return points
