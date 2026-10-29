"""界面文案字典与翻译函数。"""

from __future__ import annotations

DEFAULT_LANGUAGE = "CN"
SUPPORTED_LANGUAGES = ("CN", "EN")

LANG_MAP: dict[str, dict[str, str]] = {
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
    "msg_need_axis": {
        "CN": "请先点「🎯 设定坐标」定标，再点「📈 拾取曲线」",
        "EN": "Click 'Set Axis' to calibrate first, then 'Pick Line'",
    },
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


def translate(lang: str, key: str) -> str:
    """返回指定语言的文案；缺失时回退到 key 本身。"""
    return LANG_MAP.get(key, {}).get(lang, key)
