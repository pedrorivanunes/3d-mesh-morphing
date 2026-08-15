"""3D morphing between two objects through face matching and linear interpolation.

Opens three windows: the source object, the target object and the morph window.

Controls (in any window):
    W / S        rotate the object around X
    A / D        rotate the object around Y
    I / J / K / L move the camera (up / left / down / right)
    O / P        zoom in / out (field of view)

Only in the MORPH window:
    1            pick object 1 as the source (target = object 2)
    2            pick object 2 as the source (target = object 1)
    SPACE        start the morph animation
    M            cycle the leftover-face mode
                 (neighbor -> random -> collapse), re-animating right away
"""

import os
import sys

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

from object3d import Object3D

# --------------------------------------------------------------------- config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Menu of available objects (name -> .obj file). Change MODEL_1 / MODEL_2 to
# morph other pairs. The "hard" models have many faces and make the matching
# slow (see "Known limitations" in the README).
MODELS = {
    "banana": "models/easy1.obj",
    "tree":   "models/easy2.obj",
    "animal": "models/easy3.obj",
    "car":    "models/hard1.obj",
    "castle": "models/hard2.obj",
    "human":  "models/hard3.obj",
}

COLORS = {
    "banana": (1.000, 0.843, 0.000),
    "tree":   (0.000, 0.392, 0.000),
    "animal": (0.627, 0.322, 0.176),
    "car":    (0.863, 0.078, 0.235),
    "castle": (0.282, 0.239, 0.545),
    "human":  (0.737, 0.561, 0.561),
}

# default pair (light -> animates instantly, good for screenshots/gifs)
MODEL_1 = "banana"
MODEL_2 = "animal"

MORPH_FRAMES = 150          # frames in the animation
INTERVAL_MS = 16            # ~60 frames per second

# How to handle the leftover faces when the objects have different polygon
# counts (switch live with the M key):
#   "neighbor" -> leftovers go to the closest face (local collapses; default)
#   "collapse" -> all on the same face (collapse into a single point; exposes the limitation)
#   "random"   -> random faces (chaotic; shows why the correspondence matters)
MODES = ["neighbor", "random", "collapse"]
INITIAL_MODE = "neighbor"

# Mesh appearance. Tune it per model: objects with many polygons (the "hard*"
# ones) look cleaner with thin edges (e.g. 0.5) and smaller dots; light objects
# look fine with larger values.
EDGE_WIDTH = 0.5            # wireframe thickness
VERTEX_SIZE = 0.5           # size of the dots on the vertices

# ---------------------------------------------------------------------- state
obj1 = obj2 = None
color1 = color2 = (1, 1, 1)

# morph window state
morph_source = None
morph_target = None
morph_color_source = (1, 1, 1)   # color at the start of the animation (t = 0)
morph_color_target = (1, 1, 1)   # color at the end of the animation (t = 1)
morph_pairs = None
morph_frame = 0
morph_animating = False
morph_started = False
morph_ang_x = 0.0
morph_ang_y = 0.0
leftover_mode = INITIAL_MODE


class Camera:
    """Fixed orbit camera looking at the origin."""

    def __init__(self, position, fov):
        self.position = list(position)
        self.fov = fov

    def apply(self):
        width = glutGet(GLUT_WINDOW_WIDTH)
        height = glutGet(GLUT_WINDOW_HEIGHT) or 1
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.fov, width / height, 0.01, 50)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(self.position[0], self.position[1], self.position[2],
                  0, 0, 0, 0, 1, 0)


cam1 = Camera([3.0, 1.5, 3.0], 30)
cam2 = Camera([3.0, 1.5, 3.0], 30)
cam3 = Camera([3.0, 1.5, 3.0], 30)


# ------------------------------------------------------------------ GL setup
def setup_light():
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
    glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
    glLightfv(GL_LIGHT0, GL_SPECULAR, [0.9, 0.9, 0.9, 1.0])
    glLightfv(GL_LIGHT0, GL_POSITION, [5.0, 5.0, 5.0, 1.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.5, 0.5, 0.5, 1.0])
    glMateriali(GL_FRONT_AND_BACK, GL_SHININESS, 40)


