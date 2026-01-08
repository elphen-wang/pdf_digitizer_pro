"""Data extraction module for PDF Digitizer Pro.

This module handles curve data extraction and coordinate transformation.
"""

from typing import List, Tuple, Any, Optional
import fitz  # PyMuPDF
from core.calibration import CalibrationState
from utils.helpers import map_value, calculate_relative_position
import config


class DataExtractor:
    """Handles curve data extraction from PDF drawings."""
    
    def __init__(self, calibration: CalibrationState):
        """Initialize the data extractor.
        
        Args:
            calibration: Calibration state object
        """
        self.calibration = calibration
    
    def find_nearest_path(
        self,
        pdf_x: float,
        pdf_y: float,
        drawings: List[Any],
        search_radius: float = config.SEARCH_RADIUS,
        is_svg: bool = False
    ) -> Optional[Any]:
        """Find the nearest drawing path to a given point.
        
        Args:
            pdf_x: X coordinate in document space
            pdf_y: Y coordinate in document space
            drawings: List of drawing paths (PDF or SVG)
            search_radius: Maximum search radius
            is_svg: True if processing SVG paths
            
        Returns:
            The nearest path if found within radius, None otherwise
        """
        best_path = None
        min_dist_sq = float('inf')
        
        for path in drawings:
            rect = path.get('rect') if isinstance(path, dict) else path['rect']
            
            # Quick bounding box check
            if (pdf_x < rect.x0 - search_radius or
                pdf_x > rect.x1 + search_radius or
                pdf_y < rect.y0 - search_radius or
                pdf_y > rect.y1 + search_radius):
                continue
            
            if is_svg:
                # For SVG paths, check distance to path data points
                path_data = path.get('data', [])
                for point in path_data:
                    if isinstance(point, tuple) and len(point) >= 2:
                        px, py = point[0], point[1]
                        dist_sq = (px - pdf_x) ** 2 + (py - pdf_y) ** 2
                        if dist_sq < min_dist_sq:
                            min_dist_sq = dist_sq
                            best_path = path
            else:
                # For PDF paths, check distance to path items
                for item in path.get('items', []):
                    if len(item) > 0:
                        pt = item[-1]
                        if hasattr(pt, 'x') and hasattr(pt, 'y'):
                            dist_sq = (pt.x - pdf_x) ** 2 + (pt.y - pdf_y) ** 2
                            if dist_sq < min_dist_sq:
                                min_dist_sq = dist_sq
                                best_path = path
        
        if best_path and min_dist_sq < (search_radius ** 2):
            return best_path
        
        return None
    
    def extract_path_points(self, path: Any, is_svg: bool = False) -> List[Any]:
        """Extract all points from a drawing path.
        
        Args:
            path: Drawing path from PDF or SVG
            is_svg: True if processing SVG path
            
        Returns:
            List of point objects or tuples
        """
        if is_svg:
            # For SVG, path data is already a list of (x, y) tuples
            path_data = path.get('data', [])
            # Convert to point-like objects for compatibility
            class Point:
                def __init__(self, x, y):
                    self.x = x
                    self.y = y
            
            return [Point(p[0], p[1]) for p in path_data if isinstance(p, tuple) and len(p) >= 2]
        else:
            # For PDF paths
            points = []
            for item in path.get('items', []):
                op = item[0]
                if op == 'l':  # Line
                    if len(item) >= 3:
                        points.append(item[1])
                        points.append(item[2])
                elif op == 'c':  # Curve
                    if len(item) >= 5:
                        points.append(item[1])
                        points.append(item[2])
                        points.append(item[3])
                        points.append(item[4])
            return points
    
    def transform_points(
        self,
        points: List[Any],
        pdf_width: float,
        pdf_height: float,
        is_log_x: bool = False,
        is_log_y: bool = False
    ) -> Tuple[List[Tuple[float, float]], List[float]]:
        """Transform PDF points to real-world coordinates.
        
        Args:
            points: List of PDF point objects
            pdf_width: PDF page width
            pdf_height: PDF page height
            is_log_x: Use logarithmic scaling for X axis
            is_log_y: Use logarithmic scaling for Y axis
            
        Returns:
            Tuple of (transformed_points, highlight_coordinates)
            - transformed_points: List of (x, y) tuples in real coordinates
            - highlight_coords: Flat list of coordinates for highlighting
        """
        if not self.calibration.is_complete():
            return ([], [])
        
        # Get calibration data
        x1_point, x2_point = self.calibration.get_x_axis_points()
        y1_point, y2_point = self.calibration.get_y_axis_points()
        x1_val, x2_val = self.calibration.get_x_axis_values()
        y1_val, y2_val = self.calibration.get_y_axis_values()
        
        if not all([x1_point, x2_point, y1_point, y2_point]):
            return ([], [])
        
        transformed_points = []
        highlight_coords = []
        
        for point in points:
            if not (hasattr(point, 'x') and hasattr(point, 'y')):
                continue
            
            # Calculate relative position
            rel_x, rel_y = calculate_relative_position(
                point.x, point.y, pdf_width, pdf_height
            )
            
            # Transform X coordinate
            real_x = map_value(
                rel_x,
                x1_point[0],  # x1 relative x
                x2_point[0],  # x2 relative x
                x1_val,
                x2_val,
                is_log_x
            )
            
            # Transform Y coordinate
            real_y = map_value(
                rel_y,
                y1_point[1],  # y1 relative y
                y2_point[1],  # y2 relative y
                y1_val,
                y2_val,
                is_log_y
            )
            
            transformed_points.append((real_x, real_y))
            highlight_coords.extend([rel_x, rel_y])
        
        return (transformed_points, highlight_coords)
    
    def extract_curve_data(
        self,
        path: Any,
        pdf_width: float,
        pdf_height: float,
        view_width: float,
        view_height: float,
        is_log_x: bool = False,
        is_log_y: bool = False,
        is_svg: bool = False
    ) -> Tuple[List[Tuple[float, float]], List[float]]:
        """Extract and transform curve data from a path.
        
        Args:
            path: Drawing path from PDF or SVG
            pdf_width: Document width
            pdf_height: Document height
            view_width: View image width
            view_height: View image height
            is_log_x: Use logarithmic scaling for X axis
            is_log_y: Use logarithmic scaling for Y axis
            is_svg: True if processing SVG path
            
        Returns:
            Tuple of (transformed_points, highlight_coordinates)
        """
        # Extract points from path
        points = self.extract_path_points(path, is_svg=is_svg)
        
        # Transform to real coordinates
        transformed_points, highlight_coords_rel = self.transform_points(
            points,
            pdf_width,
            pdf_height,
            is_log_x,
            is_log_y
        )
        
        # Convert relative highlight coordinates to view coordinates
        highlight_coords = []
        for i in range(0, len(highlight_coords_rel), 2):
            if i + 1 < len(highlight_coords_rel):
                highlight_coords.append(highlight_coords_rel[i] * view_width)
                highlight_coords.append(highlight_coords_rel[i + 1] * view_height)
        
        return (transformed_points, highlight_coords)

