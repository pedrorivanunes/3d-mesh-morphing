"""Tests for the 3D point/vector type."""

import math

import pytest

from point import Point


def norm(p):
    return math.sqrt(p.x * p.x + p.y * p.y + p.z * p.z)


class TestConstruction:
    def test_defaults_to_the_origin(self):
        p = Point()
        assert (p.x, p.y, p.z) == (0.0, 0.0, 0.0)

    def test_coerces_integers_to_float(self):
        p = Point(1, 2, 3)
        assert isinstance(p.x, float) and isinstance(p.y, float) and isinstance(p.z, float)

    def test_set_defaults_z_to_zero(self):
        p = Point(1, 2, 3)
        p.set(9, 8)
        assert (p.x, p.y, p.z) == (9.0, 8.0, 0.0)

    def test_repr_shows_three_decimals(self):
        assert repr(Point(1, 2, 3)) == "Point(1.000, 2.000, 3.000)"


class TestArithmetic:
    def test_addition(self):
        p = Point(1, 2, 3) + Point(10, 20, 30)
        assert (p.x, p.y, p.z) == (11.0, 22.0, 33.0)

    def test_subtraction(self):
        p = Point(10, 20, 30) - Point(1, 2, 3)
        assert (p.x, p.y, p.z) == (9.0, 18.0, 27.0)

    def test_scalar_multiplication(self):
        p = Point(1, 2, 3) * 2.5
        assert (p.x, p.y, p.z) == (2.5, 5.0, 7.5)

    def test_operators_return_a_new_point(self):
        original = Point(1, 2, 3)
        original + Point(1, 1, 1)
        assert (original.x, original.y, original.z) == (1.0, 2.0, 3.0)


class TestRotation:
    """Rotations are the only non-trivial math in this class.

    They are checked three ways: known 90-degree results, a full turn being the
    identity, and length being preserved (a rotation is an isometry).
    """

    def test_rotate_x_by_90_takes_y_to_z(self):
        p = Point(0, 1, 0)
        p.rotate_x(90)
        assert p.x == pytest.approx(0.0)
        assert p.y == pytest.approx(0.0)
        assert p.z == pytest.approx(1.0)

    def test_rotate_y_by_90_takes_x_to_minus_z(self):
        p = Point(1, 0, 0)
        p.rotate_y(90)
        assert p.x == pytest.approx(0.0)
        assert p.y == pytest.approx(0.0)
        assert p.z == pytest.approx(-1.0)

    def test_rotate_z_by_90_takes_x_to_y(self):
        p = Point(1, 0, 0)
        p.rotate_z(90)
        assert p.x == pytest.approx(0.0)
        assert p.y == pytest.approx(1.0)
        assert p.z == pytest.approx(0.0)

    @pytest.mark.parametrize("axis", ["rotate_x", "rotate_y", "rotate_z"])
    def test_full_turn_is_the_identity(self, axis):
        p = Point(0.3, -0.7, 1.2)
        getattr(p, axis)(360)
        assert p.x == pytest.approx(0.3)
        assert p.y == pytest.approx(-0.7)
        assert p.z == pytest.approx(1.2)

    @pytest.mark.parametrize("axis", ["rotate_x", "rotate_y", "rotate_z"])
    @pytest.mark.parametrize("angle", [1, 30, 45, 90, 137, 180, 270])
    def test_rotation_preserves_length(self, axis, angle):
        p = Point(0.3, -0.7, 1.2)
        before = norm(p)
        getattr(p, axis)(angle)
        assert norm(p) == pytest.approx(before)

    def test_each_rotation_leaves_its_own_axis_alone(self):
        for axis, untouched in [("rotate_x", "x"), ("rotate_y", "y"), ("rotate_z", "z")]:
            p = Point(0.3, -0.7, 1.2)
            expected = getattr(p, untouched)
            getattr(p, axis)(57)
            assert getattr(p, untouched) == pytest.approx(expected)

    def test_opposite_rotations_cancel_out(self):
        p = Point(0.3, -0.7, 1.2)
        p.rotate_x(35)
        p.rotate_x(-35)
        assert p.x == pytest.approx(0.3)
        assert p.y == pytest.approx(-0.7)
        assert p.z == pytest.approx(1.2)
