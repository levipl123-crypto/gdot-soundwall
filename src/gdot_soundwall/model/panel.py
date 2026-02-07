"""Precast panel dataclass."""
from __future__ import annotations

from dataclasses import dataclass

from gdot_soundwall import config


@dataclass
class PrecastPanel:
    """A single precast PAAC panel in the sound wall."""
    bay_index: int                 # Which bay (post-to-post span)
    stack_index: int               # Vertical position (0 = bottom)
    station_start: float           # Station of left post
    station_end: float             # Station of right post
    easting: float                 # Center of panel easting
    northing: float                # Center of panel northing
    bottom_elevation: float        # Bottom edge elevation
    bearing: float                 # Panel face normal bearing

    width: float = config.PANEL_WIDTH_MAX
    height: float = config.PANEL_HEIGHT
    thickness: float = config.PANEL_THICKNESS
    has_drainage_slot: bool = False

    @property
    def top_elevation(self) -> float:
        return self.bottom_elevation + self.height

    @property
    def center_elevation(self) -> float:
        return self.bottom_elevation + self.height / 2.0
