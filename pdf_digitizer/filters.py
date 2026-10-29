"""数据筛选、采样、排序、格式化与导出。"""

from __future__ import annotations

import csv
from pathlib import Path

Point = tuple[float, float]

SEPARATORS = ("\t", ",", " ")
DEFAULT_STRIDE = 1
MAX_PREVIEW_ROWS = 2000


def parse_optional_float(text: str) -> float | None:
    """解析输入框文本；空串或非法值返回 None。"""
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


def filter_points(
    points: list[Point],
    xmin: float | None = None,
    xmax: float | None = None,
    ymin: float | None = None,
    ymax: float | None = None,
) -> list[Point]:
    """按 X/Y 范围闭区间筛选数据点。"""
    result: list[Point] = []
    for x, y in points:
        if xmin is not None and x < xmin:
            continue
        if xmax is not None and x > xmax:
            continue
        if ymin is not None and y < ymin:
            continue
        if ymax is not None and y > ymax:
            continue
        result.append((x, y))
    return result


def apply_stride(points: list[Point], step: int) -> list[Point]:
    """每 step 个点取 1 个；step 小于 1 时按 1 处理。"""
    return points[:: max(1, step)]


def sort_points(points: list[Point], column: int, descending: bool = False) -> list[Point]:
    """按列排序；column 为 1 表示 X，2 表示 Y。"""
    return sorted(points, key=lambda point: point[column - 1], reverse=descending)


def separator_from_index(index: int | None) -> str:
    """下拉框索引 -> 分隔符。"""
    if index == 1:
        return ","
    if index == 2:
        return " "
    return "\t"


def format_clipboard(points: list[Point], separator: str) -> str:
    """生成复制到剪贴板的两列文本。"""
    rows = "\n".join(f"{x}{separator}{y}" for x, y in points)
    return f"X{separator}Y\n{rows}"


def write_export(points: list[Point], path: str | Path, separator: str) -> None:
    """导出为 TXT/CSV。CSV 一律使用逗号分隔。"""
    destination = Path(path)
    separator = "," if destination.suffix.lower() == ".csv" else separator
    if separator == ",":
        with open(destination, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["X", "Y"])
            writer.writerows(points)
        return
    with open(destination, "w", encoding="utf-8") as handle:
        handle.write(f"X{separator}Y\n")
        for x, y in points:
            handle.write(f"{x}{separator}{y}\n")
