# 开发指南 / Development Guide

## 环境 / Requirements

- Python 3.10+
- macOS：Qt 与 pywebview 均可运行；Windows/Linux 可从源码运行 Qt 版
- 依赖见 `requirements.txt` / `requirements-dev.txt`

## 初始化 / Setup

```bash
git clone https://github.com/elphen-wang/pdf_digitizer_pro.git
cd pdf_digitizer_pro

python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

## 运行 / Run

```bash
./run.sh                              # Qt 版
.venv/bin/python main_webview.py      # pywebview 版
```

需要指定解释器时：

```bash
PYTHON_BIN=/path/to/python3 ./run.sh
```

## 测试 / Testing

```bash
.venv/bin/python -m pytest -q
```

测试覆盖：

- `tests/test_calibration.py`：线性/对数映射、退化区间
- `tests/test_filters.py`：筛选、采样、排序、复制文本、TXT/CSV 导出
- `tests/test_geometry.py`：点到线段距离、贝塞尔采样
- `tests/test_core.py`：真实 PDF 的渲染与路径命中
- `tests/test_qt_ui.py`：离屏 `QTest` 真实点击流程
- `tests/test_webview_api.py`：pywebview 后端 API

## 静态检查 / Lint

```bash
.venv/bin/python -m ruff check . --exclude build,dist,.venv
node --check pdf_digitizer/webview/web/app.js
```

## 构建 / Build

```bash
./build_macos.sh              # dist/PDF Digitizer.app
./build_macos_webview.sh      # dist/PDF Digitizer Web.app
```

构建脚本会创建隔离的 `.venv` 并安装 `requirements-dev.txt`。可用 `PYTHON=/path/to/python3` 指定基础解释器。

## 代码约定 / Conventions

- 核心算法只放在 `pdf_digitizer/` 顶层模块，界面层不得复制算法。
- 新增界面文案必须同时补充 `i18n.py` 中的 `CN` 与 `EN`。
- 定标输入使用非模态控件，不要用阻塞式模态对话框。
- 文件、用户输入与 API 参数都要校验；非法值返回明确的 `error` 字段。
- 新增功能需补充 pytest 测试，保持全部通过。

## 常见问题 / Troubleshooting

- **PyInstaller 报 `pathlib` 反向移植包错误**：说明构建环境继承了宿主 conda 的 site-packages。删除 `.venv` 后由构建脚本重新创建（脚本默认隔离）。
- **应用被 Gatekeeper 拦截**：右键「打开」，或 `xattr -dr com.apple.quarantine <app>`。
- **无法读取 `~/Downloads`**：这是 macOS TCC 权限限制，与应用本身无关；首次选择文件时授权即可。
- **pywebview 窗口空白**：确认 `pdf_digitizer/webview/web` 已作为数据文件打包（见 `PdfDigitizerWeb.spec`）。
