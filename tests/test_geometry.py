"""Tests for normalization, centroids and triangle normals."""

import math

import pytest

from conftest import make_mesh
from object3d import Object3D, _nearest_index, _triangle_normal
from point import Point


def bbox(mesh):
    xs = [v.x for v in mesh.vertices]
    ys = [v.y for v in mesh.vertices]
    zs = [v.z for v in mesh.vertices]
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


class TestNormalize:
    """Normalization centers the mesh and scales it into a unit cube.

    The scaling is uniform (a single divisor for all three axes), which is what
    keeps the shape from being distorted.
    """

    def test_centers_the_bounding_box_on_the_origin(self):
        mesh = make_mesh([(0, 0, 0), (2, 2, 2)], [])
        mesh.normalize()
        for lo, hi in bbox(mesh):
            assert (lo + hi) / 2 == pytest.approx(0.0)

    def test_the_longest_axis_ends_up_exactly_one_unit_long(self):
        mesh = make_mesh([(0, 0, 0), (4, 2, 1)], [])
        mesh.normalize()
        spans = [hi - lo for lo, hi in bbox(mesh)]
        assert max(spans) == pytest.approx(1.0)

    def test_everything_fits_inside_the_unit_cube(self, banana):
        banana.normalize()
        assert all(
            -0.5 <= c <= 0.5 for v in banana.vertices for c in (v.x, v.y, v.z)
        )

    def test_scaling_is_uniform_so_proportions_survive(self):
        mesh = make_mesh([(0, 0, 0), (4, 2, 1)], [])
        mesh.normalize()
        spans = [hi - lo for lo, hi in bbox(mesh)]
        # the original box was 4 x 2 x 1, so the ratios must stay 1 : 0.5 : 0.25
        assert spans[0] == pytest.approx(1.0)
        assert spans[1] == pytest.approx(0.5)
        assert spans[2] == pytest.approx(0.25)

    def test_a_cube_maps_to_plus_or_minus_a_half(self):
        mesh = make_mesh([(0, 0, 0), (2, 2, 2)], [])
        mesh.normalize()
        for lo, hi in bbox(mesh):
            assert lo == pytest.approx(-0.5)
            assert hi == pytest.approx(0.5)

    def test_an_empty_mesh_is_left_alone(self):
        mesh = Object3D()
        mesh.normalize()  # must not raise
        assert mesh.vertices == []

    def test_a_degenerate_mesh_does_not_divide_by_zero(self):
        # every vertex at the same spot: the bounding box has zero span
        mesh = make_mesh([(5, 5, 5), (5, 5, 5), (5, 5, 5)], [])
        mesh.normalize()
        assert all((v.x, v.y, v.z) == (0.0, 0.0, 0.0) for v in mesh.vertices)

    def test_running_it_twice_changes_nothing_further(self, banana):
        banana.normalize()
        first = [c for v in banana.vertices for c in (v.x, v.y, v.z)]
        banana.normalize()
        second = [c for v in banana.vertices for c in (v.x, v.y, v.z)]
        assert first == pytest.approx(second)

    def test_normalizing_does_not_move_vertices_relative_to_each_other(self):
        mesh = make_mesh([(0, 0, 0), (4, 0, 0), (1, 0, 0)], [])
        mesh.normalize()
        a, b, c = mesh.vertices
        # the third vertex was 1/4 of the way along; it must stay there
        assert (c.x - a.x) / (b.x - a.x) == pytest.approx(0.25)


class TestCentroid:
    def test_centroid_of_a_triangle_is_the_average_of_its_vertices(self):
        mesh = make_mesh([(0, 0, 0), (3, 0, 0), (0, 3, 0)], [[0, 1, 2]])
        c = mesh._centroid(mesh.faces[0])
        assert (c.x, c.y, c.z) == pytest.approx((1.0, 1.0, 0.0))

    def test_centroid_of_a_degenerate_face_is_that_point(self):
        mesh = make_mesh([(2, 2, 2)], [[0, 0, 0]])
        c = mesh._centroid(mesh.faces[0])
        assert (c.x, c.y, c.z) == pytest.approx((2.0, 2.0, 2.0))


class TestNearestIndex:
    def test_finds_the_closest_centroid(self):
        candidates = [Point(10, 0, 0), Point(0, 0, 0), Point(-10, 0, 0)]
        assert _nearest_index(Point(1, 0, 0), candidates) == 1

    def test_an_exact_match_wins(self):
        candidates = [Point(0, 0, 0), Point(5, 5, 5), Point(9, 9, 9)]
        assert _nearest_index(Point(5, 5, 5), candidates) == 1

    def test_ties_go_to_the_first_candidate(self):
        candidates = [Point(1, 0, 0), Point(-1, 0, 0)]
        assert _nearest_index(Point(0, 0, 0), candidates) == 0

    def test_distance_is_measured_in_all_three_axes(self):
        candidates = [Point(0, 0, 3), Point(0, 0, 1)]
        assert _nearest_index(Point(0, 0, 0), candidates) == 1


class TestTriangleNormal:
    def test_a_counter_clockwise_triangle_in_xy_points_at_plus_z(self):
        n = _triangle_normal(Point(0, 0, 0), Point(1, 0, 0), Point(0, 1, 0))
        assert n == pytest.approx((0.0, 0.0, 1.0))

    def test_reversing_the_winding_flips_the_normal(self):
        a = _triangle_normal(Point(0, 0, 0), Point(1, 0, 0), Point(0, 1, 0))
        b = _triangle_normal(Point(0, 0, 0), Point(0, 1, 0), Point(1, 0, 0))
        assert a == pytest.approx(tuple(-c for c in b))

    @pytest.mark.parametrize(
        "p0,p1,p2",
        [
            ((0, 0, 0), (1, 0, 0), (0, 1, 0)),
            ((1, 2, 3), (4, 6, 1), (-2, 0, 5)),
            ((0.1, 0.2, 0.3), (0.9, -0.4, 0.2), (0.3, 0.8, -0.6)),
        ],
    )
    def test_the_normal_is_always_a_unit_vector(self, p0, p1, p2):
        n = _triangle_normal(Point(*p0), Point(*p1), Point(*p2))
        assert math.sqrt(sum(c * c for c in n)) == pytest.approx(1.0)

    def test_the_normal_is_perpendicular_to_both_edges(self):
        p0, p1, p2 = Point(1, 2, 3), Point(4, 6, 1), Point(-2, 0, 5)
        nx, ny, nz = _triangle_normal(p0, p1, p2)
        for edge in ((p1.x - p0.x, p1.y - p0.y, p1.z - p0.z),
                     (p2.x - p0.x, p2.y - p0.y, p2.z - p0.z)):
            assert nx * edge[0] + ny * edge[1] + nz * edge[2] == pytest.approx(0.0)

    def test_a_collinear_triangle_does_not_blow_up(self):
        # zero-area triangle: the cross product is (0, 0, 0) and the guard in
        # the code stops the division by zero
        n = _triangle_normal(Point(0, 0, 0), Point(1, 0, 0), Point(2, 0, 0))
        assert n == (0.0, 0.0, 0.0)

    def test_normals_of_degenerate_morph_frames_stay_finite(self):
        # this is the case that actually shows up mid-morph, when a leftover
        # face collapses onto a single point
        n = _triangle_normal(Point(1, 1, 1), Point(1, 1, 1), Point(1, 1, 1))
        assert all(math.isfinite(c) for c in n)
