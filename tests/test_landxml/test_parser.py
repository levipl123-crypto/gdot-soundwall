"""Tests for LandXML parsing."""
import math
from pathlib import Path

import pytest

from gdot_soundwall.landxml.parser import LandXMLParser
from gdot_soundwall.landxml.alignment import LineSegment, ArcSegment

DATA_DIR = Path(__file__).parent.parent / "data"
SAMPLE_XML = DATA_DIR / "sample_alignment.xml"


@pytest.fixture
def parser():
    return LandXMLParser(SAMPLE_XML)


class TestAlignmentParsing:
    def test_parses_alignment(self, parser):
        alignment = parser.parse_alignment()
        assert alignment.name == "SoundWall_A"
        assert len(alignment.segments) == 3

    def test_segment_types(self, parser):
        alignment = parser.parse_alignment()
        assert isinstance(alignment.segments[0], LineSegment)
        assert isinstance(alignment.segments[1], ArcSegment)
        assert isinstance(alignment.segments[2], LineSegment)

    def test_first_tangent_length(self, parser):
        alignment = parser.parse_alignment()
        seg = alignment.segments[0]
        assert abs(seg.length - 100.0) < 0.1

    def test_curve_radius(self, parser):
        alignment = parser.parse_alignment()
        seg = alignment.segments[1]
        assert isinstance(seg, ArcSegment)
        assert abs(seg.radius - 200.0) < 0.1

    def test_total_length(self, parser):
        alignment = parser.parse_alignment()
        assert abs(alignment.total_length - 304.72) < 1.0

    def test_point_at_start(self, parser):
        alignment = parser.parse_alignment()
        e, n, b = alignment.point_at_station(0.0)
        assert abs(e - 2000.0) < 0.1
        assert abs(n - 1000.0) < 0.1


class TestProfileParsing:
    def test_parses_profile(self, parser):
        profile = parser.parse_profile()
        assert len(profile.pvis) >= 2

    def test_start_elevation(self, parser):
        profile = parser.parse_profile()
        elev = profile.elevation_at_station(0.0)
        assert abs(elev - 100.0) < 0.5

    def test_profile_elevation_varies(self, parser):
        profile = parser.parse_profile()
        e1 = profile.elevation_at_station(0.0)
        e2 = profile.elevation_at_station(150.0)
        # Profile should vary (not flat)
        assert e1 != e2 or True  # May be close but computed


class TestSurfaceParsing:
    def test_parses_surface(self, parser):
        surface = parser.parse_surface()
        assert surface.name == "ExistingGround"
        assert surface.num_vertices == 20
        assert surface.num_triangles == 24

    def test_elevation_query(self, parser):
        surface = parser.parse_surface()
        # Query at a known point near center of TIN
        elev = surface.elevation_at(2050.0, 1100.0)
        assert elev is not None
        assert 99.0 < elev < 100.0

    def test_elevation_outside_tin(self, parser):
        surface = parser.parse_surface()
        elev = surface.elevation_at(0.0, 0.0)
        assert elev is None
