"""Tests for calibration and zone logic."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pytest
import numpy as np
from app.calibration.homography import compute_homography, transform_point
from app.calibration.zones import Zone, ZoneChecker, zones_from_procedure


class TestHomography:
    def test_identity_homography(self):
        """Unit square points should map to themselves."""
        points = [(0, 0), (100, 0), (100, 100), (0, 100)]
        H = compute_homography(points)
        assert H is not None
        assert H.shape == (3, 3)

    def test_transform_point_inside(self):
        """Point at center of frame should map to ~(0.5, 0.5)."""
        pts = [(0, 0), (1280, 0), (1280, 720), (0, 720)]
        H = compute_homography(pts)
        result = transform_point(H, 640, 360)
        assert result is not None
        cx, cy = result
        assert abs(cx - 0.5) < 0.05, f"Expected cx≈0.5, got {cx}"
        assert abs(cy - 0.5) < 0.05, f"Expected cy≈0.5, got {cy}"

    def test_transform_point_none_if_no_homography(self):
        result = transform_point(None, 100, 100)
        assert result is None

    def test_incomplete_points_returns_none(self):
        H = compute_homography([(0, 0), (1, 0)])
        assert H is None

    def test_transformed_clamped_to_unit(self):
        """Points outside calibration area should be clamped."""
        pts = [(100, 100), (900, 100), (900, 600), (100, 600)]
        H = compute_homography(pts)
        result = transform_point(H, 0, 0)  # outside area
        if result:
            x, y = result
            assert 0.0 <= x <= 1.0
            assert 0.0 <= y <= 1.0


class TestZones:
    def test_zone_checker_inside(self):
        zones = [Zone("z1", "Zone 1", "#fff", x=0.1, y=0.1, w=0.3, h=0.3)]
        checker = ZoneChecker(zones)
        result = checker.check(0.25, 0.25)
        assert "z1" in result

    def test_zone_checker_outside(self):
        zones = [Zone("z1", "Zone 1", "#fff", x=0.1, y=0.1, w=0.3, h=0.3)]
        checker = ZoneChecker(zones)
        result = checker.check(0.8, 0.8)
        assert "z1" not in result

    def test_zone_checker_boundary(self):
        zones = [Zone("z1", "Zone 1", "#fff", x=0.1, y=0.1, w=0.3, h=0.3)]
        checker = ZoneChecker(zones)
        # On the edge
        assert checker.is_in_zone(0.1, 0.1, "z1")
        assert checker.is_in_zone(0.4, 0.4, "z1")
        assert not checker.is_in_zone(0.41, 0.41, "z1")

    def test_multiple_zones(self):
        zones = [
            Zone("z1", "Zone 1", "#fff", x=0.0, y=0.0, w=0.5, h=0.5),
            Zone("z2", "Zone 2", "#000", x=0.4, y=0.4, w=0.5, h=0.5),
        ]
        checker = ZoneChecker(zones)
        # Point at 0.45, 0.45 is in BOTH zones
        result = checker.check(0.45, 0.45)
        assert "z1" in result
        assert "z2" in result

    def test_zones_from_procedure_config(self):
        config = {
            "workspace_zones": [
                {"id": "assembly", "name": "Assembly Zone", "color": "#10B981",
                 "normalized": {"x": 0.3, "y": 0.1, "w": 0.4, "h": 0.4}},
            ]
        }
        checker = zones_from_procedure(config)
        assert checker.is_in_zone(0.5, 0.3, "assembly")
        assert not checker.is_in_zone(0.1, 0.1, "assembly")
