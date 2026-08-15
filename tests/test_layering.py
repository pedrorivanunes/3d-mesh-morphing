"""The geometry layer must not depend on OpenGL.

This is an architectural invariant rather than a behavioural one, and it is the
invariant that broke CI twice: while importing the geometry pulled in the
OpenGL binding, testing a centroid needed a graphics stack that has nothing to
do with what the test checks.

Checking it needs a fresh interpreter, because by the time this test runs the
real OpenGL is already imported and cached in sys.modules. So a subprocess
blocks OpenGL through sys.meta_path and exercises the geometry there.
"""

import subprocess
import sys
import textwrap

from helpers import PROJECT_ROOT

BLOCK_AND_USE_GEOMETRY = textwrap.dedent(
    """
    import importlib.abc
    import sys

    class BlockOpenGL(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname == "OpenGL" or fullname.startswith("OpenGL."):
                raise ImportError("OpenGL is blocked for this check: " + fullname)
            return None

    sys.meta_path.insert(0, BlockOpenGL())

    from mesh import Mesh
    from point import Point

    mesh = Mesh()
    mesh.vertices = [Point(0, 0, 0), Point(1, 0, 0), Point(0, 1, 0)]
    mesh.faces = [[0, 1, 2]]
    mesh.normalize()
    pairs = mesh.match_faces(mesh)
    frame = mesh.interpolate(mesh, pairs, 0.5)
    assert len(frame) == 1 and len(frame[0]) == 3

    assert "OpenGL" not in sys.modules, "the geometry pulled OpenGL in"
    print("geometry ran with no OpenGL")
    """
)


def run_without_opengl(script):
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


def test_the_geometry_runs_with_opengl_unavailable():
    result = run_without_opengl(BLOCK_AND_USE_GEOMETRY)
    assert result.returncode == 0, f"geometry needs OpenGL now:\n{result.stderr}"
    assert "geometry ran with no OpenGL" in result.stdout


def test_the_renderer_is_the_module_that_needs_opengl():
    """The mirror image: renderer must fail without OpenGL.

    If this ever passes, the GL calls have leaked out of renderer.py and the
    check above stops meaning anything.
    """
    script = BLOCK_AND_USE_GEOMETRY.replace(
        'print("geometry ran with no OpenGL")',
        "import renderer",
    )
    assert run_without_opengl(script).returncode != 0
