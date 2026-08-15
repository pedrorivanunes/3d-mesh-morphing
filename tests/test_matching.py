"""Tests for `match_faces`, the step that decides which face becomes which.

The invariants checked here are the ones the animation actually depends on:
no face may be left without a partner, and the number of pairs is always the
larger of the two face counts.
"""

import copy
import random

import pytest

from helpers import make_mesh

MODES = ["neighbor", "random", "collapse"]


def triangle_at(x):
    """Vertices of a unit triangle translated along X."""
    return [(x, 0, 0), (x + 1, 0, 0), (x, 1, 0)]


def strip(*positions):
    """A mesh with one triangle per position given on the X axis."""
    vertices = []
    faces = []
    for i, x in enumerate(positions):
        vertices.extend(triangle_at(x))
        faces.append([3 * i, 3 * i + 1, 3 * i + 2])
    return make_mesh(vertices, faces)


def as_keys(faces):
    """Faces are lists, so turn them into tuples to compare or hash them."""
    return [tuple(f) for f in faces]


class TestPairCount:
    """However lopsided the meshes are, the pairing covers both of them."""

    @pytest.mark.parametrize("mode", MODES)
    def test_equal_face_counts_produce_one_pair_each(self, mode):
        a, b = strip(0, 10, 20), strip(1, 11, 21)
        assert len(a.match_faces(b, mode)) == 3

    @pytest.mark.parametrize("mode", MODES)
    def test_more_source_faces_than_target_faces(self, mode):
        a, b = strip(0, 10, 20, 30), strip(0, 10)
        assert len(a.match_faces(b, mode)) == 4

    @pytest.mark.parametrize("mode", MODES)
    def test_more_target_faces_than_source_faces(self, mode):
        a, b = strip(0), strip(0, 10, 20)
        assert len(a.match_faces(b, mode)) == 3

    @pytest.mark.parametrize("mode", MODES)
    def test_pair_count_is_always_the_larger_face_count(self, mode):
        a, b = strip(0, 5, 10, 15, 20), strip(0, 10)
        pairs = a.match_faces(b, mode)
        assert len(pairs) == max(len(a.faces), len(b.faces))

    def test_real_meshes_follow_the_same_rule(self, banana):
        other = strip(0, 1, 2)
        pairs = banana.match_faces(other, "neighbor")
        assert len(pairs) == max(len(banana.faces), len(other.faces)) == 612


class TestCoverage:
    """No face may be dropped: that would leave a hole in the animation."""

    @pytest.mark.parametrize("mode", MODES)
    def test_every_source_face_is_used(self, mode):
        a, b = strip(0, 10, 20, 30), strip(0, 10)
        used = {tuple(f1) for f1, _ in a.match_faces(b, mode)}
        assert used == set(as_keys(a.faces))

    @pytest.mark.parametrize("mode", MODES)
    def test_every_target_face_is_used(self, mode):
        a, b = strip(0), strip(0, 10, 20)
        used = {tuple(f2) for _, f2 in a.match_faces(b, mode)}
        assert used == set(as_keys(b.faces))

    @pytest.mark.parametrize("mode", MODES)
    def test_pairs_only_reference_faces_that_exist(self, mode):
        a, b = strip(0, 10, 20), strip(5, 15)
        valid_a, valid_b = set(as_keys(a.faces)), set(as_keys(b.faces))
        for f1, f2 in a.match_faces(b, mode):
            assert tuple(f1) in valid_a
            assert tuple(f2) in valid_b


