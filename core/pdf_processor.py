"""PDF processing module for PDF Digitizer Pro.

This module handles PDF file loading, page rendering, and image operations.
"""

from typing import Optional, Tuple, List, Any
import fitz  # PyMuPDF
from PIL import Image
import config


class PDFProcessor:
    """Handles PDF file operations and image processing."""
    
    def __init__(self):
        """Initialize the PDF processor."""
        self.doc: Optional[fitz.Document] = None
        self.page: Optional[fitz.Page] = None
        self.drawings: List[Any] = []
        self.hq_image: Optional[Image.Image] = None
        self.view_image: Optional[Image.Image] = None
        self.base_scale: float = config.BASE_SCALE
        self.view_scale: float = 1.0
        
    def load_pdf(self, file_path: str) -> bool:
        """Load a PDF file and extract the first page.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            Exception: If PDF loading fails
        """
        try:
            self.doc = fitz.open(file_path)
            if len(self.doc) == 0:
                raise ValueError("PDF file is empty")
            self.page = self.doc[0]
            self.drawings = self.page.get_drawings()
            
            # Render page to high-quality image
            matrix = fitz.Matrix(self.base_scale, self.base_scale)
            pixmap = self.page.get_pixmap(matrix=matrix, alpha=False)
            self.hq_image = Image.frombytes(
                "RGB",
                [pixmap.width, pixmap.height],
                pixmap.samples
            )
            
            return True
        except FileNotFoundError:
            raise
        except Exception as e:
            raise Exception(f"Failed to load PDF: {str(e)}")
    
    def get_page_size(self) -> Tuple[float, float]:
        """Get the PDF page size in points.
        
        Returns:
            Tuple of (width, height) in PDF points
        """
        if not self.page:
            return (0.0, 0.0)
        rect = self.page.rect
        return (rect.width, rect.height)
    
    def calculate_fit_scale(self, canvas_width: float, canvas_height: float) -> float:
        """Calculate the scale factor to fit the image in the canvas.
        
        Args:
            canvas_width: Width of the canvas
            canvas_height: Height of the canvas
            
        Returns:
            Scale factor for fitting
        """
        if not self.hq_image:
            return 1.0
        
        if canvas_width < 10:
            canvas_width = 800
        
        img_width, img_height = self.hq_image.size
        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        
        # Use the smaller scale to fit both dimensions
        return min(scale_x, scale_y)
    
    def set_view_scale(self, scale: float) -> None:
        """Set the view scale factor.
        
        Args:
            scale: Scale factor (will be clamped to valid range)
        """
        self.view_scale = max(
            config.MIN_VIEW_SCALE,
            min(scale, config.MAX_VIEW_SCALE)
        )
    
    def zoom(self, factor: float) -> None:
        """Zoom the view by a factor.
        
        Args:
            factor: Zoom factor (multiplier)
        """
        if not self.hq_image:
            return
        self.view_scale *= factor
        self.set_view_scale(self.view_scale)  # Clamp to valid range
    
    def update_view_image(self) -> Optional[Image.Image]:
        """Update the view image based on current scale.
        
        Returns:
            The updated view image, or None if no source image
        """
        if not self.hq_image:
            return None
        
        width, height = self.hq_image.size
        new_width = int(width * self.view_scale)
        new_height = int(height * self.view_scale)
        
        # Choose interpolation method based on config
        if config.IMAGE_INTERPOLATION == "LANCZOS":
            resample = Image.LANCZOS
        elif config.IMAGE_INTERPOLATION == "BILINEAR":
            resample = Image.BILINEAR
        elif config.IMAGE_INTERPOLATION == "BICUBIC":
            resample = Image.BICUBIC
        else:
            resample = Image.NEAREST
        
        self.view_image = self.hq_image.resize(
            (new_width, new_height),
            resample
        )
        
        return self.view_image
    
    def get_view_size(self) -> Tuple[int, int]:
        """Get the current view image size.
        
        Returns:
            Tuple of (width, height) of the view image
        """
        if not self.view_image:
            return (0, 0)
        return self.view_image.size
    
    def close(self) -> None:
        """Close the PDF document and free resources."""
        if self.doc:
            self.doc.close()
            self.doc = None
        self.page = None
        self.drawings = []
        self.hq_image = None
        self.view_image = None

