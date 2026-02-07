"""Cap/coping dataclass."""
from __future__ import annotations

from dataclasses import dataclass

from gdot_soundwall import config


@dataclass
class Cap:
    """Cap or coping element spanning a bay."""
    bay_index: int
    station_start: float
    station_end: float
    easting: float
    northing: float
    bottom_elevation: float
    bearing: float
    width: float                    # Along wall direction (bay span)
    depth: float = config.PANEL_THICKNESS + 2 * config.CAP_OVERHANG
    height: float = config.CAP_HEIGHT

    @property
    def top_elevation(self) -> float:
        return self.bottom_elevation + self.height
