"""Build IfcPlate entities for caps/copings."""
from __future__ import annotations

import ifcopenshell.guid

from gdot_soundwall.ifc.project_setup import IfcProjectContext
from gdot_soundwall.ifc.geometry_builder import (
    create_placement, create_rectangle_profile, create_extruded_solid,
    create_shape_representation, create_product_shape,
)
from gdot_soundwall.ifc.material_builder import MaterialLibrary, assign_material
from gdot_soundwall.model.cap import Cap
from gdot_soundwall.model.materials import REINFORCED_CONCRETE


def build_cap(
    ctx: IfcProjectContext,
    cap: Cap,
    mat_lib: MaterialLibrary,
) -> object:
    """Create an IfcPlate for a wall cap/coping."""
    f = ctx.file
    guid = ifcopenshell.guid.new

    # Placement at cap bottom center
    placement = create_placement(
        ctx,
        cap.easting,
        cap.northing,
        cap.bottom_elevation,
        bearing=cap.bearing,
    )

    # Create geometry - rectangle (width x depth) extruded to height
    profile = create_rectangle_profile(
        ctx, "Cap_Profile",
        x_dim=cap.width,
        y_dim=cap.depth,
    )
    solid = create_extruded_solid(ctx, profile, depth=cap.height)
    body_rep = create_shape_representation(ctx, [solid])
    shape = create_product_shape(ctx, [body_rep])

    plate = f.create_entity("IfcPlate",
                            GlobalId=guid(),
                            OwnerHistory=ctx.owner_history,
                            Name=f"Cap_B{cap.bay_index}",
                            ObjectPlacement=placement,
                            Representation=shape,
                            PredefinedType="USERDEFINED",
                            ObjectType="WALL_CAP")

    # Assign material
    rc_mat = mat_lib.materials.get(REINFORCED_CONCRETE.name)
    if rc_mat:
        assign_material(ctx, plate, rc_mat)

    return plate
