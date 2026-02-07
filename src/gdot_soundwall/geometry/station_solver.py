"""Station solver: resolve station to 3D coordinates and bearing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from gdot_soundwall.landxml.alignment import HorizontalAlignment
from gdot_soundwall.landxml.profile import VerticalProfile
from gdot_soundwall.utils.math_helpers import offset_point


@dataclass
class StationPoint:
    """Resolved 3D point at a station along the alignment."""
    station: float
    easting: float
    northing: float
    elevation: float
    bearing: float                # Alignment bearing (radians, CW from north)


class StationSolver:
    """Resolves stations on a horizontal alignment + vertical profile to 3D coords."""

    def __init__(
        self,
        alignment: HorizontalAlignment,
        profile: Optional[VerticalProfile] = None,
    ):
        self.alignment = alignment
        self.profile = profile

    def solve(self, station: float, offset: float = 0.0) -> StationPoint:
        """Compute 3D coordinates at a station.

        Args:
            station: Station value in meters along alignment.
            offset: Perpendicular offset from centerline (positive = right).

        Returns:
            StationPoint with easting, northing, elevation, bearing.
        """
        # Horizontal position
        easting, northing, bearing = self.alignment.point_at_station(station)

        # Apply offset if specified
        if abs(offset) > 1e-6:
            easting, northing = offset_point(easting, northing, bearing, offset)

        # Vertical position
        if self.profile and self.profile.pvis:
            elevation = self.profile.elevation_at_station(station)
        else:
            elevation = 0.0

        return StationPoint(
            station=station,
            easting=easting,
            northing=northing,
            elevation=elevation,
            bearing=bearing,
        )

    def solve_range(
        self, start_station: float, end_station: float, interval: float,
        offset: float = 0.0,
    ) -> list[StationPoint]:
        """Solve multiple stations at regular intervals."""
        points = []
        sta = start_station
        while sta <= end_station + 1e-6:
            points.append(self.solve(min(sta, end_station), offset))
            sta += interval
        return points
