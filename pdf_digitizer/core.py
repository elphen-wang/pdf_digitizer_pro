"""PDF 加载、矢量路径命中与点提取。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz
from PIL import Image

DEFAULT_RENDER_SCALE = 2.0
DEFAULT_PICK_RADIUS = 5.0


class PdfSource:
    """一份已渲染的 PDF 页面及其矢量绘图数据。"""

    def __init__(self, path: str | Path, render_scale: float = DEFAULT_RENDER_SCALE) -> None:
        self.render_scale = render_scale
        self.document = fitz.open(str(path))
        self.page = self.document[0]
        self.drawings: list[dict[str, Any]] = self.page.get_drawings()
        matrix = fitz.Matrix(render_scale, render_scale)
        pixmap = self.page.get_pixmap(matrix=matrix, alpha=False)
        self.image = Image.frombytes(
            "RGB", [pixmap.width, pixmap.height], pixmap.samples
        )

    @property
    def width(self) -> float:
        return self.page.rect.width

    @property
    def height(self) -> float:
        return self.page.rect.height

    def close(self) -> None:
        self.document.close()

    def find_path(
        self, pdf_x: float, pdf_y: float, radius: float = DEFAULT_PICK_RADIUS
    ) -> dict[str, Any] | None:
        """返回点击位置附近最近的矢量路径；超出半径返回 None。"""
        best_path: dict[str, Any] | None = None
        min_dist_sq = float("inf")
        for path in self.drawings:
            rect = path["rect"]
            if (
                pdf_x < rect.x0 - radius
                or pdf_x > rect.x1 + radius
                or pdf_y < rect.y0 - radius
                or pdf_y > rect.y1 + radius
            ):
                continue
            for item in path["items"]:
                point = item[-1]
                if hasattr(point, "x"):
                    dist_sq = (point.x - pdf_x) ** 2 + (point.y - pdf_y) ** 2
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        best_path = path
        if best_path is not None and min_dist_sq < radius**2:
            return best_path
        return None

    @staticmethod
    def path_points(path: dict[str, Any]) -> list[tuple[float, float]]:
        """提取路径的端点（线段取两端，曲线取控制点与端点）。"""
        points: list[tuple[float, float]] = []
        for item in path["items"]:
            op = item[0]
            if op == "l":
                points.extend([(item[1].x, item[1].y), (item[2].x, item[2].y)])
            elif op == "c":
                points.extend(
                    [
                        (item[1].x, item[1].y),
                        (item[2].x, item[2].y),
                        (item[3].x, item[3].y),
                        (item[4].x, item[4].y),
                    ]
                )
        return points
