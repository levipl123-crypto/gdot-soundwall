"""IFC material definitions for sound wall components."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import ifcopenshell.guid

from gdot_soundwall.ifc.project_setup import IfcProjectContext
from gdot_soundwall.model.materials import (
    MaterialDef, STEEL_AASHTO_M270_GR36, PRECAST_PAAC,
    REINFORCED_CONCRETE, MSE_SELECT_FILL, JOINT_FILLER,
)


@dataclass
class MaterialLibrary:
    """Cache of created IfcMaterial entities keyed by name."""
    materials: Dict[str, object] = field(default_factory=dict)


def build_materials(ctx: IfcProjectContext) -> MaterialLibrary:
    """Create all IfcMaterial entities for the project.

    Returns a MaterialLibrary for lookup by name.
    """
    lib = MaterialLibrary()
    f = ctx.file
    guid = ifcopenshell.guid.new

    for mat_def in [STEEL_AASHTO_M270_GR36, PRECAST_PAAC,
                    REINFORCED_CONCRETE, MSE_SELECT_FILL, JOINT_FILLER]:
        ifc_mat = f.create_entity("IfcMaterial",
                                  Name=mat_def.name,
                                  Category=mat_def.category,
                                  Description=mat_def.description or None)

        # Add mechanical properties where available
        props = []
        if mat_def.density_kg_m3 is not None:
            props.append(f.create_entity(
                "IfcPropertySingleValue",
                Name="MassDensity",
                NominalValue=f.create_entity("IfcMassDensityMeasure",
                                             mat_def.density_kg_m3)))
        if mat_def.yield_strength_mpa is not None:
            props.append(f.create_entity(
                "IfcPropertySingleValue",
                Name="YieldStress",
                NominalValue=f.create_entity("IfcPressureMeasure",
                                             mat_def.yield_strength_mpa)))
        if mat_def.compressive_strength_mpa is not None:
            props.append(f.create_entity(
                "IfcPropertySingleValue",
                Name="CompressiveStrength",
                NominalValue=f.create_entity("IfcPressureMeasure",
                                             mat_def.compressive_strength_mpa)))

        if props:
            pset = f.create_entity("IfcMaterialProperties",
                                   Name="Pset_MaterialMechanical",
                                   Material=ifc_mat,
                                   Properties=props)

        lib.materials[mat_def.name] = ifc_mat

    return lib


def assign_material(
    ctx: IfcProjectContext,
    product,
    material,
) -> None:
    """Associate an IfcMaterial with an IfcProduct via IfcRelAssociatesMaterial."""
    f = ctx.file
    f.create_entity("IfcRelAssociatesMaterial",
                    GlobalId=ifcopenshell.guid.new(),
                    OwnerHistory=ctx.owner_history,
                    RelatedObjects=[product],
                    RelatingMaterial=material)