def setup_gl():
    """Configure the GL context of the active window (called per window)."""
    glClearColor(0.12, 0.12, 0.15, 1.0)
    glClearDepth(1.0)
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    # push the filled faces slightly back so the wireframe and the vertices
    # show up crisply on top (avoids z-fighting)
    glEnable(GL_POLYGON_OFFSET_FILL)
    glPolygonOffset(1.0, 1.0)
    setup_light()


# -------------------------------------------------------------------- scenery
def draw_tile():
    glColor3f(0.5, 0.5, 0.5)
    glNormal3f(0, 1, 0)
    glBegin(GL_QUADS)
    glVertex3f(-0.5, 0.0, -0.5)
    glVertex3f(-0.5, 0.0, 0.5)
    glVertex3f(0.5, 0.0, 0.5)
    glVertex3f(0.5, 0.0, -0.5)
    glEnd()

    glDisable(GL_LIGHTING)
    glColor3f(0.8, 0.8, 0.8)
    glBegin(GL_LINE_LOOP)
    glVertex3f(-0.5, 0.0, -0.5)
    glVertex3f(-0.5, 0.0, 0.5)
    glVertex3f(0.5, 0.0, 0.5)
    glVertex3f(0.5, 0.0, -0.5)
    glEnd()
    glEnable(GL_LIGHTING)


def draw_floor():
    glPushMatrix()
    glTranslated(-20, -1, -10)
    for _ in range(-20, 20):
        glPushMatrix()
        for _ in range(-20, 20):
            draw_tile()
            glTranslated(0, 0, 1)
        glPopMatrix()
        glTranslated(1, 0, 0)
    glPopMatrix()


# --------------------------------------------------------------- GL callbacks
def draw_window1():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    cam1.apply()
    draw_floor()
    obj1.draw(*color1)
    glutSwapBuffers()


def draw_window2():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    cam2.apply()
    draw_floor()
    obj2.draw(*color2)
    glutSwapBuffers()


def draw_morph():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    cam3.apply()
    draw_floor()

    glPushMatrix()
    glRotatef(morph_ang_x, 1, 0, 0)
    glRotatef(morph_ang_y, 0, 1, 0)
    if morph_started and morph_pairs is not None:
        t = min(morph_frame / MORPH_FRAMES, 1.0)
        # the color is interpolated too: source (t=0) -> target (t=1)
        r = (1 - t) * morph_color_source[0] + t * morph_color_target[0]
        g = (1 - t) * morph_color_source[1] + t * morph_color_target[1]
        b = (1 - t) * morph_color_source[2] + t * morph_color_target[2]
        morph_source.emit_morph(morph_target, morph_pairs, t, r, g, b)
    elif morph_source is not None:
        # before starting: show the source object static, with its own color
        morph_source.emit_static(*morph_color_source)
    glPopMatrix()

    glutSwapBuffers()


def reshape(width, height):
    glViewport(0, 0, width, max(height, 1))


def morph_step(_):
    """Advance one animation frame via timer (does not block the event loop)."""
    global morph_frame, morph_animating
    if not morph_animating:
        return
    if morph_frame < MORPH_FRAMES:
        morph_frame += 1
        glutPostRedisplay()
        glutTimerFunc(INTERVAL_MS, morph_step, 0)
    else:
        morph_animating = False         # done: keep the last frame on screen
        glutPostRedisplay()


# ------------------------------------------------------------------- keyboard
def _camera_control(key, cam):
    if key == b'i':
        cam.position[1] += 0.5
    elif key == b'k':
        cam.position[1] -= 0.5
    elif key == b'j':
        cam.position[0] -= 0.5
    elif key == b'l':
        cam.position[0] += 0.5
    elif key == b'o':
        cam.fov = max(cam.fov - 1, 5)
    elif key == b'p':
        cam.fov = min(cam.fov + 1, 100)


