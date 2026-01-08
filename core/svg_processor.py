"""SVG processing module for PDF Digitizer Pro.

This module handles SVG file loading, rendering, and path extraction.
"""

from typing import Optional, Tuple, List, Any, Dict
import xml.etree.ElementTree as ET
from PIL import Image
import io
import config

try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
    SVG_LIB_AVAILABLE = True
    CAIRO_AVAILABLE = False
except ImportError:
    SVG_LIB_AVAILABLE = False
    try:
        import cairosvg
        CAIRO_AVAILABLE = True
    except ImportError:
        CAIRO_AVAILABLE = False


class SVGProcessor:
    """Handles SVG file operations and path extraction."""
    
    def __init__(self):
        """Initialize the SVG processor."""
        self.svg_tree: Optional[ET.ElementTree] = None
        self.svg_root: Optional[ET.Element] = None
        self.hq_image: Optional[Image.Image] = None
        self.view_image: Optional[Image.Image] = None
        self.paths: List[Dict[str, Any]] = []
        self.view_scale: float = 1.0
        self.svg_width: float = 0.0
        self.svg_height: float = 0.0
        self._file_path: Optional[str] = None
        self._file_path: Optional[str] = None
        
    def load_svg(self, file_path: str) -> bool:
        """Load an SVG file and extract paths.
        
        Args:
            file_path: Path to the SVG file
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            Exception: If SVG loading fails
        """
        try:
            # Parse SVG XML
            self.svg_tree = ET.parse(file_path)
            self.svg_root = self.svg_tree.getroot()
            self._file_path = file_path  # Store for rendering
            
            # Get SVG dimensions
            self._parse_dimensions()
            
            # Extract paths
            self.paths = self._extract_paths()
            
            # Render to image
            self._render_to_image()
            
            return True
        except FileNotFoundError:
            raise
        except Exception as e:
            raise Exception(f"Failed to load SVG: {str(e)}")
    
    def _parse_dimensions(self) -> None:
        """Parse SVG dimensions from root element."""
        # Try to get width and height from root element
        width_str = self.svg_root.get('width', '')
        height_str = self.svg_root.get('height', '')
        viewbox = self.svg_root.get('viewBox', '')
        
        if viewbox:
            # Parse viewBox: "x y width height"
            parts = viewbox.split()
            if len(parts) >= 4:
                self.svg_width = float(parts[2])
                self.svg_height = float(parts[3])
        else:
            # Try to parse width and height
            if width_str and height_str:
                # Remove units if present
                self.svg_width = float(width_str.replace('px', '').replace('pt', ''))
                self.svg_height = float(height_str.replace('px', '').replace('pt', ''))
        
        # Default if not found
        if self.svg_width == 0 or self.svg_height == 0:
            self.svg_width = 800.0
            self.svg_height = 600.0
    
    def _extract_paths(self) -> List[Dict[str, Any]]:
        """Extract path elements from SVG.
        
        Returns:
            List of path dictionaries with coordinates
        """
        paths = []
        
        # Find all path elements
        for path_elem in self.svg_root.iter():
            tag = path_elem.tag
            if '}' in tag:
                tag = tag.split('}')[-1]
            
            if tag == 'path':
                d_attr = path_elem.get('d', '')
                if d_attr:
                    # Parse path data
                    path_data = self._parse_path_data(d_attr)
                    if path_data:
                        # Get bounding box (approximate)
                        bbox = self._calculate_path_bbox(path_data)
                        paths.append({
                            'type': 'path',
                            'data': path_data,
                            'rect': bbox,
                            'element': path_elem
                        })
            elif tag in ['line', 'polyline', 'polygon']:
                # Handle line, polyline, polygon elements
                coords = self._parse_shape_coords(path_elem, tag)
                if coords:
                    bbox = self._calculate_coords_bbox(coords)
                    paths.append({
                        'type': tag,
                        'data': coords,
                        'rect': bbox,
                        'element': path_elem
                    })
        
        return paths
    
    def _parse_path_data(self, d_attr: str) -> List[Tuple[float, float]]:
        """Parse SVG path data string into coordinate points.
        
        Args:
            d_attr: Path data string (e.g., "M 10 20 L 30 40")
            
        Returns:
            List of (x, y) coordinate tuples
        """
        import re
        points = []
        
        # Simple parser for basic path commands
        # This is a simplified version - full SVG path parsing is complex
        commands = re.findall(r'([MLml])\s*([-\d.]+(?:\s+[-\d.]+)*)', d_attr)
        
        current_x, current_y = 0.0, 0.0
        
        for cmd, coords_str in commands:
            coords = [float(x) for x in coords_str.split()]
            
            if cmd.upper() == 'M':  # Move to
                if len(coords) >= 2:
                    current_x, current_y = coords[0], coords[1]
                    points.append((current_x, current_y))
            elif cmd.upper() == 'L':  # Line to
                if len(coords) >= 2:
                    current_x, current_y = coords[0], coords[1]
                    points.append((current_x, current_y))
            elif cmd == 'l':  # Relative line to
                if len(coords) >= 2:
                    current_x += coords[0]
                    current_y += coords[1]
                    points.append((current_x, current_y))
            elif cmd == 'm':  # Relative move to
                if len(coords) >= 2:
                    current_x += coords[0]
                    current_y += coords[1]
                    points.append((current_x, current_y))
        
        return points
    
    def _parse_shape_coords(
        self,
        elem: ET.Element,
        shape_type: str
    ) -> List[Tuple[float, float]]:
        """Parse coordinates from line/polyline/polygon elements.
        
        Args:
            elem: XML element
            shape_type: Type of shape ('line', 'polyline', 'polygon')
            
        Returns:
            List of (x, y) coordinate tuples
        """
        coords = []
        
        if shape_type == 'line':
            x1 = float(elem.get('x1', 0))
            y1 = float(elem.get('y1', 0))
            x2 = float(elem.get('x2', 0))
            y2 = float(elem.get('y2', 0))
            coords = [(x1, y1), (x2, y2)]
        elif shape_type in ['polyline', 'polygon']:
            points_attr = elem.get('points', '')
            # Parse points string: "x1,y1 x2,y2 ..." or "x1 y1 x2 y2 ..."
            if ',' in points_attr:
                pairs = points_attr.split()
                for pair in pairs:
                    x, y = pair.split(',')
                    coords.append((float(x), float(y)))
            else:
                nums = [float(x) for x in points_attr.split()]
                for i in range(0, len(nums), 2):
                    if i + 1 < len(nums):
                        coords.append((nums[i], nums[i + 1]))
        
        return coords
    
    def _calculate_path_bbox(
        self,
        points: List[Tuple[float, float]]
    ) -> Any:
        """Calculate bounding box for path points.
        
        Args:
            points: List of (x, y) coordinates
            
        Returns:
            Bounding box object with x0, y0, x1, y1
        """
        if not points:
            return type('Rect', (), {'x0': 0, 'y0': 0, 'x1': 0, 'y1': 0})()
        
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        
        class Rect:
            def __init__(self):
                self.x0 = min(xs)
                self.y0 = min(ys)
                self.x1 = max(xs)
                self.y1 = max(ys)
        
        return Rect()
    
    def _calculate_coords_bbox(
        self,
        coords: List[Tuple[float, float]]
    ) -> Any:
        """Calculate bounding box for coordinates.
        
        Args:
            coords: List of (x, y) coordinates
            
        Returns:
            Bounding box object
        """
        return self._calculate_path_bbox(coords)
    
    def _render_to_image(self) -> None:
        """Render SVG to PIL Image."""
        if not SVG_LIB_AVAILABLE and not CAIRO_AVAILABLE:
            # Fallback: create a simple placeholder
            self.hq_image = Image.new(
                'RGB',
                (int(self.svg_width * config.BASE_SCALE), int(self.svg_height * config.BASE_SCALE)),
                'white'
            )
            return
        
        try:
            if SVG_LIB_AVAILABLE:
                # Use svglib + reportlab
                # svg2rlg needs file path
                if self._file_path:
                    drawing = svg2rlg(self._file_path)
                    if drawing:
                        # Render to PNG bytes
                        img_bytes = renderPM.drawToString(drawing, fmt='PNG', dpi=72 * config.BASE_SCALE)
                        self.hq_image = Image.open(io.BytesIO(img_bytes))
                    else:
                        raise Exception("Failed to convert SVG")
                else:
                    raise Exception("SVG file path not available")
            elif CAIRO_AVAILABLE:
                # Use cairosvg
                import cairosvg
                svg_string = ET.tostring(self.svg_root, encoding='unicode')
                img_bytes = cairosvg.svg2png(
                    bytestring=svg_string.encode('utf-8'),
                    output_width=int(self.svg_width * config.BASE_SCALE),
                    output_height=int(self.svg_height * config.BASE_SCALE)
                )
                self.hq_image = Image.open(io.BytesIO(img_bytes))
        except Exception as e:
            # Fallback to placeholder
            self.hq_image = Image.new(
                'RGB',
                (int(self.svg_width * config.BASE_SCALE), int(self.svg_height * config.BASE_SCALE)),
                'white'
            )
    
    def get_page_size(self) -> Tuple[float, float]:
        """Get the SVG size.
        
        Returns:
            Tuple of (width, height)
        """
        return (self.svg_width, self.svg_height)
    
    def calculate_fit_scale(
        self,
        canvas_width: float,
        canvas_height: float
    ) -> float:
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
        self.set_view_scale(self.view_scale)
    
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
        
        # Choose interpolation method
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
        """Close the SVG and free resources."""
        self.svg_tree = None
        self.svg_root = None
        self.paths = []
        self.hq_image = None
        self.view_image = None

