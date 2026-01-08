"""UI components for PDF Digitizer Pro.

This module contains reusable UI components including overlay input,
magnifier, and data display window.
"""

from typing import Callable, Optional, List, Tuple, Any, Dict
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import csv
import config
from utils.helpers import validate_float_string


class OverlayInput(tk.Frame):
    """Overlay input widget for entering calibration values.
    
    A non-blocking input widget that appears over the canvas to allow
    users to enter coordinate values during calibration.
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        on_confirm: Callable[[float], None],
        on_cancel: Callable[[], None]
    ):
        """Initialize the overlay input widget.
        
        Args:
            parent: Parent widget (usually canvas)
            on_confirm: Callback function called when value is confirmed
            on_cancel: Callback function called when input is cancelled
        """
        super().__init__(parent, bg="#f0f0f0", bd=2, relief=tk.RAISED)
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        
        self.lbl_prompt = tk.Label(
            self,
            text="Val:",
            bg="#f0f0f0",
            fg="blue",
            font=("Arial", 9, "bold")
        )
        self.lbl_prompt.pack(side=tk.LEFT, padx=2)
        
        vcmd = (self.register(self._validate_float), '%P')
        self.entry = tk.Entry(
            self,
            width=10,
            font=("Arial", 10),
            validate="key",
            validatecommand=vcmd
        )
        self.entry.pack(side=tk.LEFT, padx=2)
        self.entry.bind("<Return>", self._confirm)
        self.entry.bind("<Escape>", self._cancel)
        
        tk.Button(
            self,
            text="✔",
            command=self._confirm,
            bd=0,
            bg="#ddffdd",
            width=3
        ).pack(side=tk.LEFT, padx=1)
    
    def _validate_float(self, new_value: str) -> bool:
        """Validate float input string.
        
        Args:
            new_value: The new string value to validate
            
        Returns:
            True if valid, False otherwise
        """
        return validate_float_string(new_value)
    
    def show(
        self,
        x: int,
        y: int,
        default_val: float,
        label_text: str
    ) -> None:
        """Show the overlay input at specified position.
        
        Args:
            x: X coordinate in parent widget
            y: Y coordinate in parent widget
            default_val: Default value to display
            label_text: Label text for the input
        """
        self.lbl_prompt.config(text=f"{label_text}:")
        self.entry.delete(0, tk.END)
        self.entry.insert(0, str(default_val))
        self.entry.selection_range(0, tk.END)
        
        req_w = config.OVERLAY_INPUT_WIDTH
        parent_w = self.master.winfo_width()
        final_x = x + config.OVERLAY_INPUT_OFFSET_X
        if final_x + req_w > parent_w:
            final_x = x - req_w - config.OVERLAY_INPUT_OFFSET_X
        
        self.place(x=final_x, y=y - config.OVERLAY_INPUT_OFFSET_Y)
        self.lift()
        self.after(50, self.entry.focus_set)
    
    def hide(self) -> None:
        """Hide the overlay input widget."""
        self.place_forget()
    
    def _confirm(self, event: Optional[tk.Event] = None) -> None:
        """Handle confirmation of input value.
        
        Args:
            event: Optional event object
        """
        try:
            val = float(self.entry.get())
            self.hide()
            self.on_confirm(val)
        except ValueError:
            self.entry.config(bg="#ffcccc")
    
    def _cancel(self, event: Optional[tk.Event] = None) -> None:
        """Handle cancellation of input.
        
        Args:
            event: Optional event object
        """
        self.hide()
        self.on_cancel()


class FastMag(tk.Toplevel):
    """Magnifier window for precise point selection.
    
    A floating window that shows a magnified view of the area around
    the cursor, helping users select precise calibration points.
    """
    
    def __init__(self, root: tk.Tk):
        """Initialize the magnifier window.
        
        Args:
            root: Root window
        """
        super().__init__(root)
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        self.sz = config.MAGNIFIER_SIZE
        self.crop_r = config.MAGNIFIER_CROP_RADIUS
        self.zoom_ratio = config.MAGNIFIER_ZOOM_RATIO
        
        self.canvas = tk.Canvas(
            self,
            width=self.sz,
            height=self.sz,
            bg="white",
            highlightthickness=1
        )
        self.canvas.pack()
        self.img_ref: Optional[ImageTk.PhotoImage] = None
        
        # Performance optimization: image cache
        self._image_cache: List[Tuple[float, float, ImageTk.PhotoImage]] = []
        self._last_position: Optional[Tuple[float, float]] = None
        self._last_markers: Optional[List[Tuple[float, float, str]]] = None
    
    def _get_cached_image(
        self,
        cx: float,
        cy: float
    ) -> Optional[ImageTk.PhotoImage]:
        """Get cached image if position is close enough.
        
        Args:
            cx: Current X coordinate
            cy: Current Y coordinate
            
        Returns:
            Cached image if found, None otherwise
        """
        if not self._last_position:
            return None
        
        last_cx, last_cy = self._last_position
        dx = abs(cx - last_cx)
        dy = abs(cy - last_cy)
        
        if dx < config.MAGNIFIER_CACHE_THRESHOLD and dy < config.MAGNIFIER_CACHE_THRESHOLD:
            # Check cache
            for cache_cx, cache_cy, cached_img in self._image_cache:
                if (abs(cx - cache_cx) < config.MAGNIFIER_CACHE_THRESHOLD and
                    abs(cy - cache_cy) < config.MAGNIFIER_CACHE_THRESHOLD):
                    return cached_img
        
        return None
    
    def _add_to_cache(
        self,
        cx: float,
        cy: float,
        img: ImageTk.PhotoImage
    ) -> None:
        """Add image to cache.
        
        Args:
            cx: X coordinate
            cy: Y coordinate
            img: Image to cache
        """
        self._image_cache.append((cx, cy, img))
        # Keep only recent cache entries
        if len(self._image_cache) > config.MAGNIFIER_CACHE_SIZE:
            self._image_cache.pop(0)
    
    def show(
        self,
        root_x: int,
        root_y: int,
        crop_img: Image.Image,
        center_canvas_xy: Tuple[float, float],
        existing_markers: List[Tuple[float, float, str]]
    ) -> None:
        """Show the magnifier at specified position.
        
        Args:
            root_x: X coordinate in root window
            root_y: Y coordinate in root window
            crop_img: Cropped image to display
            center_canvas_xy: Center point in canvas coordinates
            existing_markers: List of existing markers (x, y, name)
        """
        cx, cy = center_canvas_xy
        
        # Check if markers changed (compare content properly)
        if self._last_markers is None:
            markers_changed = True
        else:
            markers_changed = (
                len(self._last_markers) != len(existing_markers) or
                any(m1 != m2 for m1, m2 in zip(self._last_markers, existing_markers))
            )
        
        # Check if position changed significantly
        position_changed = True
        if self._last_position:
            last_cx, last_cy = self._last_position
            dx = abs(cx - last_cx)
            dy = abs(cy - last_cy)
            position_changed = (dx >= config.MAGNIFIER_CACHE_THRESHOLD or 
                               dy >= config.MAGNIFIER_CACHE_THRESHOLD)
        else:
            position_changed = True  # First call, always update
        
        # Try to use cached image only if position and markers haven't changed much
        # For smooth movement, be more aggressive about updates
        cached_img = None
        if not markers_changed and not position_changed and self._last_position:
            cached_img = self._get_cached_image(cx, cy)
        
        if cached_img:
            self.img_ref = cached_img
        else:
            # Create new image
            self.img_ref = ImageTk.PhotoImage(crop_img)
            self._add_to_cache(cx, cy, self.img_ref)
        
        self._last_position = (cx, cy)
        self._last_markers = existing_markers.copy() if existing_markers else []
        
        # Always update window position first (important for visibility)
        target_y = root_y - self.sz - 30
        if target_y < 0:
            target_y = root_y + 30
        self.geometry(f"+{root_x - self.sz // 2}+{int(target_y)}")
        
        # Always redraw to ensure visibility (optimization: only skip if truly unchanged)
        if markers_changed or position_changed or not cached_img:
            self.canvas.delete("all")
            self.canvas.create_image(
                self.sz // 2,
                self.sz // 2,
                image=self.img_ref
            )
            
            left_bound = cx - self.crop_r
            top_bound = cy - self.crop_r
            
            # Draw existing markers in view
            for mx, my, m_name in existing_markers:
                if (left_bound < mx < left_bound + self.crop_r * 2 and
                    top_bound < my < top_bound + self.crop_r * 2):
                    mag_x = (mx - left_bound) * self.zoom_ratio
                    mag_y = (my - top_bound) * self.zoom_ratio
                    self.canvas.create_oval(
                        mag_x - config.MARKER_SIZE,
                        mag_y - config.MARKER_SIZE,
                        mag_x + config.MARKER_SIZE,
                        mag_y + config.MARKER_SIZE,
                        outline=config.MARKER_COLOR,
                        width=2
                    )
                    self.canvas.create_text(
                        mag_x + 5,
                        mag_y - 5,
                        text=m_name,
                        fill=config.MARKER_COLOR,
                        anchor="sw",
                        font=("Arial", 9, "bold")
                    )
            
            # Draw crosshair
            c = self.sz // 2
            self.canvas.create_line(c, 0, c, self.sz, fill="red", width=1)
            self.canvas.create_line(0, c, self.sz, c, fill="red", width=1)
            self.canvas.create_rectangle(
                0, 0, self.sz, self.sz,
                outline="#0078d7",
                width=2
            )
        else:
            # With cached image, ensure image is still displayed
            items = self.canvas.find_all()
            has_image = False
            for item in items:
                if self.canvas.type(item) == 'image':
                    # Update existing image reference
                    try:
                        self.canvas.itemconfig(item, image=self.img_ref)
                        has_image = True
                    except:
                        pass
                    break
            if not has_image:
                # No image found, need to redraw
                self.canvas.delete("all")
                self.canvas.create_image(
                    self.sz // 2,
                    self.sz // 2,
                    image=self.img_ref
                )
                # Redraw crosshair and border
                c = self.sz // 2
                self.canvas.create_line(c, 0, c, self.sz, fill="red", width=1)
                self.canvas.create_line(0, c, self.sz, c, fill="red", width=1)
                self.canvas.create_rectangle(
                    0, 0, self.sz, self.sz,
                    outline="#0078d7",
                    width=2
                )
        
        # Always show and bring to front
        if self.state() == "withdrawn":
            self.deiconify()
        self.lift()  # Ensure window is on top
    
    def hide(self) -> None:
        """Hide the magnifier window."""
        self.withdraw()


class DataWindow(tk.Toplevel):
    """Data display and export window.
    
    A window that displays extracted curve data in a table format,
    allows filtering, sorting, and exporting to various formats.
    """
    
    def __init__(
        self,
        parent: tk.Tk,
        full_data: List[Tuple[float, float]],
        lang_code: str,
        app_ref: Any
    ):
        super().__init__(parent)
        self.full_data = full_data if full_data else []
        self.display_data: List[Tuple[float, float]] = []
        self.lang = lang_code
        self.app = app_ref
        self.app.sub_windows.append(self)
        
        self.title("Data")
        self.geometry(config.DEFAULT_DATA_WINDOW_SIZE)
        
        # Main frame
        self.main_frame = tk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Setup UI
        self.setup_controls()
        self.setup_table()
        
        # Initialize
        self.spin_step.delete(0, "end")
        self.spin_step.insert(0, "1")
        
        self.update_lang_ui()
        self.cmb_sep.current(1)
        
        # 初始化时，不强制填充占位符 (force_fill=False)
        self.after(100, lambda: self.process_data(force_fill=False))

    def _setup_placeholder(self, entry: tk.Entry, placeholder: str):
        """Helper to add placeholder behavior to an Entry widget."""
        entry.default_val = placeholder
        
        entry.delete(0, tk.END)
        entry.insert(0, placeholder)
        entry.config(fg="#999999") 

        def on_focus_in(event):
            # 只有当颜色为灰色（占位符状态）且内容匹配默认值时才清空
            if entry.cget('fg') == "#999999" and entry.get().strip() == entry.default_val:
                entry.delete(0, tk.END)
                entry.config(fg="black")

        def on_focus_out(event):
            # 如果为空，恢复占位符
            if not entry.get().strip():
                entry.insert(0, entry.default_val)
                entry.config(fg="#999999")

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
    
    def setup_controls(self) -> None:
        """Setup control panel with filters and export options."""
        # Filter section
        lf_filter = ttk.LabelFrame(
            self.main_frame,
            text="Filter",
            padding=5
        )
        lf_filter.pack(fill=tk.X, padx=5, pady=5)
        
        f_grid = tk.Frame(lf_filter)
        f_grid.pack(fill=tk.X)
        
        # 计算 Placeholder - 使用校准参考点的四个点
        # 从主应用获取校准值
        if hasattr(self.app, 'calibration') and self.app.calibration:
            calib_values = self.app.calibration.calib_values
            x1_val = calib_values.get('x1', 0.0)
            x2_val = calib_values.get('x2', 0.0)
            y1_val = calib_values.get('y1', 0.0)
            y2_val = calib_values.get('y2', 0.0)
            
            # X轴：取x1和x2中的最小值和最大值
            x_min_str = f"{min(x1_val, x2_val):.5g}"
            x_max_str = f"{max(x1_val, x2_val):.5g}"
            
            # Y轴：取y1和y2中的最小值和最大值
            y_min_str = f"{min(y1_val, y2_val):.5g}"
            y_max_str = f"{max(y1_val, y2_val):.5g}"
        else:
            # 如果没有校准信息，回退到使用数据的最小最大值
            if self.full_data:
                xs = [p[0] for p in self.full_data]
                ys = [p[1] for p in self.full_data]
                x_min_str = f"{min(xs):.5g}"
                x_max_str = f"{max(xs):.5g}"
                y_min_str = f"{min(ys):.5g}"
                y_max_str = f"{max(ys):.5g}"
            else:
                x_min_str = x_max_str = y_min_str = y_max_str = "0"

        self.lbl_xmin = tk.Label(f_grid, text="XMin:")
        self.lbl_xmin.grid(row=0, column=0, sticky="e")
        self.e_xmin = tk.Entry(f_grid, width=10)
        self._setup_placeholder(self.e_xmin, x_min_str)
        self.e_xmin.grid(row=0, column=1, padx=2)
        
        self.lbl_xmax = tk.Label(f_grid, text="XMax:")
        self.lbl_xmax.grid(row=0, column=2, sticky="e")
        self.e_xmax = tk.Entry(f_grid, width=10)
        self._setup_placeholder(self.e_xmax, x_max_str)
        self.e_xmax.grid(row=0, column=3, padx=2)
        
        self.lbl_ymin = tk.Label(f_grid, text="YMin:")
        self.lbl_ymin.grid(row=1, column=0, sticky="e")
        self.e_ymin = tk.Entry(f_grid, width=10)
        self._setup_placeholder(self.e_ymin, y_min_str)
        self.e_ymin.grid(row=1, column=1, padx=2)
        
        self.lbl_ymax = tk.Label(f_grid, text="YMax:")
        self.lbl_ymax.grid(row=1, column=2, sticky="e")
        self.e_ymax = tk.Entry(f_grid, width=10)
        self._setup_placeholder(self.e_ymax, y_max_str)
        self.e_ymax.grid(row=1, column=3, padx=2)
        
        # [修改] 按钮点击视为“强制填充并应用”
        self.btn_apply = ttk.Button(
            f_grid, 
            command=lambda: self.process_data(force_fill=True)
        )
        self.btn_apply.grid(row=0, column=4, rowspan=2, padx=5, sticky="ns")
        
        # [修改] 回车键视为“强制填充并应用”
        for entry in [self.e_xmin, self.e_xmax, self.e_ymin, self.e_ymax]:
            entry.bind("<Return>", lambda x: self.process_data(force_fill=True))
        
        # Export section
        lf_export = ttk.LabelFrame(
            self.main_frame,
            text="Export",
            padding=5
        )
        lf_export.pack(fill=tk.X, padx=5, pady=5)
        
        f_line1 = tk.Frame(lf_export)
        f_line1.pack(fill=tk.X, pady=2)
        
        self.lbl_step = tk.Label(f_line1)
        self.lbl_step.pack(side=tk.LEFT)
        self.spin_step = tk.Spinbox(
            f_line1,
            from_=config.MIN_STEP_VALUE,
            to=config.MAX_STEP_VALUE,
            width=5,
            command=lambda: self.process_data(force_fill=False) # 调整步长通常不强制锁定范围，除非你希望这样
        )
        self.spin_step.bind("<Return>", lambda x: self.process_data(force_fill=False))
        self.spin_step.pack(side=tk.LEFT, padx=5)
        
        self.lbl_sep = tk.Label(f_line1)
        self.lbl_sep.pack(side=tk.LEFT, padx=(10, 0))
        self.sep_var = tk.StringVar()
        self.cmb_sep = ttk.Combobox(
            f_line1,
            textvariable=self.sep_var,
            state="readonly",
            width=10
        )
        self.cmb_sep.pack(side=tk.LEFT, padx=5)
        
        f_line2 = tk.Frame(lf_export)
        f_line2.pack(fill=tk.X, pady=5)
        self.btn_copy = ttk.Button(f_line2, command=self.copy_to_clipboard)
        self.btn_copy.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.btn_save = ttk.Button(f_line2, command=self.export_file)
        self.btn_save.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.lbl_count = tk.Label(lf_export, text="", fg="#666")
        self.lbl_count.pack(anchor="e")
        
        self.lf_filter = lf_filter
        self.lf_export = lf_export
    
    def setup_table(self) -> None:
        """Setup data table with sorting capability."""
        f_table = tk.Frame(self.main_frame)
        f_table.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tree = ttk.Treeview(
            f_table,
            columns=("idx", "x", "y"),
            show="headings"
        )
        self.tree.column("idx", width=50, anchor="center")
        self.tree.column("x", width=140, anchor="center")
        self.tree.column("y", width=140, anchor="center")
        
        self.tree.heading("x", command=lambda: self.sort_data(1))
        self.tree.heading("y", command=lambda: self.sort_data(2))
        
        vs = ttk.Scrollbar(
            f_table,
            orient="vertical",
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=vs.set)
        vs.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.sort_col: Optional[int] = None
        self.sort_desc = False
    
    def t(self, key: str) -> str:
        """Get translated text for a key."""
        return config.LANG_MAP.get(key, {}).get(self.lang, key)
    
    def update_lang_ui(self, new_lang: Optional[str] = None) -> None:
        """Update UI text based on language."""
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
        
        vals = [
            self.t("sep_tab"),
            self.t("sep_comma"),
            self.t("sep_space")
        ]
        idx = self.cmb_sep.current()
        self.cmb_sep['values'] = vals
        if idx >= 0:
            self.cmb_sep.current(idx)
        self.update_count_label()
    
    def update_headers(self) -> None:
        """Update table column headers with sort indicators."""
        arrow = " ▼" if self.sort_desc else " ▲"
        tx, ty = self.t("col_x"), self.t("col_y")
        if self.sort_col == 1:
            tx += arrow
        elif self.sort_col == 2:
            ty += arrow
        self.tree.heading("x", text=tx)
        self.tree.heading("y", text=ty)
    
    def process_data(self, force_fill: bool = False) -> None:
        """Process and filter data based on current settings.
        
        Args:
            force_fill: If True, convert placeholders to active values and filter.
                        If False, placeholders are treated as 'No Filter'.
        """
        target_entries = [self.e_xmin, self.e_xmax, self.e_ymin, self.e_ymax]
        
        # 1. 预处理：如果是 force_fill (用户点击刷新)，把灰色 Placeholder 变成黑色实值
        if force_fill:
            for entry in target_entries:
                default_val = getattr(entry, "default_val", "")
                is_placeholder = (entry.cget('fg') == "#999999")
                
                if is_placeholder:
                    # 将灰色占位符转为黑色实值 -> 这意味着启用了该数值的筛选
                    entry.delete(0, tk.END)
                    entry.insert(0, default_val)
                    entry.config(fg="black")

        def get_val(entry: tk.Entry) -> Optional[float]:
            """Get float value if active, None if placeholder/empty."""
            try:
                # 检查是否为占位符状态（灰色）
                is_placeholder = (entry.cget('fg') == "#999999")
                if is_placeholder:
                    # 按照要求：如果没点刷新（没转成黑色），则不启用范围筛选 -> 返回 None
                    return None
                
                v = entry.get().strip()
                return float(v) if v else None
            except ValueError:
                return None
        
        xmin, xmax = get_val(self.e_xmin), get_val(self.e_xmax)
        ymin, ymax = get_val(self.e_ymin), get_val(self.e_ymax)
        
        try:
            step = int(self.spin_step.get())
            if step < config.MIN_STEP_VALUE:
                step = config.MIN_STEP_VALUE
        except ValueError:
            step = config.MIN_STEP_VALUE
        
        # Filter data
        temp = []
        for x, y in self.full_data:
            # 如果 get_val 返回 None (placeholder 状态)，条件不成立，不进行 continue -> 数据保留
            if xmin is not None and x < xmin:
                continue
            if xmax is not None and x > xmax:
                continue
            if ymin is not None and y < ymin:
                continue
            if ymax is not None and y > ymax:
                continue
            temp.append((x, y))
        
        # Apply stride
        self.display_data = temp[::step]
        self.refresh_table()
        self.update_count_label()
    
    def refresh_table(self) -> None:
        """Refresh table display with current data."""
        self.tree.delete(*self.tree.get_children())
        
        # Preview limited rows
        limit = config.TABLE_PREVIEW_LIMIT
        preview_data = self.display_data[:limit]
        
        for i, (x, y) in enumerate(preview_data):
            self.tree.insert(
                "",
                "end",
                values=(i + 1, f"{x:.5g}", f"{y:.5g}")
            )
    
    def update_count_label(self) -> None:
        """Update data count label."""
        n = len(self.display_data)
        msg = f"Total: {n} pts"
        if n > config.TABLE_PREVIEW_LIMIT:
            msg += f" | Previewing top {config.TABLE_PREVIEW_LIMIT} (Export for all)"
        self.lbl_count.config(text=msg)
    
    def sort_data(self, col: int) -> None:
        """Sort data by column."""
        if self.sort_col == col:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = col
            self.sort_desc = False
        
        self.display_data.sort(
            key=lambda x: x[col - 1],
            reverse=self.sort_desc
        )
        self.update_headers()
        self.refresh_table()
    
    def get_sep_char(self) -> str:
        """Get separator character based on selection."""
        idx = self.cmb_sep.current()
        if idx == 1:
            return ","
        if idx == 2:
            return " "
        return "\t"
    
    def copy_to_clipboard(self) -> None:
        """Copy data to clipboard."""
        sep = self.get_sep_char()
        lines = [f"X{sep}Y"] + [f"{x}{sep}{y}" for x, y in self.display_data]
        s = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(s)
        messagebox.showinfo("OK", self.t("msg_copy_ok"), parent=self)
    
    def export_file(self) -> None:
        """Export data to file."""
        sep = self.get_sep_char()
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("TXT", "*.txt"), ("CSV", "*.csv")]
        )
        
        if not filename:
            return
        
        if filename.lower().endswith(".csv") and sep != ",":
            sep = ","
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                if sep == ",":
                    writer = csv.writer(file)
                    writer.writerow(["X", "Y"])
                    writer.writerows(self.display_data)
                else:
                    file.write(f"X{sep}Y\n")
                    for x, y in self.display_data:
                        file.write(f"{x}{sep}{y}\n")
            
            messagebox.showinfo("OK", self.t("msg_save_ok"), parent=self)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)

