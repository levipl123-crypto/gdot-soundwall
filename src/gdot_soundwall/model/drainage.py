"""Drainage slot model."""
from __future__ import annotations

from dataclasses import dataclass

from gdot_soundwall import config


@dataclass
class DrainageSlot:
    """A drainage slot cut in a panel."""
    panel_bay_index: int
    station: float
    easting: float
    northing: float
    elevation: float              # Center of slot elevation
    width: float = config.DRAINAGE_SLOT_WIDTH
    height: float = config.DRAINAGE_SLOT_HEIGHT
