"""主窗口：打开 PDF、定标、拾取曲线。"""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from PIL import Image, ImageTk

from .. import __version__
from ..activation import activate_application, is_application_active
from ..calibration import DEFAULT_CALIBRATION_VALUES, map_point
from ..core import PdfSource
from ..i18n import DEFAULT_LANGUAGE, translate
from .calibration_entry import CalibrationEntry
from .data_window import DataWindow

WINDOW_GEOMETRY = "1100x800"
BASE_RENDER_SCALE = 2.0
INITIAL_VIEW_SCALE = 1.0
ZOOM_STEP = 1.2
MIN_ZOOM = 0.1
MAX_ZOOM = 4.0
MOVE_THROTTLE_SECONDS = 0.03

MAGNIFIER_SIZE = 150
MAGNIFIER_SOURCE = 60
MAGNIFIER_MARGIN = 30
MAGNIFIER_MIN_MOVE = 2
ACTIVATION_RETRY_SECONDS = 0.5

AXIS_LABELS = ("X1", "X2", "Y1", "Y2")
AXIS_FIELDS = ("x1", "x2", "y1", "y2")

TOOLBAR_BUTTONS = (
    "btn_open",
    "btn_zi",
    "btn_zo",
    "btn_rv",
    "btn_lng",
    "btn_axis",
    "btn_reset_axis",
    "btn_select",
    "btn_data",
    "btn_exit",
)


