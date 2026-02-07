"""Material constant definitions for IFC material assignment."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MaterialDef:
    """Material definition for IFC export."""
    name: str
    category: str
    description: str = ""
    density_kg_m3: Optional[float] = None
    yield_strength_mpa: Optional[float] = None
    compressive_strength_mpa: Optional[float] = None
    friction_angle_deg: Optional[float] = None


STEEL_AASHTO_M270_GR36 = MaterialDef(
    name="Structural Steel - AASHTO M 270 GR 36",
    category="Steel",
    description="Hot-rolled structural steel, hot dip galvanized",
    density_kg_m3=7850.0,
    yield_strength_mpa=248.0,
)

PRECAST_PAAC = MaterialDef(
    name="Precast PAAC",
    category="Concrete",
    description="Plant-produced autoclaved aerated concrete",
    density_kg_m3=600.0,
    compressive_strength_mpa=4.0,
)

REINFORCED_CONCRETE = MaterialDef(
    name="Reinforced Concrete",
    category="Concrete",
    description="Cast-in-place reinforced concrete for footings/copings",
    density_kg_m3=2400.0,
    compressive_strength_mpa=28.0,
)

MSE_SELECT_FILL = MaterialDef(
    name="MSE Select Fill",
    category="Soil",
    description="Granular backfill for MSE wall",
    density_kg_m3=1920.0,
    friction_angle_deg=34.0,
)

JOINT_FILLER = MaterialDef(
    name="Preformed Joint Filler",
    category="Sealant",
    description="1-inch preformed expansion joint filler",
)
