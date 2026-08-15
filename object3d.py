"""3D object loaded from an .obj file, with morphing support.

Morphing happens in two steps:
  1. `match_faces`: pairs every face of this object with the closest face of
     the target object (nearest neighbour by centroid);
  2. `emit_morph`: linearly interpolates the vertices of the paired faces
     according to a parameter t in [0, 1].
"""

from math import inf, sqrt
from random import choice

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

from point import Point


def _nearest_index(centroid, centroids):
    """Index of the nearest centroid (squared distance; no sqrt)."""
    best_i, smallest = 0, inf
    for i, c in enumerate(centroids):
        d = (centroid.x - c.x) ** 2 + (centroid.y - c.y) ** 2 + (centroid.z - c.z) ** 2
        if d < smallest:
            smallest, best_i = d, i
    return best_i


def _triangle_normal(p0, p1, p2):
    """Unit normal of a triangle (used for flat shading)."""
    ux, uy, uz = p1.x - p0.x, p1.y - p0.y, p1.z - p0.z
    vx, vy, vz = p2.x - p0.x, p2.y - p0.y, p2.z - p0.z
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    length = sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / length, ny / length, nz / length


class Object3D:
    def __init__(self):
        self.vertices = []      # list of Point
        self.faces = []         # list of triangles: each one is [i0, i1, i2]
        self.position = Point(0, 0, 0)
        self.ang_x = 0.0        # accumulated rotation around X
        self.ang_y = 0.0        # accumulated rotation around Y
        self.color = (1.0, 1.0, 1.0)
        self.edge_width = 1.5   # wireframe thickness (glLineWidth)
        self.vertex_size = 4.0  # size of the vertex dots (glPointSize)

    # ------------------------------------------------------------------ loading
    def load(self, path):
        """Read an .obj file, triangulating any face with more than 3 vertices.

        Uses `split()` (any whitespace), which tolerates double spaces and
        Windows line endings.
        """
        with open(path) as file:
            for line in file:
                tokens = line.split()
                if not tokens:
                    continue
                if tokens[0] == "v":
                    x, y, z = (float(t) for t in tokens[1:4])
                    self.vertices.append(Point(x, y, z))
                elif tokens[0] == "f":
                    # ignore texture/normal indices (the "v/vt/vn" format)
                    indices = [int(t.split("/")[0]) - 1 for t in tokens[1:]]
                    self.faces.extend(self._triangulate(indices))
        return self

    @staticmethod
    def _triangulate(face):
        """Fan triangulation: [a, b, c, d, ...] -> [[a,b,c], [a,c,d], ...]."""
        return [[face[0], face[i], face[i + 1]] for i in range(1, len(face) - 1)]

    def normalize(self):
        """Center at the origin and scale to fit inside a unit cube.

        Must be called ONCE, right after loading -- never inside the draw
        loop, so the vertices are not mutated on every frame.
        """
        if not self.vertices:
            return
        xs = [v.x for v in self.vertices]
        ys = [v.y for v in self.vertices]
        zs = [v.z for v in self.vertices]
        cx, cy, cz = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2
        span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) or 1.0
        for v in self.vertices:
            v.x = (v.x - cx) / span
            v.y = (v.y - cy) / span
            v.z = (v.z - cz) / span

    # ------------------------------------------------------------------ drawing
    def _apply_transform(self):
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glRotatef(self.ang_x, 1, 0, 0)
        glRotatef(self.ang_y, 0, 1, 0)

    def draw(self, r=None, g=None, b=None):
        """Solid (lit) faces + wireframe + vertices, already transformed."""
        if r is None:
            r, g, b = self.color
        glPushMatrix()
        self._apply_transform()
        self.emit_static(r, g, b)
        glPopMatrix()

    def emit_static(self, r, g, b):
        """Emit the geometry without applying a transform or push/pop.
        The caller owns the model matrix (used by the morph window)."""
        self._emit_solid(r, g, b)
        self._emit_wireframe()
        self._emit_vertices()
        glEnable(GL_LIGHTING)

    def _emit_solid(self, r, g, b):
        glEnable(GL_LIGHTING)
        glColor3f(r, g, b)
        glBegin(GL_TRIANGLES)
        for face in self.faces:
            p0, p1, p2 = (self.vertices[i] for i in face)
            glNormal3f(*_triangle_normal(p0, p1, p2))
            for idx in face:
                v = self.vertices[idx]
                glVertex3f(v.x, v.y, v.z)
        glEnd()

    def _emit_wireframe(self):
        glDisable(GL_LIGHTING)
        glColor3f(0, 0, 0)
        glLineWidth(self.edge_width)
        for face in self.faces:
            glBegin(GL_LINE_LOOP)
            for idx in face:
                v = self.vertices[idx]
                glVertex3f(v.x, v.y, v.z)
            glEnd()

    def _emit_vertices(self):
        glDisable(GL_LIGHTING)
        glColor3f(0, 0, 0)
        glPointSize(self.vertex_size)
        glBegin(GL_POINTS)
        for v in self.vertices:
            glVertex3f(v.x, v.y, v.z)
        glEnd()

    # -------------------------------------------------------------------- morph
    def _centroid(self, face):
        cx = cy = cz = 0.0
        for idx in face:
            v = self.vertices[idx]
            cx += v.x
            cy += v.y
            cz += v.z
        n = len(face)
        return Point(cx / n, cy / n, cz / n)

    def match_faces(self, other, mode="neighbor"):
        """Pair every face of this object with a face of `other`.

        Phase 1 (the same for every mode): greedy one-to-one pairing by
        nearest centroid, without reusing faces while free ones remain.

        Phase 2: when the objects have different face counts, some faces are
        left without a partner. `mode` decides what happens to them:
          - "collapse": all of them go to the SAME face of the other object.
                        This is the original behaviour; it produces the
                        collapse into a single point (useful to demonstrate
                        the limitation).
          - "neighbor": each leftover goes to the CLOSEST face of the other
                        object (repetition allowed). The collapses stay local
                        and spread across the surface -- much nicer to watch.
          - "random":   each leftover goes to a random face. Deliberately
                        chaotic, showing why the correspondence matters.

        Complexity O(n1 * n2): the centroids are precomputed, but the cost is
        still quadratic (see "Known limitations" in the README).
        """
        self_centroids = [self._centroid(f) for f in self.faces]
        other_centroids = [other._centroid(f) for f in other.faces]

        pairs = []
        used = set()
        unpaired = []

        # phase 1: greedy one-to-one (injective) pairing by nearest centroid
        for face1, c1 in zip(self.faces, self_centroids):
            best_i, smallest = None, inf
            for i, c2 in enumerate(other_centroids):
                if i in used:
                    continue
                d = (c1.x - c2.x) ** 2 + (c1.y - c2.y) ** 2 + (c1.z - c2.z) ** 2
                if d < smallest:
                    smallest, best_i = d, i
            if best_i is None:                      # no free faces left
                unpaired.append((face1, c1))
            else:
                used.add(best_i)
                pairs.append((face1, other.faces[best_i]))

        other_remaining = [i for i in range(len(other.faces)) if i not in used]

        # phase 2a: self has leftover faces -> pick a face from `other`
        for face1, c1 in unpaired:
            if mode == "neighbor":
                face2 = other.faces[_nearest_index(c1, other_centroids)]
            elif mode == "random":
                face2 = choice(other.faces)
            else:  # collapse
                face2 = other.faces[other_remaining.pop()] if other_remaining else pairs[-1][1]
            pairs.append((face1, face2))

        # phase 2b: other has leftover faces -> pick a face from `self`
        for i in other_remaining:
            face2 = other.faces[i]
            if mode == "neighbor":
                face1 = self.faces[_nearest_index(other_centroids[i], self_centroids)]
            elif mode == "random":
                face1 = choice(self.faces)
            else:  # collapse
                face1 = pairs[-1][0] if pairs else self.faces[0]
            pairs.append((face1, face2))

        return pairs

    def interpolate(self, other, pairs, t):
        """Geometry of a single morph frame: one triangle per pair of faces.

        Every vertex is a linear interpolation between this object and `other`:

            v(t) = (1 - t) * v_self + t * v_other

        so t = 0 reproduces this object exactly and t = 1 reproduces `other`.
        Pure geometry, no OpenGL -- `emit_morph` is what draws the result.
        """
        return [
            [
                Point(
                    (1 - t) * self.vertices[i].x + t * other.vertices[j].x,
                    (1 - t) * self.vertices[i].y + t * other.vertices[j].y,
                    (1 - t) * self.vertices[i].z + t * other.vertices[j].z,
                )
                for i, j in zip(face1, face2)
            ]
            for face1, face2 in pairs
        ]

    def emit_morph(self, other, pairs, t, r, g, b):
        """Draw a single morph frame (no push/pop and no transform; the caller
        owns the model matrix). `t` goes from 0 (this object) to 1 (`other`)."""
        # interpolate each triangle once and reuse it across the three passes
        triangles = self.interpolate(other, pairs, t)

        glEnable(GL_LIGHTING)
        glColor3f(r, g, b)
        glBegin(GL_TRIANGLES)
        for tri in triangles:
            glNormal3f(*_triangle_normal(*tri))
            for v in tri:
                glVertex3f(v.x, v.y, v.z)
        glEnd()

        glDisable(GL_LIGHTING)
        glColor3f(0, 0, 0)
        glLineWidth(self.edge_width)
        for tri in triangles:
            glBegin(GL_LINE_LOOP)
            for v in tri:
                glVertex3f(v.x, v.y, v.z)
            glEnd()

        glPointSize(self.vertex_size)
        glBegin(GL_POINTS)
        for tri in triangles:
            for v in tri:
                glVertex3f(v.x, v.y, v.z)
        glEnd()
        glEnable(GL_LIGHTING)
