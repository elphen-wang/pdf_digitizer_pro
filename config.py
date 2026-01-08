"""Configuration module for PDF Digitizer Pro.

This module contains all global configuration including language mappings,
UI constants, and application settings.
"""

from typing import Dict, Any

# Language mapping for UI text
LANG_MAP: Dict[str, Dict[str, str]] = {
    "title": {"CN": "PDF 矢量提取器", "EN": "PDF Extractor"},
    
    # --- 工具栏 ---
    "btn_open": {"CN": "📂 打开", "EN": "📂 Open"},
    "btn_zi": {"CN": "➕ 放大", "EN": "➕ In"},
    "btn_zo": {"CN": "➖ 缩小", "EN": "➖ Out"},
    "btn_rv": {"CN": "⛶ 适应", "EN": "⛶ Fit"},
    "btn_lng": {"CN": "En/中", "EN": "En/CN"},
    
    "lbl_step1": {"CN": "1.定标:", "EN": "1.Calib:"},
    "btn_axis": {"CN": "🎯 设定坐标", "EN": "🎯 Set Axis"},
    "btn_reset_axis": {"CN": "↺ 重置", "EN": "↺ Reset"},
    "chk_log_x": {"CN": "Log-X", "EN": "Log-X"},
    "chk_log_y": {"CN": "Log-Y", "EN": "Log-Y"},
    
    "lbl_step2": {"CN": "2.提取:", "EN": "2.Extract:"},
    "btn_select": {"CN": "📈 拾取曲线", "EN": "📈 Pick Line"},
    "btn_data": {"CN": "📊 数据表", "EN": "📊 Data"},
    "btn_exit": {"CN": "❌", "EN": "❌"},
    
    # --- 状态栏 ---
    "status_ready": {"CN": "就绪 - 请打开 PDF", "EN": "Ready - Open PDF"},
    "status_axis": {"CN": "【定标中】请点击图中位置: ", "EN": "[Calib] Click point: "},
    "status_pick": {"CN": "【提取中】请点击目标曲线", "EN": "[Pick] Click curve"},
    "status_done": {"CN": "定标完成", "EN": "Calib Done"},
    
    # --- 数据窗口 ---
    "data_win_title": {"CN": "数据筛选与导出", "EN": "Filter & Export"},
    
    "grp_filter": {"CN": "范围筛选", "EN": "Filter"},
    "lbl_xmin": {"CN": "XMin:", "EN": "XMin:"},
    "lbl_xmax": {"CN": "XMax:", "EN": "XMax:"},
    "lbl_ymin": {"CN": "YMin:", "EN": "YMin:"},
    "lbl_ymax": {"CN": "YMax:", "EN": "YMax:"},
    "btn_apply": {"CN": "刷新数据", "EN": "Refresh"},
    
    "grp_export": {"CN": "导出选项", "EN": "Export"},
    "lbl_step": {"CN": "采样间隔:", "EN": "Stride:"},
    "lbl_sep": {"CN": "分隔符:", "EN": "Sep:"},
    "sep_tab": {"CN": "Tab", "EN": "Tab"},
    "sep_comma": {"CN": "Comma", "EN": "Comma"},
    "sep_space": {"CN": "Space", "EN": "Space"},
    
    "col_idx": {"CN": "序号", "EN": "Idx"},
    "col_x": {"CN": "X", "EN": "X"},
    "col_y": {"CN": "Y", "EN": "Y"},
    
    "btn_copy": {"CN": "复制", "EN": "Copy"},
    "btn_save": {"CN": "保存", "EN": "Save"},
    
    "msg_no_curve": {"CN": "此处无矢量数据", "EN": "No vector data"},
    "msg_copy_ok": {"CN": "已复制", "EN": "Copied"},
    "msg_save_ok": {"CN": "保存成功", "EN": "Saved"},
}

# Application constants
DEFAULT_WINDOW_SIZE = "1100x800"
DEFAULT_DATA_WINDOW_SIZE = "480x650"

# PDF processing constants
BASE_SCALE = 2.0  # Base scale factor for PDF rendering
MIN_VIEW_SCALE = 0.1  # Minimum zoom level
MAX_VIEW_SCALE = 4.0  # Maximum zoom level
ZOOM_IN_FACTOR = 1.2  # Zoom in multiplier
ZOOM_OUT_FACTOR = 0.8  # Zoom out multiplier

# Image processing constants
MAGNIFIER_SIZE = 150  # Size of magnifier window
MAGNIFIER_CROP_RADIUS = 30  # Crop radius for magnifier
MAGNIFIER_ZOOM_RATIO = MAGNIFIER_SIZE / (MAGNIFIER_CROP_RADIUS * 2)

# Calibration constants
CALIBRATION_POINTS = ["x1", "x2", "y1", "y2"]
CALIBRATION_DEFAULT_VALUES = {
    "x1": 0.0,
    "x2": 100.0,
    "y1": 0.0,
    "y2": 100.0,
}

# Curve extraction constants
SEARCH_RADIUS = 5.0  # Search radius for curve picking (in PDF coordinates)
MIN_DISTANCE_EPSILON = 1e-9  # Minimum distance for coordinate mapping

# Data processing constants
TABLE_PREVIEW_LIMIT = 2000  # Maximum rows to preview in table
MIN_STEP_VALUE = 1  # Minimum stride value for data sampling
MAX_STEP_VALUE = 99999  # Maximum stride value

# UI constants
OVERLAY_INPUT_WIDTH = 160  # Width of overlay input widget
OVERLAY_INPUT_OFFSET_X = 15  # X offset for overlay input
OVERLAY_INPUT_OFFSET_Y = 15  # Y offset for overlay input
MARKER_SIZE = 3  # Size of calibration markers
MARKER_COLOR = "#00FF00"  # Color for calibration markers
HIGHLIGHT_COLOR = "cyan"  # Color for extracted curve highlight
HIGHLIGHT_WIDTH = 2  # Width of highlight line

# Mouse event throttling
MOVE_THROTTLE_INTERVAL = 0.016  # Throttle interval for mouse move events (seconds, ~60fps)

# Magnifier performance optimization
MAGNIFIER_CACHE_THRESHOLD = 2.0  # Position change threshold for cache reuse (pixels, smaller = more updates)
MAGNIFIER_UPDATE_DELAY = 16  # Delay for non-critical updates (milliseconds)
MAGNIFIER_CACHE_SIZE = 2  # Number of cached images to keep (reduced for better responsiveness)

# Marker coordinate caching
MARKER_COORD_CACHE_ENABLED = True  # Enable marker coordinate caching

# Image interpolation method
# Use LANCZOS for better quality, NEAREST for speed
IMAGE_INTERPOLATION = "LANCZOS"  # Options: "LANCZOS", "NEAREST", "BILINEAR", "BICUBIC"

# Default language
DEFAULT_LANGUAGE = "CN"

# Supported file formats
SUPPORTED_PDF_EXTENSIONS = [".pdf"]
SUPPORTED_SVG_EXTENSIONS = [".svg"]
SUPPORTED_IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".bmp", ".gif"]  # For future use

