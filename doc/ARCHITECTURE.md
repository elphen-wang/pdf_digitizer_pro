# 项目架构 / Architecture

## 概览 / Overview

本项目把「PDF 矢量提取引擎」与「桌面界面」完全分离。两套界面共用同一套核心模块，因此行为、数据和测试完全一致。

```text
┌────────────────────┐        ┌──────────────────────────┐
│ Qt 界面             │        │ pywebview 界面            │
│ pdf_digitizer/qt/   │        │ pdf_digitizer/webview/    │
│ PySide6             │        │ HTML/CSS/JS + Python API  │
└─────────┬──────────┘        └────────────┬─────────────┘
          └──────────────┬─────────────────┘
                         ▼
            核心引擎 pdf_digitizer/
     core · calibration · geometry · filters · i18n
```

## 模块 / Modules

| 模块 | 职责 |
|---|---|
| `pdf_digitizer/core.py` | 打开 PDF/SVG、2× 渲染首页、读取矢量路径、点击命中、提取路径点 |
| `pdf_digitizer/calibration.py` | 四点定标的线性/对数映射，把相对坐标转换为数据坐标 |
| `pdf_digitizer/geometry.py` | 点到线段距离、三次贝塞尔采样、路径点展开 |
| `pdf_digitizer/filters.py` | 范围筛选、采样间隔、排序、剪贴板文本、TXT/CSV 导出 |
| `pdf_digitizer/i18n.py` | 中英文文案字典与 `translate()` |
| `pdf_digitizer/qt/` | PySide6 界面：主窗口、画布、定标输入条、数据窗口 |
| `pdf_digitizer/webview/` | pywebview 界面：API 类、`index.html`、`style.css`、`app.js` |
| `pdf_digitizer/ui/` | 旧 Tk 实现，仅作参考，不作为入口 |

## 数据流 / Data flow

1. **加载**：`PdfSource(path, render_scale=2.0)` 读取第一页的绘图指令，并以 2× 渲染为 `PIL.Image`。PyMuPDF 原生支持 SVG，因此无需 svglib/reportlab。
2. **定标**：用户在图上点击 X1、X2、Y1、Y2，界面记录相对坐标 `(rel_x, rel_y)` 并输入真实数值。
   - X 轴只取两个定标点的 x 分量，Y 轴只取 y 分量。
   - 对数轴使用 `log10` 插值。
3. **拾取**：点击位置先换算为 PDF 坐标 `scene / render_scale`，`PdfSource.find_path()` 在半径 5 pt 内寻找最近的矢量路径。
4. **映射**：路径端点 → PDF 坐标 → 相对坐标 → `map_point()` → 数据坐标。
5. **输出**：`filters.py` 负责筛选、采样、排序与导出；界面只负责展示和交互。

## 线程与状态 / Threading

- Qt 版所有界面逻辑运行在 Qt 主线程。
- pywebview 的 API 调用运行在独立线程；`WebViewApi` 用一把互斥锁保护 PDF、定标与数据状态。
- 文件对话框通过 `window.create_file_dialog()` 调用，测试时可注入替代函数。

## 打包 / Packaging

- `PdfDigitizer.spec`：Qt 版，PyInstaller onedir + macOS BUNDLE。
- `PdfDigitizerWeb.spec`：pywebview 版，包含 `pdf_digitizer/webview/web` 数据文件与 cocoa/pyobjc 隐藏导入。
- 构建脚本创建隔离的 `.venv`，避免宿主 conda 环境中的废弃包（如 `pathlib` 反向移植）干扰 PyInstaller。
- 图标由 `scripts/make_icon.py` 生成 PNG 与 ICNS。

## 扩展 / Extending

新增一种界面（例如 Web 前端、命令行批处理）时，只需：

1. 复用 `PdfSource`、`map_point()` 和 `filters.py`；
2. 实现「打开 → 定标 → 拾取 → 展示/导出」四个交互；
3. 为界面层补充测试，核心算法无需改动。
