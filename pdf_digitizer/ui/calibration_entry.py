"""定标数值输入框。

内嵌在画布上的非模态输入框：不使用 Toplevel / grab_set，
避免 macOS 上模态对话框被主窗口遮挡后吞掉主窗口点击的问题。
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

ALLOWED_CHARS = frozenset("0123456789.-eE+")
PLACEMENT_OFFSET_X = 18
PLACEMENT_OFFSET_Y = 16
MIN_WIDTH = 190
INVALID_BG = "#ffcccc"
NORMAL_BG = "#ffffff"


class CalibrationEntry(tk.Frame):
    """点击定标点后出现的数值输入条。"""

    def __init__(
        self,
        parent: tk.Misc,
        on_confirm: Callable[[float], None],
        on_cancel: Callable[[], None],
    ) -> None:
        super().__init__(
            parent,
            bg="#f7f7f7",
            bd=1,
            relief=tk.SOLID,
            highlightthickness=1,
            highlightbackground="#0057b8",
        )
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

        self.label = tk.Label(
            self, text="", bg="#f7f7f7", fg="#0057b8", font=("Arial", 10, "bold")
        )
        self.label.pack(side=tk.LEFT, padx=(5, 2))

        self.var = tk.StringVar()
        validator = (self.register(self._validate), "%P")
        self.entry = tk.Entry(
            self,
            textvariable=self.var,
            width=12,
            font=("Arial", 11),
            validate="key",
            validatecommand=validator,
            bg=NORMAL_BG,
        )
        self.entry.pack(side=tk.LEFT, padx=2, pady=3)
        self.entry.bind("<Return>", self._confirm)
        self.entry.bind("<Escape>", self._cancel)

        self.ok_button = tk.Button(
            self,
            text="✔",
            command=self._confirm,
            bd=0,
            bg="#ddffdd",
            width=3,
            takefocus=0,
        )
        self.ok_button.pack(side=tk.LEFT, padx=(1, 3))

    # --- 显示与隐藏 ---

    def show(self, x: int, y: int, label: str, default: float) -> None:
        """在画布 (x, y) 附近显示输入框。"""
        self.label.config(text=f"{label} =")
        self.var.set(f"{default:g}")
        self.entry.config(bg=NORMAL_BG)

        self.update_idletasks()
        width = max(self.winfo_reqwidth(), MIN_WIDTH)
        height = self.winfo_reqheight()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()

        pos_x = x + PLACEMENT_OFFSET_X
        if pos_x + width > parent_width:
            pos_x = x - width - PLACEMENT_OFFSET_X
        pos_x = max(0, min(pos_x, parent_width - width))
        pos_y = max(0, min(y - PLACEMENT_OFFSET_Y, parent_height - height))

        self.place(x=pos_x, y=pos_y, width=width)
        self.lift()
        self.after(10, self._focus)

    def hide(self) -> None:
        self.place_forget()

    def is_visible(self) -> bool:
        return bool(self.winfo_manager())

    # --- 内部 ---

    def _focus(self) -> None:
        if not self.is_visible():
            return
        self.entry.focus_set()
        self.entry.selection_range(0, tk.END)
        self.entry.icursor(tk.END)

    def _validate(self, proposed: str) -> bool:
        if proposed == "":
            return True
        return all(char in ALLOWED_CHARS for char in proposed)

    def _confirm(self, _event: tk.Event | None = None) -> None:
        try:
            value = float(self.var.get())
        except ValueError:
            self.entry.config(bg=INVALID_BG)
            return
        self.hide()
        self.on_confirm(value)

    def _cancel(self, _event: tk.Event | None = None) -> None:
        self.hide()
        self.on_cancel()
