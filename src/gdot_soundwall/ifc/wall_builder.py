"""Build IfcWall entities for precast panels."""
from __future__ import annotations

import ifcopenshell.guid

from gdot_soundwall.ifc.project_setup import IfcProjectContext
from gdot_soundwall.ifc.geometry_builder import (
    create_placement, create_rectangle_profile, create_extruded_solid,
    create_shape_representation, create_product_shape,
)
from gdot_soundwall.ifc.type_library import TypeLibrary
from gdot_soundwall.ifc.material_builder import MaterialLibrary, assign_material
from gdot_soundwall.model.panel import PrecastPanel
from gdot_soundwall.model.materials import PRECAST_PAAC


def build_panel(
    ctx: IfcProjectContext,
    panel: PrecastPanel,
    type_lib: TypeLibrary,
    mat_lib: MaterialLibrary,
) -> object:
    """Create an IfcWall for a precast panel.

    Each panel is an extruded rectangle (width x thickness) extruded
    to panel height.
    """
    f = ctx.file
    guid = ifcopenshell.guid.new

    # Placement at panel center-bottom
    placement = create_placement(
        ctx,
        panel.easting,
        panel.northing,
        panel.bottom_elevation,
        bearing=panel.bearing,
    )

    # Create geometry
    profile = create_rectangle_profile(
        ctx, "Panel_Profile",
        x_dim=panel.width,
        y_dim=panel.thickness,
    )
    solid = create_extruded_solid(ctx, profile, depth=panel.height)
    body_rep = create_shape_representation(ctx, [solid])
    shape = create_product_shape(ctx, [body_rep])

    # Create IfcWall
    wall = f.create_entity("IfcWall",
                           GlobalId=guid(),
                           OwnerHistory=ctx.owner_history,
                           Name=f"Panel_B{panel.bay_index}_S{panel.stack_index}",
                           ObjectPlacement=placement,
                           Representation=shape,
                           PredefinedType="PARAPET")

    # Assign type
    if panel.has_drainage_slot and type_lib.panel_drainage_type:
        rel_type = type_lib.panel_drainage_type
    elif type_lib.panel_type:
        rel_type = type_lib.panel_type
    else:
        rel_type = None

    if rel_type:
        f.create_entity("IfcRelDefinesByType",
                        GlobalId=guid(),
                        OwnerHistory=ctx.owner_history,
                        RelatedObjects=[wall],
                        RelatingType=rel_type)

    # Assign material
    paac_mat = mat_lib.materials.get(PRECAST_PAAC.name)
    if paac_mat:
        assign_material(ctx, wall, paac_mat)

    return wall
