# PDF Vector Curve Extractor

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-Apache--2.0-green)
![Platform](https://img.shields.io/badge/platform-macOS%20app-lightgrey)

A native desktop application for extracting **vector curve data** from PDF charts — the upgraded desktop version of [pdf_digitizer_pro](https://github.com/elphen-wang/pdf_digitizer_pro). Open a PDF, calibrate four axis points (linear or logarithmic), click a curve, and get numeric data you can filter, sort and export.

Unlike raster digitizers, this tool reads the PDF's drawing commands through PyMuPDF, so coordinates come from the actual curve geometry instead of pixel guessing.

## Why this version

- **Two native frontends, one engine.** PySide6/Qt is the default UI; a pywebview build uses the system WKWebView. No Electron, no external browser, fully offline.
- **No more "click several times" on macOS.** The previous Tk 8.6 build could drop left-click events on macOS 26 when the app was not active. Qt and WKWebView use native event delivery, so buttons and calibration clicks respond immediately.
- **The engine is decoupled from the UI.** PDF parsing, calibration, geometry, filtering and i18n live in reusable modules, so both frontends share exactly the same behavior.
- **Self-contained macOS apps.** `PDF Digitizer.app` and `PDF Digitizer Web.app` bundle Python and every dependency; no environment setup is needed on the target machine.
- **55 automated tests**, including real Qt mouse-click tests that walk through four-point calibration, cancellation, curve picking and the data table.
- **Offline and local.** PDFs never leave your machine; no telemetry, no network calls.

## Features

1. **PDF and SVG vector extraction** — loads the first page, renders it at 2× and reads all vector paths with PyMuPDF. SVG is opened natively, with no extra conversion dependency.
2. **Four-point calibration** — click X1, X2, Y1, Y2 and enter their real values; supports linear and logarithmic axes (Log-X / Log-Y).
3. **Curve picking** — click a curve and the app selects the nearest vector path and converts every point into data coordinates.
4. **Precision magnifier** — a 150 px magnifier follows the cursor during calibration, showing nearby axis markers and a crosshair.
5. **Non-modal calibration input** — the value field appears next to the clicked point; no blocking dialog, Enter confirms, Esc cancels.
6. **Data table** — filter by X/Y ranges, downsample with a stride, sort by X or Y, and preview the first 2000 rows.
7. **Copy and export** — copy to the clipboard or export TXT/CSV with Tab, comma or space separators.
8. **Bilingual UI** — switch between Chinese and English at runtime.
9. **Canvas controls** — wheel zoom at the cursor, left-drag pan in view mode, double-click to fit, Retina/HiDPI rendering.

## Requirements

- Python 3.10+
- macOS 11+ for the prebuilt `.app` (built for Apple Silicon)
- The Qt build runs on Windows and Linux from source; the pywebview build needs a system webview (WKWebView on macOS, Edge WebView2 on Windows, GTK/Qt on Linux).

## Installation

```bash
git clone https://github.com/elphen-wang/pdf_digitizer_pro.git
cd pdf_digitizer_pro

python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

## Run

```bash
./run.sh                              # Qt version (default)
.venv/bin/python main_webview.py      # pywebview version
```

On Windows, run `.venv\Scripts\python.exe main.py` or `main_webview.py`.

## Build macOS apps

```bash
./build_macos.sh              # -> dist/PDF Digitizer.app      (Qt)
./build_macos_webview.sh      # -> dist/PDF Digitizer Web.app  (pywebview)
```

The scripts create an isolated `.venv`, install dependencies, generate the icon and run PyInstaller. Use `PYTHON=/path/to/python3` to build with a specific interpreter.

The generated apps are unsigned. On another Mac, right-click → **Open**, or run:

```bash
xattr -dr com.apple.quarantine "/Applications/PDF Digitizer.app"
```

## Usage

1. **Open** a PDF or SVG (the button or drag-and-drop in the Qt build). The first page is rendered and fitted to the window.
2. **Set Axis** (🎯), then click X1, X2, Y1, Y2. Type the real value in the field that appears and press Enter. Enable **Log-X / Log-Y** before calibrating if needed.
3. **Pick Line** (📈), then click the target curve. The data window opens with the extracted points.
4. Filter, choose a stride and separator, then **Copy** or **Save**.
5. Use **Reset** to recalibrate; **Data** reopens the last result.

## Project structure

```text
pdf_digitizer_desktop/
├── main.py                      Qt entry point (default)
├── main_webview.py              pywebview entry point
├── pdf_digitizer/
│   ├── core.py                  PDF loading, path hit-testing, point extraction
│   ├── calibration.py           pixel ↔ data coordinate mapping
│   ├── geometry.py              Bézier sampling and point-to-segment distance
│   ├── filters.py               filtering, stride, sorting, export
│   ├── i18n.py                  Chinese/English strings
│   ├── qt/                      PySide6 implementation
│   └── webview/                 pywebview API + HTML/CSS/JS frontend
├── tests/                       unit, integration and Qt interaction tests
├── scripts/make_icon.py         generates assets/icon.icns
├── PdfDigitizer.spec            Qt PyInstaller spec
├── PdfDigitizerWeb.spec         pywebview PyInstaller spec
├── build_macos.sh               build the Qt app
├── build_macos_webview.sh       build the pywebview app
└── requirements.txt             runtime dependencies
```

## Testing

```bash
.venv/bin/python -m pytest -q
```

The suite covers calibration mapping, filtering/export, geometry, real PDF loading, the pywebview backend API, and the Qt UI driven by real `QTest` mouse clicks (calibration, cancel, pick, data table).

## Compatibility and notes

- The prebuilt apps are arm64 and unsigned; see the Gatekeeper note above.
- The classic Tk implementation is kept under `pdf_digitizer/ui/` for reference and is **no longer the entry point**.
- The previous README note about sluggish controls is obsolete: it was caused by Tk's event handling on macOS 26 and does not apply to the Qt or pywebview frontends.
- Only the first page of a PDF/SVG is processed, as before.
- Drag-and-drop opening (`.pdf` / `.svg`) is available in the Qt build.
- Calibration requires four points; curve picking requires a completed calibration.

---

## 中文说明

一个从 PDF 图表中提取**矢量曲线数据**的原生桌面应用，是 [pdf_digitizer_pro](https://github.com/elphen-wang/pdf_digitizer_pro) 的桌面升级版。打开 PDF、标定四个坐标点（线性或对数）、点击曲线，即可得到可筛选、可排序、可导出的数值数据。

与基于像素的数字化工具不同，本程序通过 PyMuPDF 读取 PDF 的矢量绘图指令，坐标直接来自曲线几何，而不是在图像上猜点。

### 为什么升级

- **两套原生前端，共用一套引擎。** 默认使用 PySide6/Qt，另提供 pywebview 版（macOS 使用系统自带 WKWebView）。不使用 Electron，不启动外部浏览器，完全离线。
- **解决 macOS 上“点很多次才有反应”的问题。** 旧版 Tk 8.6 在 macOS 26 上会丢弃应用未激活时的左键事件；Qt 与 WKWebView 使用原生事件路径，按钮和定标点击即时响应。
- **核心引擎与界面解耦。** PDF 解析、定标映射、几何计算、筛选导出、中英文文案都是独立模块，两个前端行为完全一致。
- **自包含的 macOS 应用。** `PDF Digitizer.app` 与 `PDF Digitizer Web.app` 已打包 Python 与全部依赖，目标机器无需配置环境。
- **55 个自动化测试**，包含真实 Qt 鼠标点击流程：四点定标、取消、拾取曲线、数据表。
- **离线、本地。** PDF 不会离开本机，无遥测、无网络请求。

### 主要功能

1. **PDF / SVG 矢量提取**：加载第一页，以 2× 渲染，并读取全部矢量路径。SVG 由 PyMuPDF 原生打开，不需要额外的转换依赖。
2. **四点定标**：依次点击 X1、X2、Y1、Y2 并输入真实数值，支持线性轴与对数轴（Log-X / Log-Y）。
3. **曲线拾取**：点击曲线，自动选择最近的矢量路径，把每个点映射为数据坐标。
4. **高精度放大镜**：定标时跟随光标显示 150 px 放大镜，并标出附近已定的坐标点与十字准星。
5. **非模态定标输入**：数值输入条出现在点击位置旁边，不阻塞主窗口；Enter 确认，Esc 取消。
6. **数据表**：按 X/Y 范围筛选、按采样间隔稀疏、按 X/Y 排序，预览前 2000 行。
7. **复制与导出**：复制到剪贴板，或导出 TXT/CSV，支持 Tab、逗号、空格分隔符。
8. **中英文界面**：运行时可随时切换。
9. **画布操作**：滚轮以光标为中心缩放，VIEW 模式左键拖拽平移，双击恢复适应，支持 Retina/HiDPI。

### 环境要求

- Python 3.10 及以上
- 预打包 `.app` 需要 macOS 11+（Apple Silicon）
- Qt 版可在 Windows / Linux 从源码运行；pywebview 版依赖系统 WebView（macOS WKWebView、Windows Edge WebView2、Linux GTK/Qt）

### 安装

```bash
git clone https://github.com/elphen-wang/pdf_digitizer_pro.git
cd pdf_digitizer_pro

python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

### 运行

```bash
./run.sh                              # Qt 版（默认）
.venv/bin/python main_webview.py      # pywebview 版
```

Windows 下使用 `.venv\Scripts\python.exe main.py` 或 `main_webview.py`。

### 构建 macOS 应用

```bash
./build_macos.sh              # -> dist/PDF Digitizer.app      （Qt）
./build_macos_webview.sh      # -> dist/PDF Digitizer Web.app  （pywebview）
```

脚本会创建隔离的 `.venv`、安装依赖、生成图标并调用 PyInstaller。可用 `PYTHON=/path/to/python3` 指定解释器。

产物未签名。在其他 Mac 上首次打开请右键选择「打开」，或执行：

```bash
xattr -dr com.apple.quarantine "/Applications/PDF Digitizer.app"
```

### 使用流程

1. **打开** PDF 或 SVG（按钮或 Qt 版直接把文件拖进窗口），第一页会自动渲染并适应窗口。
2. 点 **🎯 设定坐标**，依次点击 X1、X2、Y1、Y2；在点击处出现的输入条中输入真实数值并回车。需要对数轴时提前勾选 **Log-X / Log-Y**。
3. 点 **📈 拾取曲线**，点击目标曲线，数据表自动打开。
4. 在数据表中筛选、设置采样间隔与分隔符，然后 **复制** 或 **保存**。
5. 点 **重置** 可重新定标；点 **数据表** 可重新打开最近一次结果。

### 目录结构

```text
pdf_digitizer_desktop/
├── main.py                      Qt 入口（默认）
├── main_webview.py              pywebview 入口
├── pdf_digitizer/
│   ├── core.py                  PDF 加载、路径命中、点提取
│   ├── calibration.py           像素坐标 ↔ 数据坐标
│   ├── geometry.py              贝塞尔采样、点到线段距离
│   ├── filters.py               筛选、采样、排序、导出
│   ├── i18n.py                  中英文文案
│   ├── qt/                      PySide6 实现
│   └── webview/                 pywebview API + HTML/CSS/JS 前端
├── tests/                       单元、集成与 Qt 交互测试
├── scripts/make_icon.py         生成 assets/icon.icns
├── PdfDigitizer.spec            Qt 版 PyInstaller 配置
├── PdfDigitizerWeb.spec         pywebview 版 PyInstaller 配置
├── build_macos.sh               构建 Qt 版
├── build_macos_webview.sh       构建 pywebview 版
└── requirements.txt             运行依赖
```

### 测试

```bash
.venv/bin/python -m pytest -q
```

覆盖坐标映射、筛选导出、几何工具、真实 PDF 加载、pywebview 后端 API，以及由真实 `QTest` 鼠标点击驱动的 Qt 界面流程（定标、取消、拾取、数据表）。

### 兼容性与说明

- 预打包应用为 arm64 且未签名，分发时请参考上面的 Gatekeeper 处理方式。
- 旧 Tk 实现保留在 `pdf_digitizer/ui/` 作为参考，**不再作为入口**。
- 旧 README 中“按键/控件切换有阻滞感”的说明已作废：那是 macOS 26 上 Tk 事件处理造成的问题，Qt 与 pywebview 前端不存在该现象。
- 与原版一致，仅处理 PDF/SVG 的第一页。
- Qt 版支持把 `.pdf` / `.svg` 直接拖入窗口打开。
- 必须先完成四点定标，才能拾取曲线。

## Example

<img width="1280" height="670" alt="image" src="https://github.com/user-attachments/assets/12447315-2ea3-48b9-8a12-487379545e38" />

<img width="1280" height="671" alt="image" src="https://github.com/user-attachments/assets/31048eea-9689-4389-a908-ad113a789610" />

**Note**: The figure of this example is taken from https://arxiv.org/abs/2411.11749 .

## 更多文档 / More Documentation

- [项目架构](doc/ARCHITECTURE.md) - 模块划分、数据流与打包
- [开发指南](doc/DEVELOPMENT.md) - 环境、测试、构建与约定

- [Project Architecture](doc/ARCHITECTURE.md) - modules, data flow and packaging
- [Development Guide](doc/DEVELOPMENT.md) - setup, testing, builds and conventions

## Cite this project

```text
@misc{pdf_digitizer_pro2026,
  author       = {J. Wang, X.Y. Wang},
  title        = {{PDF Vector Curve Extractor}},
  howpublished = {\url{https://github.com/elphen-wang/pdf_digitizer_pro}},
  year         = {2026},
  note         = {Accessed: 2026-01-08}
}
```

## License

Licensed under the Apache License, Version 2.0. See LICENSE file for details.

本项目采用 Apache License 2.0 许可，详见 LICENSE 文件。
