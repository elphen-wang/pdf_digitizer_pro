"""画布内联的定标数值输入条（非模态）。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QToolButton, QWidget

OFFSET_X = 18
OFFSET_Y = 10
MIN_WIDTH = 200
INVALID_STYLE = "border: 1px solid #d00; background: #ffe5e5;"
NORMAL_STYLE = "border: 1px solid #9bb4cc; background: #ffffff;"


class CalibrationOverlay(QWidget):
    """点击定标点后出现在光标旁的输入条。"""

    confirmed = Signal(float)
    cancelled = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("calibrationOverlay")
        self.setStyleSheet(
            "#calibrationOverlay { background: #f4f7fa; border: 1px solid #0057b8;"
            " border-radius: 4px; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 6, 4)
        layout.setSpacing(6)

        self.label = QLabel("X1 =", self)
        self.label.setStyleSheet("color: #0057b8; font-weight: 600;")
        layout.addWidget(self.label)

        self.line_edit = QLineEdit(self)
        self.line_edit.setFixedWidth(120)
        self.line_edit.setStyleSheet(NORMAL_STYLE)
        self.line_edit.returnPressed.connect(self._confirm)
        self.line_edit.installEventFilter(self)
        layout.addWidget(self.line_edit)

        self.ok_button = QToolButton(self)
        self.ok_button.setText("✔")
        self.ok_button.setToolTip("确认 (Enter)")
        self.ok_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_button.clicked.connect(self._confirm)
        layout.addWidget(self.ok_button)

        self.adjustSize()
        self.hide()

    # --- 显示 ---

    def show_at(self, position: QPoint, label: str, default: float) -> None:
        self.label.setText(f"{label} =")
        self.line_edit.setStyleSheet(NORMAL_STYLE)
        self.line_edit.setText(f"{default:g}")
        self.adjustSize()

        parent = self.parentWidget()
        x = position.x() + OFFSET_X
        y = position.y() - self.height() - OFFSET_Y
        if x + self.width() > parent.width():
            x = position.x() - self.width() - OFFSET_X
        x = max(0, min(x, parent.width() - self.width()))
        y = max(0, min(y, parent.height() - self.height()))

        self.move(x, y)
        self.show()
        self.raise_()
        self.line_edit.setFocus()
        self.line_edit.selectAll()

    def hide_overlay(self) -> None:
        self.hide()

    def is_open(self) -> bool:
        return self.isVisible()

    # --- 交互 ---

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt 命名
        if (
            watched is self.line_edit
            and event.type() == QEvent.Type.KeyPress
            and event.key() == Qt.Key.Key_Escape
        ):
            self._cancel()
            return True
        return super().eventFilter(watched, event)

    def _confirm(self) -> None:
        try:
            value = float(self.line_edit.text())
        except ValueError:
            self.line_edit.setStyleSheet(INVALID_STYLE)
            return
        self.hide()
        self.confirmed.emit(value)

    def _cancel(self) -> None:
        self.hide()
        self.cancelled.emit()
