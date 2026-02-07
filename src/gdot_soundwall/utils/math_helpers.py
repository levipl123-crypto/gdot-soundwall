"""Mathematical helpers for bearings, offsets, and interpolation."""
from __future__ import annotations

import math
from typing import Tuple


def normalize_angle(angle: float) -> float:
    """Normalize angle to [0, 2*pi)."""
    angle = angle % (2 * math.pi)
    if angle < 0:
        angle += 2 * math.pi
    return angle


def bearing_to_math_angle(bearing: float) -> float:
    """Convert survey bearing (clockwise from north) to math angle (CCW from east)."""
    return normalize_angle(math.pi / 2 - bearing)


def math_angle_to_bearing(angle: float) -> float:
    """Convert math angle (CCW from east) to survey bearing (CW from north)."""
    return normalize_angle(math.pi / 2 - angle)


def azimuth_from_points(x1: float, y1: float, x2: float, y2: float) -> float:
    """Compute azimuth (bearing) from point 1 to point 2.

    Returns bearing in radians, clockwise from north (positive Y axis).
    """
    dx = x2 - x1
    dy = y2 - y1
    return normalize_angle(math.atan2(dx, dy))


def offset_point(
    easting: float, northing: float, bearing: float, offset: float
) -> Tuple[float, float]:
    """Compute a point offset perpendicular to a bearing.

    Args:
        easting: Base point easting.
        northing: Base point northing.
        bearing: Direction of travel (radians, CW from north).
        offset: Perpendicular offset (positive = right of travel).

    Returns:
        (easting, northing) of offset point.
    """
    # Perpendicular to bearing: bearing + pi/2 for right offset
    perp = bearing + math.pi / 2
    e = easting + offset * math.sin(perp)
    n = northing + offset * math.cos(perp)
    return (e, n)


def point_along_bearing(
    easting: float, northing: float, bearing: float, distance: float
) -> Tuple[float, float]:
    """Compute a point along a bearing at a given distance.

    Args:
        easting: Start easting.
        northing: Start northing.
        bearing: Direction (radians, CW from north).
        distance: Distance along bearing.
    """
    e = easting + distance * math.sin(bearing)
    n = northing + distance * math.cos(bearing)
    return (e, n)


def interpolate_linear(x: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Linear interpolation between two points."""
    if abs(x2 - x1) < 1e-12:
        return (y1 + y2) / 2.0
    t = (x - x1) / (x2 - x1)
    return y1 + t * (y2 - y1)


def parabolic_curve_elevation(
    station: float,
    pvi_station: float,
    pvi_elevation: float,
    grade_in: float,
    grade_out: float,
    curve_length: float,
) -> float:
    """Compute elevation on a symmetric parabolic vertical curve.

    Args:
        station: Station to evaluate.
        pvi_station: Station of the PVI.
        pvi_elevation: Elevation at PVI.
        grade_in: Incoming grade (rise/run as decimal, e.g., 0.02 for 2%).
        grade_out: Outgoing grade.
        curve_length: Length of vertical curve.

    Returns:
        Elevation at the given station.
    """
    bvc_station = pvi_station - curve_length / 2.0
    bvc_elevation = pvi_elevation - grade_in * (curve_length / 2.0)

    x = station - bvc_station
    r = (grade_out - grade_in) / curve_length
    return bvc_elevation + grade_in * x + (r / 2.0) * x * x


def distance_2d(x1: float, y1: float, x2: float, y2: float) -> float:
    """2D Euclidean distance."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range [min_val, max_val]."""
    return max(min_val, min(max_val, value))
