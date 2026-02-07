"""Sample ground elevation from TIN surface at alignment stations."""
from __future__ import annotations

from typing import Optional

from gdot_soundwall.landxml.surface import TerrainSurface
from gdot_soundwall.geometry.station_solver import StationSolver, StationPoint


class TerrainSampler:
    """Samples ground elevation from a TIN surface.

    Falls back to the vertical profile elevation if the point is outside
    the TIN coverage area.
    """

    def __init__(self, surface: Optional[TerrainSurface] = None):
        self.surface = surface

    def sample(self, easting: float, northing: float) -> Optional[float]:
        """Query terrain elevation at a point."""
        if self.surface is None:
            return None
        return self.surface.elevation_at(easting, northing)

    def sample_at_station(
        self, solver: StationSolver, station: float, offset: float = 0.0,
    ) -> float:
        """Get ground elevation at a station, using TIN if available.

        Falls back to profile elevation if TIN doesn't cover the point.
        """
        point = solver.solve(station, offset)

        if self.surface is not None:
            elev = self.surface.elevation_at(point.easting, point.northing)
            if elev is not None:
                return elev

        # Fall back to profile elevation
        return point.elevation
