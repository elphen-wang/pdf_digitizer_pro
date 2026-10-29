"""数据筛选与导出窗口。"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

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

WINDOW_SIZE = "480x650"


class DataWindow(tk.Toplevel):
    """显示提取结果，支持范围筛选、采样、排序、复制与导出。"""

    def __init__(
        self,
        parent: tk.Misc,
        full_data: list[Point] | None,
        lang_code: str,
        app_ref: Any,
    ) -> None:
        super().__init__(parent)
        self.full_data: list[Point] = full_data or []
        self.display_data: list[Point] = []
        self.lang = lang_code
        self.app = app_ref
        self.app.sub_windows.append(self)

        self.title("Data")
        self.geometry(WINDOW_SIZE)

        self.main_frame = tk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.setup_controls()
        self.setup_table()

        self.spin_step.delete(0, "end")
        self.spin_step.insert(0, "1")

        self.update_lang_ui()
        self.cmb_sep.current(0)

        self.after(100, self.process_data)

    # --- 布局 ---

    def setup_controls(self) -> None:
        lf_filter = ttk.LabelFrame(self.main_frame, text="Filter", padding=5)
        lf_filter.pack(fill=tk.X, padx=5, pady=5)

        grid = tk.Frame(lf_filter)
        grid.pack(fill=tk.X)

        self.lbl_xmin = tk.Label(grid, text="XMin:")
        self.lbl_xmin.grid(row=0, column=0, sticky="e")
        self.e_xmin = tk.Entry(grid, width=7)
        self.e_xmin.grid(row=0, column=1, padx=2)

        self.lbl_xmax = tk.Label(grid, text="XMax:")
        self.lbl_xmax.grid(row=0, column=2, sticky="e")
        self.e_xmax = tk.Entry(grid, width=7)
        self.e_xmax.grid(row=0, column=3, padx=2)

        self.lbl_ymin = tk.Label(grid, text="YMin:")
        self.lbl_ymin.grid(row=1, column=0, sticky="e")
        self.e_ymin = tk.Entry(grid, width=7)
        self.e_ymin.grid(row=1, column=1, padx=2)

        self.lbl_ymax = tk.Label(grid, text="YMax:")
        self.lbl_ymax.grid(row=1, column=2, sticky="e")
        self.e_ymax = tk.Entry(grid, width=7)
        self.e_ymax.grid(row=1, column=3, padx=2)

        self.btn_apply = ttk.Button(grid, command=self.process_data)
        self.btn_apply.grid(row=0, column=4, rowspan=2, padx=5, sticky="ns")

        for entry in (self.e_xmin, self.e_xmax, self.e_ymin, self.e_ymax):
            entry.bind("<Return>", lambda _event: self.process_data())

        lf_export = ttk.LabelFrame(self.main_frame, text="Export", padding=5)
        lf_export.pack(fill=tk.X, padx=5, pady=5)

        line1 = tk.Frame(lf_export)
        line1.pack(fill=tk.X, pady=2)

        self.lbl_step = tk.Label(line1)
        self.lbl_step.pack(side=tk.LEFT)
        self.spin_step = tk.Spinbox(
            line1, from_=1, to=99999, width=5, command=self.process_data
        )
        self.spin_step.bind("<Return>", lambda _event: self.process_data())
        self.spin_step.pack(side=tk.LEFT, padx=5)

        self.lbl_sep = tk.Label(line1)
        self.lbl_sep.pack(side=tk.LEFT, padx=(10, 0))
        self.sep_var = tk.StringVar()
        self.cmb_sep = ttk.Combobox(
            line1, textvariable=self.sep_var, state="readonly", width=10
        )
        self.cmb_sep.pack(side=tk.LEFT, padx=5)

        line2 = tk.Frame(lf_export)
        line2.pack(fill=tk.X, pady=5)
        self.btn_copy = ttk.Button(line2, command=self.copy_to_clipboard)
        self.btn_copy.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.btn_save = ttk.Button(line2, command=self.export_file)
        self.btn_save.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        self.lbl_count = tk.Label(lf_export, text="", fg="#666")
        self.lbl_count.pack(anchor="e")

        self.lf_filter = lf_filter
        self.lf_export = lf_export

    def setup_table(self) -> None:
        table = tk.Frame(self.main_frame)
        table.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(table, columns=("idx", "x", "y"), show="headings")
        self.tree.column("idx", width=50, anchor="center")
        self.tree.column("x", width=140, anchor="center")
        self.tree.column("y", width=140, anchor="center")

        self.tree.heading("x", command=lambda: self.sort_data(1))
        self.tree.heading("y", command=lambda: self.sort_data(2))

        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.sort_col: int | None = None
        self.sort_desc = False

    # --- 语言 ---

    def t(self, key: str) -> str:
        return translate(self.lang, key)

    def update_lang_ui(self, new_lang: str | None = None) -> None:
        if new_lang:
            self.lang = new_lang
        self.title(self.t("data_win_title"))
        self.lf_filter.config(text=self.t("grp_filter"))
        self.lbl_xmin.config(text=self.t("lbl_xmin"))
        self.lbl_xmax.config(text=self.t("lbl_xmax"))
        self.lbl_ymin.config(text=self.t("lbl_ymin"))
        self.lbl_ymax.config(text=self.t("lbl_ymax"))
        self.btn_apply.config(text=self.t("btn_apply"))
        self.lf_export.config(text=self.t("grp_export"))
        self.lbl_step.config(text=self.t("lbl_step"))
        self.lbl_sep.config(text=self.t("lbl_sep"))
        self.btn_copy.config(text=self.t("btn_copy"))
        self.btn_save.config(text=self.t("btn_save"))
        self.tree.heading("idx", text=self.t("col_idx"))
        self.update_headers()
        values = [self.t("sep_tab"), self.t("sep_comma"), self.t("sep_space")]
        index = self.cmb_sep.current()
        self.cmb_sep["values"] = values
        self.cmb_sep.current(index if index >= 0 else 0)
        self.update_count_label()

    def update_headers(self) -> None:
        arrow = " ▼" if self.sort_desc else " ▲"
        label_x, label_y = self.t("col_x"), self.t("col_y")
        if self.sort_col == 1:
            label_x += arrow
        elif self.sort_col == 2:
            label_y += arrow
        self.tree.heading("x", text=label_x)
        self.tree.heading("y", text=label_y)

    # --- 数据处理 ---

    def process_data(self) -> None:
        xmin = parse_optional_float(self.e_xmin.get())
        xmax = parse_optional_float(self.e_xmax.get())
        ymin = parse_optional_float(self.e_ymin.get())
        ymax = parse_optional_float(self.e_ymax.get())

        try:
            step = int(self.spin_step.get())
        except ValueError:
            step = 1

        filtered = filter_points(self.full_data, xmin, xmax, ymin, ymax)
        self.display_data = apply_stride(filtered, step)
        self.refresh_table()
        self.update_count_label()

    def refresh_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for index, (x, y) in enumerate(self.display_data[:MAX_PREVIEW_ROWS]):
            self.tree.insert("", "end", values=(index + 1, f"{x:.5g}", f"{y:.5g}"))

    def update_count_label(self) -> None:
        count = len(self.display_data)
        message = f"Total: {count} pts"
        if count > MAX_PREVIEW_ROWS:
            message += " | Previewing top 2000 (Export for all)"
        self.lbl_count.config(text=message)

    def sort_data(self, column: int) -> None:
        if self.sort_col == column:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = column
            self.sort_desc = False
        self.display_data = sort_points(self.display_data, column, self.sort_desc)
        self.update_headers()
        self.refresh_table()

    def get_sep_char(self) -> str:
        return separator_from_index(self.cmb_sep.current())

    # --- 导出 ---

    def copy_to_clipboard(self) -> None:
        content = format_clipboard(self.display_data, self.get_sep_char())
        self.clipboard_clear()
        self.clipboard_append(content)
        messagebox.showinfo("OK", self.t("msg_copy_ok"), parent=self)

    def export_file(self) -> None:
        separator = self.get_sep_char()
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("TXT", "*.txt"), ("CSV", "*.csv")],
        )
        if not path:
            return
        try:
            write_export(self.display_data, path, separator)
            messagebox.showinfo("OK", self.t("msg_save_ok"), parent=self)
        except OSError as error:
            messagebox.showerror("Error", str(error))
