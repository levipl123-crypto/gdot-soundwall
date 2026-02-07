"""IfcProject, IfcSite, IfcFacility, geometric contexts, and units setup."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import ifcopenshell
import ifcopenshell.guid


@dataclass
class IfcProjectContext:
    """Container for the IFC project hierarchy and shared resources."""
    file: ifcopenshell.file
    project: object  # IfcProject
    site: object     # IfcSite
    facility: object  # IfcFacility
    context_3d: object  # IfcGeometricRepresentationContext (Model)
    context_body: object  # IfcGeometricRepresentationSubContext (Body)
    context_axis: object  # IfcGeometricRepresentationSubContext (Axis)
    owner_history: object  # IfcOwnerHistory
    origin: object   # IfcAxis2Placement3D at world origin


def create_project(
    project_name: str = "GDOT Sound Wall",
    site_name: str = "Sound Wall Site",
    facility_name: str = "Noise Barrier",
    project_number: str = "",
    route: str = "",
) -> IfcProjectContext:
    """Create the IFC4.3 project structure with all required contexts.

    Returns an IfcProjectContext with references to all shared resources.
    """
    f = ifcopenshell.file(schema="IFC4X3_ADD2")
    guid = ifcopenshell.guid.new

    # ── Owner / Application ────────────────────────────────────────
    person = f.create_entity("IfcPerson", FamilyName="GDOT", GivenName="Engineer")
    org = f.create_entity("IfcOrganization", Name="Georgia DOT")
    person_org = f.create_entity("IfcPersonAndOrganization",
                                 ThePerson=person, TheOrganization=org)
    app = f.create_entity("IfcApplication",
                          ApplicationDeveloper=org,
                          Version="0.1.0",
                          ApplicationFullName="GDOT Sound Wall Modeler",
                          ApplicationIdentifier="GDOT_SW")
    owner = f.create_entity("IfcOwnerHistory",
                            OwningUser=person_org,
                            OwningApplication=app,
                            ChangeAction="ADDED",
                            CreationDate=0)

    # ── Units ──────────────────────────────────────────────────────
    length_unit = f.create_entity("IfcSIUnit",
                                  UnitType="LENGTHUNIT", Name="METRE")
    area_unit = f.create_entity("IfcSIUnit",
                                UnitType="AREAUNIT", Name="SQUARE_METRE")
    volume_unit = f.create_entity("IfcSIUnit",
                                  UnitType="VOLUMEUNIT", Name="CUBIC_METRE")
    angle_unit = f.create_entity("IfcSIUnit",
                                 UnitType="PLANEANGLEUNIT", Name="RADIAN")
    unit_assignment = f.create_entity("IfcUnitAssignment",
                                      Units=[length_unit, area_unit,
                                             volume_unit, angle_unit])

    # ── Geometric Contexts ─────────────────────────────────────────
    origin_pt = f.create_entity("IfcCartesianPoint",
                                Coordinates=[0.0, 0.0, 0.0])
    dir_z = f.create_entity("IfcDirection", DirectionRatios=[0.0, 0.0, 1.0])
    dir_x = f.create_entity("IfcDirection", DirectionRatios=[1.0, 0.0, 0.0])
    world_origin = f.create_entity("IfcAxis2Placement3D",
                                   Location=origin_pt, Axis=dir_z,
                                   RefDirection=dir_x)

    context_3d = f.create_entity("IfcGeometricRepresentationContext",
                                 ContextType="Model",
                                 CoordinateSpaceDimension=3,
                                 Precision=1e-5,
                                 WorldCoordinateSystem=world_origin)

    context_body = f.create_entity("IfcGeometricRepresentationSubContext",
                                   ContextIdentifier="Body",
                                   ContextType="Model",
                                   ParentContext=context_3d,
                                   TargetView="MODEL_VIEW")

    context_axis = f.create_entity("IfcGeometricRepresentationSubContext",
                                   ContextIdentifier="Axis",
                                   ContextType="Model",
                                   ParentContext=context_3d,
                                   TargetView="GRAPH_VIEW")

    # ── Project ────────────────────────────────────────────────────
    project = f.create_entity("IfcProject",
                              GlobalId=guid(),
                              OwnerHistory=owner,
                              Name=project_name,
                              UnitsInContext=unit_assignment,
                              RepresentationContexts=[context_3d])

    # ── Site ───────────────────────────────────────────────────────
    site_placement = f.create_entity("IfcLocalPlacement",
                                     RelativePlacement=world_origin)
    site = f.create_entity("IfcSite",
                           GlobalId=guid(),
                           OwnerHistory=owner,
                           Name=site_name,
                           ObjectPlacement=site_placement,
                           CompositionType="ELEMENT")

    # Project -> Site
    f.create_entity("IfcRelAggregates",
                    GlobalId=guid(),
                    OwnerHistory=owner,
                    RelatingObject=project,
                    RelatedObjects=[site])

    # ── Facility ───────────────────────────────────────────────────
    facility_placement = f.create_entity("IfcLocalPlacement",
                                         PlacementRelTo=site_placement,
                                         RelativePlacement=world_origin)
    facility = f.create_entity("IfcFacility",
                               GlobalId=guid(),
                               OwnerHistory=owner,
                               Name=facility_name,
                               ObjectPlacement=facility_placement,
                               CompositionType="ELEMENT",
                               ObjectType="NOISE_BARRIER")

    # Site -> Facility
    f.create_entity("IfcRelAggregates",
                    GlobalId=guid(),
                    OwnerHistory=owner,
                    RelatingObject=site,
                    RelatedObjects=[facility])

    return IfcProjectContext(
        file=f,
        project=project,
        site=site,
        facility=facility,
        context_3d=context_3d,
        context_body=context_body,
        context_axis=context_axis,
        owner_history=owner,
        origin=world_origin,
    )
