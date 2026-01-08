import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import math
import sys
import time
import csv

# ==========================================
# 0. 全局配置
# ==========================================
LANG_MAP = {
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
    # -------------------------------------------------------
    # 修改处：更名为 "采样间隔" (Stride)
    # 含义：每 N 个点取 1 个 (1=全取, 10=稀疏)
    # -------------------------------------------------------
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

# ==========================================
# 组件: 输入框 (无阻塞)
# ==========================================
class OverlayInput(tk.Frame):
    def __init__(self, parent, on_confirm, on_cancel):
        super().__init__(parent, bg="#f0f0f0", bd=2, relief=tk.RAISED)
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.lbl_prompt = tk.Label(self, text="Val:", bg="#f0f0f0", fg="blue", font=("Arial", 9, "bold"))
        self.lbl_prompt.pack(side=tk.LEFT, padx=2)
        vcmd = (self.register(self.validate_float), '%P')
        self.entry = tk.Entry(self, width=10, font=("Arial", 10), validate="key", validatecommand=vcmd)
        self.entry.pack(side=tk.LEFT, padx=2)
        self.entry.bind("<Return>", self._confirm)
        self.entry.bind("<Escape>", self._cancel)
        tk.Button(self, text="✔", command=self._confirm, bd=0, bg="#ddffdd", width=3).pack(side=tk.LEFT, padx=1)

    def validate_float(self, new_value):
        if new_value == "": return True
        for char in new_value:
            if char not in "0123456789.-eE": return False
        return True

    def show(self, x, y, default_val, label_text):
        self.lbl_prompt.config(text=f"{label_text}:")
        self.entry.delete(0, tk.END)
        self.entry.insert(0, str(default_val))
        self.entry.selection_range(0, tk.END)
        req_w = 160
        parent_w = self.master.winfo_width()
        final_x = x + 15
        if final_x + req_w > parent_w: final_x = x - req_w - 15
        self.place(x=final_x, y=y - 15)
        self.lift()
        self.after(50, self.entry.focus_set)

    def hide(self): self.place_forget()
    def _confirm(self, event=None):
        try:
            val = float(self.entry.get())
            self.hide(); self.on_confirm(val)
        except: self.entry.config(bg="#ffcccc")
    def _cancel(self, event=None): self.hide(); self.on_cancel()

# ==========================================
# 组件: 放大镜
# ==========================================
class FastMag(tk.Toplevel):
    def __init__(self, root):
        super().__init__(root)
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.sz = 150
        self.crop_r = 30
        self.zoom_ratio = self.sz / (self.crop_r * 2)
        self.canvas = tk.Canvas(self, width=self.sz, height=self.sz, bg="white", highlightthickness=1)
        self.canvas.pack()
        self.img_ref = None

    def show(self, root_x, root_y, crop_img, center_canvas_xy, existing_markers):
        self.img_ref = ImageTk.PhotoImage(crop_img)
        self.canvas.delete("all")
        self.canvas.create_image(self.sz//2, self.sz//2, image=self.img_ref)
        cx, cy = center_canvas_xy
        left_bound = cx - self.crop_r
        top_bound = cy - self.crop_r
        for mx, my, m_name in existing_markers:
            if (left_bound < mx < left_bound + self.crop_r*2) and (top_bound < my < top_bound + self.crop_r*2):
                mag_x = (mx - left_bound) * self.zoom_ratio
                mag_y = (my - top_bound) * self.zoom_ratio
                self.canvas.create_oval(mag_x-3, mag_y-3, mag_x+3, mag_y+3, outline="#00FF00", width=2)
                self.canvas.create_text(mag_x+5, mag_y-5, text=m_name, fill="#00FF00", anchor="sw", font=("Arial", 9, "bold"))
        c = self.sz // 2
        self.canvas.create_line(c, 0, c, self.sz, fill="red", width=1)
        self.canvas.create_line(0, c, self.sz, c, fill="red", width=1)
        self.canvas.create_rectangle(0, 0, self.sz, self.sz, outline="#0078d7", width=2)
        target_y = root_y - self.sz - 30
        if target_y < 0: target_y = root_y + 30
        self.geometry(f"+{root_x-self.sz//2}+{int(target_y)}")
        if self.state() == "withdrawn": self.deiconify()
    
    def hide(self): self.withdraw()

# ==========================================
# 组件: 数据窗口
# ==========================================
class DataWindow(tk.Toplevel):
    def __init__(self, parent, full_data, lang_code, app_ref):
        super().__init__(parent)
        self.full_data = full_data if full_data else []
        self.display_data = []
        self.lang = lang_code
        self.app = app_ref
        self.app.sub_windows.append(self)
        
        self.title("Data")
        self.geometry("480x650")
        
        # 布局：Main Frame
        self.main_frame = tk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 控制面板
        self.setup_controls()
        
        # 2. 表格区域
        self.setup_table()
        
        # 3. 初始设置：默认全量 (1)
        self.spin_step.delete(0, "end")
        self.spin_step.insert(0, "1")
        
        self.update_lang_ui()
        self.cmb_sep.current(0)

        # 延时 100ms 填充数据
        self.after(100, self.process_data)

    def setup_controls(self):
        # Filter (使用 ttk.LabelFrame)
        lf_filter = ttk.LabelFrame(self.main_frame, text="Filter", padding=5)
        lf_filter.pack(fill=tk.X, padx=5, pady=5)
        
        f_grid = tk.Frame(lf_filter)
        f_grid.pack(fill=tk.X)
        
        self.lbl_xmin = tk.Label(f_grid, text="XMin:")
        self.lbl_xmin.grid(row=0, column=0, sticky="e")
        self.e_xmin = tk.Entry(f_grid, width=7)
        self.e_xmin.grid(row=0, column=1, padx=2)
        
        self.lbl_xmax = tk.Label(f_grid, text="XMax:")
        self.lbl_xmax.grid(row=0, column=2, sticky="e")
        self.e_xmax = tk.Entry(f_grid, width=7)
        self.e_xmax.grid(row=0, column=3, padx=2)
        
        self.lbl_ymin = tk.Label(f_grid, text="YMin:")
        self.lbl_ymin.grid(row=1, column=0, sticky="e")
        self.e_ymin = tk.Entry(f_grid, width=7)
        self.e_ymin.grid(row=1, column=1, padx=2)
        
        self.lbl_ymax = tk.Label(f_grid, text="YMax:")
        self.lbl_ymax.grid(row=1, column=2, sticky="e")
        self.e_ymax = tk.Entry(f_grid, width=7)
        self.e_ymax.grid(row=1, column=3, padx=2)
        
        self.btn_apply = ttk.Button(f_grid, command=self.process_data)
        self.btn_apply.grid(row=0, column=4, rowspan=2, padx=5, sticky="ns")
        
        # 回车刷新
        for e in [self.e_xmin, self.e_xmax, self.e_ymin, self.e_ymax]:
            e.bind("<Return>", lambda x: self.process_data())

        # Export (使用 ttk.LabelFrame)
        lf_export = ttk.LabelFrame(self.main_frame, text="Export", padding=5)
        lf_export.pack(fill=tk.X, padx=5, pady=5)
        
        f_line1 = tk.Frame(lf_export)
        f_line1.pack(fill=tk.X, pady=2)
        
        self.lbl_step = tk.Label(f_line1)
        self.lbl_step.pack(side=tk.LEFT)
        self.spin_step = tk.Spinbox(f_line1, from_=1, to=99999, width=5, command=self.process_data)
        self.spin_step.bind("<Return>", lambda x: self.process_data())
        self.spin_step.pack(side=tk.LEFT, padx=5)
        
        self.lbl_sep = tk.Label(f_line1)
        self.lbl_sep.pack(side=tk.LEFT, padx=(10, 0))
        self.sep_var = tk.StringVar()
        self.cmb_sep = ttk.Combobox(f_line1, textvariable=self.sep_var, state="readonly", width=10)
        self.cmb_sep.pack(side=tk.LEFT, padx=5)
        
        f_line2 = tk.Frame(lf_export)
        f_line2.pack(fill=tk.X, pady=5)
        self.btn_copy = ttk.Button(f_line2, command=self.copy_to_clipboard)
        self.btn_copy.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.btn_save = ttk.Button(f_line2, command=self.export_file)
        self.btn_save.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.lbl_count = tk.Label(lf_export, text="", fg="#666")
        self.lbl_count.pack(anchor="e")
        
        self.lf_filter = lf_filter; self.lf_export = lf_export

    def setup_table(self):
        f_table = tk.Frame(self.main_frame)
        f_table.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tree = ttk.Treeview(f_table, columns=("idx", "x", "y"), show="headings")
        self.tree.column("idx", width=50, anchor="center")
        self.tree.column("x", width=140, anchor="center")
        self.tree.column("y", width=140, anchor="center")
        
        self.tree.heading("x", command=lambda: self.sort_data(1))
        self.tree.heading("y", command=lambda: self.sort_data(2))
        
        vs = ttk.Scrollbar(f_table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        vs.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.sort_col = None; self.sort_desc = False

    def t(self, key): return LANG_MAP.get(key, {}).get(self.lang, key)

    def update_lang_ui(self, new_lang=None):
        if new_lang: self.lang = new_lang
        self.title(self.t("data_win_title"))
        self.lf_filter.config(text=self.t("grp_filter"))
        self.lbl_xmin.config(text=self.t("lbl_xmin")); self.lbl_xmax.config(text=self.t("lbl_xmax"))
        self.lbl_ymin.config(text=self.t("lbl_ymin")); self.lbl_ymax.config(text=self.t("lbl_ymax"))
        self.btn_apply.config(text=self.t("btn_apply"))
        self.lf_export.config(text=self.t("grp_export"))
        self.lbl_step.config(text=self.t("lbl_step")); self.lbl_sep.config(text=self.t("lbl_sep"))
        self.btn_copy.config(text=self.t("btn_copy")); self.btn_save.config(text=self.t("btn_save"))
        self.tree.heading("idx", text=self.t("col_idx"))
        self.update_headers()
        vals = [self.t("sep_tab"), self.t("sep_comma"), self.t("sep_space")]
        idx = self.cmb_sep.current()
        self.cmb_sep['values'] = vals
        self.cmb_sep.current(idx if idx >=0 else 0)
        self.update_count_label()

    def update_headers(self):
        arrow = " ▼" if self.sort_desc else " ▲"
        tx, ty = self.t("col_x"), self.t("col_y")
        if self.sort_col == 1: tx += arrow
        elif self.sort_col == 2: ty += arrow
        self.tree.heading("x", text=tx); self.tree.heading("y", text=ty)

    def process_data(self):
        def get_val(entry):
            try:
                v = entry.get().strip(); return float(v) if v else None
            except: return None
        xmin, xmax = get_val(self.e_xmin), get_val(self.e_xmax)
        ymin, ymax = get_val(self.e_ymin), get_val(self.e_ymax)
        
        try:
            step = int(self.spin_step.get())
            if step < 1: step = 1
        except: step = 1
        
        temp = []
        for x, y in self.full_data:
            if xmin is not None and x < xmin: continue
            if xmax is not None and x > xmax: continue
            if ymin is not None and y < ymin: continue
            if ymax is not None and y > ymax: continue
            temp.append((x, y))
            
        self.display_data = temp[::step]
        self.refresh_table()
        self.update_count_label()

    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        # 仅预览前 2000 行
        limit = 2000
        preview_data = self.display_data[:limit]
        for i, (x, y) in enumerate(preview_data):
            self.tree.insert("", "end", values=(i+1, f"{x:.5g}", f"{y:.5g}"))

    def update_count_label(self):
        n = len(self.display_data)
        msg = f"Total: {n} pts"
        if n > 2000: msg += " | Previewing top 2000 (Export for all)"
        self.lbl_count.config(text=msg)

    def sort_data(self, col):
        if self.sort_col == col: self.sort_desc = not self.sort_desc
        else: self.sort_col = col; self.sort_desc = False
        self.display_data.sort(key=lambda x: x[col-1], reverse=self.sort_desc)
        self.update_headers(); self.refresh_table()

    def get_sep_char(self):
        idx = self.cmb_sep.current()
        if idx == 1: return ",";
        if idx == 2: return " ";
        return "\t"

    def copy_to_clipboard(self):
        sep = self.get_sep_char()
        s = f"X{sep}Y\n" + "\n".join([f"{x}{sep}{y}" for x, y in self.display_data])
        self.clipboard_clear(); self.clipboard_append(s)
        messagebox.showinfo("OK", self.t("msg_copy_ok"), parent=self)

    def export_file(self):
        sep = self.get_sep_char()
        f = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("TXT", "*.txt"), ("CSV", "*.csv")])
        if f:
            if f.lower().endswith(".csv") and sep != ",": sep = ","
            try:
                with open(f, 'w', newline='', encoding='utf-8') as file:
                    if sep == ",":
                        writer = csv.writer(file)
                        writer.writerow(["X", "Y"])
                        writer.writerows(self.display_data)
                    else:
                        file.write(f"X{sep}Y\n")
                        for x, y in self.display_data: file.write(f"{x}{sep}{y}\n")
                messagebox.showinfo("OK", self.t("msg_save_ok"), parent=self)
            except Exception as e: messagebox.showerror("Error", str(e))

# ==========================================
# 主程序
# ==========================================
class PDFCurveExtractor:
    def __init__(self, root):
        self.root = root
        self.lang = "CN"
        self.root.geometry("1100x800")
        
        self.doc = None; self.page = None
        self.hq_image = None; self.view_image = None; self.tk_img = None
        self.base_scale = 2.0; self.view_scale = 1.0
        
        self.calib_points = {'x1': None, 'x2': None, 'y1': None, 'y2': None}
        self.calib_values = {'x1': 0.0, 'x2': 100.0, 'y1': 0.0, 'y2': 100.0}
        self.calib_markers_rel = []
        
        self.mode = "VIEW"; self.axis_step = 0
        self.current_click_pos_rel = None
        self.sub_windows = []; self.extracted_data = []
        
        self.is_log_x = tk.BooleanVar(value=False)
        self.is_log_y = tk.BooleanVar(value=False)
        self.last_move_time = 0
        
        self.mag = FastMag(root)
        self.setup_ui()
        self.overlay_input = OverlayInput(self.canvas, self.on_input_confirm, self.on_input_cancel)
        self.refresh_ui()

    def t(self, k): return LANG_MAP.get(k, {}).get(self.lang, k)

    def toggle_lang(self):
        self.lang = "EN" if self.lang == "CN" else "CN"
        self.refresh_ui()
        for win in self.sub_windows:
            if win.winfo_exists(): win.update_lang_ui(self.lang)

    def setup_ui(self):
        self.tb = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        self.tb.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2)
        
        def add_btn(parent, k, cmd, state=tk.NORMAL):
            b = tk.Button(parent, command=cmd, state=state, relief=tk.GROOVE, bg="#f9f9f9")
            b.pack(side=tk.LEFT, padx=2, pady=2, fill=tk.Y)
            setattr(self, k, b)
            return b

        f1 = tk.Frame(self.tb); f1.pack(side=tk.LEFT, padx=5)
        add_btn(f1, "btn_open", self.load_pdf)
        add_btn(f1, "btn_zi", lambda: self.fast_zoom(1.2))
        add_btn(f1, "btn_zo", lambda: self.fast_zoom(0.8))
        add_btn(f1, "btn_rv", self.fit_view)
        add_btn(f1, "btn_lng", self.toggle_lang)

        tk.Frame(self.tb, width=2, bg="#ccc").pack(side=tk.LEFT, fill=tk.Y, padx=5)

        f2 = tk.Frame(self.tb); f2.pack(side=tk.LEFT, padx=5)
        self.lbl_s1 = tk.Label(f2, font=("Arial", 9, "bold"), fg="blue"); self.lbl_s1.pack(side=tk.LEFT)
        add_btn(f2, "btn_axis", self.start_axis, tk.DISABLED)
        add_btn(f2, "btn_reset_axis", self.reset_axis_state, tk.DISABLED)
        self.chk_lx = tk.Checkbutton(f2, variable=self.is_log_x); self.chk_lx.pack(side=tk.LEFT, padx=2)
        self.chk_ly = tk.Checkbutton(f2, variable=self.is_log_y); self.chk_ly.pack(side=tk.LEFT, padx=2)

        tk.Frame(self.tb, width=2, bg="#ccc").pack(side=tk.LEFT, fill=tk.Y, padx=5)

        f3 = tk.Frame(self.tb); f3.pack(side=tk.LEFT, padx=5)
        self.lbl_s2 = tk.Label(f3, font=("Arial", 9, "bold"), fg="green"); self.lbl_s2.pack(side=tk.LEFT)
        add_btn(f3, "btn_select", self.start_pick, tk.DISABLED)
        add_btn(f3, "btn_data", self.show_data_win)

        add_btn(self.tb, "btn_exit", self.quit_app)
        self.btn_exit.pack(side=tk.RIGHT, padx=5)

        self.status_var = tk.StringVar()
        tk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, bg="#e8e8e8", pady=4).pack(side=tk.BOTTOM, fill=tk.X)

        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(container, bg="#555", highlightthickness=0)
        vb = ttk.Scrollbar(container, command=self.canvas.yview); vb.pack(side=tk.RIGHT, fill=tk.Y)
        hb = ttk.Scrollbar(container, orient=tk.HORIZONTAL, command=self.canvas.xview); hb.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.config(yscrollcommand=vb.set, xscrollcommand=hb.set)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_click)

    def refresh_ui(self):
        self.root.title(self.t("title"))
        for k in ["btn_open","btn_zi","btn_zo","btn_rv","btn_lng","btn_axis","btn_reset_axis","btn_select","btn_data","btn_exit"]:
            getattr(self, k).config(text=self.t(k))
        self.lbl_s1.config(text=self.t("lbl_step1"))
        self.lbl_s2.config(text=self.t("lbl_step2"))
        self.chk_lx.config(text=self.t("chk_log_x"))
        self.chk_ly.config(text=self.t("chk_log_y"))
        self.update_status()

    def quit_app(self): self.root.quit(); sys.exit()

    def update_status(self):
        if self.mode == "VIEW":
            if self.calib_points['x1']:
                mx = "Log" if self.is_log_x.get() else "Lin"
                my = "Log" if self.is_log_y.get() else "Lin"
                self.status_var.set(f"{self.t('status_done')} | X:{mx} Y:{my}")
            else:
                self.status_var.set(self.t("status_ready"))
            self.canvas.unbind("<Motion>")
        elif self.mode == "SET_AXIS":
            keys = ["X1", "X2", "Y1", "Y2"]
            if self.axis_step < 4:
                self.status_var.set(self.t("status_axis") + keys[self.axis_step])
            self.canvas.bind("<Motion>", self.on_move_throttled)
        elif self.mode == "SELECT_CURVE":
            self.status_var.set(self.t("status_pick"))
            self.canvas.unbind("<Motion>")

    def load_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if not path: return
        self.doc = fitz.open(path); self.page = self.doc[0]
        self.drawings = self.page.get_drawings()
        mat = fitz.Matrix(self.base_scale, self.base_scale)
        pix = self.page.get_pixmap(matrix=mat, alpha=False)
        self.hq_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.fit_view()
        self.btn_axis.config(state=tk.NORMAL)
        self.btn_reset_axis.config(state=tk.NORMAL)
        self.status_var.set(self.t("status_ready"))

    def fit_view(self):
        if not self.hq_image: return
        sw = self.canvas.winfo_width(); sh = self.canvas.winfo_height()
        if sw < 10: sw = 800
        w, h = self.hq_image.size
        self.view_scale = sw / w
        self.update_canvas()

    def fast_zoom(self, factor):
        if not self.hq_image: return
        self.view_scale *= factor
        if self.view_scale < 0.1: self.view_scale = 0.1
        if self.view_scale > 4.0: self.view_scale = 4.0
        self.update_canvas()

    def update_canvas(self):
        w, h = self.hq_image.size
        new_w = int(w * self.view_scale)
        new_h = int(h * self.view_scale)
        self.view_image = self.hq_image.resize((new_w, new_h), Image.NEAREST)
        self.tk_img = ImageTk.PhotoImage(self.view_image)
        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0, 0, new_w, new_h))
        self.canvas.create_image(0, 0, image=self.tk_img, anchor=tk.NW)
        self.redraw_markers()

    def reset_axis_state(self):
        self.mode = "VIEW"; self.axis_step = 0
        self.overlay_input.hide()
        self.canvas.delete("markers"); self.canvas.delete("temp_marker"); self.canvas.delete("highlight")
        self.canvas.config(cursor="arrow")
        self.btn_axis.config(state=tk.NORMAL); self.btn_select.config(state=tk.DISABLED)
        self.calib_points = {'x1': None, 'x2': None, 'y1': None, 'y2': None}
        self.calib_markers_rel = []
        self.mag.hide()
        self.update_status()

    def start_axis(self):
        if not self.hq_image: return
        self.mode = "SET_AXIS"; self.axis_step = 0
        self.btn_axis.config(state=tk.DISABLED); self.btn_select.config(state=tk.DISABLED)
        self.canvas.config(cursor="crosshair")
        self.update_status()

    def start_pick(self):
        self.mode = "SELECT_CURVE"
        self.canvas.config(cursor="hand2")
        self.update_status()

    def on_move_throttled(self, event):
        now = time.time()
        if now - self.last_move_time < 0.03: return
        self.last_move_time = now
        self.on_move(event)

    def on_move(self, event):
        if not self.view_image: return
        if self.mode == "SET_AXIS":
            if self.overlay_input.winfo_ismapped():
                self.mag.hide(); return
            cx = self.canvas.canvasx(event.x); cy = self.canvas.canvasy(event.y)
            w, h = self.view_image.size
            if cx < 20 or cy < 20 or cx > w-20 or cy > h-20:
                self.mag.hide(); return
            try:
                box = (cx-30, cy-30, cx+30, cy+30)
                crop_img = self.view_image.crop(box).resize((150, 150), Image.NEAREST)
                cpm = []
                for m in self.calib_markers_rel:
                    cpm.append((m['rx']*w, m['ry']*h, m['key']))
                self.mag.show(event.x_root, event.y_root, crop_img, (cx, cy), cpm)
            except: pass
        else: self.mag.hide()

    def on_click(self, event):
        if not self.view_image: return
        cx = self.canvas.canvasx(event.x); cy = self.canvas.canvasy(event.y)
        w, h = self.view_image.size
        if self.overlay_input.winfo_ismapped():
            self.overlay_input.hide(); self.canvas.delete("temp_marker")
            return
        if cx < 0 or cy < 0 or cx > w or cy > h: return

        if self.mode == "SET_AXIS":
            self.mag.hide()
            rel_x = cx / w; rel_y = cy / h
            self.current_click_pos_rel = (rel_x, rel_y)
            keys = ["X1", "X2", "Y1", "Y2"]; k_low = ["x1", "x2", "y1", "y2"]
            self.canvas.create_oval(cx-3, cy-3, cx+3, cy+3, fill="yellow", tags="temp_marker")
            self.overlay_input.show(event.x, event.y, self.calib_values[k_low[self.axis_step]], keys[self.axis_step])
            
        elif self.mode == "SELECT_CURVE":
            pdf_w = self.page.rect.width; pdf_h = self.page.rect.height
            target_pdf_x = (cx / w) * pdf_w
            target_pdf_y = (cy / h) * pdf_h
            self.handle_pick(target_pdf_x, target_pdf_y)

    def on_input_confirm(self, val):
        if not self.current_click_pos_rel: return
        self.canvas.delete("temp_marker")
        rel_x, rel_y = self.current_click_pos_rel
        keys = ["x1", "x2", "y1", "y2"]; curr = keys[self.axis_step]
        self.calib_points[curr] = (rel_x, rel_y)
        self.calib_values[curr] = val
        self.calib_markers_rel.append({'rx': rel_x, 'ry': rel_y, 'val': val, 'key': curr.upper()})
        self.redraw_markers()
        self.axis_step += 1
        if self.axis_step < 4: self.update_status()
        else:
            self.mode = "VIEW"; self.update_status()
            self.btn_select.config(state=tk.NORMAL)
            self.canvas.config(cursor="arrow")

    def on_input_cancel(self): self.canvas.delete("temp_marker")

    def redraw_markers(self):
        self.canvas.delete("markers")
        if not self.view_image: return
        w, h = self.view_image.size
        for m in self.calib_markers_rel:
            cx, cy = m['rx'] * w, m['ry'] * h
            col = "#00FF00"
            self.canvas.create_oval(cx-3, cy-3, cx+3, cy+3, fill=col, outline="black", tags="markers")
            self.canvas.create_text(cx+5, cy-5, text=f"{m['key']}={m['val']:g}", fill=col, anchor=tk.SW, font=("Arial", 10, "bold"), tags="markers")

    def handle_pick(self, pdf_x, pdf_y):
        search_radius = 5.0
        best_path = None; min_dist_sq = float('inf')
        for path in self.drawings:
            rect = path['rect']
            if (pdf_x < rect.x0 - search_radius or pdf_x > rect.x1 + search_radius or
                pdf_y < rect.y0 - search_radius or pdf_y > rect.y1 + search_radius): continue
            for item in path['items']:
                pt = item[-1]
                if hasattr(pt, 'x'):
                    d_sq = (pt.x - pdf_x)**2 + (pt.y - pdf_y)**2
                    if d_sq < min_dist_sq: min_dist_sq = d_sq; best_path = path
        if best_path and min_dist_sq < (search_radius**2): self.extract_data(best_path)
        else: messagebox.showinfo("Tip", self.t("msg_no_curve"))

    def extract_data(self, path):
        pts = []
        for item in path['items']:
            op = item[0]
            if op == 'l': pts.extend([item[1], item[2]])
            elif op == 'c': pts.extend([item[1], item[2], item[3], item[4]])
            
        res = []; hl_coords = []
        pdf_w = self.page.rect.width; pdf_h = self.page.rect.height
        view_w, view_h = self.view_image.size
        
        sx1 = self.calib_points['x1'][0]; sx2 = self.calib_points['x2'][0]
        sy1 = self.calib_points['y1'][1]; sy2 = self.calib_points['y2'][1]
        v1, v2 = self.calib_values['x1'], self.calib_values['x2']
        w1, w2 = self.calib_values['y1'], self.calib_values['y2']
        is_lx, is_ly = self.is_log_x.get(), self.is_log_y.get()
        
        for p in pts:
            rel_x = p.x / pdf_w; rel_y = p.y / pdf_h
            rx = self.map_val(rel_x, sx1, sx2, v1, v2, is_lx)
            ry = self.map_val(rel_y, sy1, sy2, w1, w2, is_ly)
            res.append((rx, ry))
            hl_coords.extend([rel_x * view_w, rel_y * view_h])
            
        self.extracted_data = res
        self.canvas.delete("highlight")
        if len(hl_coords) >= 4: self.canvas.create_line(hl_coords, fill="cyan", width=2, tags="highlight")
        DataWindow(self.root, res, self.lang, self)

    def map_val(self, val, p1, p2, v1, v2, is_log):
        if abs(p2 - p1) < 1e-9: return v1
        r = (val - p1) / (p2 - p1)
        if not is_log: return v1 + r * (v2 - v1)
        else:
            try:
                lv1, lv2 = math.log10(v1), math.log10(v2)
                return 10 ** (lv1 + r * (lv2 - lv1))
            except: return v1
    def show_data_win(self):
        if self.extracted_data: DataWindow(self.root, self.extracted_data, self.lang, self)

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFCurveExtractor(root)
    root.mainloop()
