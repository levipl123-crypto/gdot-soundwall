"""IFC type definitions for geometry reuse via IfcMappedItem.

Creates shared IfcColumnType, IfcWallType, IfcFootingType entities
so that identical components share a single geometry definition.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import ifcopenshell.guid

from gdot_soundwall import config
from gdot_soundwall.ifc.project_setup import IfcProjectContext
from gdot_soundwall.ifc.geometry_builder import (
    create_i_shape_profile, create_rectangle_profile,
    create_circle_profile, create_extruded_solid,
    create_shape_representation,
)


@dataclass
class TypeLibrary:
    """Cache of shared IFC type entities."""
    post_type: Optional[object] = None
    panel_type: Optional[object] = None
    panel_drainage_type: Optional[object] = None
    caisson_type: Optional[object] = None
    spread_footing_type: Optional[object] = None
    cap_type: Optional[object] = None
    # Maps for custom sizes
    types: Dict[str, object] = field(default_factory=dict)
    rep_maps: Dict[str, object] = field(default_factory=dict)


def build_type_library(ctx: IfcProjectContext) -> TypeLibrary:
    """Create all shared type definitions.

    Each type includes an IfcRepresentationMap so instances can use IfcMappedItem
    for geometry reuse.
    """
    lib = TypeLibrary()
    f = ctx.file
    guid = ifcopenshell.guid.new

    # ── Post Type: W6x20 ──────────────────────────────────────────
    post_profile = create_i_shape_profile(
        ctx, config.POST_SECTION,
        width=config.POST_FLANGE_WIDTH,
        depth=config.POST_DEPTH,
        web_thickness=config.POST_WEB_THICKNESS,
        flange_thickness=config.POST_FLANGE_THICKNESS,
        fillet_radius=config.POST_FILLET_RADIUS,
    )
    # Extrude to unit height (1m) - instances will scale
    post_solid = create_extruded_solid(ctx, post_profile, depth=1.0)
    post_rep = create_shape_representation(ctx, [post_solid])

    # Create rep map (origin at bottom center)
    origin = f.create_entity("IfcCartesianPoint", Coordinates=[0.0, 0.0, 0.0])
    dir_z = f.create_entity("IfcDirection", DirectionRatios=[0.0, 0.0, 1.0])
    dir_x = f.create_entity("IfcDirection", DirectionRatios=[1.0, 0.0, 0.0])
    map_origin = f.create_entity("IfcAxis2Placement3D",
                                 Location=origin, Axis=dir_z, RefDirection=dir_x)
    post_rep_map = f.create_entity("IfcRepresentationMap",
                                   MappingOrigin=map_origin,
                                   MappedRepresentation=post_rep)

    lib.post_type = f.create_entity("IfcColumnType",
                                    GlobalId=guid(),
                                    OwnerHistory=ctx.owner_history,
                                    Name=f"GDOT_Post_{config.POST_SECTION}",
                                    PredefinedType="USERDEFINED",
                                    ElementType="SOUNDWALL_POST",
                                    RepresentationMaps=[post_rep_map])
    lib.rep_maps["post"] = post_rep_map
    lib.types["post"] = lib.post_type

    # ── Panel Type: Standard ──────────────────────────────────────
    panel_profile = create_rectangle_profile(
        ctx, "GDOT_Panel_Profile",
        x_dim=config.PANEL_WIDTH_MAX,
        y_dim=config.PANEL_THICKNESS,
    )
    panel_solid = create_extruded_solid(ctx, panel_profile,
                                        depth=config.PANEL_HEIGHT)
    panel_rep = create_shape_representation(ctx, [panel_solid])
    panel_rep_map = _make_rep_map(f, panel_rep)

    lib.panel_type = f.create_entity("IfcWallType",
                                     GlobalId=guid(),
                                     OwnerHistory=ctx.owner_history,
                                     Name="GDOT_Panel_32x144x4",
                                     PredefinedType="PARAPET",
                                     RepresentationMaps=[panel_rep_map])
    lib.rep_maps["panel"] = panel_rep_map
    lib.types["panel"] = lib.panel_type

    # ── Panel Type: With Drainage Slot ────────────────────────────
    # Same as standard but flagged differently (geometry simplified)
    lib.panel_drainage_type = f.create_entity(
        "IfcWallType",
        GlobalId=guid(),
        OwnerHistory=ctx.owner_history,
        Name="GDOT_Panel_32x144x4_Drainage",
        PredefinedType="PARAPET",
        RepresentationMaps=[panel_rep_map])
    lib.types["panel_drainage"] = lib.panel_drainage_type

    # ── Caisson Footing Type ──────────────────────────────────────
    caisson_profile = create_circle_profile(
        ctx, "GDOT_Caisson_Profile",
        radius=config.CAISSON_DIAMETER / 2.0,
    )
    caisson_solid = create_extruded_solid(ctx, caisson_profile,
                                          depth=config.CAISSON_DEPTH)
    caisson_rep = create_shape_representation(ctx, [caisson_solid])
    caisson_rep_map = _make_rep_map(f, caisson_rep)

    lib.caisson_type = f.create_entity("IfcFootingType",
                                       GlobalId=guid(),
                                       OwnerHistory=ctx.owner_history,
                                       Name="GDOT_Caisson_30in",
                                       PredefinedType="CAISSON_FOUNDATION",
                                       RepresentationMaps=[caisson_rep_map])
    lib.rep_maps["caisson"] = caisson_rep_map
    lib.types["caisson"] = lib.caisson_type

    # ── Spread Footing Type ───────────────────────────────────────
    spread_profile = create_rectangle_profile(
        ctx, "GDOT_SpreadFooting_Profile",
        x_dim=config.SPREAD_LENGTH,
        y_dim=config.SPREAD_WIDTH,
    )
    spread_solid = create_extruded_solid(ctx, spread_profile,
                                         depth=config.SPREAD_DEPTH)
    spread_rep = create_shape_representation(ctx, [spread_solid])
    spread_rep_map = _make_rep_map(f, spread_rep)

    lib.spread_footing_type = f.create_entity(
        "IfcFootingType",
        GlobalId=guid(),
        OwnerHistory=ctx.owner_history,
        Name="GDOT_SpreadFooting_5x5",
        PredefinedType="PAD_FOOTING",
        RepresentationMaps=[spread_rep_map])
    lib.rep_maps["spread"] = spread_rep_map
    lib.types["spread"] = lib.spread_footing_type

    return lib


def _make_rep_map(f, representation) -> object:
    """Create an IfcRepresentationMap at the origin."""
    origin = f.create_entity("IfcCartesianPoint", Coordinates=[0.0, 0.0, 0.0])
    dir_z = f.create_entity("IfcDirection", DirectionRatios=[0.0, 0.0, 1.0])
    dir_x = f.create_entity("IfcDirection", DirectionRatios=[1.0, 0.0, 0.0])
    map_origin = f.create_entity("IfcAxis2Placement3D",
                                 Location=origin, Axis=dir_z, RefDirection=dir_x)
    return f.create_entity("IfcRepresentationMap",
                           MappingOrigin=map_origin,
                           MappedRepresentation=representation)
