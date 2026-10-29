"""PDF Digitizer 桌面应用入口（PySide6）。"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from pdf_digitizer.qt.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("PDF Digitizer")
    app.setApplicationDisplayName("PDF Digitizer")

    window = MainWindow()
    window.show()
    window.raise_()
    window.activateWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
