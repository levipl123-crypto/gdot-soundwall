"""Expansion and contraction joint models."""
from __future__ import annotations

from dataclasses import dataclass

from gdot_soundwall.config import JointType, EXPANSION_JOINT_GAP


@dataclass
class Joint:
    """A joint in the sound wall."""
    joint_type: JointType
    station: float
    easting: float
    northing: float
    ground_elevation: float
    top_elevation: float
    bearing: float
    gap_width: float = EXPANSION_JOINT_GAP
    bay_index: int = 0            # Bay at which the joint occurs

    @property
    def height(self) -> float:
        return self.top_elevation - self.ground_elevation

    @property
    def filler_material(self) -> str:
        if self.joint_type == JointType.EXPANSION:
            return "Preformed Joint Filler"
        return "Sealant"