class PDFCurveExtractor:
    """应用主控制器。"""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.lang = DEFAULT_LANGUAGE
        self.root.geometry(WINDOW_GEOMETRY)

        self.source: PdfSource | None = None
        self.hq_image: Image.Image | None = None
        self.view_image: Image.Image | None = None
        self.tk_img: ImageTk.PhotoImage | None = None
        self.base_scale = BASE_RENDER_SCALE
        self.view_scale = INITIAL_VIEW_SCALE

        self.calib_points: dict[str, tuple[float, float] | None] = {
            key: None for key in AXIS_FIELDS
        }
        self.calib_values: dict[str, float] = dict(DEFAULT_CALIBRATION_VALUES)
        self.calib_markers_rel: list[dict[str, Any]] = []

        self.mode = "VIEW"
        self.axis_step = 0
        self.pending_calib: tuple[float, float] | None = None
        self.sub_windows: list[DataWindow] = []
        self.extracted_data: list[tuple[float, float]] = []

        self.is_log_x = tk.BooleanVar(value=False)
        self.is_log_y = tk.BooleanVar(value=False)
        self.last_move_time = 0.0
        self._mag_img: ImageTk.PhotoImage | None = None
        self._last_mag_pos: tuple[int, int] | None = None
        self._last_activation_attempt = 0.0

        self.setup_ui()
        self.refresh_ui()
        self.root.after(100, self._bring_to_front)
        self.root.after(900, self._bring_to_front)

    # --- 通用 ---

    def _bring_to_front(self) -> None:
        """macOS 上确保应用与窗口都处于前台并获得焦点。"""
        try:
            activate_application()
            self.root.lift()
            self.root.focus_force()
        except tk.TclError:
            pass

    def _on_pointer_motion(self, _event: tk.Event) -> None:
        """应用未激活时 Tk 仍会收到鼠标移动事件，借此在点击前先激活自身。

        Tk 会丢弃应用未激活时的左键事件，所以必须在点击之前完成激活。
        """
        now = time.monotonic()
        if now - self._last_activation_attempt < ACTIVATION_RETRY_SECONDS:
            return
        self._last_activation_attempt = now
        if not is_application_active():
            activate_application()

    def t(self, key: str) -> str:
        return translate(self.lang, key)

    def toggle_lang(self) -> None:
        self.lang = "EN" if self.lang == "CN" else "CN"
        self.refresh_ui()
        for window in self.sub_windows:
            if window.winfo_exists():
                window.update_lang_ui(self.lang)

    # --- 界面构建 ---

    def setup_ui(self) -> None:
        self.tb = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        self.tb.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2)

        def add_button(
            parent: tk.Misc, key: str, command: Any, state: str = tk.NORMAL
        ) -> tk.Button:
            button = tk.Button(
                parent, command=command, state=state, relief=tk.GROOVE, bg="#f9f9f9"
            )
            button.pack(side=tk.LEFT, padx=2, pady=2, fill=tk.Y)
            setattr(self, key, button)
            return button

        group_open = tk.Frame(self.tb)
        group_open.pack(side=tk.LEFT, padx=5)
        add_button(group_open, "btn_open", self.load_pdf)
        add_button(group_open, "btn_zi", lambda: self.fast_zoom(ZOOM_STEP))
        add_button(group_open, "btn_zo", lambda: self.fast_zoom(1 / ZOOM_STEP))
        add_button(group_open, "btn_rv", self.fit_view)
        add_button(group_open, "btn_lng", self.toggle_lang)

        tk.Frame(self.tb, width=2, bg="#ccc").pack(side=tk.LEFT, fill=tk.Y, padx=5)

        group_calib = tk.Frame(self.tb)
        group_calib.pack(side=tk.LEFT, padx=5)
        self.lbl_s1 = tk.Label(group_calib, font=("Arial", 9, "bold"), fg="blue")
        self.lbl_s1.pack(side=tk.LEFT)
        add_button(group_calib, "btn_axis", self.start_axis, tk.DISABLED)
        add_button(group_calib, "btn_reset_axis", self.reset_axis_state, tk.DISABLED)
        self.chk_lx = tk.Checkbutton(group_calib, variable=self.is_log_x)
        self.chk_lx.pack(side=tk.LEFT, padx=2)
        self.chk_ly = tk.Checkbutton(group_calib, variable=self.is_log_y)
        self.chk_ly.pack(side=tk.LEFT, padx=2)

        tk.Frame(self.tb, width=2, bg="#ccc").pack(side=tk.LEFT, fill=tk.Y, padx=5)

        group_pick = tk.Frame(self.tb)
        group_pick.pack(side=tk.LEFT, padx=5)
        self.lbl_s2 = tk.Label(group_pick, font=("Arial", 9, "bold"), fg="green")
        self.lbl_s2.pack(side=tk.LEFT)
        add_button(group_pick, "btn_select", self.start_pick, tk.DISABLED)
        add_button(group_pick, "btn_data", self.show_data_win)

        add_button(self.tb, "btn_exit", self.quit_app)
        self.btn_exit.pack(side=tk.RIGHT, padx=5)

        self.status_var = tk.StringVar()
        tk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg="#e8e8e8",
            pady=4,
        ).pack(side=tk.BOTTOM, fill=tk.X)

        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(container, bg="#555", highlightthickness=0)
        vbar = ttk.Scrollbar(container, command=self.canvas.yview)
        vbar.pack(side=tk.RIGHT, fill=tk.Y)
        hbar = ttk.Scrollbar(container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        hbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.config(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_click)
        self.calib_entry = CalibrationEntry(
            self.canvas, self._confirm_calib_value, self._cancel_calib_value
        )
        self.root.bind_all("<Motion>", self._on_pointer_motion, add="+")

    def refresh_ui(self) -> None:
        self.root.title(f"{self.t('title')} v{__version__}")
        for key in TOOLBAR_BUTTONS:
            getattr(self, key).config(text=self.t(key))
        self.lbl_s1.config(text=self.t("lbl_step1"))
        self.lbl_s2.config(text=self.t("lbl_step2"))
        self.chk_lx.config(text=self.t("chk_log_x"))
        self.chk_ly.config(text=self.t("chk_log_y"))
        self.update_status()

    def quit_app(self) -> None:
        self.root.destroy()

    def update_status(self) -> None:
        if self.mode == "VIEW":
            if self.calib_points["x1"] is not None:
                mode_x = "Log" if self.is_log_x.get() else "Lin"
                mode_y = "Log" if self.is_log_y.get() else "Lin"
                self.status_var.set(f"{self.t('status_done')} | X:{mode_x} Y:{mode_y}")
            else:
                self.status_var.set(self.t("status_ready"))
            self.canvas.unbind("<Motion>")
            self.canvas.delete("mag")
        elif self.mode == "SET_AXIS":
            if self.axis_step < len(AXIS_LABELS):
                self.status_var.set(self.t("status_axis") + AXIS_LABELS[self.axis_step])
            self.canvas.bind("<Motion>", self.on_move_throttled)
        elif self.mode == "SELECT_CURVE":
            self.status_var.set(self.t("status_pick"))
            self.canvas.unbind("<Motion>")
            self.canvas.delete("mag")

    # --- 文件与视图 ---

    def load_pdf(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        try:
            source = PdfSource(path, self.base_scale)
        except Exception as error:  # noqa: BLE001 - 文件可能损坏或加密
            messagebox.showerror("Error", f"无法打开 PDF:\n{error}", parent=self.root)
            return

        if self.source is not None:
            self.source.close()
        self.source = source
        self.hq_image = source.image
        self.fit_view()
        self.btn_axis.config(state=tk.NORMAL)
        self.btn_reset_axis.config(state=tk.NORMAL)
        self.status_var.set(self.t("status_ready"))
        # 文件对话框关闭后 macOS 可能把焦点交还给其他应用
        self.root.after(50, self._bring_to_front)

    def fit_view(self) -> None:
        if not self.hq_image:
            return
        canvas_width = self.canvas.winfo_width()
        if canvas_width < 10:
            canvas_width = 800
        image_width, _ = self.hq_image.size
        self.view_scale = canvas_width / image_width
        self.update_canvas()

    def fast_zoom(self, factor: float) -> None:
        if not self.hq_image:
            return
        self.view_scale *= factor
        self.view_scale = max(MIN_ZOOM, min(self.view_scale, MAX_ZOOM))
        self.update_canvas()

    def update_canvas(self) -> None:
        if not self.hq_image:
            return
        self._dismiss_calib_entry()
        width, height = self.hq_image.size
        new_width = int(width * self.view_scale)
        new_height = int(height * self.view_scale)
        self.view_image = self.hq_image.resize(
            (new_width, new_height), Image.Resampling.NEAREST
        )
        self.tk_img = ImageTk.PhotoImage(self.view_image)
        self.canvas.delete("all")
        self.canvas.config(scrollregion=(0, 0, new_width, new_height))
        self.canvas.create_image(0, 0, image=self.tk_img, anchor=tk.NW)
        self.redraw_markers()

    # --- 定标 ---

    def reset_axis_state(self) -> None:
        self.mode = "VIEW"
        self.axis_step = 0
        self._dismiss_calib_entry()
        self.canvas.delete("markers")
        self.canvas.delete("temp_marker")
        self.canvas.delete("highlight")
        self.canvas.delete("mag")
        self.canvas.config(cursor="arrow")
        self.btn_axis.config(state=tk.NORMAL)
        self.btn_select.config(state=tk.DISABLED)
        self.calib_points = {key: None for key in AXIS_FIELDS}
        self.calib_markers_rel = []
        self.update_status()

    def start_axis(self) -> None:
        if not self.hq_image:
            return
        self.mode = "SET_AXIS"
        self.axis_step = 0
        self._dismiss_calib_entry()
        self.btn_axis.config(state=tk.DISABLED)
        self.btn_select.config(state=tk.DISABLED)
        self.canvas.config(cursor="crosshair")
        self.update_status()

    def start_pick(self) -> None:
        self.mode = "SELECT_CURVE"
        self._dismiss_calib_entry()
        self.canvas.config(cursor="hand2")
        self.update_status()

    def _dismiss_calib_entry(self) -> None:
        self.calib_entry.hide()
        self.pending_calib = None
        self._last_mag_pos = None

    # --- 放大镜 ---

    def on_move_throttled(self, event: tk.Event) -> None:
        now = time.time()
        if now - self.last_move_time < MOVE_THROTTLE_SECONDS:
            return
        self.last_move_time = now
        self.on_move(event)

    def on_move(self, event: tk.Event) -> None:
        if not self.view_image:
            return
        if self.mode != "SET_AXIS" or self.calib_entry.is_visible():
            self.canvas.delete("mag")
            self._last_mag_pos = None
            return
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        width, height = self.view_image.size
        margin = MAGNIFIER_SOURCE // 2
        if (
            width < MAGNIFIER_SOURCE + 110
            or height < MAGNIFIER_SOURCE + 110
            or canvas_x < margin
            or canvas_y < margin
            or canvas_x > width - margin
            or canvas_y > height - margin
        ):
            self.canvas.delete("mag")
            self._last_mag_pos = None
            return

        position = (int(canvas_x), int(canvas_y))
        if (
            self._last_mag_pos is not None
            and abs(position[0] - self._last_mag_pos[0]) < MAGNIFIER_MIN_MOVE
            and abs(position[1] - self._last_mag_pos[1]) < MAGNIFIER_MIN_MOVE
        ):
            return
        self._last_mag_pos = position
        try:
            box = (
                int(canvas_x - margin),
                int(canvas_y - margin),
                int(canvas_x + margin),
                int(canvas_y + margin),
            )
            crop = self.view_image.crop(box).resize(
                (MAGNIFIER_SIZE, MAGNIFIER_SIZE), Image.Resampling.NEAREST
            )
            self._mag_img = ImageTk.PhotoImage(crop)
            self.draw_mag(canvas_x, canvas_y, width, height)
        except (ValueError, OSError):
            self.canvas.delete("mag")

    def draw_mag(self, cx: float, cy: float, width: int, height: int) -> None:
        """在画布上直接绘制放大镜，避免独立窗口抢走点击事件。"""
        mx = int(cx - MAGNIFIER_SIZE / 2)
        my = int(cy - MAGNIFIER_SIZE - MAGNIFIER_MARGIN)
        if my < 0:
            my = int(cy + MAGNIFIER_MARGIN)
        mx = max(0, min(mx, width - MAGNIFIER_SIZE))
        my = max(0, min(my, height - MAGNIFIER_SIZE))

        self.canvas.delete("mag")
        self.canvas.create_image(mx, my, image=self._mag_img, anchor=tk.NW, tags="mag")
        self.canvas.create_rectangle(
            mx,
            my,
            mx + MAGNIFIER_SIZE,
            my + MAGNIFIER_SIZE,
            outline="#0078d7",
            width=2,
            tags="mag",
        )
        self.canvas.create_line(
            mx + MAGNIFIER_SIZE // 2,
            my,
            mx + MAGNIFIER_SIZE // 2,
            my + MAGNIFIER_SIZE,
            fill="red",
            width=1,
            tags="mag",
        )
        self.canvas.create_line(
            mx,
            my + MAGNIFIER_SIZE // 2,
            mx + MAGNIFIER_SIZE,
            my + MAGNIFIER_SIZE // 2,
            fill="red",
            width=1,
            tags="mag",
        )

        zoom = MAGNIFIER_SIZE / MAGNIFIER_SOURCE
        for marker in self.calib_markers_rel:
            global_x, global_y = marker["rx"] * width, marker["ry"] * height
            if (
                cx - MAGNIFIER_SOURCE / 2 < global_x < cx + MAGNIFIER_SOURCE / 2
                and cy - MAGNIFIER_SOURCE / 2 < global_y < cy + MAGNIFIER_SOURCE / 2
            ):
                local_x = mx + (global_x - (cx - MAGNIFIER_SOURCE / 2)) * zoom
                local_y = my + (global_y - (cy - MAGNIFIER_SOURCE / 2)) * zoom
                self.canvas.create_oval(
                    local_x - 3,
                    local_y - 3,
                    local_x + 3,
                    local_y + 3,
                    outline="#00FF00",
                    width=2,
                    tags="mag",
                )
                self.canvas.create_text(
                    local_x + 5,
                    local_y - 5,
                    text=marker["key"],
                    fill="#00FF00",
                    anchor="sw",
                    font=("Arial", 9, "bold"),
                    tags="mag",
                )

    # --- 点击处理 ---

    def on_click(self, event: tk.Event) -> None:
        if not self.view_image:
            return
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        width, height = self.view_image.size
        if canvas_x < 0 or canvas_y < 0 or canvas_x > width or canvas_y > height:
            return

        if self.mode == "SET_AXIS":
            self.canvas.delete("mag")
            self._last_mag_pos = None
            self.pending_calib = (canvas_x / width, canvas_y / height)
            key = AXIS_LABELS[self.axis_step]
            default = self.calib_values[AXIS_FIELDS[self.axis_step]]
            # 内嵌非模态输入框：不弹 Toplevel、不 grab，主窗口保持可交互
            self.calib_entry.show(event.x, event.y, key, default)

        elif self.mode == "SELECT_CURVE":
            if self.source is None:
                return
            pdf_x = (canvas_x / width) * self.source.width
            pdf_y = (canvas_y / height) * self.source.height
            self.handle_pick(pdf_x, pdf_y)

        else:
            self.status_var.set(self.t("msg_need_axis"))

    def _confirm_calib_value(self, value: float) -> None:
        if self.pending_calib is None:
            return
        rel_x, rel_y = self.pending_calib
        self.pending_calib = None
        self._record_calib(rel_x, rel_y, value)

    def _cancel_calib_value(self) -> None:
        self.pending_calib = None
        self.update_status()

    def _record_calib(self, rel_x: float, rel_y: float, value: float) -> None:
        field = AXIS_FIELDS[self.axis_step]
        self.calib_points[field] = (rel_x, rel_y)
        self.calib_values[field] = value
        self.calib_markers_rel.append(
            {"rx": rel_x, "ry": rel_y, "val": value, "key": field.upper()}
        )
        self.redraw_markers()
        self.axis_step += 1
        if self.axis_step < len(AXIS_LABELS):
            self.update_status()
            return
        self.mode = "VIEW"
        self.update_status()
        self.btn_select.config(state=tk.NORMAL)
        self.canvas.config(cursor="arrow")

    def redraw_markers(self) -> None:
        self.canvas.delete("markers")
        if not self.view_image:
            return
        width, height = self.view_image.size
        for marker in self.calib_markers_rel:
            cx, cy = marker["rx"] * width, marker["ry"] * height
            self.canvas.create_oval(
                cx - 3, cy - 3, cx + 3, cy + 3, fill="#00FF00", outline="black", tags="markers"
            )
            self.canvas.create_text(
                cx + 5,
                cy - 5,
                text=f"{marker['key']}={marker['val']:g}",
                fill="#00FF00",
                anchor=tk.SW,
                font=("Arial", 10, "bold"),
                tags="markers",
            )

    # --- 曲线拾取与提取 ---

    def handle_pick(self, pdf_x: float, pdf_y: float) -> None:
        assert self.source is not None
        path = self.source.find_path(pdf_x, pdf_y)
        if path is None:
            messagebox.showinfo("Tip", self.t("msg_no_curve"))
            return
        self.extract_data(path)

    def extract_data(self, path: dict[str, Any]) -> None:
        assert self.source is not None
        assert self.view_image is not None

        pdf_points = self.source.path_points(path)
        rel_points = [
            (x / self.source.width, y / self.source.height) for x, y in pdf_points
        ]

        is_log_x = self.is_log_x.get()
        is_log_y = self.is_log_y.get()
        result = [
            map_point(rel_x, rel_y, self.calib_points, self.calib_values, is_log_x, is_log_y)
            for rel_x, rel_y in rel_points
        ]

        view_width, view_height = self.view_image.size
        highlight_coords: list[float] = []
        for rel_x, rel_y in rel_points:
            highlight_coords.extend([rel_x * view_width, rel_y * view_height])

        self.extracted_data = result
        self.canvas.delete("highlight")
        if len(highlight_coords) >= 4:
            self.canvas.create_line(
                highlight_coords, fill="cyan", width=2, tags="highlight"
            )
        DataWindow(self.root, result, self.lang, self)

    def show_data_win(self) -> None:
        if self.extracted_data:
            DataWindow(self.root, self.extracted_data, self.lang, self)
