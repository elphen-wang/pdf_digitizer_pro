# Changelog / 更新日志

## 1.3.0 — Desktop rewrite / 桌面前端重写

### Added / 新增

- PySide6/Qt frontend as the default UI, with native widgets and reliable mouse handling.
- SVG support through PyMuPDF's native reader, and drag-and-drop opening for `.pdf`/`.svg` in the Qt build.
- pywebview frontend using the system WKWebView (no Electron, no external browser).
- Non-modal inline calibration input with Enter/Esc support.
- Canvas pan (left-drag in view mode), double-click fit and wheel zoom.
- Self-contained macOS bundles (`PDF Digitizer.app`, `PDF Digitizer Web.app`).
- 55 automated tests, including Qt `QTest` interaction tests and pywebview backend tests.
- Bilingual README and changelog.

### Changed / 变更

- Core engine separated from the UI: `core.py`, `calibration.py`, `geometry.py`, `filters.py`, `i18n.py`.
- `main.py` now launches the Qt application; `main_webview.py` launches the pywebview application.
- Build scripts create an isolated virtual environment and accept a portable `PYTHON` override.

### Fixed / 修复

- Buttons and canvas clicks could require several attempts on macOS 26 with the old Tk build. Qt and WKWebView use native event delivery.
- Calibration no longer uses a blocking modal dialog that could be hidden behind the main window.
- The window is brought to the foreground on launch, so the first click is delivered.

### Removed / 移除

- The Tk implementation is no longer the entry point. It remains under `pdf_digitizer/ui/` for reference.
- Obsolete dependencies (`tkinterdnd2`, `svglib`, `reportlab`) are no longer required: SVG, drag-and-drop and PDF handling are native.
