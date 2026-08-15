"""3D point/vector with the operations used by the morphing pipeline."""

import math


class Point:
    """A point (or vector) in 3D space."""

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def set(self, x, y, z=0.0):
        self.x, self.y, self.z = float(x), float(y), float(z)

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar):
        return Point(self.x * scalar, self.y * scalar, self.z * scalar)

    def __repr__(self):
        return f"Point({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"

    def rotate_x(self, angle_degrees):
        rad = math.radians(angle_degrees)
        y = self.y * math.cos(rad) - self.z * math.sin(rad)
        z = self.y * math.sin(rad) + self.z * math.cos(rad)
        self.y, self.z = y, z

    def rotate_y(self, angle_degrees):
        rad = math.radians(angle_degrees)
        x = self.x * math.cos(rad) + self.z * math.sin(rad)
        z = -self.x * math.sin(rad) + self.z * math.cos(rad)
        self.x, self.z = x, z

    def rotate_z(self, angle_degrees):
        rad = math.radians(angle_degrees)
        x = self.x * math.cos(rad) - self.y * math.sin(rad)
        y = self.x * math.sin(rad) + self.y * math.cos(rad)
        self.x, self.y = x, y
