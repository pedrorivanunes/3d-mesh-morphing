"""End-to-end test of the real OpenGL path, rendered off-screen.

Everything else in this suite is pure geometry and needs no graphics driver.
This module is the exception: it opens an actual GL context, runs the same
`emit_morph` the application calls every frame, and reads the framebuffer back
to check that something was really drawn.

It needs a display. On Linux CI that comes from Xvfb (a virtual X server) with
Mesa's software renderer, so no GPU is involved; the `glut` fixture skips the
whole module when neither is available.
"""

import pytest

from helpers import make_mesh

# `-m "not gl"` deselects these tests, but pytest still *collects* the module,
# and collecting it imports renderer, which imports OpenGL. On a machine with
# no GL library that import is what fails, so skip the module outright rather
# than letting collection blow up. (pytest.importorskip is not the tool here:
# since 8.2 it re-raises when the ImportError names a nested dependency rather
# than the requested module, which is exactly this case.)
try:
    import renderer
except ImportError:  # pragma: no cover - depends on the machine
    pytest.skip("needs the OpenGL library", allow_module_level=True)

pytestmark = pytest.mark.gl

SIZE = 64
CLEAR_COLOR = (0.12, 0.12, 0.15, 1.0)


@pytest.fixture
def window(glut):
    """A small off-screen GL window, torn down after the test."""
    from OpenGL.GL import GL_DEPTH_TEST, glClearColor, glEnable, glViewport
    from OpenGL.GLUT import (
        GLUT_DEPTH,
        GLUT_RGBA,
        GLUT_SINGLE,
        glutCreateWindow,
        glutDestroyWindow,
        glutInitDisplayMode,
        glutInitWindowSize,
    )

    # single-buffered so the pixels can be read straight back without a swap
    glutInitDisplayMode(GLUT_RGBA | GLUT_DEPTH | GLUT_SINGLE)
    glutInitWindowSize(SIZE, SIZE)
    handle = glutCreateWindow(b"morph-3d test")
    glViewport(0, 0, SIZE, SIZE)
    glClearColor(*CLEAR_COLOR)
    glEnable(GL_DEPTH_TEST)
    yield handle
    glutDestroyWindow(handle)


def read_framebuffer():
    """Read the colour buffer back as plain RGB bytes.

    This calls the *raw* glReadPixels with a ctypes buffer instead of the
    friendly wrapper. The wrapper allocates the destination through PyOpenGL's
    array plugins, which drags numpy (and PyOpenGL-accelerate) into the test;
    going raw keeps this independent of whatever numpy build is installed.
    """
    import ctypes

    from OpenGL.GL import GL_RGB, GL_UNSIGNED_BYTE
    from OpenGL.raw.GL.VERSION.GL_1_0 import glReadPixels as raw_read_pixels

    buffer = (ctypes.c_ubyte * (SIZE * SIZE * 3))()
    raw_read_pixels(0, 0, SIZE, SIZE, GL_RGB, GL_UNSIGNED_BYTE, buffer)
    return bytes(buffer)


def render(draw):
    """Clear, run `draw`, and return the framebuffer as raw RGB bytes."""
    from OpenGL.GL import (
        GL_COLOR_BUFFER_BIT,
        GL_DEPTH_BUFFER_BIT,
        GL_MODELVIEW,
        GL_PROJECTION,
        glClear,
        glFinish,
        glLoadIdentity,
        glMatrixMode,
    )
    from OpenGL.GLU import gluLookAt, gluPerspective

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, 1.0, 0.01, 50)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(0, 0, 3, 0, 0, 0, 0, 1, 0)

    draw()

    glFinish()
    return read_framebuffer()


def background_byte():
    return round(CLEAR_COLOR[0] * 255)


def drawn_pixel_count(pixels):
    """How many pixels differ from the clear color."""
    bg = background_byte()
    return sum(
        1
        for i in range(0, len(pixels), 3)
        if abs(pixels[i] - bg) > 8
        or abs(pixels[i + 1] - bg) > 8
        or abs(pixels[i + 2] - round(CLEAR_COLOR[2] * 255)) > 8
    )


@pytest.fixture
def quad():
    """A flat square facing the camera, large enough to cover many pixels."""
    return make_mesh(
        [(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0)],
        [[0, 1, 2], [0, 2, 3]],
    )


@pytest.fixture
def tall_quad():
    """The same square, stretched, so a morph between the two is visible."""
    return make_mesh(
        [(-0.1, -0.9, 0), (0.1, -0.9, 0), (0.1, 0.9, 0), (-0.1, 0.9, 0)],
        [[0, 1, 2], [0, 2, 3]],
    )


class TestContext:
    def test_an_empty_scene_is_all_background(self, window):
        pixels = render(lambda: None)
        assert len(pixels) == SIZE * SIZE * 3
        assert drawn_pixel_count(pixels) == 0


class TestStaticRendering:
    def test_a_mesh_actually_puts_pixels_on_the_screen(self, window, quad):
        pixels = render(lambda: renderer.emit_static(quad, 1.0, 0.0, 0.0))
        assert drawn_pixel_count(pixels) > 100

    def test_draw_falls_back_to_the_object_color(self, window, quad):
        quad.color = (1.0, 0.0, 0.0)
        explicit = render(lambda: renderer.draw(quad, 1.0, 0.0, 0.0))
        implicit = render(lambda: renderer.draw(quad))
        assert implicit == explicit

    def test_draw_applies_the_object_transform(self, window, quad):
        centered = render(lambda: renderer.draw(quad, 1.0, 0.0, 0.0))
        quad.position.x = 5.0
        moved = render(lambda: renderer.draw(quad, 1.0, 0.0, 0.0))
        # pushed far to the right, the quad leaves the frustum
        assert drawn_pixel_count(centered) > drawn_pixel_count(moved)


class TestMorphRendering:
    """The whole pipeline: match faces, interpolate, draw the frame."""

    def test_a_morph_frame_renders(self, window, quad, tall_quad):
        pairs = quad.match_faces(tall_quad, "neighbor")
        pixels = render(lambda: renderer.emit_morph(quad, tall_quad, pairs, 0.5, 1.0, 0.0, 0.0))
        assert drawn_pixel_count(pixels) > 100

    def test_the_start_and_end_of_a_morph_look_different(self, window, quad, tall_quad):
        pairs = quad.match_faces(tall_quad, "neighbor")
        start = render(lambda: renderer.emit_morph(quad, tall_quad, pairs, 0.0, 1.0, 0.0, 0.0))
        end = render(lambda: renderer.emit_morph(quad, tall_quad, pairs, 1.0, 1.0, 0.0, 0.0))
        assert start != end

    def test_t_zero_renders_the_same_as_the_source_mesh(self, window, quad, tall_quad):
        pairs = quad.match_faces(tall_quad, "neighbor")
        morph_at_zero = render(
            lambda: renderer.emit_morph(quad, tall_quad, pairs, 0.0, 1.0, 0.0, 0.0)
        )
        static = render(lambda: renderer.emit_static(quad, 1.0, 0.0, 0.0))
        assert morph_at_zero == static

    @pytest.mark.parametrize("mode", ["neighbor", "random", "collapse"])
    def test_every_mode_produces_a_drawable_frame(self, window, quad, tall_quad, mode):
        pairs = quad.match_faces(tall_quad, mode)
        pixels = render(lambda: renderer.emit_morph(quad, tall_quad, pairs, 0.5, 0.0, 1.0, 0.0))
        assert drawn_pixel_count(pixels) > 0