def keyboard1(key, x, y):
    if key == b'w':
        obj1.ang_x += 2
    elif key == b's':
        obj1.ang_x -= 2
    elif key == b'a':
        obj1.ang_y += 2
    elif key == b'd':
        obj1.ang_y -= 2
    else:
        _camera_control(key, cam1)
    glutPostRedisplay()


def keyboard2(key, x, y):
    if key == b'w':
        obj2.ang_x += 2
    elif key == b's':
        obj2.ang_x -= 2
    elif key == b'a':
        obj2.ang_y += 2
    elif key == b'd':
        obj2.ang_y -= 2
    else:
        _camera_control(key, cam2)
    glutPostRedisplay()


def keyboard3(key, x, y):
    global morph_ang_x, morph_ang_y
    if key == b'w':
        morph_ang_x += 2
    elif key == b's':
        morph_ang_x -= 2
    elif key == b'a':
        morph_ang_y += 2
    elif key == b'd':
        morph_ang_y -= 2
    elif key == b'1':
        _select_source(1)
    elif key == b'2':
        _select_source(2)
    elif key == b' ':
        _start_morph()
    elif key == b'm':
        _cycle_mode()
    else:
        _camera_control(key, cam3)
    glutPostRedisplay()


def _select_source(choice):
    global morph_source, morph_target, morph_color_source, morph_color_target
    global morph_started, morph_animating, morph_frame, morph_pairs
    if choice == 1:
        morph_source, morph_target = obj1, obj2
        morph_color_source, morph_color_target = color1, color2
    else:
        morph_source, morph_target = obj2, obj1
        morph_color_source, morph_color_target = color2, color1
    morph_started = False
    morph_animating = False
    morph_frame = 0
    morph_pairs = None
    print(f"[morph] object {choice} selected -- press SPACE to animate.")


def _start_morph():
    global morph_pairs, morph_frame, morph_animating, morph_started
    if morph_source is None:
        print("[morph] pick 1 or 2 before starting.")
        return
    if morph_animating:
        return
    print(f"[morph] computing the face matching (mode: {leftover_mode})...")
    morph_pairs = morph_source.match_faces(morph_target, leftover_mode)
    morph_frame = 0
    morph_started = True
    morph_animating = True
    glutTimerFunc(INTERVAL_MS, morph_step, 0)
    print(f"[morph] animating ({len(morph_pairs)} face pairs).")


def _cycle_mode():
    global leftover_mode, morph_animating
    leftover_mode = MODES[(MODES.index(leftover_mode) + 1) % len(MODES)]
    print(f"[morph] leftover-face mode: {leftover_mode}")
    if morph_source is not None:
        morph_animating = False         # allows recomputing and re-animating on the spot
        _start_morph()


# ----------------------------------------------------------------------- boot
def load_models():
    global obj1, obj2, color1, color2
    path1 = os.path.join(BASE_DIR, MODELS[MODEL_1])
    path2 = os.path.join(BASE_DIR, MODELS[MODEL_2])
    obj1 = Object3D().load(path1)
    obj1.normalize()
    obj1.color = COLORS[MODEL_1]
    obj2 = Object3D().load(path2)
    obj2.normalize()
    obj2.color = COLORS[MODEL_2]
    for obj in (obj1, obj2):
        obj.edge_width = EDGE_WIDTH
        obj.vertex_size = VERTEX_SIZE
    color1 = COLORS[MODEL_1]
    color2 = COLORS[MODEL_2]


def _create_window(title, position, display_func, keyboard_func):
    glutInitWindowPosition(*position)
    glutCreateWindow(title)
    glutDisplayFunc(display_func)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard_func)
    setup_gl()


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_RGBA | GLUT_DEPTH | GLUT_DOUBLE)
    glutInitWindowSize(500, 500)

    load_models()

    _create_window("Morph 3D - Object 1 (source)", (100, 120), draw_window1, keyboard1)
    _create_window("Morph 3D - Object 2 (target)", (640, 120), draw_window2, keyboard2)
    _create_window("Morph 3D - Result", (1180, 120), draw_morph, keyboard3)

    print(__doc__)
    glutMainLoop()


if __name__ == "__main__":
    main()
