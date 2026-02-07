"""Build IfcReinforcedSoil + composite assembly for MSE walls.

MSE (Mechanically Stabilized Earth) wall segments with:
- IfcReinforcedSoil for the MSE body
- IfcWall [RETAININGWALL] for facing panels
- IfcPlate for traffic barrier and coping
- IfcFooting [STRIP_FOOTING] for leveling pad
"""
from __future__ import annotations

from typing import List

import ifcopenshell.guid

from gdot_soundwall import config
from gdot_soundwall.ifc.project_setup import IfcProjectContext
from gdot_soundwall.ifc.geometry_builder import (
    create_placement, create_rectangle_profile, create_extruded_solid,
    create_shape_representation, create_product_shape,
    create_nj_barrier_profile,
)
from gdot_soundwall.ifc.material_builder import MaterialLibrary, assign_material
from gdot_soundwall.ifc.pset_builder import attach_mse_pset
from gdot_soundwall.ifc.spatial_structure import contain_in_facility
from gdot_soundwall.model.mse import MSESegment
from gdot_soundwall.model.materials import (
    MSE_SELECT_FILL, REINFORCED_CONCRETE, PRECAST_PAAC,
)


def build_mse_segment(
    ctx: IfcProjectContext,
    segment: MSESegment,
    mat_lib: MaterialLibrary,
) -> object:
    """Build an IfcElementAssembly for one MSE wall segment.

    Returns the assembly entity.
    """
    f = ctx.file
    guid = ifcopenshell.guid.new
    children = []

    # ── MSE Body (IfcReinforcedSoil) ─────────────────────────────
    mse_placement = create_placement(
        ctx,
        segment.easting_start,
        segment.northing_start,
        segment.base_elevation,
        bearing=segment.bearing,
    )

    # Trapezoidal cross-section for MSE body
    hw_base = segment.base_width / 2.0
    hw_top = segment.top_width / 2.0
    points = [
        f.create_entity("IfcCartesianPoint", Coordinates=[-hw_base, 0.0]),
        f.create_entity("IfcCartesianPoint", Coordinates=[hw_base, 0.0]),
        f.create_entity("IfcCartesianPoint", Coordinates=[hw_top, segment.wall_height]),
        f.create_entity("IfcCartesianPoint", Coordinates=[-hw_top, segment.wall_height]),
        f.create_entity("IfcCartesianPoint", Coordinates=[-hw_base, 0.0]),
    ]
    polyline = f.create_entity("IfcPolyline", Points=points)
    mse_profile = f.create_entity("IfcArbitraryClosedProfileDef",
                                  ProfileType="AREA",
                                  ProfileName="MSE_CrossSection",
                                  OuterCurve=polyline)

    mse_solid = create_extruded_solid(
        ctx, mse_profile, depth=segment.length,
        direction=(1.0, 0.0, 0.0),  # Extrude along local X (alignment direction)
    )
    mse_rep = create_shape_representation(ctx, [mse_solid])
    mse_shape = create_product_shape(ctx, [mse_rep])

    mse_body = f.create_entity("IfcReinforcedSoil",
                               GlobalId=guid(),
                               OwnerHistory=ctx.owner_history,
                               Name=f"MSE_Body_{segment.index}",
                               ObjectPlacement=mse_placement,
                               Representation=mse_shape,
                               PredefinedType="USERDEFINED",
                               ObjectType="MSE_WALL")

    mse_fill_mat = mat_lib.materials.get(MSE_SELECT_FILL.name)
    if mse_fill_mat:
        assign_material(ctx, mse_body, mse_fill_mat)
    attach_mse_pset(ctx, mse_body, segment)
    children.append(mse_body)

    # ── Facing Panels (IfcWall RETAININGWALL) ─────────────────────
    num_rows = segment.num_facing_rows
    for row in range(num_rows):
        facing_z = segment.base_elevation + row * segment.facing_panel_height
        facing_placement = create_placement(
            ctx,
            segment.easting_start,
            segment.northing_start,
            facing_z,
            bearing=segment.bearing,
        )

        facing_profile = create_rectangle_profile(
            ctx, "MSE_Facing_Profile",
            x_dim=segment.length,
            y_dim=segment.facing_thickness,
        )
        facing_solid = create_extruded_solid(ctx, facing_profile,
                                             depth=segment.facing_panel_height)
        facing_rep = create_shape_representation(ctx, [facing_solid])
        facing_shape = create_product_shape(ctx, [facing_rep])

        facing = f.create_entity("IfcWall",
                                 GlobalId=guid(),
                                 OwnerHistory=ctx.owner_history,
                                 Name=f"MSE_Facing_{segment.index}_R{row}",
                                 ObjectPlacement=facing_placement,
                                 Representation=facing_shape,
                                 PredefinedType="RETAININGWALL")

        rc_mat = mat_lib.materials.get(REINFORCED_CONCRETE.name)
        if rc_mat:
            assign_material(ctx, facing, rc_mat)
        children.append(facing)

    # ── Traffic Barrier H ─────────────────────────────────────────
    barrier_z = segment.base_elevation + segment.wall_height
    barrier_placement = create_placement(
        ctx,
        segment.easting_start,
        segment.northing_start,
        barrier_z,
        bearing=segment.bearing,
    )

    barrier_profile = create_nj_barrier_profile(
        ctx, "TrafficBarrierH_Profile",
        height=segment.barrier_height,
        base_width=segment.barrier_base_width,
        top_width=segment.barrier_top_width,
    )
    barrier_solid = create_extruded_solid(ctx, barrier_profile,
                                          depth=segment.length,
                                          direction=(1.0, 0.0, 0.0))
    barrier_rep = create_shape_representation(ctx, [barrier_solid])
    barrier_shape = create_product_shape(ctx, [barrier_rep])

    barrier = f.create_entity("IfcPlate",
                              GlobalId=guid(),
                              OwnerHistory=ctx.owner_history,
                              Name=f"TrafficBarrierH_{segment.index}",
                              ObjectPlacement=barrier_placement,
                              Representation=barrier_shape,
                              PredefinedType="USERDEFINED",
                              ObjectType="TRAFFIC_BARRIER_H")

    rc_mat = mat_lib.materials.get(REINFORCED_CONCRETE.name)
    if rc_mat:
        assign_material(ctx, barrier, rc_mat)
    children.append(barrier)

    # ── Cast-in-place Coping B ────────────────────────────────────
    coping_z = barrier_z + segment.barrier_height
    coping_placement = create_placement(
        ctx,
        segment.easting_start,
        segment.northing_start,
        coping_z,
        bearing=segment.bearing,
    )

    coping_profile = create_rectangle_profile(
        ctx, "CopingB_Profile",
        x_dim=segment.length,
        y_dim=segment.coping_width,
    )
    coping_solid = create_extruded_solid(ctx, coping_profile,
                                         depth=segment.coping_height)
    coping_rep = create_shape_representation(ctx, [coping_solid])
    coping_shape = create_product_shape(ctx, [coping_rep])

    coping = f.create_entity("IfcPlate",
                             GlobalId=guid(),
                             OwnerHistory=ctx.owner_history,
                             Name=f"CopingB_{segment.index}",
                             ObjectPlacement=coping_placement,
                             Representation=coping_shape,
                             PredefinedType="USERDEFINED",
                             ObjectType="CAST_IN_PLACE_COPING_B")

    if rc_mat:
        assign_material(ctx, coping, rc_mat)
    children.append(coping)

    # ── Leveling Pad (IfcFooting STRIP_FOOTING) ──────────────────
    pad_placement = create_placement(
        ctx,
        segment.easting_start,
        segment.northing_start,
        segment.base_elevation - 0.152,  # 6 in pad below MSE base
        bearing=segment.bearing,
    )

    pad_profile = create_rectangle_profile(
        ctx, "LevelingPad_Profile",
        x_dim=segment.length,
        y_dim=segment.base_width,
    )
    pad_solid = create_extruded_solid(ctx, pad_profile, depth=0.152)
    pad_rep = create_shape_representation(ctx, [pad_solid])
    pad_shape = create_product_shape(ctx, [pad_rep])

    pad = f.create_entity("IfcFooting",
                          GlobalId=guid(),
                          OwnerHistory=ctx.owner_history,
                          Name=f"LevelingPad_{segment.index}",
                          ObjectPlacement=pad_placement,
                          Representation=pad_shape,
                          PredefinedType="STRIP_FOOTING")

    if rc_mat:
        assign_material(ctx, pad, rc_mat)
    children.append(pad)

    # ── Assembly ──────────────────────────────────────────────────
    assembly_placement = create_placement(
        ctx,
        segment.easting_start,
        segment.northing_start,
        segment.base_elevation,
        bearing=segment.bearing,
    )

    assembly = f.create_entity("IfcElementAssembly",
                               GlobalId=guid(),
                               OwnerHistory=ctx.owner_history,
                               Name=f"MSE_Segment_{segment.index}",
                               ObjectPlacement=assembly_placement,
                               PredefinedType="USERDEFINED",
                               ObjectType="SOUNDWALL_MSE_COMPOSITE")

    f.create_entity("IfcRelAggregates",
                    GlobalId=guid(),
                    OwnerHistory=ctx.owner_history,
                    RelatingObject=assembly,
                    RelatedObjects=children)

    return assembly


def build_all_mse_segments(
    ctx: IfcProjectContext,
    segments: list,
    mat_lib: MaterialLibrary,
) -> List[object]:
    """Build all MSE wall segments."""
    assemblies = []
    for segment in segments:
        assembly = build_mse_segment(ctx, segment, mat_lib)
        assemblies.append(assembly)

    if assemblies:
        contain_in_facility(ctx, assemblies)

    return assemblies
