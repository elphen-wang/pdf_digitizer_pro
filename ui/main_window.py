"""Main window module for PDF Digitizer Pro.

This module contains the main application window and coordinates
all UI components and core processing modules.
"""

from typing import Optional, List, Tuple, Any, Dict
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import sys
import time

import config
import os
from core.pdf_processor import PDFProcessor
from core.svg_processor import SVGProcessor
from core.calibration import CalibrationState
from core.data_extractor import DataExtractor
from ui.components import OverlayInput, FastMag, DataWindow
from utils.helpers import calculate_relative_position, calculate_absolute_position

# Try to import drag and drop support
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    TkinterDnD = None


class PDFCurveExtractor:
    """Main application class for PDF curve extraction."""
    
    # Application modes
    MODE_VIEW = "VIEW"
    MODE_SET_AXIS = "SET_AXIS"
    MODE_SELECT_CURVE = "SELECT_CURVE"
    
    def __init__(self, root: tk.Tk):
        """Initialize the main application.
        
        Args:
            root: Root Tkinter window
        """
        self.root = root
        self.lang = config.DEFAULT_LANGUAGE
        self.root.geometry(config.DEFAULT_WINDOW_SIZE)
        
        # Core modules
        self.pdf_processor = PDFProcessor()
        self.svg_processor: Optional[SVGProcessor] = None
        self.calibration = CalibrationState()
        self.data_extractor: Optional[DataExtractor] = None
        self.file_type: str = "PDF"  # "PDF" or "SVG"
        
        # Application state
        self.mode = self.MODE_VIEW
        self.tk_img: Optional[ImageTk.PhotoImage] = None
        self.sub_windows: List[DataWindow] = []
        self.extracted_data: List[Tuple[float, float]] = []
        
        # UI state
        self.is_log_x = tk.BooleanVar(value=False)
        self.is_log_y = tk.BooleanVar(value=False)
        self.last_move_time = 0.0
        self._last_move_pos: Optional[Tuple[int, int]] = None
        
        # Performance optimization: marker coordinate cache
        self._marker_coord_cache: Optional[Dict[str, Tuple[float, float]]] = None
        self._last_view_size: Optional[Tuple[int, int]] = None
        
        # UI components
        self.mag = FastMag(root)
        self.setup_ui()
        self.overlay_input = OverlayInput(
            self.canvas,
            self.on_input_confirm,
            self.on_input_cancel
        )
        self.refresh_ui()
    
    def t(self, key: str) -> str:
        """Get translated text for a key.
        
        Args:
            key: Translation key
            
        Returns:
            Translated text or key if not found
        """
        return config.LANG_MAP.get(key, {}).get(self.lang, key)
    
    def toggle_lang(self) -> None:
        """Toggle between Chinese and English language."""
        self.lang = "EN" if self.lang == "CN" else "CN"
        self.refresh_ui()
        for win in self.sub_windows:
            if win.winfo_exists():
                win.update_lang_ui(self.lang)
    
    def setup_ui(self) -> None:
        """Setup the main UI components."""
        # Toolbar
        self.tb = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        self.tb.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2)
        
        def add_btn(
            parent: tk.Widget,
            key: str,
            cmd: Any,
            state: str = tk.NORMAL
        ) -> tk.Button:
            """Helper to add button and store reference."""
            btn = tk.Button(
                parent,
                command=cmd,
                state=state,
                relief=tk.GROOVE,
                bg="#f9f9f9"
            )
            btn.pack(side=tk.LEFT, padx=2, pady=2, fill=tk.Y)
            setattr(self, key, btn)
            return btn
        
        # Toolbar group 1: File operations
        f1 = tk.Frame(self.tb)
        f1.pack(side=tk.LEFT, padx=5)
        add_btn(f1, "btn_open", self.load_pdf)
        add_btn(f1, "btn_zi", lambda: self.fast_zoom(config.ZOOM_IN_FACTOR))
        add_btn(f1, "btn_zo", lambda: self.fast_zoom(config.ZOOM_OUT_FACTOR))
        add_btn(f1, "btn_rv", self.fit_view)
        add_btn(f1, "btn_lng", self.toggle_lang)
        
        # Separator
        tk.Frame(self.tb, width=2, bg="#ccc").pack(
            side=tk.LEFT,
            fill=tk.Y,
            padx=5
        )
        
        # Toolbar group 2: Calibration
        f2 = tk.Frame(self.tb)
        f2.pack(side=tk.LEFT, padx=5)
        self.lbl_s1 = tk.Label(
            f2,
            font=("Arial", 9, "bold"),
            fg="blue"
        )
        self.lbl_s1.pack(side=tk.LEFT)
        add_btn(f2, "btn_axis", self.start_axis, tk.DISABLED)
        add_btn(f2, "btn_reset_axis", self.reset_axis_state, tk.DISABLED)
        self.chk_lx = tk.Checkbutton(f2, variable=self.is_log_x)
        self.chk_lx.pack(side=tk.LEFT, padx=2)
        self.chk_ly = tk.Checkbutton(f2, variable=self.is_log_y)
        self.chk_ly.pack(side=tk.LEFT, padx=2)
        
        # Separator
        tk.Frame(self.tb, width=2, bg="#ccc").pack(
            side=tk.LEFT,
            fill=tk.Y,
            padx=5
        )
        
        # Toolbar group 3: Extraction
        f3 = tk.Frame(self.tb)
        f3.pack(side=tk.LEFT, padx=5)
        self.lbl_s2 = tk.Label(
            f3,
            font=("Arial", 9, "bold"),
            fg="green"
        )
        self.lbl_s2.pack(side=tk.LEFT)
        add_btn(f3, "btn_select", self.start_pick, tk.DISABLED)
        add_btn(f3, "btn_data", self.show_data_win)
        
        # Exit button
        add_btn(self.tb, "btn_exit", self.quit_app)
        self.btn_exit.pack(side=tk.RIGHT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        tk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg="#e8e8e8",
            pady=4
        ).pack(side=tk.BOTTOM, fill=tk.X)
        
        # Canvas with scrollbars
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(
            container,
            bg="#555",
            highlightthickness=0
        )
        vb = ttk.Scrollbar(container, command=self.canvas.yview)
        vb.pack(side=tk.RIGHT, fill=tk.Y)
        hb = ttk.Scrollbar(
            container,
            orient=tk.HORIZONTAL,
            command=self.canvas.xview
        )
        hb.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.config(yscrollcommand=vb.set, xscrollcommand=hb.set)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_click)
        
        # Setup drag and drop if available
        if DND_AVAILABLE:
            self._setup_drag_drop()
    
    def refresh_ui(self) -> None:
        """Refresh UI text based on current language."""
        self.root.title(self.t("title"))
        for key in [
            "btn_open", "btn_zi", "btn_zo", "btn_rv", "btn_lng",
            "btn_axis", "btn_reset_axis", "btn_select", "btn_data", "btn_exit"
        ]:
            getattr(self, key).config(text=self.t(key))
        self.lbl_s1.config(text=self.t("lbl_step1"))
        self.lbl_s2.config(text=self.t("lbl_step2"))
        self.chk_lx.config(text=self.t("chk_log_x"))
        self.chk_ly.config(text=self.t("chk_log_y"))
        self.update_status()
    
    def quit_app(self) -> None:
        """Quit the application."""
        self.pdf_processor.close()
        if self.svg_processor:
            self.svg_processor.close()
        self.root.quit()
        sys.exit()
    
    def update_status(self) -> None:
        """Update status bar text based on current mode."""
        if self.mode == self.MODE_VIEW:
            if self.calibration.is_complete():
                mx = "Log" if self.is_log_x.get() else "Lin"
                my = "Log" if self.is_log_y.get() else "Lin"
                self.status_var.set(
                    f"{self.t('status_done')} | X:{mx} Y:{my}"
                )
            else:
                self.status_var.set(self.t("status_ready"))
            self.canvas.unbind("<Motion>")
        elif self.mode == self.MODE_SET_AXIS:
            if self.calibration.axis_step < 4:
                label = self.calibration.get_current_point_label()
                self.status_var.set(self.t("status_axis") + label)
            self.canvas.bind("<Motion>", self.on_move_throttled)
        elif self.mode == self.MODE_SELECT_CURVE:
            self.status_var.set(self.t("status_pick"))
            self.canvas.unbind("<Motion>")
    
    def _setup_drag_drop(self) -> None:
        """Setup drag and drop functionality."""
        if not DND_AVAILABLE:
            return
        
        try:
            # Make root window droppable
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self._on_file_drop)
            
            # Make canvas droppable
            self.canvas.drop_target_register(DND_FILES)
            self.canvas.dnd_bind('<<Drop>>', self._on_file_drop)
        except Exception:
            pass  # Silently fail if DnD setup fails
    
    def _on_file_drop(self, event: Any) -> None:
        """Handle file drop event.
        
        Args:
            event: Drop event
        """
        if not DND_AVAILABLE:
            return
        
        try:
            # Get dropped file path
            files = self.root.tk.splitlist(event.data)
            if files:
                file_path = files[0]
                self._load_file(file_path)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load file: {str(e)}",
                parent=self.root
            )
    
    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type from extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            File type: "PDF", "SVG", or "UNKNOWN"
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext in config.SUPPORTED_PDF_EXTENSIONS:
            return "PDF"
        elif ext in config.SUPPORTED_SVG_EXTENSIONS:
            return "SVG"
        return "UNKNOWN"
    
    def _load_file(self, file_path: str) -> None:
        """Load a file (PDF or SVG).
        
        Args:
            file_path: Path to file
        """
        file_type = self._detect_file_type(file_path)
        
        try:
            if file_type == "PDF":
                self.pdf_processor.load_pdf(file_path)
                self.svg_processor = None
                self.file_type = "PDF"
                self.data_extractor = DataExtractor(self.calibration)
            elif file_type == "SVG":
                self.svg_processor = SVGProcessor()
                self.svg_processor.load_svg(file_path)
                self.file_type = "SVG"
                self.data_extractor = DataExtractor(self.calibration)
            else:
                messagebox.showerror(
                    "Error",
                    f"Unsupported file type. Please use PDF or SVG files.",
                    parent=self.root
                )
                return
            
            self.fit_view()
            self.btn_axis.config(state=tk.NORMAL)
            self.btn_reset_axis.config(state=tk.NORMAL)
            self.status_var.set(self.t("status_ready"))
        except FileNotFoundError:
            messagebox.showerror(
                "Error",
                f"File not found: {file_path}",
                parent=self.root
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to load file: {str(e)}",
                parent=self.root
            )
    
    def load_pdf(self) -> None:
        """Load a PDF or SVG file via file dialog."""
        path = filedialog.askopenfilename(
            filetypes=[
                ("PDF files", "*.pdf"),
                ("SVG files", "*.svg"),
                ("All supported", "*.pdf;*.svg")
            ]
        )
        if not path:
            return
        self._load_file(path)
    
    def fit_view(self) -> None:
        """Fit the image to the canvas."""
        processor = self._get_current_processor()
        if not processor or not processor.hq_image:
            return
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        scale = processor.calculate_fit_scale(
            canvas_width,
            canvas_height
        )
        processor.set_view_scale(scale)
        self.update_canvas()
    
    def _get_current_processor(self):
        """Get the current file processor (PDF or SVG).
        
        Returns:
            PDFProcessor or SVGProcessor instance
        """
        if self.file_type == "SVG" and self.svg_processor:
            return self.svg_processor
        return self.pdf_processor
    
    def fast_zoom(self, factor: float) -> None:
        """Zoom the view by a factor.
        
        Args:
            factor: Zoom factor (multiplier)
        """
        processor = self._get_current_processor()
        if not processor or not processor.hq_image:
            return
        processor.zoom(factor)
        self.update_canvas()
    
    def update_canvas(self) -> None:
        """Update the canvas with current view image."""
        processor = self._get_current_processor()
        if not processor:
            return
        
        view_img = processor.update_view_image()
        if not view_img:
            return
        
        self.tk_img = ImageTk.PhotoImage(view_img)
        self.canvas.delete("all")
        
        width, height = view_img.size
        self.canvas.config(scrollregion=(0, 0, width, height))
        self.canvas.create_image(0, 0, image=self.tk_img, anchor=tk.NW)
        self.redraw_markers()
    
    def reset_axis_state(self) -> None:
        """Reset calibration state."""
        self.mode = self.MODE_VIEW
        self.calibration.reset()
        self.overlay_input.hide()
        self.canvas.delete("markers")
        self.canvas.delete("temp_marker")
        self.canvas.delete("highlight")
        self.canvas.config(cursor="arrow")
        self.btn_axis.config(state=tk.NORMAL)
        self.btn_select.config(state=tk.DISABLED)
        self.mag.hide()
        self.update_status()
    
    def start_axis(self) -> None:
        """Start axis calibration mode."""
        processor = self._get_current_processor()
        if not processor or not processor.hq_image:
            return
        self.mode = self.MODE_SET_AXIS
        self.calibration.reset()
        self.btn_axis.config(state=tk.DISABLED)
        self.btn_select.config(state=tk.DISABLED)
        self.canvas.config(cursor="crosshair")
        self.update_status()
    
    def start_pick(self) -> None:
        """Start curve picking mode."""
        self.mode = self.MODE_SELECT_CURVE
        self.canvas.config(cursor="hand2")
        self.update_status()
    
    def on_move_throttled(self, event: tk.Event) -> None:
        """Throttled mouse move handler with adaptive throttling.
        
        Args:
            event: Mouse event
        """
        now = time.time()
        elapsed = now - self.last_move_time
        
        # Adaptive throttling: faster movement = more frequent updates
        # Calculate movement speed (simple heuristic)
        if self._last_move_pos is not None:
            dx = abs(event.x - self._last_move_pos[0])
            dy = abs(event.y - self._last_move_pos[1])
            distance = dx + dy
            
            # If moved significantly, update immediately (for smooth tracking)
            if distance > 3.0:
                throttle = 0.0  # No throttle for significant movement
            else:
                speed = distance / max(elapsed, 0.001)  # pixels per second
                
                # Adjust throttle interval based on speed
                # Fast movement (>300 px/s): update more frequently
                if speed > 300:
                    throttle = config.MOVE_THROTTLE_INTERVAL * 0.5
                else:
                    throttle = config.MOVE_THROTTLE_INTERVAL
        else:
            throttle = 0.0  # First call, no throttle
        
        if elapsed < throttle:
            return
        
        self.last_move_time = now
        self._last_move_pos = (event.x, event.y)
        
        # Call on_move directly (removed after_idle to ensure magnifier shows immediately)
        self.on_move(event)
    
    def on_move(self, event: tk.Event) -> None:
        """Handle mouse movement.
        
        Args:
            event: Mouse event
        """
        processor = self._get_current_processor()
        if not processor or not processor.view_image:
            return
        
        if self.mode == self.MODE_SET_AXIS:
            if self.overlay_input.winfo_ismapped():
                self.mag.hide()
                return
            
            cx = self.canvas.canvasx(event.x)
            cy = self.canvas.canvasy(event.y)
            width, height = processor.get_view_size()
            
            # Hide magnifier if near edges
            margin = 20
            if (cx < margin or cy < margin or
                cx > width - margin or cy > height - margin):
                self.mag.hide()
                return
            
            try:
                # Create crop box for magnifier
                crop_size = config.MAGNIFIER_CROP_RADIUS * 2
                box = (
                    int(cx - config.MAGNIFIER_CROP_RADIUS),
                    int(cy - config.MAGNIFIER_CROP_RADIUS),
                    int(cx + config.MAGNIFIER_CROP_RADIUS),
                    int(cy + config.MAGNIFIER_CROP_RADIUS)
                )
                
                # Ensure box is within image bounds
                box = (
                    max(0, box[0]),
                    max(0, box[1]),
                    min(width, box[2]),
                    min(height, box[3])
                )
                
                crop_img = processor.view_image.crop(box)
                crop_img = crop_img.resize(
                    (config.MAGNIFIER_SIZE, config.MAGNIFIER_SIZE),
                    Image.NEAREST
                )
                
                # Get existing markers in canvas coordinates (with caching)
                markers = self._get_marker_coordinates(width, height)
                
                self.mag.show(
                    event.x_root,
                    event.y_root,
                    crop_img,
                    (cx, cy),
                    markers
                )
            except Exception:
                pass
        else:
            self.mag.hide()
    
    def on_click(self, event: tk.Event) -> None:
        """Handle mouse click.
        
        Args:
            event: Mouse click event
        """
        processor = self._get_current_processor()
        if not processor or not processor.view_image:
            return
        
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        width, height = processor.get_view_size()
        
        # Hide overlay input if clicking elsewhere
        if self.overlay_input.winfo_ismapped():
            self.overlay_input.hide()
            self.canvas.delete("temp_marker")
            return
        
        # Check bounds
        if cx < 0 or cy < 0 or cx > width or cy > height:
            return
        
        if self.mode == self.MODE_SET_AXIS:
            self.mag.hide()
            rel_x, rel_y = calculate_relative_position(cx, cy, width, height)
            self.calibration.current_click_pos_rel = (rel_x, rel_y)
            
            # Show temporary marker
            self.canvas.create_oval(
                cx - config.MARKER_SIZE,
                cy - config.MARKER_SIZE,
                cx + config.MARKER_SIZE,
                cy + config.MARKER_SIZE,
                fill="yellow",
                tags="temp_marker"
            )
            
            # Show input overlay
            key = self.calibration.get_current_point_key()
            label = self.calibration.get_current_point_label()
            default_val = self.calibration.calib_values[key]
            self.overlay_input.show(event.x, event.y, default_val, label)
            
        elif self.mode == self.MODE_SELECT_CURVE:
            # Convert canvas coordinates to document coordinates
            doc_width, doc_height = processor.get_page_size()
            target_doc_x = (cx / width) * doc_width
            target_doc_y = (cy / height) * doc_height
            self.handle_pick(target_doc_x, target_doc_y)
    
    def on_input_confirm(self, val: float) -> None:
        """Handle confirmation of calibration input.
        
        Args:
            val: The confirmed coordinate value
        """
        if not self.calibration.current_click_pos_rel:
            return
        
        self.canvas.delete("temp_marker")
        rel_x, rel_y = self.calibration.current_click_pos_rel
        
        # Set calibration point
        self.calibration.set_calibration_point(rel_x, rel_y, val)
        self.redraw_markers()
        
        # Check if calibration is complete
        if self.calibration.axis_step < 4:
            self.update_status()
        else:
            self.mode = self.MODE_VIEW
            self.update_status()
            self.btn_select.config(state=tk.NORMAL)
            self.canvas.config(cursor="arrow")
    
    def on_input_cancel(self) -> None:
        """Handle cancellation of calibration input."""
        self.canvas.delete("temp_marker")
    
    def _get_marker_coordinates(
        self,
        width: int,
        height: int
    ) -> List[Tuple[float, float, str]]:
        """Get marker coordinates with caching.
        
        Args:
            width: View width
            height: View height
            
        Returns:
            List of (x, y, key) tuples
        """
        # Check if cache is valid
        current_view_size = (width, height)
        if (config.MARKER_COORD_CACHE_ENABLED and
            self._marker_coord_cache is not None and
            self._last_view_size == current_view_size):
            # Use cached coordinates
            markers = []
            for marker in self.calibration.calib_markers_rel:
                key = marker['key']
                if key in self._marker_coord_cache:
                    abs_x, abs_y = self._marker_coord_cache[key]
                    markers.append((abs_x, abs_y, key))
            return markers
        
        # Calculate and cache coordinates
        markers = []
        if config.MARKER_COORD_CACHE_ENABLED:
            self._marker_coord_cache = {}
        
        for marker in self.calibration.calib_markers_rel:
            abs_x, abs_y = calculate_absolute_position(
                marker['rx'],
                marker['ry'],
                width,
                height
            )
            markers.append((abs_x, abs_y, marker['key']))
            
            if config.MARKER_COORD_CACHE_ENABLED:
                self._marker_coord_cache[marker['key']] = (abs_x, abs_y)
        
        self._last_view_size = current_view_size
        return markers
    
    def redraw_markers(self) -> None:
        """Redraw calibration markers on canvas."""
        self.canvas.delete("markers")
        processor = self._get_current_processor()
        if not processor or not processor.view_image:
            return
        
        # Invalidate cache when redrawing
        self._marker_coord_cache = None
        
        width, height = processor.get_view_size()
        for marker in self.calibration.calib_markers_rel:
            abs_x, abs_y = calculate_absolute_position(
                marker['rx'],
                marker['ry'],
                width,
                height
            )
            color = config.MARKER_COLOR
            self.canvas.create_oval(
                abs_x - config.MARKER_SIZE,
                abs_y - config.MARKER_SIZE,
                abs_x + config.MARKER_SIZE,
                abs_y + config.MARKER_SIZE,
                fill=color,
                outline="black",
                tags="markers"
            )
            self.canvas.create_text(
                abs_x + 5,
                abs_y - 5,
                text=f"{marker['key']}={marker['val']:g}",
                fill=color,
                anchor=tk.SW,
                font=("Arial", 10, "bold"),
                tags="markers"
            )
    
    def handle_pick(self, doc_x: float, doc_y: float) -> None:
        """Handle curve picking at document coordinates.
        
        Args:
            doc_x: X coordinate in document space
            doc_y: Y coordinate in document space
        """
        if not self.data_extractor:
            return
        
        processor = self._get_current_processor()
        if not processor:
            return
        
        # Get drawings/paths based on file type
        is_svg = (self.file_type == "SVG")
        if is_svg and self.svg_processor:
            drawings = self.svg_processor.paths
        else:
            drawings = self.pdf_processor.drawings
        
        # Find nearest path
        path = self.data_extractor.find_nearest_path(
            doc_x,
            doc_y,
            drawings,
            is_svg=is_svg
        )
        
        if path:
            self.extract_data(path, is_svg=is_svg)
        else:
            messagebox.showinfo("Tip", self.t("msg_no_curve"), parent=self.root)
    
    def extract_data(self, path: Any, is_svg: bool = False) -> None:
        """Extract data from a drawing path.
        
        Args:
            path: Drawing path from PDF or SVG
            is_svg: True if processing SVG path
        """
        if not self.data_extractor:
            return
        
        processor = self._get_current_processor()
        if not processor:
            return
        
        doc_width, doc_height = processor.get_page_size()
        view_width, view_height = processor.get_view_size()
        
        # Extract and transform data
        transformed_points, highlight_coords = self.data_extractor.extract_curve_data(
            path,
            doc_width,
            doc_height,
            view_width,
            view_height,
            self.is_log_x.get(),
            self.is_log_y.get(),
            is_svg=is_svg
        )
        
        self.extracted_data = transformed_points
        
        # Draw highlight
        self.canvas.delete("highlight")
        if len(highlight_coords) >= 4:
            self.canvas.create_line(
                highlight_coords,
                fill=config.HIGHLIGHT_COLOR,
                width=config.HIGHLIGHT_WIDTH,
                tags="highlight"
            )
        
        # Show data window
        DataWindow(self.root, transformed_points, self.lang, self)
    
    def show_data_win(self) -> None:
        """Show data window with extracted data."""
        if self.extracted_data:
            DataWindow(self.root, self.extracted_data, self.lang, self)

