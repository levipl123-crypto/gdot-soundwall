"""Tests for geometry computation."""
import math
from pathlib import Path

import pytest

from gdot_soundwall.landxml.parser import LandXMLParser
from gdot_soundwall.geometry.station_solver import StationSolver
from gdot_soundwall.geometry.terrain_sampler import TerrainSampler
from gdot_soundwall.geometry.wall_layout import WallLayoutEngine
from gdot_soundwall.config import WallType, FoundationType
from gdot_soundwall import config

DATA_DIR = Path(__file__).parent.parent / "data"
SAMPLE_XML = DATA_DIR / "sample_alignment.xml"


@pytest.fixture
def parsed_data():
    parser = LandXMLParser(SAMPLE_XML)
    return {
        "alignment": parser.parse_alignment(),
        "profile": parser.parse_profile(),
        "surface": parser.parse_surface(),
    }


class TestStationSolver:
    def test_solve_start(self, parsed_data):
        solver = StationSolver(parsed_data["alignment"], parsed_data["profile"])
        pt = solver.solve(0.0)
        assert abs(pt.easting - 2000.0) < 0.1
        assert abs(pt.northing - 1000.0) < 0.1

    def test_solve_mid(self, parsed_data):
        solver = StationSolver(parsed_data["alignment"], parsed_data["profile"])
        pt = solver.solve(50.0)
        # 50m along a north-heading tangent
        assert abs(pt.easting - 2000.0) < 0.1
        assert abs(pt.northing - 1050.0) < 0.5

    def test_solve_with_offset(self, parsed_data):
        solver = StationSolver(parsed_data["alignment"], parsed_data["profile"])
        pt_cl = solver.solve(50.0)
        pt_off = solver.solve(50.0, offset=5.0)
        # Offset should move perpendicular to bearing
        dist = math.sqrt((pt_off.easting - pt_cl.easting) ** 2 +
                         (pt_off.northing - pt_cl.northing) ** 2)
        assert abs(dist - 5.0) < 0.1

    def test_solve_range(self, parsed_data):
        solver = StationSolver(parsed_data["alignment"], parsed_data["profile"])
        points = solver.solve_range(0.0, 100.0, 10.0)
        assert len(points) == 11


class TestTerrainSampler:
    def test_sample_within_tin(self, parsed_data):
        sampler = TerrainSampler(parsed_data["surface"])
        elev = sampler.sample(2050.0, 1100.0)
        assert elev is not None
        assert 99.0 < elev < 100.0

    def test_sample_fallback_to_profile(self, parsed_data):
        sampler = TerrainSampler(parsed_data["surface"])
        solver = StationSolver(parsed_data["alignment"], parsed_data["profile"])
        elev = sampler.sample_at_station(solver, 0.0)
        assert elev is not None


class TestWallLayout:
    def test_precast_layout(self, parsed_data):
        engine = WallLayoutEngine(
            alignment=parsed_data["alignment"],
            profile=parsed_data["profile"],
            surface=parsed_data["surface"],
            wall_type=WallType.PRECAST,
            wall_height=config.DEFAULT_WALL_HEIGHT,
        )
        layout = engine.compute()

        # ~305m / 3.048m spacing ≈ 100 bays, 101 posts
        assert len(layout.posts) > 90
        assert len(layout.posts) < 110
        assert layout.num_bays == len(layout.posts) - 1
        assert len(layout.panels) > 0
        assert len(layout.footings) == len(layout.posts)
        assert len(layout.caps) == layout.num_bays

    def test_joints_present(self, parsed_data):
        engine = WallLayoutEngine(
            alignment=parsed_data["alignment"],
            profile=parsed_data["profile"],
            wall_type=WallType.PRECAST,
        )
        layout = engine.compute()
        # 305m / 24.384m ≈ 12 expansion joints
        expansion_joints = [j for j in layout.joints if j.joint_type.value == "expansion"]
        assert len(expansion_joints) >= 10

    def test_mse_layout(self, parsed_data):
        engine = WallLayoutEngine(
            alignment=parsed_data["alignment"],
            profile=parsed_data["profile"],
            wall_type=WallType.MSE_COMPOSITE,
        )
        layout = engine.compute()
        assert len(layout.mse_segments) > 0
        # Should also have precast components on top
        assert len(layout.posts) > 0

    def test_post_spacing_respected(self, parsed_data):
        engine = WallLayoutEngine(
            alignment=parsed_data["alignment"],
            profile=parsed_data["profile"],
            post_spacing=3.048,
        )
        layout = engine.compute()
        for i in range(len(layout.posts) - 1):
            spacing = layout.posts[i + 1].station - layout.posts[i].station
            assert spacing <= 3.048 + 0.01
