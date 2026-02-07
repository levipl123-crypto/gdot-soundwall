"""Horizontal alignment data structures and computation."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional

from gdot_soundwall.utils.math_helpers import (
    normalize_angle, azimuth_from_points, point_along_bearing,
)


class SegmentType(Enum):
    LINE = "line"
    ARC = "arc"
    SPIRAL = "spiral"


@dataclass
class AlignmentSegment:
    """Base class for horizontal alignment segments."""
    segment_type: SegmentType
    start_station: float
    end_station: float
    start_easting: float
    start_northing: float
    end_easting: float
    end_northing: float

    @property
    def length(self) -> float:
        return self.end_station - self.start_station


@dataclass
class LineSegment(AlignmentSegment):
    """Tangent (straight) segment."""
    bearing: float = 0.0  # Azimuth in radians

    def __post_init__(self):
        self.segment_type = SegmentType.LINE
        if self.bearing == 0.0:
            self.bearing = azimuth_from_points(
                self.start_easting, self.start_northing,
                self.end_easting, self.end_northing,
            )

    def point_at_station(self, station: float) -> Tuple[float, float, float]:
        """Get (easting, northing, bearing) at a station along this segment."""
        dist = station - self.start_station
        e = self.start_easting + dist * math.sin(self.bearing)
        n = self.start_northing + dist * math.cos(self.bearing)
        return (e, n, self.bearing)


@dataclass
class ArcSegment(AlignmentSegment):
    """Circular arc segment."""
    radius: float = 0.0
    center_easting: float = 0.0
    center_northing: float = 0.0
    is_clockwise: bool = True      # Curve direction (right = CW)
    start_bearing: float = 0.0
    end_bearing: float = 0.0

    def __post_init__(self):
        self.segment_type = SegmentType.ARC

    @property
    def delta_angle(self) -> float:
        """Central angle of the arc."""
        if abs(self.radius) < 1e-10:
            return 0.0
        return self.length / self.radius

    def point_at_station(self, station: float) -> Tuple[float, float, float]:
        """Get (easting, northing, bearing) at a station along this arc."""
        dist = station - self.start_station
        angle_traveled = dist / self.radius

        # Start radial angle: from center to start point
        start_radial = math.atan2(
            self.start_easting - self.center_easting,
            self.start_northing - self.center_northing,
        )

        if self.is_clockwise:
            radial = start_radial + angle_traveled
            bearing = normalize_angle(radial + math.pi / 2)
        else:
            radial = start_radial - angle_traveled
            bearing = normalize_angle(radial - math.pi / 2)

        e = self.center_easting + self.radius * math.sin(radial)
        n = self.center_northing + self.radius * math.cos(radial)
        return (e, n, bearing)


@dataclass
class SpiralSegment(AlignmentSegment):
    """Euler spiral (clothoid) segment - simplified linear radius change."""
    start_radius: float = float('inf')
    end_radius: float = 0.0
    start_bearing: float = 0.0
    is_clockwise: bool = True

    def __post_init__(self):
        self.segment_type = SegmentType.SPIRAL

    def point_at_station(self, station: float) -> Tuple[float, float, float]:
        """Approximate spiral by linear interpolation of curvature."""
        dist = station - self.start_station
        t = dist / self.length if self.length > 0 else 0.0

        # Linear interpolation of curvature (1/radius)
        k_start = 0.0 if math.isinf(self.start_radius) else 1.0 / self.start_radius
        k_end = 0.0 if math.isinf(self.end_radius) else 1.0 / self.end_radius
        k = k_start + t * (k_end - k_start)

        # Approximate bearing change
        avg_k = (k_start + k) / 2.0
        delta_bearing = avg_k * dist
        if not self.is_clockwise:
            delta_bearing = -delta_bearing

        bearing = normalize_angle(self.start_bearing + delta_bearing)

        # Approximate position by integration (trapezoidal)
        n_steps = max(10, int(dist / 0.5))
        step = dist / n_steps
        e, n_coord = self.start_easting, self.start_northing
        b = self.start_bearing
        for i in range(n_steps):
            s = (i + 0.5) * step
            frac = s / self.length if self.length > 0 else 0.0
            ki = k_start + frac * (k_end - k_start)
            db = ki * step * (1 if self.is_clockwise else -1)
            b_mid = b + db / 2.0
            e += step * math.sin(b_mid)
            n_coord += step * math.cos(b_mid)
            b += db

        return (e, n_coord, bearing)


@dataclass
class HorizontalAlignment:
    """Complete horizontal alignment made of sequential segments."""
    name: str = ""
    segments: List[AlignmentSegment] = field(default_factory=list)

    @property
    def start_station(self) -> float:
        if not self.segments:
            return 0.0
        return self.segments[0].start_station

    @property
    def end_station(self) -> float:
        if not self.segments:
            return 0.0
        return self.segments[-1].end_station

    @property
    def total_length(self) -> float:
        return self.end_station - self.start_station

    def point_at_station(self, station: float) -> Tuple[float, float, float]:
        """Get (easting, northing, bearing) at any station.

        Finds the segment containing the station, then delegates.
        """
        for seg in self.segments:
            if seg.start_station <= station <= seg.end_station + 1e-6:
                return seg.point_at_station(min(station, seg.end_station))

        # Extrapolate beyond alignment
        if station < self.start_station and self.segments:
            return self.segments[0].point_at_station(self.segments[0].start_station)
        if station > self.end_station and self.segments:
            return self.segments[-1].point_at_station(self.segments[-1].end_station)

        raise ValueError(f"Station {station} outside alignment range "
                         f"[{self.start_station}, {self.end_station}]")
