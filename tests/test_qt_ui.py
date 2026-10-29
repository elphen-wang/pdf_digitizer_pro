"""Qt 界面的交互测试（离屏运行，覆盖真实事件路径）。"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import fitz
import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pdf_digitizer.qt.data_dialog import DataDialog
from pdf_digitizer.qt.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture()
def pdf_path(tmp_path: Path) -> Path:
    path = tmp_path / "chart.pdf"
    document = fitz.open()
    page = document.new_page(width=200, height=200)
    page.draw_line(fitz.Point(50, 150), fitz.Point(150, 50), width=2)
    document.save(path)
    document.close()
    return path


@pytest.fixture()
def window(qapp: QApplication, pdf_path: Path):
    main = MainWindow()
    main.resize(900, 700)
    main.show()
    qapp.processEvents()
    main.load_path(str(pdf_path))
    main.view.fit_image()
    qapp.processEvents()
    yield main
    main.close()
    qapp.processEvents()


def click_scene(window: MainWindow, qapp: QApplication, x: float, y: float) -> None:
    position = window.view.mapFromScene(QPointF(x, y))
    QTest.mouseClick(
        window.view.viewport(), Qt.MouseButton.LeftButton, pos=position
    )
    qapp.processEvents()


def complete_calibration(window: MainWindow, qapp: QApplication) -> None:
    window.start_axis()
    qapp.processEvents()
    for index, (x, y) in enumerate(((20, 20), (380, 20), (20, 380), (380, 380))):
        click_scene(window, qapp, x, y)
        assert window.calib_overlay.isVisible()
        window.calib_overlay.line_edit.setText(str(index + 1))
        QTest.keyClick(window.calib_overlay.line_edit, Qt.Key.Key_Return)
        qapp.processEvents()


@pytest.mark.integration
def test_load_path_renders_page(window: MainWindow) -> None:
    assert window.source is not None
    assert window.hq_image is not None
    assert window.hq_image.size == (400, 400)
    assert window.actions["btn_axis"].isEnabled()
    assert not window.actions["btn_select"].isEnabled()


@pytest.mark.integration
def test_click_in_calibration_mode_opens_overlay(
    window: MainWindow, qapp: QApplication
) -> None:
    window.start_axis()
    qapp.processEvents()
    click_scene(window, qapp, 200, 200)

    assert window.calib_overlay.isVisible()
    assert window.pending_calib is not None
    assert window.calib_overlay.line_edit.text()


@pytest.mark.integration
def test_four_points_complete_calibration(
    window: MainWindow, qapp: QApplication
) -> None:
    complete_calibration(window, qapp)

    assert window.mode == "VIEW"
    assert window.calib_values == {"x1": 1.0, "x2": 2.0, "y1": 3.0, "y2": 4.0}
    assert window.actions["btn_select"].isEnabled()
    assert len(window.marker_records) == 4


@pytest.mark.integration
def test_cancel_does_not_advance(window: MainWindow, qapp: QApplication) -> None:
    window.start_axis()
    qapp.processEvents()
    click_scene(window, qapp, 100, 100)

    QTest.keyClick(window.calib_overlay.line_edit, Qt.Key.Key_Escape)
    qapp.processEvents()

    assert window.axis_step == 0
    assert window.pending_calib is None
    assert not window.calib_overlay.isVisible()


@pytest.mark.integration
def test_pick_curve_extracts_points_and_opens_dialog(
    window: MainWindow, qapp: QApplication
) -> None:
    complete_calibration(window, qapp)
    window.start_pick()
    qapp.processEvents()

    click_scene(window, qapp, 300, 100)  # 线段端点 pdf (150, 50) * render_scale 2

    assert window.extracted_data
    assert window.highlight_item is not None
    assert len(window.dialogs) == 1


@pytest.mark.integration
def test_loads_svg_natively(qapp: QApplication, tmp_path: Path) -> None:
    svg_path = tmp_path / "chart.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">'
        '<line x1="50" y1="150" x2="150" y2="50" stroke="black" stroke-width="2"/>'
        "</svg>",
        encoding="utf-8",
    )

    window = MainWindow()
    window.resize(900, 700)
    window.show()
    window.load_path(str(svg_path))
    qapp.processEvents()
    try:
        assert window.source is not None
        assert window.hq_image is not None
        assert window.hq_image.size == (400, 400)
        assert window.source.drawings
    finally:
        window.close()
        qapp.processEvents()


@pytest.mark.unit
def test_drag_path_filter_accepts_pdf_and_svg(qapp: QApplication) -> None:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile("/tmp/chart.svg")])
    assert MainWindow._first_supported_path(mime) == "/tmp/chart.svg"

    unsupported = QMimeData()
    unsupported.setUrls([QUrl.fromLocalFile("/tmp/notes.txt")])
    assert MainWindow._first_supported_path(unsupported) is None


@pytest.mark.integration
def test_data_dialog_filters_stride_and_sorts(qapp: QApplication) -> None:
    data = [(0.0, 10.0), (1.0, 20.0), (2.0, 30.0), (3.0, 40.0)]
    dialog = DataDialog(None, data, "CN")
    try:
        dialog.e_xmin.setText("1")
        dialog.e_xmax.setText("2")
        dialog.process_data()
        assert dialog.display_data == [(1.0, 20.0), (2.0, 30.0)]

        dialog.e_xmin.clear()
        dialog.e_xmax.clear()
        dialog.stride_spin.setValue(2)
        qapp.processEvents()
        assert dialog.display_data == [(0.0, 10.0), (2.0, 30.0)]

        dialog._on_header_clicked(2)
        assert dialog.display_data == [(0.0, 10.0), (2.0, 30.0)]

        dialog._on_header_clicked(2)
        assert dialog.display_data == [(2.0, 30.0), (0.0, 10.0)]
        assert dialog.table.rowCount() == 2
    finally:
        dialog.close()
