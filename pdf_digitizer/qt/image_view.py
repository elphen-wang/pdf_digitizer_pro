"""可缩放画布与定标放大镜。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QImage,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QResizeEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QWidget

MIN_ZOOM = 0.1
MAX_ZOOM = 4.0
ZOOM_STEP = 1.2
MAGNIFIER_SIZE = 150
MAGNIFIER_SOURCE = 60
MAGNIFIER_OFFSET = 24


def pil_to_qimage(pil_image) -> QImage:
    """把 PIL.Image 转成自持内存的 QImage。"""
    rgb = pil_image.convert("RGB")
    data = rgb.tobytes("raw", "RGB")
    image = QImage(
        data, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888
    )
    return image.copy()


class Magnifier(QWidget):
    """画布上的放大镜，跟随光标显示局部图像与已定标点。"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedSize(MAGNIFIER_SIZE, MAGNIFIER_SIZE)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._crop: QPixmap | None = None
        self._crop_rect = QRectF()
        self._markers: list[tuple[float, float, str]] = []

    def update_content(
        self,
        image: QImage,
        scene_pos: QPointF,
        markers: list[tuple[float, float, str]],
    ) -> None:
        half = MAGNIFIER_SOURCE / 2
        left = max(0.0, min(scene_pos.x() - half, image.width() - MAGNIFIER_SOURCE))
        top = max(0.0, min(scene_pos.y() - half, image.height() - MAGNIFIER_SOURCE))
        rect = QRectF(left, top, MAGNIFIER_SOURCE, MAGNIFIER_SOURCE)

        crop = image.copy(rect.toRect())
        self._crop = QPixmap.fromImage(crop).scaled(
            MAGNIFIER_SIZE,
            MAGNIFIER_SIZE,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self._crop_rect = rect
        self._markers = markers
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt 命名
        painter = QPainter(self)
        if self._crop is not None:
            painter.drawPixmap(0, 0, self._crop)

        painter.setPen(QPen(QColor("#0078d7"), 2))
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))

        centre = self.rect().center()
        painter.setPen(QPen(QColor("#ff3b30"), 1))
        painter.drawLine(centre.x(), 0, centre.x(), self.height())
        painter.drawLine(0, centre.y(), self.width(), centre.y())

        if self._crop_rect.isEmpty():
            return
        scale = MAGNIFIER_SIZE / MAGNIFIER_SOURCE
        painter.setPen(QPen(QColor("#00ff66"), 2))
        for scene_x, scene_y, label in self._markers:
            if not self._crop_rect.contains(scene_x, scene_y):
                continue
            local_x = (scene_x - self._crop_rect.left()) * scale
            local_y = (scene_y - self._crop_rect.top()) * scale
            painter.drawEllipse(QPointF(local_x, local_y), 4, 4)
            painter.drawText(QPointF(local_x + 6, local_y - 4), label)


class ImageView(QGraphicsView):
    """显示 PDF 渲染图，提供缩放、适配与点击坐标。"""

    clicked = Signal(QPointF, QPoint)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._image: QImage | None = None
        self._markers: list[tuple[float, float, str]] = []
        self._magnifier_enabled = False

        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setMouseTracking(True)
        self.setBackgroundBrush(QColor("#555555"))
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )

        self._magnifier = Magnifier(self.viewport())
        self._magnifier.hide()

    # --- 图像 ---

    def set_image(self, image: QImage) -> None:
        self._scene.clear()
        self._image = image
        self._pixmap_item = self._scene.addPixmap(QPixmap.fromImage(image))
        self._scene.setSceneRect(QRectF(image.rect()))
        self._magnifier.hide()

    def fit_image(self) -> None:
        if self._pixmap_item is not None:
            self.fitInView(
                self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio
            )

    def zoom_by(self, factor: float) -> None:
        if self._pixmap_item is None:
            return
        current = self.transform().m11()
        target = current * factor
        clamped = max(MIN_ZOOM, min(target, MAX_ZOOM))
        if abs(clamped - current) < 1e-9:
            return
        self.scale(clamped / current, clamped / current)

    def zoom_in(self) -> None:
        self.zoom_by(ZOOM_STEP)

    def zoom_out(self) -> None:
        self.zoom_by(1 / ZOOM_STEP)

    def wheelEvent(self, event: QWheelEvent) -> None:  # noqa: N802 - Qt 命名
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 - Qt 命名
        super().resizeEvent(event)
        self._magnifier.raise_()

    # --- 放大镜 ---

    def set_magnifier_enabled(self, enabled: bool) -> None:
        self._magnifier_enabled = enabled
        if not enabled:
            self._magnifier.hide()

    def set_markers(self, markers: list[tuple[float, float, str]]) -> None:
        self._markers = markers

    def _update_magnifier(self, scene_pos: QPointF, cursor: QPoint) -> None:
        if self._image is None:
            return
        self._magnifier.update_content(self._image, scene_pos, self._markers)

        x = cursor.x() + MAGNIFIER_OFFSET
        y = cursor.y() - MAGNIFIER_SIZE - MAGNIFIER_OFFSET
        if y < 0:
            y = cursor.y() + MAGNIFIER_OFFSET
        viewport = self.viewport()
        x = max(0, min(x, viewport.width() - MAGNIFIER_SIZE))
        y = max(0, min(y, viewport.height() - MAGNIFIER_SIZE))
        self._magnifier.move(x, y)
        self._magnifier.raise_()
        self._magnifier.show()

    # --- 鼠标 ---

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt 命名
        if event.button() == Qt.MouseButton.LeftButton and self._pixmap_item is not None:
            position = event.position().toPoint()
            scene_pos = self.mapToScene(position)
            if self._scene.sceneRect().contains(scene_pos):
                self.clicked.emit(scene_pos, position)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 - Qt 命名
        if self._pixmap_item is not None and self._image is not None:
            position = event.position().toPoint()
            scene_pos = self.mapToScene(position)
            if self._magnifier_enabled and self._scene.sceneRect().contains(scene_pos):
                self._update_magnifier(scene_pos, position)
            else:
                self._magnifier.hide()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt 命名
        self._magnifier.hide()
        super().leaveEvent(event)
