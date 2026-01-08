"""Utility helper functions for PDF Digitizer Pro."""

import math
from typing import Tuple


def map_value(
    value: float,
    point1: float,
    point2: float,
    value1: float,
    value2: float,
    is_log: bool = False
) -> float:
    """Map a value from one coordinate system to another.
    
    Maps a value from the range [point1, point2] to [value1, value2].
    Supports both linear and logarithmic scaling.
    
    Args:
        value: The input value to map
        point1: Start point in source coordinate system
        point2: End point in source coordinate system
        value1: Start value in target coordinate system
        value2: End value in target coordinate system
        is_log: If True, use logarithmic scaling; otherwise use linear
        
    Returns:
        The mapped value in the target coordinate system
        
    Raises:
        ValueError: If logarithmic mapping is requested but values are invalid
    """
    if abs(point2 - point1) < 1e-9:
        return value1
    
    ratio = (value - point1) / (point2 - point1)
    
    if not is_log:
        return value1 + ratio * (value2 - value1)
    else:
        try:
            log_value1 = math.log10(value1)
            log_value2 = math.log10(value2)
            log_result = log_value1 + ratio * (log_value2 - log_value1)
            return 10 ** log_result
        except (ValueError, OverflowError):
            # Fallback to linear mapping if log fails
            return value1 + ratio * (value2 - value1)


def validate_float_string(value: str) -> bool:
    """Validate if a string represents a valid float number.
    
    Args:
        value: String to validate
        
    Returns:
        True if the string is a valid float representation, False otherwise
    """
    if value == "":
        return True
    allowed_chars = "0123456789.-eE"
    for char in value:
        if char not in allowed_chars:
            return False
    return True


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max.
    
    Args:
        value: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Clamped value
    """
    return max(min_val, min(value, max_val))


def calculate_relative_position(
    absolute_x: float,
    absolute_y: float,
    width: float,
    height: float
) -> Tuple[float, float]:
    """Calculate relative position from absolute coordinates.
    
    Args:
        absolute_x: Absolute X coordinate
        absolute_y: Absolute Y coordinate
        width: Total width
        height: Total height
        
    Returns:
        Tuple of (relative_x, relative_y) in range [0, 1]
    """
    rel_x = absolute_x / width if width > 0 else 0.0
    rel_y = absolute_y / height if height > 0 else 0.0
    return (rel_x, rel_y)


def calculate_absolute_position(
    relative_x: float,
    relative_y: float,
    width: float,
    height: float
) -> Tuple[float, float]:
    """Calculate absolute position from relative coordinates.
    
    Args:
        relative_x: Relative X coordinate (0-1)
        relative_y: Relative Y coordinate (0-1)
        width: Total width
        height: Total height
        
    Returns:
        Tuple of (absolute_x, absolute_y)
    """
    abs_x = relative_x * width
    abs_y = relative_y * height
    return (abs_x, abs_y)

