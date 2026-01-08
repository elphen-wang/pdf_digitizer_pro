"""Calibration module for PDF Digitizer Pro.

This module handles coordinate axis calibration logic.
"""

from typing import Dict, Optional, Tuple, List, Any
import config


class CalibrationState:
    """Manages calibration state and calculations."""
    
    def __init__(self):
        """Initialize calibration state."""
        self.calib_points: Dict[str, Optional[Tuple[float, float]]] = {
            'x1': None,
            'x2': None,
            'y1': None,
            'y2': None
        }
        self.calib_values: Dict[str, float] = config.CALIBRATION_DEFAULT_VALUES.copy()
        self.calib_markers_rel: List[Dict[str, Any]] = []
        self.axis_step: int = 0
        self.current_click_pos_rel: Optional[Tuple[float, float]] = None
    
    def reset(self) -> None:
        """Reset all calibration data."""
        self.calib_points = {
            'x1': None,
            'x2': None,
            'y1': None,
            'y2': None
        }
        self.calib_values = config.CALIBRATION_DEFAULT_VALUES.copy()
        self.calib_markers_rel = []
        self.axis_step = 0
        self.current_click_pos_rel = None
    
    def is_complete(self) -> bool:
        """Check if calibration is complete.
        
        Returns:
            True if all 4 calibration points are set
        """
        return all(
            self.calib_points[key] is not None
            for key in config.CALIBRATION_POINTS
        )
    
    def get_current_point_key(self) -> str:
        """Get the key for the current calibration point.
        
        Returns:
            Key string (x1, x2, y1, or y2)
        """
        if self.axis_step < len(config.CALIBRATION_POINTS):
            return config.CALIBRATION_POINTS[self.axis_step]
        return ""
    
    def get_current_point_label(self) -> str:
        """Get the label for the current calibration point.
        
        Returns:
            Label string (X1, X2, Y1, or Y2)
        """
        keys = ["X1", "X2", "Y1", "Y2"]
        if self.axis_step < len(keys):
            return keys[self.axis_step]
        return ""
    
    def set_calibration_point(
        self,
        relative_x: float,
        relative_y: float,
        value: float
    ) -> None:
        """Set a calibration point.
        
        Args:
            relative_x: Relative X coordinate (0-1)
            relative_y: Relative Y coordinate (0-1)
            value: The actual coordinate value at this point
        """
        if self.axis_step >= len(config.CALIBRATION_POINTS):
            return
        
        key = config.CALIBRATION_POINTS[self.axis_step]
        self.calib_points[key] = (relative_x, relative_y)
        self.calib_values[key] = value
        
        # Add marker
        self.calib_markers_rel.append({
            'rx': relative_x,
            'ry': relative_y,
            'val': value,
            'key': key.upper()
        })
        
        self.axis_step += 1
    
    def get_calibration_data(self) -> Dict[str, Any]:
        """Get all calibration data.
        
        Returns:
            Dictionary containing calibration points and values
        """
        return {
            'points': self.calib_points.copy(),
            'values': self.calib_values.copy(),
            'markers': self.calib_markers_rel.copy()
        }
    
    def get_x_axis_points(self) -> Tuple[Optional[Tuple[float, float]], Optional[Tuple[float, float]]]:
        """Get X-axis calibration points.
        
        Returns:
            Tuple of (x1_point, x2_point) or (None, None) if not set
        """
        return (self.calib_points['x1'], self.calib_points['x2'])
    
    def get_y_axis_points(self) -> Tuple[Optional[Tuple[float, float]], Optional[Tuple[float, float]]]:
        """Get Y-axis calibration points.
        
        Returns:
            Tuple of (y1_point, y2_point) or (None, None) if not set
        """
        return (self.calib_points['y1'], self.calib_points['y2'])
    
    def get_x_axis_values(self) -> Tuple[float, float]:
        """Get X-axis calibration values.
        
        Returns:
            Tuple of (x1_value, x2_value)
        """
        return (self.calib_values['x1'], self.calib_values['x2'])
    
    def get_y_axis_values(self) -> Tuple[float, float]:
        """Get Y-axis calibration values.
        
        Returns:
            Tuple of (y1_value, y2_value)
        """
        return (self.calib_values['y1'], self.calib_values['y2'])

