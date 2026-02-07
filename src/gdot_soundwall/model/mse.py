"""MSE wall segment with traffic barrier and coping."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from gdot_soundwall import config


@dataclass
class MSESegment:
    """An MSE (Mechanically Stabilized Earth) wall segment."""
    index: int
    station_start: float
    station_end: float
    easting_start: float
    northing_start: float
    easting_end: float
    northing_end: float
    base_elevation: float
    top_elevation: float
    bearing: float

    # MSE body
    wall_height: float = 3.048        # Height of MSE body
    top_width: float = 0.610          # Top width of MSE trapezoidal section
    base_width: float = 4.572         # Base width (top + reinforcement length)
    batter: float = 0.0              # Face batter (radians)

    # Facing panels
    facing_thickness: float = config.MSE_PANEL_THICKNESS
    facing_panel_height: float = config.MSE_PANEL_HEIGHT
    facing_panel_width: float = config.MSE_PANEL_WIDTH

    # Traffic barrier on top
    barrier_height: float = config.TRAFFIC_BARRIER_H_HEIGHT
    barrier_base_width: float = config.TRAFFIC_BARRIER_H_BASE_WIDTH
    barrier_top_width: float = config.TRAFFIC_BARRIER_H_TOP_WIDTH

    # Coping on top of barrier
    coping_height: float = config.COPING_B_HEIGHT
    coping_width: float = config.COPING_B_WIDTH

    @property
    def length(self) -> float:
        return self.station_end - self.station_start

    @property
    def total_height(self) -> float:
        return self.top_elevation - self.base_elevation

    @property
    def num_facing_rows(self) -> int:
        import math
        return max(1, math.ceil(self.wall_height / self.facing_panel_height))


@dataclass
class MSEWallLayout:
    """Complete MSE wall layout with noise barrier on top."""
    segments: List[MSESegment] = field(default_factory=list)
    noise_barrier_height: float = config.DEFAULT_WALL_HEIGHT
