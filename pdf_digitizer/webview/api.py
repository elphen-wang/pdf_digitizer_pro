"""pywebview 的 Python 后端。

界面通过 ``window.pywebview.api`` 调用本类的方法；PDF 解析、定标映射、
筛选导出全部复用 ``pdf_digitizer`` 的核心模块。
"""

from __future__ import annotations

import base64
import io
import math
import threading
from collections.abc import Callable
from typing import Any

from .. import __version__
from ..calibration import (
    CALIBRATION_FIELDS,
    DEFAULT_CALIBRATION_VALUES,
    map_point,
)
from ..core import PdfSource
from ..filters import (
    MAX_PREVIEW_ROWS,
    Point,
    apply_stride,
    filter_points,
    format_clipboard,
    sort_points,
    write_export,
)
from ..i18n import LANG_MAP, translate

DEFAULT_RENDER_SCALE = 2.0
DEFAULT_SEPARATOR = "\t"
ALLOWED_SEPARATORS = ("\t", ",", " ")
AXIS_LABELS = ("X1", "X2", "Y1", "Y2")

OpenDialog = Callable[[], str | None]
SaveDialog = Callable[[str, tuple[str, ...]], str | None]


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


class WebViewApi:
    """暴露给前端 JavaScript 的接口。"""

    def __init__(
        self,
        window_getter: Callable[[], Any] | None = None,
        open_dialog: OpenDialog | None = None,
        save_dialog: SaveDialog | None = None,
        render_scale: float = DEFAULT_RENDER_SCALE,
    ) -> None:
        self._window_getter = window_getter
        self._open_dialog = open_dialog
        self._save_dialog = save_dialog
        self._render_scale = render_scale
        self._lock = threading.Lock()

        self._source: PdfSource | None = None
        self._calib_points: dict[str, tuple[float, float] | None] = {
            field: None for field in CALIBRATION_FIELDS
        }
        self._calib_values: dict[str, float] = dict(DEFAULT_CALIBRATION_VALUES)
        self._step = 0
        self._data: list[Point] = []
        self._highlight: list[tuple[float, float]] = []

    # --- 窗口 / 文件对话框 ---

    def _get_window(self) -> Any:
        if self._window_getter is not None:
            return self._window_getter()
        import webview  # 延迟导入，便于无窗口测试

        windows = getattr(webview, "windows", [])
        return windows[0] if windows else None

    def _default_open_dialog(self) -> str | None:
        import webview

        window = self._get_window()
        if window is None:
            return None
        result = window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=False,
            file_types=("PDF/SVG files (*.pdf *.svg)",),
        )
        if not result:
            return None
        return result[0] if isinstance(result, (list, tuple)) else str(result)

    def _default_save_dialog(self, filename: str, file_types: tuple[str, ...]) -> str | None:
        import webview

        window = self._get_window()
        if window is None:
            return None
        result = window.create_file_dialog(
            webview.FileDialog.SAVE,
            save_filename=filename,
            file_types=file_types,
        )
        if not result:
            return None
        return result[0] if isinstance(result, (list, tuple)) else str(result)

    def close_window(self) -> None:
        window = self._get_window()
        if window is not None:
            window.destroy()

    # --- 文档 ---

    def open_pdf(self) -> dict[str, Any]:
        dialog = self._open_dialog or self._default_open_dialog
        path = dialog()
        if not path:
            return self._failure(None)

        with self._lock:
            try:
                source = PdfSource(path, self._render_scale)
            except Exception as error:  # noqa: BLE001 - 文件可能损坏或加密
                return self._failure(f"无法打开文件: {error}")

            previous = self._source
            self._source = source
            self._data = []
            self._highlight = []
            self._reset_calibration_locked()

            buffer = io.BytesIO()
            source.image.save(buffer, format="PNG")
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

            if previous is not None:
                previous.close()

            return {
                "ok": True,
                "error": None,
                "image": f"data:image/png;base64,{encoded}",
                "width": source.image.width,
                "height": source.image.height,
            }

    def close(self) -> None:
        with self._lock:
            if self._source is not None:
                self._source.close()
                self._source = None

    # --- 定标 ---

    def reset_calibration(self) -> dict[str, Any]:
        with self._lock:
            self._reset_calibration_locked()
            return {"ok": True}

    def record_calibration(
        self, index: int, rel_x: float, rel_y: float, value: float
    ) -> dict[str, Any]:
        with self._lock:
            if self._source is None:
                return {"ok": False, "complete": False, "error": "no_pdf"}
            if not isinstance(index, int) or index != self._step:
                return {
                    "ok": False,
                    "complete": False,
                    "error": f"unexpected_index:{index}",
                }
            try:
                rel_x = float(rel_x)
                rel_y = float(rel_y)
                value = float(value)
            except (TypeError, ValueError):
                return {"ok": False, "complete": False, "error": "invalid_value"}
            if not all(math.isfinite(number) for number in (rel_x, rel_y, value)):
                return {"ok": False, "complete": False, "error": "invalid_value"}
            if not (0.0 <= rel_x <= 1.0 and 0.0 <= rel_y <= 1.0):
                return {"ok": False, "complete": False, "error": "out_of_bounds"}

            field = CALIBRATION_FIELDS[index]
            self._calib_points[field] = (rel_x, rel_y)
            self._calib_values[field] = value
            self._step += 1
            return {
                "ok": True,
                "complete": self._step >= len(CALIBRATION_FIELDS),
                "error": None,
            }

    def _reset_calibration_locked(self) -> None:
        self._step = 0
        self._calib_points = {field: None for field in CALIBRATION_FIELDS}
        self._calib_values = dict(DEFAULT_CALIBRATION_VALUES)

    def _is_calibrated(self) -> bool:
        return all(self._calib_points[field] is not None for field in CALIBRATION_FIELDS)

    # --- 曲线 ---

    def pick_curve(
        self, rel_x: float, rel_y: float, log_x: bool, log_y: bool
    ) -> dict[str, Any]:
        with self._lock:
            if self._source is None:
                return self._failure("no_pdf")
            if not self._is_calibrated():
                return self._failure("not_calibrated")
            try:
                rel_x = float(rel_x)
                rel_y = float(rel_y)
            except (TypeError, ValueError):
                return self._failure("invalid_value")
            if not (0.0 <= rel_x <= 1.0 and 0.0 <= rel_y <= 1.0):
                return self._failure("out_of_bounds")

            source = self._source
            pdf_x = rel_x * source.width
            pdf_y = rel_y * source.height
            path = source.find_path(pdf_x, pdf_y)
            if path is None:
                return self._failure("no_curve")

            pdf_points = source.path_points(path)
            rel_points = [
                (x / source.width, y / source.height) for x, y in pdf_points
            ]
            mapped = [
                map_point(
                    point_x,
                    point_y,
                    self._calib_points,
                    self._calib_values,
                    bool(log_x),
                    bool(log_y),
                )
                for point_x, point_y in rel_points
            ]
            self._data = mapped
            self._highlight = rel_points
            return {
                "ok": True,
                "error": None,
                "points": [[x, y] for x, y in mapped],
                "highlight": [[x, y] for x, y in rel_points],
            }

    # --- 数据 ---

    def process_data(self, filters: dict[str, Any] | None) -> dict[str, Any]:
        with self._lock:
            rows = self._filtered_rows(filters)
            return {
                "rows": [[x, y] for x, y in rows[:MAX_PREVIEW_ROWS]],
                "total": len(rows),
            }

    def copy_text(self, filters: dict[str, Any] | None, separator: str) -> str:
        with self._lock:
            return format_clipboard(
                self._filtered_rows(filters), self._safe_separator(separator)
            )

    def save_export(
        self, filters: dict[str, Any] | None, separator: str
    ) -> dict[str, Any]:
        with self._lock:
            rows = self._filtered_rows(filters)
            dialog = self._save_dialog or self._default_save_dialog
            path = dialog("data.txt", ("TXT (*.txt)", "CSV (*.csv)"))
            if not path:
                return {"ok": False, "error": None}
            try:
                write_export(rows, path, self._safe_separator(separator))
            except OSError as error:
                return {"ok": False, "error": str(error)}
            return {"ok": True, "error": None}

    def _filtered_rows(self, filters: dict[str, Any] | None) -> list[Point]:
        filters = filters or {}
        rows = filter_points(
            self._data,
            _optional_float(filters.get("xmin")),
            _optional_float(filters.get("xmax")),
            _optional_float(filters.get("ymin")),
            _optional_float(filters.get("ymax")),
        )
        try:
            step = int(filters.get("step", 1))
        except (TypeError, ValueError):
            step = 1
        rows = apply_stride(rows, step)
        sort_col = filters.get("sort_col")
        if sort_col in (1, 2):
            rows = sort_points(rows, int(sort_col), bool(filters.get("desc", False)))
        return rows

    @staticmethod
    def _safe_separator(separator: str) -> str:
        return separator if separator in ALLOWED_SEPARATORS else DEFAULT_SEPARATOR

    # --- 文案 ---

    def get_strings(self, lang: str) -> dict[str, str]:
        language = lang if lang in ("CN", "EN") else "CN"
        return {key: translate(language, key) for key in LANG_MAP}

    def get_version(self) -> str:
        return __version__

    @staticmethod
    def _failure(error: str | None) -> dict[str, Any]:
        return {
            "ok": False,
            "error": error,
            "image": None,
            "width": 0,
            "height": 0,
            "points": [],
            "highlight": [],
        }
