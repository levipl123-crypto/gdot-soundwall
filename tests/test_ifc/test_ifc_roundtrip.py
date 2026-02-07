"""IFC roundtrip tests: write -> read -> verify."""
from pathlib import Path
import tempfile

import pytest
import ifcopenshell

from gdot_soundwall.landxml.parser import LandXMLParser
from gdot_soundwall.geometry.wall_layout import WallLayoutEngine
from gdot_soundwall.config import WallType, FoundationType
from gdot_soundwall import config
from gdot_soundwall.ifc.project_setup import create_project
from gdot_soundwall.ifc.material_builder import build_materials
from gdot_soundwall.ifc.type_library import build_type_library
from gdot_soundwall.ifc.alignment_builder import build_alignment
from gdot_soundwall.ifc.assembly_builder import build_all_assemblies
from gdot_soundwall.ifc.pset_builder import attach_general_pset
from gdot_soundwall.ifc.spatial_structure import contain_in_facility

DATA_DIR = Path(__file__).parent.parent / "data"
SAMPLE_XML = DATA_DIR / "sample_alignment.xml"


@pytest.fixture
def ifc_model():
    """Create a complete IFC model and return the file object."""
    parser = LandXMLParser(SAMPLE_XML)
    alignment = parser.parse_alignment()
    profile = parser.parse_profile()
    surface = parser.parse_surface()

    engine = WallLayoutEngine(
        alignment=alignment,
        profile=profile,
        surface=surface,
        wall_type=WallType.PRECAST,
        wall_height=config.DEFAULT_WALL_HEIGHT,
    )
    layout = engine.compute()

    ctx = create_project()
    mat_lib = build_materials(ctx)
    type_lib = build_type_library(ctx)

    ifc_alignment = build_alignment(ctx, alignment, profile)
    contain_in_facility(ctx, [ifc_alignment])

    assemblies = build_all_assemblies(ctx, layout, type_lib, mat_lib)
    attach_general_pset(ctx, ctx.facility, layout)

    return ctx.file, layout


@pytest.fixture
def roundtrip_file(ifc_model):
    """Write and re-read the IFC file."""
    ifc_file, layout = ifc_model
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
        tmp_path = tmp.name
    ifc_file.write(tmp_path)
    reloaded = ifcopenshell.open(tmp_path)
    Path(tmp_path).unlink(missing_ok=True)
    return reloaded, layout


class TestSpatialHierarchy:
    def test_project_exists(self, roundtrip_file):
        f, _ = roundtrip_file
        projects = f.by_type("IfcProject")
        assert len(projects) == 1

    def test_site_exists(self, roundtrip_file):
        f, _ = roundtrip_file
        sites = f.by_type("IfcSite")
        assert len(sites) == 1

    def test_facility_exists(self, roundtrip_file):
        f, _ = roundtrip_file
        facilities = f.by_type("IfcFacility")
        assert len(facilities) == 1
        fac = facilities[0]
        assert fac.ObjectType == "NOISE_BARRIER"


class TestAlignment:
    def test_alignment_exists(self, roundtrip_file):
        f, _ = roundtrip_file
        alignments = f.by_type("IfcAlignment")
        assert len(alignments) == 1

    def test_horizontal_segments(self, roundtrip_file):
        f, _ = roundtrip_file
        h_segs = f.by_type("IfcAlignmentHorizontalSegment")
        assert len(h_segs) == 3  # tangent + curve + tangent


class TestAssemblies:
    def test_assembly_count(self, roundtrip_file):
        f, layout = roundtrip_file
        assemblies = f.by_type("IfcElementAssembly")
        assert len(assemblies) == layout.num_bays

    def test_columns_exist(self, roundtrip_file):
        f, layout = roundtrip_file
        columns = f.by_type("IfcColumn")
        assert len(columns) == len(layout.posts)

    def test_walls_exist(self, roundtrip_file):
        f, layout = roundtrip_file
        walls = f.by_type("IfcWall")
        assert len(walls) == len(layout.panels)

    def test_footings_exist(self, roundtrip_file):
        f, layout = roundtrip_file
        footings = f.by_type("IfcCaissonFoundation")
        assert len(footings) == len(layout.footings)

    def test_plates_exist(self, roundtrip_file):
        f, layout = roundtrip_file
        plates = f.by_type("IfcPlate")
        assert len(plates) == len(layout.caps)


class TestPropertySets:
    def test_general_pset(self, roundtrip_file):
        f, _ = roundtrip_file
        psets = [ps for ps in f.by_type("IfcPropertySet")
                 if ps.Name == "GDOT_SoundWall_General"]
        assert len(psets) >= 1

    def test_post_pset(self, roundtrip_file):
        f, _ = roundtrip_file
        psets = [ps for ps in f.by_type("IfcPropertySet")
                 if ps.Name == "GDOT_SoundWall_Post"]
        assert len(psets) > 0

    def test_panel_pset(self, roundtrip_file):
        f, _ = roundtrip_file
        psets = [ps for ps in f.by_type("IfcPropertySet")
                 if ps.Name == "GDOT_SoundWall_Panel"]
        assert len(psets) > 0

    def test_footing_pset(self, roundtrip_file):
        f, _ = roundtrip_file
        psets = [ps for ps in f.by_type("IfcPropertySet")
                 if ps.Name == "GDOT_SoundWall_Footing"]
        assert len(psets) > 0

    def test_surface_treatment_pset(self, roundtrip_file):
        f, _ = roundtrip_file
        psets = [ps for ps in f.by_type("IfcPropertySet")
                 if ps.Name == "GDOT_SurfaceTreatment"]
        assert len(psets) > 0

    def test_wall_quantities(self, roundtrip_file):
        f, _ = roundtrip_file
        qtos = [q for q in f.by_type("IfcElementQuantity")
                if q.Name == "Qto_WallBaseQuantities"]
        assert len(qtos) > 0


class TestMaterials:
    def test_materials_exist(self, roundtrip_file):
        f, _ = roundtrip_file
        materials = f.by_type("IfcMaterial")
        names = [m.Name for m in materials]
        assert "Structural Steel - AASHTO M 270 GR 36" in names
        assert "Precast PAAC" in names
        assert "Reinforced Concrete" in names

    def test_material_associations(self, roundtrip_file):
        f, _ = roundtrip_file
        assocs = f.by_type("IfcRelAssociatesMaterial")
        assert len(assocs) > 0


class TestTypes:
    def test_column_type(self, roundtrip_file):
        f, _ = roundtrip_file
        types = f.by_type("IfcColumnType")
        assert len(types) >= 1
        assert any("W6x20" in t.Name for t in types)

    def test_wall_type(self, roundtrip_file):
        f, _ = roundtrip_file
        types = f.by_type("IfcWallType")
        assert len(types) >= 1

    def test_footing_type(self, roundtrip_file):
        f, _ = roundtrip_file
        types = f.by_type("IfcFootingType")
        assert len(types) >= 1
