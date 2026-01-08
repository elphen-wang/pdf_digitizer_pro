"""Main entry point for PDF Digitizer Pro.

This module initializes and runs the main application.
"""

import tkinter as tk

# Try to use TkinterDnD for drag and drop support
try:
    from tkinterdnd2 import TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    TkinterDnD = tk.Tk

from ui.main_window import PDFCurveExtractor


def main() -> None:
    """Main function to start the application."""
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = PDFCurveExtractor(root)
    root.mainloop()


if __name__ == "__main__":
    main()

