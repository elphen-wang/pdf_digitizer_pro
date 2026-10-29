"""PySide6 主窗口。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QPoint, QPointF, QSize, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QKeySequence,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsSimpleTextItem,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QToolBar,
    QWidget,
)

from .. import __version__
from ..calibration import DEFAULT_CALIBRATION_VALUES, map_point
from ..core import PdfSource
from ..i18n import DEFAULT_LANGUAGE, translate
from .calibration_overlay import CalibrationOverlay
from .data_dialog import DataDialog
from .image_view import ImageView, pil_to_qimage

WINDOW_SIZE = QSize(1100, 820)
RENDER_SCALE = 2.0
SUPPORTED_SUFFIXES = (".pdf", ".svg")

AXIS_LABELS = ("X1", "X2", "Y1", "Y2")
AXIS_FIELDS = ("x1", "x2", "y1", "y2")

TOOLBAR_ACTIONS = (
    "btn_open",
    "btn_zi",
    "btn_zo",
    "btn_rv",
    "btn_lng",
    "btn_axis",
    "btn_reset_axis",
    "btn_select",
    "btn_data",
    "btn_exit",
)


class MainWindow(QMainWindow):
    """PDF 定标与曲线提取主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.lang = DEFAULT_LANGUAGE
        self.source: PdfSource | None = None
        self.hq_image = None
        self.render_scale = RENDER_SCALE

        self.calib_points: dict[str, tuple[float, float] | None] = {
            field: None for field in AXIS_FIELDS
        }
        self.calib_values: dict[str, float] = dict(DEFAULT_CALIBRATION_VALUES)
        self.marker_records: list[dict[str, Any]] = []
        self.marker_items: list[Any] = []
        self.highlight_item: QGraphicsPathItem | None = None

        self.mode = "VIEW"
        self.axis_step = 0
        self.pending_calib: tuple[float, float] | None = None
        self.extracted_data: list[tuple[float, float]] = []
        self.dialogs: list[DataDialog] = []

        self.resize(WINDOW_SIZE)
        self.setAcceptDrops(True)
        self._build_ui()
        self.refresh_ui()

    # --- 构建界面 ---

    def _build_ui(self) -> None:
        self.view = ImageView(self)
        self.setCentralWidget(self.view)
        self.view.clicked.connect(self._on_image_clicked)

        self.calib_overlay = CalibrationOverlay(self.view.viewport())
        self.calib_overlay.confirmed.connect(self._on_calib_confirmed)
        self.calib_overlay.cancelled.connect(self._on_calib_cancelled)

        self.toolbar = QToolBar("Main", self)
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.toolbar.setIconSize(QSize(18, 18))
        self.addToolBar(self.toolbar)

        self.actions: dict[str, QAction] = {}
        self._add_action("btn_open", self.open_pdf, QKeySequence.StandardKey.Open)
        self._add_action("btn_zi", self.view.zoom_in)
        self._add_action("btn_zo", self.view.zoom_out)
        self._add_action("btn_rv", self.view.fit_image)
        self._add_action("btn_lng", self.toggle_lang)
        self.toolbar.addSeparator()

        self.lbl_step1 = QLabel(self)
        self.lbl_step1.setStyleSheet("color: #0057b8; font-weight: 600;")
        self.toolbar.addWidget(self.lbl_step1)
        self._add_action("btn_axis", self.start_axis)
        self._add_action("btn_reset_axis", self.reset_axis)
        self.chk_log_x = QCheckBox(self)
        self.chk_log_y = QCheckBox(self)
        self.toolbar.addWidget(self.chk_log_x)
        self.toolbar.addWidget(self.chk_log_y)
        self.toolbar.addSeparator()

        self.lbl_step2 = QLabel(self)
        self.lbl_step2.setStyleSheet("color: #1a7f37; font-weight: 600;")
        self.toolbar.addWidget(self.lbl_step2)
        self._add_action("btn_select", self.start_pick)
        self._add_action("btn_data", self.show_data)

        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)
        self._add_action("btn_exit", self.close)

        self.statusBar().setSizeGripEnabled(True)

    def _add_action(self, key: str, handler, shortcut=None) -> QAction:
        action = QAction(self)
        action.triggered.connect(handler)
        if shortcut is not None:
            action.setShortcut(shortcut)
        self.toolbar.addAction(action)
        self.actions[key] = action
        return action

    def refresh_ui(self) -> None:
        self.setWindowTitle(f"{self.t('title')} v{__version__}")
        for key in TOOLBAR_ACTIONS:
            self.actions[key].setText(self.t(key))
        self.lbl_step1.setText(self.t("lbl_step1"))
        self.lbl_step2.setText(self.t("lbl_step2"))
        self.chk_log_x.setText(self.t("chk_log_x"))
        self.chk_log_y.setText(self.t("chk_log_y"))
        self.update_status()

    def t(self, key: str) -> str:
        return translate(self.lang, key)

    def toggle_lang(self) -> None:
        self.lang = "EN" if self.lang == "CN" else "CN"
        self.refresh_ui()
        for dialog in self.dialogs:
            if dialog.isVisible():
                dialog.update_lang_ui(self.lang)

    # --- 文件 ---

    def open_pdf(self) -> None:
        path, _selected = QFileDialog.getOpenFileName(
            self, self.t("btn_open"), "", "PDF/SVG (*.pdf *.svg)"
        )
        if not path:
            return
        try:
            self.load_path(path)
        except Exception as error:  # noqa: BLE001 - 文件可能损坏或加密
            QMessageBox.critical(self, "Error", f"无法打开文件:\n{error}")

    @staticmethod
    def _first_supported_path(mime_data) -> str | None:
        if not mime_data.hasUrls():
            return None
        for url in mime_data.urls():
            if not url.isLocalFile():
                continue
            candidate = Path(url.toLocalFile())
            if candidate.suffix.lower() in SUPPORTED_SUFFIXES:
                return str(candidate)
        return None

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 - Qt 命名
        if self._first_supported_path(event.mimeData()) is not None:
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 - Qt 命名
        path = self._first_supported_path(event.mimeData())
        if path is None:
            return
        event.acceptProposedAction()
        try:
            self.load_path(path)
        except Exception as error:  # noqa: BLE001 - 文件可能损坏或加密
            QMessageBox.critical(self, "Error", f"无法打开文件:\n{error}")

    def load_path(self, path: str) -> None:
        """加载 PDF（与文件对话框解耦，便于测试）。"""
        source = PdfSource(path, self.render_scale)
        previous = self.source
        self.source = source
        self.hq_image = source.image

        self.mode = "VIEW"
        self.axis_step = 0
        self.pending_calib = None
        self.calib_points = {field: None for field in AXIS_FIELDS}
        self.calib_values = dict(DEFAULT_CALIBRATION_VALUES)
        self.marker_records.clear()
        self.marker_items.clear()
        self.highlight_item = None
        self.extracted_data = []

        self.calib_overlay.hide_overlay()
        self.view.set_image(pil_to_qimage(source.image))
        self.view.set_markers([])
        self.view.set_magnifier_enabled(False)
        QTimer.singleShot(0, self.view.fit_image)

        if previous is not None:
            previous.close()

        self.actions["btn_axis"].setEnabled(True)
        self.actions["btn_reset_axis"].setEnabled(True)
        self.actions["btn_select"].setEnabled(False)
        self.view.setCursor(Qt.CursorShape.ArrowCursor)
        self.update_status()

    # --- 定标 ---

    def start_axis(self) -> None:
        if self.source is None:
            return
        self.mode = "SET_AXIS"
        self.axis_step = 0
        self.pending_calib = None
        self.actions["btn_axis"].setEnabled(False)
        self.actions["btn_select"].setEnabled(False)
        self.view.set_magnifier_enabled(True)
        self.view.setCursor(Qt.CursorShape.CrossCursor)
        self.calib_overlay.hide_overlay()
        self.update_status()

    def reset_axis(self) -> None:
        self.mode = "VIEW"
        self.axis_step = 0
        self.pending_calib = None
        self.calib_points = {field: None for field in AXIS_FIELDS}
        self.calib_values = dict(DEFAULT_CALIBRATION_VALUES)
        self.marker_records.clear()
        self.view.set_markers([])
        self._clear_marker_items()
        self.calib_overlay.hide_overlay()
        self.view.set_magnifier_enabled(False)
        self.view.setCursor(Qt.CursorShape.ArrowCursor)
        self.actions["btn_axis"].setEnabled(True)
        self.actions["btn_select"].setEnabled(False)
        self.update_status()

    def start_pick(self) -> None:
        self.mode = "SELECT_CURVE"
        self.calib_overlay.hide_overlay()
        self.view.set_magnifier_enabled(False)
        self.view.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_status()

    def _on_image_clicked(self, scene_pos: QPointF, viewport_pos: QPoint) -> None:
        if self.source is None or self.hq_image is None:
            return
        width, height = self.hq_image.size
        x, y = scene_pos.x(), scene_pos.y()
        if x < 0 or y < 0 or x > width or y > height:
            return

        if self.mode == "SET_AXIS":
            self.pending_calib = (x / width, y / height)
            key = AXIS_LABELS[self.axis_step]
            default = self.calib_values[AXIS_FIELDS[self.axis_step]]
            self.view.set_magnifier_enabled(False)
            self.calib_overlay.show_at(viewport_pos, key, default)
            return

        if self.mode == "SELECT_CURVE":
            pdf_x = x / self.render_scale
            pdf_y = y / self.render_scale
            self._handle_pick(pdf_x, pdf_y)
            return

        self.statusBar().showMessage(self.t("msg_need_axis"))

    def _on_calib_confirmed(self, value: float) -> None:
        if self.pending_calib is None:
            return
        rel_x, rel_y = self.pending_calib
        self.pending_calib = None
        field = AXIS_FIELDS[self.axis_step]
        self.calib_points[field] = (rel_x, rel_y)
        self.calib_values[field] = value
        self._add_marker(rel_x, rel_y, value, field.upper())

        self.axis_step += 1
        if self.axis_step < len(AXIS_LABELS):
            self.view.set_magnifier_enabled(True)
            self.update_status()
            return

        self.mode = "VIEW"
        self.view.set_magnifier_enabled(False)
        self.view.setCursor(Qt.CursorShape.ArrowCursor)
        self.actions["btn_select"].setEnabled(True)
        self.update_status()

    def _on_calib_cancelled(self) -> None:
        self.pending_calib = None
        self.view.set_magnifier_enabled(True)
        self.update_status()

    def _add_marker(self, rel_x: float, rel_y: float, value: float, label: str) -> None:
        if self.hq_image is None:
            return
        width, height = self.hq_image.size
        x, y = rel_x * width, rel_y * height

        ellipse = self.view.scene().addEllipse(
            x - 4, y - 4, 8, 8, QPen(QColor("black"), 1), QColor("#00ff66")
        )
        ellipse.setZValue(20)

        text = QGraphicsSimpleTextItem(f"{label}={value:g}")
        text.setBrush(QColor("#00ff66"))
        text.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        text.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        text.setPos(x + 6, y - 6)
        text.setZValue(21)
        self.view.scene().addItem(text)

        self.marker_items.extend([ellipse, text])
        self.marker_records.append(
            {"rx": rel_x, "ry": rel_y, "val": value, "key": label}
        )
        self.view.set_markers(
            [
                (record["rx"] * width, record["ry"] * height, record["key"])
                for record in self.marker_records
            ]
        )

    def _clear_marker_items(self) -> None:
        scene = self.view.scene()
        for item in self.marker_items:
            if item.scene() is scene:
                scene.removeItem(item)
        self.marker_items.clear()
        self.view.set_markers([])

    # --- 曲线提取 ---

    def _handle_pick(self, pdf_x: float, pdf_y: float) -> None:
        assert self.source is not None
        path = self.source.find_path(pdf_x, pdf_y)
        if path is None:
            QMessageBox.information(self, "Tip", self.t("msg_no_curve"))
            return
        self.extract_data(path)

    def extract_data(self, path: dict[str, Any]) -> None:
        assert self.source is not None
        assert self.hq_image is not None

        pdf_points = self.source.path_points(path)
        rel_points = [
            (x / self.source.width, y / self.source.height) for x, y in pdf_points
        ]
        result = [
            map_point(
                rel_x,
                rel_y,
                self.calib_points,
                self.calib_values,
                self.chk_log_x.isChecked(),
                self.chk_log_y.isChecked(),
            )
            for rel_x, rel_y in rel_points
        ]
        self.extracted_data = result
        self._draw_highlight(rel_points)

        dialog = DataDialog(self, result, self.lang)
        dialog.show()
        self.dialogs.append(dialog)

    def _draw_highlight(self, rel_points: list[tuple[float, float]]) -> None:
        if self.hq_image is None:
            return
        width, height = self.hq_image.size
        scene = self.view.scene()
        if self.highlight_item is not None and self.highlight_item.scene() is scene:
            scene.removeItem(self.highlight_item)

        if len(rel_points) < 2:
            self.highlight_item = None
            return

        path = QPainterPath()
        first_x, first_y = rel_points[0]
        path.moveTo(first_x * width, first_y * height)
        for rel_x, rel_y in rel_points[1:]:
            path.lineTo(rel_x * width, rel_y * height)

        pen = QPen(QColor("cyan"), 2)
        pen.setCosmetic(True)
        item = scene.addPath(path, pen)
        item.setZValue(10)
        self.highlight_item = item

    def show_data(self) -> None:
        if not self.extracted_data:
            return
        dialog = DataDialog(self, self.extracted_data, self.lang)
        dialog.show()
        self.dialogs.append(dialog)

    # --- 状态 ---

    def update_status(self) -> None:
        if self.mode == "VIEW":
            if self.calib_points["x1"] is not None:
                mode_x = "Log" if self.chk_log_x.isChecked() else "Lin"
                mode_y = "Log" if self.chk_log_y.isChecked() else "Lin"
                message = f"{self.t('status_done')} | X:{mode_x} Y:{mode_y}"
            else:
                message = self.t("status_ready")
        elif self.mode == "SET_AXIS":
            key = AXIS_LABELS[self.axis_step] if self.axis_step < len(AXIS_LABELS) else ""
            message = self.t("status_axis") + key
        else:
            message = self.t("status_pick")
        self.statusBar().showMessage(message)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt 命名
        if self.source is not None:
            self.source.close()
            self.source = None
        super().closeEvent(event)
