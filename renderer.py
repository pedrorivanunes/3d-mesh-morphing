"""Drawing a Mesh with OpenGL.

Everything that touches the graphics API lives here, and nothing here computes
geometry -- the numbers all come from `mesh.py`. Importing this module needs
the OpenGL library installed; importing `mesh` does not, which is what lets the
geometry tests run on a machine with no graphics stack at all.

The mesh carries its own placement (`position`, `ang_x`, `ang_y`) and
appearance (`color`, `edge_width`, `vertex_size`); these functions only read
them.
"""

from OpenGL.GL import (
    GL_LIGHTING,
    GL_LINE_LOOP,
    GL_POINTS,
    GL_TRIANGLES,
    glBegin,
    glColor3f,
    glDisable,
    glEnable,
    glEnd,
    glLineWidth,
    glNormal3f,
    glPointSize,
    glPopMatrix,
    glPushMatrix,
    glRotatef,
    glTranslatef,
    glVertex3f,
)

from mesh import triangle_normal


def _apply_transform(mesh):
    glTranslatef(mesh.position.x, mesh.position.y, mesh.position.z)
    glRotatef(mesh.ang_x, 1, 0, 0)
    glRotatef(mesh.ang_y, 0, 1, 0)


def draw(mesh, r=None, g=None, b=None):
    """Solid (lit) faces + wireframe + vertices, with the mesh transform applied."""
    if r is None:
        r, g, b = mesh.color
    glPushMatrix()
    _apply_transform(mesh)
    emit_static(mesh, r, g, b)
    glPopMatrix()


def emit_static(mesh, r, g, b):
    """Emit the geometry without applying a transform or push/pop.
    The caller owns the model matrix (used by the morph window)."""
    _emit_solid(mesh, r, g, b)
    _emit_wireframe(mesh)
    _emit_vertices(mesh)
    glEnable(GL_LIGHTING)


def _emit_solid(mesh, r, g, b):
    glEnable(GL_LIGHTING)
    glColor3f(r, g, b)
    glBegin(GL_TRIANGLES)
    for face in mesh.faces:
        p0, p1, p2 = (mesh.vertices[i] for i in face)
        glNormal3f(*triangle_normal(p0, p1, p2))
        for idx in face:
            v = mesh.vertices[idx]
            glVertex3f(v.x, v.y, v.z)
    glEnd()


def _emit_wireframe(mesh):
    glDisable(GL_LIGHTING)
    glColor3f(0, 0, 0)
    glLineWidth(mesh.edge_width)
    for face in mesh.faces:
        glBegin(GL_LINE_LOOP)
        for idx in face:
            v = mesh.vertices[idx]
            glVertex3f(v.x, v.y, v.z)
        glEnd()


def _emit_vertices(mesh):
    glDisable(GL_LIGHTING)
    glColor3f(0, 0, 0)
    glPointSize(mesh.vertex_size)
    glBegin(GL_POINTS)
    for v in mesh.vertices:
        glVertex3f(v.x, v.y, v.z)
    glEnd()


def emit_morph(mesh, other, pairs, t, r, g, b):
    """Draw a single morph frame (no push/pop and no transform; the caller
    owns the model matrix). `t` goes from 0 (`mesh`) to 1 (`other`)."""
    # interpolate each triangle once and reuse it across the three passes
    triangles = mesh.interpolate(other, pairs, t)

    glEnable(GL_LIGHTING)
    glColor3f(r, g, b)
    glBegin(GL_TRIANGLES)
    for tri in triangles:
        glNormal3f(*triangle_normal(*tri))
        for v in tri:
            glVertex3f(v.x, v.y, v.z)
    glEnd()

    glDisable(GL_LIGHTING)
    glColor3f(0, 0, 0)
    glLineWidth(mesh.edge_width)
    for tri in triangles:
        glBegin(GL_LINE_LOOP)
        for v in tri:
            glVertex3f(v.x, v.y, v.z)
        glEnd()

    glPointSize(mesh.vertex_size)
    glBegin(GL_POINTS)
    for tri in triangles:
        for v in tri:
            glVertex3f(v.x, v.y, v.z)
    glEnd()
    glEnable(GL_LIGHTING)
