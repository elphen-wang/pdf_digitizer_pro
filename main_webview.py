"""PDF Digitizer 桌面应用入口（pywebview 版）。"""

from __future__ import annotations

import sys
from pathlib import Path

import webview

from pdf_digitizer.webview.api import WebViewApi

APP_NAME = "PDF Digitizer Web"
WINDOW_SIZE = (1100, 820)
MIN_SIZE = (820, 620)


def _resource_root() -> Path:
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return Path(bundled)
    return Path(__file__).resolve().parent


def main() -> None:
    api = WebViewApi(window_getter=lambda: window)
    html_path = _resource_root() / "pdf_digitizer" / "webview" / "web" / "index.html"

    window = webview.create_window(
        APP_NAME,
        url=str(html_path),
        js_api=api,
        width=WINDOW_SIZE[0],
        height=WINDOW_SIZE[1],
        min_size=MIN_SIZE,
        background_color="#eef2f6",
    )
    window.events.closed += lambda: api.close()
    webview.start()


if __name__ == "__main__":
    main()
