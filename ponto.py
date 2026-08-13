"""Ponto/vetor em 3D com as operacoes usadas pelo morphing."""

import math


class Ponto:
    """Representa um ponto (ou vetor) no espaco 3D."""

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def set(self, x, y, z=0.0):
        self.x, self.y, self.z = float(x), float(y), float(z)

    def __add__(self, outro):
        return Ponto(self.x + outro.x, self.y + outro.y, self.z + outro.z)

    def __sub__(self, outro):
        return Ponto(self.x - outro.x, self.y - outro.y, self.z - outro.z)

    def __mul__(self, escalar):
        return Ponto(self.x * escalar, self.y * escalar, self.z * escalar)

    def __repr__(self):
        return f"Ponto({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"

    def rotaciona_x(self, angulo_graus):
        rad = math.radians(angulo_graus)
        y = self.y * math.cos(rad) - self.z * math.sin(rad)
        z = self.y * math.sin(rad) + self.z * math.cos(rad)
        self.y, self.z = y, z

    def rotaciona_y(self, angulo_graus):
        rad = math.radians(angulo_graus)
        x = self.x * math.cos(rad) + self.z * math.sin(rad)
        z = -self.x * math.sin(rad) + self.z * math.cos(rad)
        self.x, self.z = x, z

    def rotaciona_z(self, angulo_graus):
        rad = math.radians(angulo_graus)
        x = self.x * math.cos(rad) - self.y * math.sin(rad)
        y = self.x * math.sin(rad) + self.y * math.cos(rad)
        self.x, self.y = x, y
