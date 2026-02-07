"""Sound wall assembly configuration and layout result."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from gdot_soundwall.config import WallType, FoundationType
from gdot_soundwall.model.post import SteelPost
from gdot_soundwall.model.panel import PrecastPanel
from gdot_soundwall.model.footing import Footing
from gdot_soundwall.model.cap import Cap
from gdot_soundwall.model.joints import Joint
from gdot_soundwall.model.drainage import DrainageSlot
from gdot_soundwall.model.mse import MSESegment


@dataclass
class Bay:
    """A single bay (post-to-post span) of the sound wall."""
    index: int
    post_left: SteelPost
    post_right: SteelPost
    panels: List[PrecastPanel] = field(default_factory=list)
    cap: Optional[Cap] = None
    footing_left: Optional[Footing] = None
    footing_right: Optional[Footing] = None
    joints: List[Joint] = field(default_factory=list)
    drainage_slots: List[DrainageSlot] = field(default_factory=list)


@dataclass
class WallLayout:
    """Complete computed layout for a sound wall."""
    wall_type: WallType
    start_station: float
    end_station: float
    wall_height: float
    foundation_type: FoundationType

    posts: List[SteelPost] = field(default_factory=list)
    panels: List[PrecastPanel] = field(default_factory=list)
    footings: List[Footing] = field(default_factory=list)
    caps: List[Cap] = field(default_factory=list)
    joints: List[Joint] = field(default_factory=list)
    drainage_slots: List[DrainageSlot] = field(default_factory=list)
    bays: List[Bay] = field(default_factory=list)

    # MSE segments (only for MSE_COMPOSITE wall type)
    mse_segments: List[MSESegment] = field(default_factory=list)

    @property
    def num_bays(self) -> int:
        return len(self.bays)

    @property
    def total_length(self) -> float:
        return self.end_station - self.start_station
