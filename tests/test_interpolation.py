"""Tests for the interpolation, which is the heart of the morph.

    v(t) = (1 - t) * v_source + t * v_target

The endpoints are the properties that matter most: at t = 0 the frame has to be
the source mesh exactly, and at t = 1 the target mesh exactly. Anything else
would mean the animation does not start or end where the user can see it should.
"""

import copy

import pytest

from helpers import make_mesh


def coords(triangles):
    return [[(p.x, p.y, p.z) for p in tri] for tri in triangles]


def flat(triangles):
    """pytest.approx only handles flat sequences, so squash the nesting."""
    return [c for tri in triangles for point in tri for c in point]


@pytest.fixture
def source():
    return make_mesh([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [[0, 1, 2]])


@pytest.fixture
def target():
    return make_mesh([(10, 0, 0), (11, 0, 0), (10, 1, 0)], [[0, 1, 2]])


@pytest.fixture
def pairs(source, target):
    return source.match_faces(target, "neighbor")


class TestEndpoints:
    def test_t_zero_reproduces_the_source_exactly(self, source, target, pairs):
        frame = source.interpolate(target, pairs, 0.0)
        assert coords(frame) == [[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]]

    def test_t_one_reproduces_the_target_exactly(self, source, target, pairs):
        frame = source.interpolate(target, pairs, 1.0)
        assert coords(frame) == [[(10.0, 0.0, 0.0), (11.0, 0.0, 0.0), (10.0, 1.0, 0.0)]]

    def test_the_endpoints_are_exact_not_approximate(self, banana):
        # floating point: (1 - 0) * a + 0 * b is a, bit for bit
        twin = copy.deepcopy(banana)
        pairs = banana.match_faces(twin, "neighbor")
        frame = banana.interpolate(twin, pairs, 0.0)
        for tri, face in zip(frame, [f1 for f1, _ in pairs]):
            for point, index in zip(tri, face):
                original = banana.vertices[index]
                assert (point.x, point.y, point.z) == (original.x, original.y, original.z)


class TestMidpoints:
    def test_t_half_is_the_arithmetic_mean(self, source, target, pairs):
        frame = source.interpolate(target, pairs, 0.5)
        assert coords(frame) == [[(5.0, 0.0, 0.0), (6.0, 0.0, 0.0), (5.0, 1.0, 0.0)]]

    @pytest.mark.parametrize("t", [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0])
    def test_every_vertex_stays_on_the_segment_between_its_endpoints(
        self, source, target, pairs, t
    ):
        frame = source.interpolate(target, pairs, t)
        for tri, (face1, face2) in zip(frame, pairs):
            for point, i, j in zip(tri, face1, face2):
                lo = min(source.vertices[i].x, target.vertices[j].x)
                hi = max(source.vertices[i].x, target.vertices[j].x)
                assert lo - 1e-9 <= point.x <= hi + 1e-9

    def test_the_motion_is_monotonic_in_t(self, source, target, pairs):
        xs = [source.interpolate(target, pairs, t / 10)[0][0].x for t in range(11)]
        assert xs == sorted(xs)

    def test_equal_steps_in_t_give_equal_steps_in_space(self, source, target, pairs):
        # linear interpolation means constant speed
        xs = [source.interpolate(target, pairs, t / 10)[0][0].x for t in range(11)]
        deltas = [b - a for a, b in zip(xs, xs[1:])]
        assert all(d == pytest.approx(deltas[0]) for d in deltas)


class TestShape:
    def test_one_triangle_comes_out_per_pair(self, banana):
        other = make_mesh([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [[0, 1, 2]])
        pairs = banana.match_faces(other, "neighbor")
        assert len(banana.interpolate(other, pairs, 0.5)) == len(pairs)

    def test_every_output_triangle_has_three_points(self, source, target, pairs):
        assert all(len(tri) == 3 for tri in source.interpolate(target, pairs, 0.3))

    def test_an_empty_pairing_produces_no_geometry(self, source, target):
        assert source.interpolate(target, [], 0.5) == []

    def test_interpolating_does_not_mutate_the_meshes(self, source, target, pairs):
        before = [(v.x, v.y, v.z) for v in source.vertices]
        source.interpolate(target, pairs, 0.5)
        assert [(v.x, v.y, v.z) for v in source.vertices] == before


class TestMorphingIntoItself:
    def test_a_mesh_morphing_into_its_own_copy_never_moves(self, tetrahedron):
        twin = copy.deepcopy(tetrahedron)
        pairs = tetrahedron.match_faces(twin, "neighbor")
        for t in (0.0, 0.25, 0.5, 0.75, 1.0):
            frame = tetrahedron.interpolate(twin, pairs, t)
            expected = [
                [(tetrahedron.vertices[i].x, tetrahedron.vertices[i].y, tetrahedron.vertices[i].z)
                 for i in face]
                for face in tetrahedron.faces
            ]
            assert flat(coords(frame)) == pytest.approx(flat(expected))
