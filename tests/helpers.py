"""Helpers shared by the test modules.

Kept out of conftest.py on purpose: conftest is where pytest looks for fixtures
and hooks, and plain functions are easier to follow in a module of their own.
"""

import os

from mesh import Mesh
from point import Point

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")


def make_mesh(vertices, faces):
    """Build an Mesh straight from coordinates, bypassing the .obj reader."""
    mesh = Mesh()
    mesh.vertices = [Point(*v) for v in vertices]
    mesh.faces = [list(f) for f in faces]
    return mesh
