"""Tests for the .obj reader and the fan triangulation."""

import pytest

from object3d import Object3D


class TestTriangulation:
    """Fan triangulation must always produce exactly n - 2 triangles."""

    def test_a_triangle_is_left_alone(self):
        assert Object3D._triangulate([0, 1, 2]) == [[0, 1, 2]]

    def test_a_quad_becomes_two_triangles(self):
        assert Object3D._triangulate([0, 1, 2, 3]) == [[0, 1, 2], [0, 2, 3]]

    def test_a_pentagon_becomes_three_triangles(self):
        assert Object3D._triangulate([0, 1, 2, 3, 4]) == [[0, 1, 2], [0, 2, 3], [0, 3, 4]]

    @pytest.mark.parametrize("n", [3, 4, 5, 6, 10, 25])
    def test_an_ngon_becomes_n_minus_2_triangles(self, n):
        assert len(Object3D._triangulate(list(range(n)))) == n - 2

    def test_every_triangle_shares_the_first_vertex(self):
        for tri in Object3D._triangulate([7, 1, 2, 3, 4]):
            assert tri[0] == 7

    def test_the_fan_covers_every_vertex(self):
        face = [0, 1, 2, 3, 4, 5]
        used = {i for tri in Object3D._triangulate(face) for i in tri}
        assert used == set(face)


class TestLoading:
    def test_reads_vertices_and_faces(self, write_obj):
        path = write_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
        mesh = Object3D().load(path)
        assert len(mesh.vertices) == 3
        assert mesh.faces == [[0, 1, 2]]

    def test_converts_from_one_based_to_zero_based_indices(self, write_obj):
        path = write_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
        mesh = Object3D().load(path)
        assert mesh.faces == [[0, 1, 2]]

    def test_vertex_coordinates_are_preserved(self, write_obj):
        path = write_obj("v -1.5 2.25 -3.75\n")
        mesh = Object3D().load(path)
        v = mesh.vertices[0]
        assert (v.x, v.y, v.z) == (-1.5, 2.25, -3.75)

    def test_a_quad_face_is_triangulated_on_load(self, write_obj):
        path = write_obj("v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3 4\n")
        mesh = Object3D().load(path)
        assert mesh.faces == [[0, 1, 2], [0, 2, 3]]

    def test_ignores_texture_and_normal_indices(self, write_obj):
        path = write_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1/1/1 2/2/2 3/3/3\n")
        mesh = Object3D().load(path)
        assert mesh.faces == [[0, 1, 2]]

    def test_handles_faces_with_no_texture_index(self, write_obj):
        path = write_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1//1 2//2 3//3\n")
        mesh = Object3D().load(path)
        assert mesh.faces == [[0, 1, 2]]

    def test_skips_comments_blank_lines_and_unknown_directives(self, write_obj):
        path = write_obj(
            "# a comment\n"
            "\n"
            "o some_object\n"
            "v 0 0 0\n"
            "vt 0.5 0.5\n"
            "vn 0 0 1\n"
            "s off\n"
            "usemtl material\n"
            "v 1 0 0\n"
            "v 0 1 0\n"
            "f 1 2 3\n"
        )
        mesh = Object3D().load(path)
        assert len(mesh.vertices) == 3
        assert mesh.faces == [[0, 1, 2]]

    def test_tolerates_extra_whitespace(self, write_obj):
        path = write_obj("v   0   0   0\nv  1  0  0\nv 0  1   0\nf   1   2   3\n")
        mesh = Object3D().load(path)
        assert len(mesh.vertices) == 3
        assert mesh.faces == [[0, 1, 2]]

    def test_tolerates_windows_line_endings(self, tmp_path):
        path = tmp_path / "crlf.obj"
        path.write_bytes(b"v 0 0 0\r\nv 1 0 0\r\nv 0 1 0\r\nf 1 2 3\r\n")
        mesh = Object3D().load(str(path))
        assert len(mesh.vertices) == 3
        assert mesh.faces == [[0, 1, 2]]

    def test_ignores_a_fourth_vertex_component(self, write_obj):
        # some exporters write "v x y z w" or "v x y z r g b"
        path = write_obj("v 1 2 3 1.0\n")
        mesh = Object3D().load(path)
        v = mesh.vertices[0]
        assert (v.x, v.y, v.z) == (1.0, 2.0, 3.0)

    def test_load_returns_self_so_it_can_be_chained(self, write_obj):
        mesh = Object3D()
        assert mesh.load(write_obj("v 0 0 0\n")) is mesh

    def test_an_empty_file_yields_an_empty_mesh(self, write_obj):
        mesh = Object3D().load(write_obj(""))
        assert mesh.vertices == [] and mesh.faces == []


class TestRealModel:
    """Sanity check against a mesh that actually ships with the repository."""

    def test_banana_has_the_expected_size(self, banana):
        assert len(banana.vertices) == 308
        assert len(banana.faces) == 612

    def test_every_face_is_a_triangle(self, banana):
        assert all(len(face) == 3 for face in banana.faces)

    def test_every_face_index_is_in_range(self, banana):
        limit = len(banana.vertices)
        assert all(0 <= i < limit for face in banana.faces for i in face)
