"""Profile definitions and extruded solid geometry creation.

Provides helper functions to create IFC geometric representations
for all sound wall component types.
"""
from __future__ import annotations

import math
from typing import Tuple

import ifcopenshell
import ifcopenshell.guid

from gdot_soundwall.ifc.project_setup import IfcProjectContext


def create_placement(
    ctx: IfcProjectContext,
    x: float, y: float, z: float,
    bearing: float = 0.0,
    relative_to=None,
) -> object:
    """Create an IfcLocalPlacement at given coordinates with optional rotation.

    Args:
        ctx: IFC project context.
        x, y, z: Position coordinates (easting, northing, elevation).
        bearing: Rotation angle in radians (CW from north / Y-axis).
        relative_to: Parent placement, or None for world origin.
    """
    f = ctx.file
    location = f.create_entity("IfcCartesianPoint", Coordinates=[x, y, z])

    # Bearing rotates around Z axis. IFC X-axis is East, Y-axis is North.
    # bearing=0 means facing north. We orient the local X-axis along the bearing.
    cos_b = math.cos(bearing)
    sin_b = math.sin(bearing)
    # Local X along bearing direction, local Y perpendicular
    dir_x = f.create_entity("IfcDirection",
                            DirectionRatios=[sin_b, cos_b, 0.0])
    dir_z = f.create_entity("IfcDirection",
                            DirectionRatios=[0.0, 0.0, 1.0])

    axis = f.create_entity("IfcAxis2Placement3D",
                           Location=location, Axis=dir_z, RefDirection=dir_x)

    return f.create_entity("IfcLocalPlacement",
                           PlacementRelTo=relative_to,
                           RelativePlacement=axis)


def create_i_shape_profile(
    ctx: IfcProjectContext,
    profile_name: str,
    width: float,
    depth: float,
    web_thickness: float,
    flange_thickness: float,
    fillet_radius: float = 0.0,
) -> object:
    """Create an IfcIShapeProfileDef for steel H-posts."""
    f = ctx.file
    return f.create_entity("IfcIShapeProfileDef",
                           ProfileType="AREA",
                           ProfileName=profile_name,
                           OverallWidth=width,
                           OverallDepth=depth,
                           WebThickness=web_thickness,
                           FlangeThickness=flange_thickness,
                           FilletRadius=fillet_radius if fillet_radius > 0 else None)


def create_rectangle_profile(
    ctx: IfcProjectContext,
    profile_name: str,
    x_dim: float,
    y_dim: float,
) -> object:
    """Create an IfcRectangleProfileDef."""
    f = ctx.file
    return f.create_entity("IfcRectangleProfileDef",
                           ProfileType="AREA",
                           ProfileName=profile_name,
                           XDim=x_dim,
                           YDim=y_dim)


def create_circle_profile(
    ctx: IfcProjectContext,
    profile_name: str,
    radius: float,
) -> object:
    """Create an IfcCircleProfileDef for caisson foundations."""
    f = ctx.file
    return f.create_entity("IfcCircleProfileDef",
                           ProfileType="AREA",
                           ProfileName=profile_name,
                           Radius=radius)


def create_extruded_solid(
    ctx: IfcProjectContext,
    profile,
    depth: float,
    direction: Tuple[float, float, float] = (0.0, 0.0, 1.0),
    position=None,
) -> object:
    """Create an IfcExtrudedAreaSolid from a profile.

    Args:
        ctx: IFC project context.
        profile: An IfcProfileDef entity.
        depth: Extrusion depth (length).
        direction: Extrusion direction vector.
        position: Optional IfcAxis2Placement3D for the extrusion position.
    """
    f = ctx.file
    ext_dir = f.create_entity("IfcDirection",
                              DirectionRatios=list(direction))
    return f.create_entity("IfcExtrudedAreaSolid",
                           SweptArea=profile,
                           Position=position,
                           Depth=depth,
                           ExtrudedDirection=ext_dir)


def create_shape_representation(
    ctx: IfcProjectContext,
    items: list,
    rep_type: str = "SweptSolid",
    rep_id: str = "Body",
) -> object:
    """Create an IfcShapeRepresentation."""
    f = ctx.file
    sub_context = ctx.context_body if rep_id == "Body" else ctx.context_axis
    return f.create_entity("IfcShapeRepresentation",
                           ContextOfItems=sub_context,
                           RepresentationIdentifier=rep_id,
                           RepresentationType=rep_type,
                           Items=items)


def create_product_shape(
    ctx: IfcProjectContext,
    representations: list,
) -> object:
    """Create an IfcProductDefinitionShape."""
    f = ctx.file
    return f.create_entity("IfcProductDefinitionShape",
                           Representations=representations)


def create_mapped_item(
    ctx: IfcProjectContext,
    rep_map,
    target_placement=None,
) -> object:
    """Create an IfcMappedItem from a representation map.

    Used for type-based geometry reuse (100 identical posts share one geometry).
    """
    f = ctx.file
    if target_placement is None:
        origin = f.create_entity("IfcCartesianPoint",
                                 Coordinates=[0.0, 0.0, 0.0])
        dir1 = f.create_entity("IfcDirection",
                               DirectionRatios=[1.0, 0.0, 0.0])
        dir2 = f.create_entity("IfcDirection",
                               DirectionRatios=[0.0, 1.0, 0.0])
        target_placement = f.create_entity(
            "IfcCartesianTransformationOperator3D",
            Axis1=dir1, Axis2=dir2, LocalOrigin=origin)

    return f.create_entity("IfcMappedItem",
                           MappingSource=rep_map,
                           MappingTarget=target_placement)


def create_nj_barrier_profile(
    ctx: IfcProjectContext,
    profile_name: str,
    height: float,
    base_width: float,
    top_width: float,
) -> object:
    """Create an IfcArbitraryClosedProfileDef for NJ barrier (trapezoidal)."""
    f = ctx.file
    hw = base_width / 2.0
    tw = top_width / 2.0
    # Create polyline for trapezoidal cross-section
    points = [
        f.create_entity("IfcCartesianPoint", Coordinates=[-hw, 0.0]),
        f.create_entity("IfcCartesianPoint", Coordinates=[hw, 0.0]),
        f.create_entity("IfcCartesianPoint", Coordinates=[tw, height]),
        f.create_entity("IfcCartesianPoint", Coordinates=[-tw, height]),
        f.create_entity("IfcCartesianPoint", Coordinates=[-hw, 0.0]),
    ]
    polyline = f.create_entity("IfcPolyline", Points=points)
    return f.create_entity("IfcArbitraryClosedProfileDef",
                           ProfileType="AREA",
                           ProfileName=profile_name,
                           OuterCurve=polyline)