class TestGreedyPhase:
    """Phase 1 pairs faces one-to-one, by nearest centroid."""

    def test_equal_counts_give_a_bijection(self):
        a, b = strip(0, 10, 20), strip(1, 11, 21)
        pairs = a.match_faces(b, "neighbor")
        targets = as_keys([f2 for _, f2 in pairs])
        assert len(targets) == len(set(targets)) == len(b.faces)

    def test_faces_are_paired_with_their_nearest_counterpart(self):
        a, b = strip(0, 100), strip(100, 0)
        pairs = dict(zip(as_keys(a.faces), as_keys([f2 for _, f2 in a.match_faces(b, "neighbor")])))
        # a's first triangle sits at x=0, so it must pair with b's *second*
        assert pairs[tuple(a.faces[0])] == tuple(b.faces[1])
        assert pairs[tuple(a.faces[1])] == tuple(b.faces[0])

    def test_a_mesh_matched_against_a_copy_of_itself_gives_the_identity(self, tetrahedron):
        twin = copy.deepcopy(tetrahedron)
        pairs = tetrahedron.match_faces(twin, "neighbor")
        # every centroid is at distance zero from its own copy, so the greedy
        # pass has to reproduce the mesh face for face, in order
        assert as_keys([f1 for f1, _ in pairs]) == as_keys(tetrahedron.faces)
        assert as_keys([f2 for _, f2 in pairs]) == as_keys(twin.faces)

    def test_identity_holds_for_a_real_mesh_too(self, banana):
        twin = copy.deepcopy(banana)
        pairs = banana.match_faces(twin, "neighbor")
        assert all(tuple(f1) == tuple(f2) for f1, f2 in pairs)


class TestLeftoverModes:
    """Phase 2 is where the three modes differ."""

    def test_neighbor_sends_the_leftover_to_the_closest_face(self):
        # a's third triangle (x=8) has no partner left; the closest face of b
        # is the one at x=0, not the one paired last (x=20)
        a, b = strip(0, 20, 8), strip(0, 20)
        pairs = a.match_faces(b, "neighbor")
        leftover_target = pairs[-1][1]
        assert tuple(leftover_target) == tuple(b.faces[0])

    def test_collapse_reuses_the_last_pair_instead(self):
        a, b = strip(0, 20, 8), strip(0, 20)
        pairs = a.match_faces(b, "collapse")
        leftover_target = pairs[-1][1]
        assert tuple(leftover_target) == tuple(b.faces[1])

    def test_neighbor_and_collapse_really_do_differ(self):
        a, b = strip(0, 20, 8), strip(0, 20)
        assert a.match_faces(b, "neighbor")[-1][1] != a.match_faces(b, "collapse")[-1][1]

    def test_random_is_reproducible_under_a_seed(self):
        a, b = strip(0, 10, 20, 30), strip(0, 10)
        random.seed(1234)
        first = as_keys([f2 for _, f2 in a.match_faces(b, "random")])
        random.seed(1234)
        second = as_keys([f2 for _, f2 in a.match_faces(b, "random")])
        assert first == second

    def test_random_can_pick_any_face(self):
        a, b = strip(0, 10, 20, 30, 40, 50), strip(0, 10)
        random.seed(7)
        chosen = {tuple(f2) for _, f2 in a.match_faces(b, "random")}
        assert chosen == set(as_keys(b.faces))

    def test_the_default_mode_is_neighbor(self):
        a, b = strip(0, 20, 8), strip(0, 20)
        assert a.match_faces(b) == a.match_faces(b, "neighbor")

    def test_an_unknown_mode_falls_back_to_collapse(self):
        # the implementation treats anything that is not "neighbor" or "random"
        # as "collapse"; this pins that behaviour down
        a, b = strip(0, 20, 8), strip(0, 20)
        assert a.match_faces(b, "nonsense") == a.match_faces(b, "collapse")


class TestSymmetry:
    @pytest.mark.parametrize("mode", ["neighbor", "collapse"])
    def test_matching_works_in_both_directions(self, mode):
        a, b = strip(0, 10, 20, 30), strip(0, 10)
        assert len(a.match_faces(b, mode)) == len(b.match_faces(a, mode)) == 4

    def test_matching_does_not_mutate_either_mesh(self, tetrahedron):
        a, b = tetrahedron, strip(0, 10)
        before_a = as_keys(a.faces), [(v.x, v.y, v.z) for v in a.vertices]
        before_b = as_keys(b.faces), [(v.x, v.y, v.z) for v in b.vertices]
        a.match_faces(b, "neighbor")
        assert (as_keys(a.faces), [(v.x, v.y, v.z) for v in a.vertices]) == before_a
        assert (as_keys(b.faces), [(v.x, v.y, v.z) for v in b.vertices]) == before_b
