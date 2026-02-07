"""Tests for DXF export."""
import tempfile
from pathlib import Path

import pytest
import ezdxf

from gdot_soundwall.landxml.parser import LandXMLParser
from gdot_soundwall.geometry.wall_layout import WallLayoutEngine
from gdot_soundwall.config import WallType
from gdot_soundwall import config
from gdot_soundwall.dxf.exporter import export_dxf

DATA_DIR = Path(__file__).parent.parent / "data"
SAMPLE_XML = DATA_DIR / "sample_alignment.xml"


@pytest.fixture
def dxf_path():
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

    tmp = tempfile.NamedTemporaryFile(suffix=".dxf", delete=False)
    tmp_path = tmp.name
    tmp.close()

    export_dxf(layout, alignment, profile, tmp_path)
    yield tmp_path
    Path(tmp_path).unlink(missing_ok=True)


class TestDXFExport:
    def test_file_created(self, dxf_path):
        assert Path(dxf_path).exists()
        assert Path(dxf_path).stat().st_size > 0

    def test_readable(self, dxf_path):
        doc = ezdxf.readfile(dxf_path)
        assert doc is not None

    def test_layers_present(self, dxf_path):
        doc = ezdxf.readfile(dxf_path)
        layer_names = [l.dxf.name for l in doc.layers]
        assert "ALIGNMENT_CL" in layer_names
        assert "POSTS" in layer_names
        assert "PANELS" in layer_names

    def test_has_entities(self, dxf_path):
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        entities = list(msp)
        assert len(entities) > 100  # Should have many entities
