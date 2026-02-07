"""GDOT Sound Wall dimensional constants and specifications.

References:
- GDOT Section 624 Sound Barriers
- GDOT Standard Detail N-5 Type C
- GDOT Standard 4949B
- AASHTO M 270 GR 36 steel specification

All internal dimensions are in SI (meters). Imperial equivalents noted in comments.
"""
from enum import Enum


class WallType(Enum):
    """Sound wall construction type."""
    PRECAST = "precast"        # Post-and-panel precast PAAC
    MSE_COMPOSITE = "mse"      # MSE wall with noise barrier on top


class FoundationType(Enum):
    """Foundation type for post support."""
    CAISSON = "caisson"              # Drilled shaft
    SPREAD_FOOTING = "spread"        # Pad footing
    CONTINUOUS_FOOTING = "continuous" # Strip footing


class JointType(Enum):
    """Joint type."""
    EXPANSION = "expansion"
    CONTRACTION = "contraction"


# ── Post Specifications ──────────────────────────────────────────────
POST_SPACING_MAX = 3.048        # 10 ft on center (max)
POST_SECTION = "W6x20"          # Steel H-shape designation
POST_STEEL_GRADE = "AASHTO M 270 GR 36"
POST_GALVANIZED = True          # Hot dip galvanized per GDOT spec

# W6x20 profile dimensions (metric)
POST_FLANGE_WIDTH = 0.1524      # 6.018 in -> 0.1529m, use nominal 6"
POST_DEPTH = 0.1572             # 6.20 in
POST_WEB_THICKNESS = 0.00655    # 0.258 in
POST_FLANGE_THICKNESS = 0.00935 # 0.368 in
POST_FILLET_RADIUS = 0.0064     # ~0.25 in fillet

# Post embedment
POST_EMBED_FROM_BOTTOM = 0.3048  # 1 ft from bottom of footing

# ── Panel Specifications ─────────────────────────────────────────────
PANEL_HEIGHT = 0.8128           # 32 in
PANEL_WIDTH_MAX = 3.6576        # 12 ft (144 in)
PANEL_THICKNESS = 0.1016        # 4 in
PANEL_MATERIAL = "Precast PAAC" # Plant-produced autoclaved aerated concrete

# ── Cap / Coping ─────────────────────────────────────────────────────
CAP_HEIGHT = 0.1524             # 6 in typical
CAP_OVERHANG = 0.0508           # 2 in overhang each side

# ── Joint Specifications ─────────────────────────────────────────────
EXPANSION_JOINT_SPACING = 24.384   # 80 ft max
EXPANSION_JOINT_GAP = 0.0254       # 1 in preformed joint filler
CONTRACTION_JOINT_SPACING = 6.096  # 20 ft max

# ── Footing Specifications ───────────────────────────────────────────
# Caisson (drilled shaft) defaults
CAISSON_DIAMETER = 0.762        # 30 in typical
CAISSON_DEPTH = 3.048           # 10 ft typical (varies by soil)

# Spread footing defaults
SPREAD_LENGTH = 1.524           # 5 ft
SPREAD_WIDTH = 1.524            # 5 ft
SPREAD_DEPTH = 0.762            # 2.5 ft

# Continuous footing defaults
CONTINUOUS_WIDTH = 0.914        # 3 ft
CONTINUOUS_DEPTH = 0.610        # 2 ft

# Reinforcement cover
REBAR_COVER_STEM = 0.0508       # 2 in in stem/barrier
REBAR_COVER_FOOTING = 0.0762    # 3 in in footing

# ── MSE Wall Specifications ──────────────────────────────────────────
MSE_PANEL_HEIGHT = 1.524        # 5 ft typical facing panel
MSE_PANEL_WIDTH = 3.048         # 10 ft typical facing panel
MSE_PANEL_THICKNESS = 0.1397    # 5.5 in facing
MSE_REINFORCEMENT_LENGTH = 4.572  # 15 ft typical strip length
MSE_COMPACTION_PERCENT = 95     # % of max density

# Traffic Barrier H (NJ Barrier profile)
TRAFFIC_BARRIER_H_HEIGHT = 0.813  # 32 in
TRAFFIC_BARRIER_H_BASE_WIDTH = 0.381  # 15 in
TRAFFIC_BARRIER_H_TOP_WIDTH = 0.152   # 6 in

# Cast-in-place Coping B
COPING_B_HEIGHT = 0.254         # 10 in
COPING_B_WIDTH = 0.610          # 24 in

# ── Drainage ─────────────────────────────────────────────────────────
DRAINAGE_SLOT_WIDTH = 0.1016    # 4 in
DRAINAGE_SLOT_HEIGHT = 0.0508   # 2 in
DRAINAGE_SLOT_SPACING = 6.096   # 20 ft typical

# ── Surface Treatment ────────────────────────────────────────────────
GRAFFITI_PROOF_COATING = True   # Per GDOT Section 838

# ── Default Wall Height ──────────────────────────────────────────────
DEFAULT_WALL_HEIGHT = 4.572     # 15 ft typical sound wall height
MIN_WALL_HEIGHT = 1.829         # 6 ft minimum
MAX_WALL_HEIGHT = 7.620         # 25 ft maximum

# ── Materials (for IFC material definitions) ─────────────────────────
MATERIAL_STEEL = {
    "name": "Structural Steel - AASHTO M 270 GR 36",
    "grade": "GR 36",
    "yield_strength_mpa": 248.0,
    "density_kg_m3": 7850.0,
}

MATERIAL_PAAC = {
    "name": "Precast PAAC",
    "description": "Plant-produced autoclaved aerated concrete",
    "density_kg_m3": 600.0,
    "compressive_strength_mpa": 4.0,
}

MATERIAL_CONCRETE_RC = {
    "name": "Reinforced Concrete",
    "description": "Cast-in-place reinforced concrete",
    "density_kg_m3": 2400.0,
    "compressive_strength_mpa": 28.0,
}

MATERIAL_MSE_FILL = {
    "name": "MSE Select Fill",
    "description": "Granular backfill for MSE wall",
    "density_kg_m3": 1920.0,
    "friction_angle_deg": 34.0,
}

MATERIAL_JOINT_FILLER = {
    "name": "Preformed Joint Filler",
    "description": "1-inch preformed expansion joint filler",
}
