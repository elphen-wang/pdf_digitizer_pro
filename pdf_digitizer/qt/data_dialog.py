"""数据筛选与导出窗口（Qt 版）。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..filters import (
    MAX_PREVIEW_ROWS,
    Point,
    apply_stride,
    filter_points,
    format_clipboard,
    parse_optional_float,
    separator_from_index,
    sort_points,
    write_export,
)
from ..i18n import translate

COLUMN_LABELS = ("idx", "x", "y")


class DataDialog(QDialog):
    """显示提取结果，支持范围筛选、采样、排序、复制与导出。"""

    def __init__(self, parent: QWidget | None, full_data: list[Point] | None, lang: str) -> None:
        super().__init__(parent)
        self.full_data: list[Point] = list(full_data or [])
        self.display_data: list[Point] = []
        self.lang = lang
        self.sort_col: int | None = None
        self.sort_desc = False

        self.resize(500, 680)
        self._build_ui()
        self.update_lang_ui()
        self.separator_combo.setCurrentIndex(0)
        self.stride_spin.setValue(1)
        self.process_data()

    # --- 构建 ---

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.filter_group = QGroupBox(self)
        grid = QGridLayout(self.filter_group)
        grid.setContentsMargins(10, 10, 10, 10)

        self.lbl_xmin = QLabel("XMin:", self)
        self.e_xmin = QLineEdit(self)
        self.lbl_xmax = QLabel("XMax:", self)
        self.e_xmax = QLineEdit(self)
        self.lbl_ymin = QLabel("YMin:", self)
        self.e_ymin = QLineEdit(self)
        self.lbl_ymax = QLabel("YMax:", self)
        self.e_ymax = QLineEdit(self)

        for entry in (self.e_xmin, self.e_xmax, self.e_ymin, self.e_ymax):
            entry.setFixedWidth(90)
            entry.returnPressed.connect(self.process_data)

        grid.addWidget(self.lbl_xmin, 0, 0)
        grid.addWidget(self.e_xmin, 0, 1)
        grid.addWidget(self.lbl_xmax, 0, 2)
        grid.addWidget(self.e_xmax, 0, 3)
        grid.addWidget(self.lbl_ymin, 1, 0)
        grid.addWidget(self.e_ymin, 1, 1)
        grid.addWidget(self.lbl_ymax, 1, 2)
        grid.addWidget(self.e_ymax, 1, 3)

        self.btn_apply = QPushButton(self)
        self.btn_apply.clicked.connect(self.process_data)
        grid.addWidget(self.btn_apply, 0, 4, 2, 1)

        layout.addWidget(self.filter_group)

        self.export_group = QGroupBox(self)
        export_layout = QVBoxLayout(self.export_group)
        export_layout.setContentsMargins(10, 10, 10, 10)

        line1 = QHBoxLayout()
        self.lbl_step = QLabel(self)
        self.stride_spin = QSpinBox(self)
        self.stride_spin.setRange(1, 99999)
        self.stride_spin.valueChanged.connect(self.process_data)
        self.lbl_sep = QLabel(self)
        self.separator_combo = QComboBox(self)
        self.separator_combo.setFixedWidth(110)
        line1.addWidget(self.lbl_step)
        line1.addWidget(self.stride_spin)
        line1.addSpacing(12)
        line1.addWidget(self.lbl_sep)
        line1.addWidget(self.separator_combo)
        line1.addStretch(1)
        export_layout.addLayout(line1)

        line2 = QHBoxLayout()
        self.btn_copy = QPushButton(self)
        self.btn_copy.clicked.connect(self.copy_to_clipboard)
        self.btn_save = QPushButton(self)
        self.btn_save.clicked.connect(self.export_file)
        line2.addWidget(self.btn_copy)
        line2.addWidget(self.btn_save)
        export_layout.addLayout(line2)

        self.lbl_count = QLabel("", self)
        self.lbl_count.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_count.setStyleSheet("color: #666;")
        export_layout.addWidget(self.lbl_count)

        layout.addWidget(self.export_group)

        self.table = QTableWidget(0, 3, self)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 70)
        header.sectionClicked.connect(self._on_header_clicked)
        layout.addWidget(self.table, 1)

    # --- 语言 ---

    def t(self, key: str) -> str:
        return translate(self.lang, key)

    def update_lang_ui(self, new_lang: str | None = None) -> None:
        if new_lang:
            self.lang = new_lang
        self.setWindowTitle(self.t("data_win_title"))
        self.filter_group.setTitle(self.t("grp_filter"))
        self.lbl_xmin.setText(self.t("lbl_xmin"))
        self.lbl_xmax.setText(self.t("lbl_xmax"))
        self.lbl_ymin.setText(self.t("lbl_ymin"))
        self.lbl_ymax.setText(self.t("lbl_ymax"))
        self.btn_apply.setText(self.t("btn_apply"))
        self.export_group.setTitle(self.t("grp_export"))
        self.lbl_step.setText(self.t("lbl_step"))
        self.lbl_sep.setText(self.t("lbl_sep"))
        self.btn_copy.setText(self.t("btn_copy"))
        self.btn_save.setText(self.t("btn_save"))

        current = max(0, self.separator_combo.currentIndex())
        self.separator_combo.clear()
        self.separator_combo.addItems(
            [self.t("sep_tab"), self.t("sep_comma"), self.t("sep_space")]
        )
        self.separator_combo.setCurrentIndex(current)

        self._update_headers()
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem(self.t("col_idx")))
        self.update_count_label()

    def _update_headers(self) -> None:
        arrow = " ▼" if self.sort_desc else " ▲"
        label_x = self.t("col_x")
        label_y = self.t("col_y")
        if self.sort_col == 1:
            label_x += arrow
        elif self.sort_col == 2:
            label_y += arrow
        self.table.setHorizontalHeaderItem(1, QTableWidgetItem(label_x))
        self.table.setHorizontalHeaderItem(2, QTableWidgetItem(label_y))

    # --- 数据 ---

    def process_data(self) -> None:
        xmin = parse_optional_float(self.e_xmin.text())
        xmax = parse_optional_float(self.e_xmax.text())
        ymin = parse_optional_float(self.e_ymin.text())
        ymax = parse_optional_float(self.e_ymax.text())
        filtered = filter_points(self.full_data, xmin, xmax, ymin, ymax)
        self.display_data = apply_stride(filtered, self.stride_spin.value())
        self.refresh_table()
        self.update_count_label()

    def refresh_table(self) -> None:
        preview = self.display_data[:MAX_PREVIEW_ROWS]
        self.table.setRowCount(len(preview))
        for row, (x, y) in enumerate(preview):
            index_item = QTableWidgetItem(str(row + 1))
            index_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            x_item = QTableWidgetItem(f"{x:.5g}")
            x_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            y_item = QTableWidgetItem(f"{y:.5g}")
            y_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, index_item)
            self.table.setItem(row, 1, x_item)
            self.table.setItem(row, 2, y_item)

    def update_count_label(self) -> None:
        count = len(self.display_data)
        message = f"Total: {count} pts"
        if count > MAX_PREVIEW_ROWS:
            message += " | Previewing top 2000 (Export for all)"
        self.lbl_count.setText(message)

    def _on_header_clicked(self, column: int) -> None:
        if column not in (1, 2):
            return
        if self.sort_col == column:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = column
            self.sort_desc = False
        self.display_data = sort_points(self.display_data, column, self.sort_desc)
        self._update_headers()
        self.refresh_table()

    # --- 导出 ---

    def _separator(self) -> str:
        return separator_from_index(self.separator_combo.currentIndex())

    def copy_to_clipboard(self) -> None:
        QApplication.clipboard().setText(
            format_clipboard(self.display_data, self._separator())
        )
        QMessageBox.information(self, "OK", self.t("msg_copy_ok"))

    def export_file(self) -> None:
        path, _selected = QFileDialog.getSaveFileName(
            self,
            self.t("btn_save"),
            "",
            "TXT (*.txt);;CSV (*.csv)",
        )
        if not path:
            return
        try:
            write_export(self.display_data, Path(path), self._separator())
        except OSError as error:
            QMessageBox.critical(self, "Error", str(error))
            return
        QMessageBox.information(self, "OK", self.t("msg_save_ok"))
