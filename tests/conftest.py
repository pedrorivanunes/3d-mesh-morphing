"""Shared fixtures.

The geometry tests need no OpenGL context at all: importing `OpenGL.GL` only
binds the library, it never opens a window. The single test that does need a
real context asks for the `glut` fixture, which skips itself when no display
is available.
"""

import os

import pytest

from helpers import MODELS_DIR, make_mesh
from object3d import Object3D


@pytest.fixture
def write_obj(tmp_path):
    """Write an .obj file with the given text and return its path."""

    def _write(text, name="mesh.obj"):
        path = tmp_path / name
        path.write_text(text)
        return str(path)

    return _write


@pytest.fixture
def tetrahedron():
    """Four vertices, four faces, all centroids distinct."""
    return make_mesh(
        vertices=[(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)],
        faces=[[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]],
    )


@pytest.fixture
def two_triangles():
    """Two triangles far apart on the X axis, so nearest-neighbour is obvious."""
    return make_mesh(
        vertices=[(0, 0, 0), (1, 0, 0), (0, 1, 0), (10, 0, 0), (11, 0, 0), (10, 1, 0)],
        faces=[[0, 1, 2], [3, 4, 5]],
    )


@pytest.fixture
def banana():
    """A real mesh from the repository (612 faces), used as a sanity fixture."""
    return Object3D().load(os.path.join(MODELS_DIR, "easy1.obj"))


@pytest.fixture(scope="session")
def glut():
    """Initialise GLUT once per session, or skip when there is no display.

    On Linux this needs an X server; CI provides one through xvfb-run. On
    Windows and macOS the system display is always there.
    """
    if os.name == "posix" and not os.environ.get("DISPLAY"):
        pytest.skip("no X display available (run under xvfb-run to exercise the GL path)")
    try:
        from OpenGL.GLUT import glutInit

        # a bytes argv keeps pytest's own command line out of GLUT's parser
        # (and PyOpenGL rejects a list of str here)
        glutInit([b"morph-3d-tests"])
    except Exception as exc:  # pragma: no cover - depends on the machine
        pytest.skip(f"GLUT could not be initialised: {exc}")
    return True
