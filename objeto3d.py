"""Objeto 3D carregado de um arquivo .obj, com suporte a morphing.

O morphing e feito em duas etapas:
  1. `associa_faces`: casa cada face deste objeto com a face mais proxima
     do objeto destino (vizinho mais proximo por centroide);
  2. `emite_morph`: interpola linearmente os vertices das faces casadas
     de acordo com um parametro t em [0, 1].
"""

from math import inf, sqrt
from random import choice

from OpenGL.GL import (
    glBegin, glEnd, glVertex3f, glNormal3f, glColor3f,
    glPushMatrix, glPopMatrix, glTranslatef, glRotatef,
    glPointSize, glLineWidth, glEnable, glDisable,
    GL_TRIANGLES, GL_LINE_LOOP, GL_POINTS, GL_LIGHTING,
)

from ponto import Ponto


def _indice_mais_proximo(centroide, centroides):
    """Indice do centroide mais proximo (distancia ao quadrado; sem sqrt)."""
    melhor_i, menor = 0, inf
    for i, c in enumerate(centroides):
        d = (centroide.x - c.x) ** 2 + (centroide.y - c.y) ** 2 + (centroide.z - c.z) ** 2
        if d < menor:
            menor, melhor_i = d, i
    return melhor_i


def _normal_triangulo(p0, p1, p2):
    """Normal unitaria de um triangulo (para iluminacao flat)."""
    ux, uy, uz = p1.x - p0.x, p1.y - p0.y, p1.z - p0.z
    vx, vy, vz = p2.x - p0.x, p2.y - p0.y, p2.z - p0.z
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    comp = sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / comp, ny / comp, nz / comp


class Objeto3D:
    def __init__(self):
        self.vertices = []          # lista de Ponto
        self.faces = []             # lista de triangulos: cada um e [i0, i1, i2]
        self.position = Ponto(0, 0, 0)
        self.ang_x = 0.0            # rotacao acumulada em torno de X
        self.ang_y = 0.0            # rotacao acumulada em torno de Y
        self.color = (1.0, 1.0, 1.0)
        self.largura_aresta = 1.5   # espessura do wireframe (glLineWidth)
        self.tamanho_vertice = 4.0  # tamanho dos pontos dos vertices (glPointSize)

    # ----------------------------------------------------------- carregamento
    def carrega(self, caminho):
        """Le um .obj triangulando qualquer face com mais de 3 vertices.

        Usa `split()` (qualquer espaco em branco), o que tolera espacos
        duplos e finais de linha do Windows.
        """
        with open(caminho, "r") as arquivo:
            for linha in arquivo:
                tokens = linha.split()
                if not tokens:
                    continue
                if tokens[0] == "v":
                    x, y, z = (float(t) for t in tokens[1:4])
                    self.vertices.append(Ponto(x, y, z))
                elif tokens[0] == "f":
                    # ignora indices de textura/normal (formato "v/vt/vn")
                    indices = [int(t.split("/")[0]) - 1 for t in tokens[1:]]
                    self.faces.extend(self._triangula(indices))
        return self

    @staticmethod
    def _triangula(face):
        """Triangulacao em leque: [a, b, c, d, ...] -> [[a,b,c], [a,c,d], ...]."""
        return [[face[0], face[i], face[i + 1]] for i in range(1, len(face) - 1)]

    def normaliza(self):
        """Centraliza na origem e escala para caber num cubo unitario.

        Deve ser chamado UMA vez, logo apos o carregamento -- nunca dentro
        do laco de desenho, para nao mutar os vertices a cada quadro.
        """
        if not self.vertices:
            return
        xs = [v.x for v in self.vertices]
        ys = [v.y for v in self.vertices]
        zs = [v.z for v in self.vertices]
        cx, cy, cz = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2
        maior = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) or 1.0
        for v in self.vertices:
            v.x = (v.x - cx) / maior
            v.y = (v.y - cy) / maior
            v.z = (v.z - cz) / maior

    # ---------------------------------------------------------------- desenho
    def _aplica_transformacao(self):
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glRotatef(self.ang_x, 1, 0, 0)
        glRotatef(self.ang_y, 0, 1, 0)

    def desenha(self, r=None, g=None, b=None):
        """Faces solidas (iluminadas) + wireframe + vertices, ja transformadas."""
        if r is None:
            r, g, b = self.color
        glPushMatrix()
        self._aplica_transformacao()
        self.emite_estatico(r, g, b)
        glPopMatrix()

    def emite_estatico(self, r, g, b):
        """Emite a geometria sem aplicar transformacao nem push/pop.
        Quem chama controla a matriz de modelo (usado pela janela de morph)."""
        self._emite_solido(r, g, b)
        self._emite_wireframe()
        self._emite_vertices()
        glEnable(GL_LIGHTING)

    def _emite_solido(self, r, g, b):
        glEnable(GL_LIGHTING)
        glColor3f(r, g, b)
        glBegin(GL_TRIANGLES)
        for face in self.faces:
            p0, p1, p2 = (self.vertices[i] for i in face)
            glNormal3f(*_normal_triangulo(p0, p1, p2))
            for idx in face:
                v = self.vertices[idx]
                glVertex3f(v.x, v.y, v.z)
        glEnd()

    def _emite_wireframe(self):
        glDisable(GL_LIGHTING)
        glColor3f(0, 0, 0)
        glLineWidth(self.largura_aresta)
        for face in self.faces:
            glBegin(GL_LINE_LOOP)
            for idx in face:
                v = self.vertices[idx]
                glVertex3f(v.x, v.y, v.z)
            glEnd()

    def _emite_vertices(self):
        glDisable(GL_LIGHTING)
        glColor3f(0, 0, 0)
        glPointSize(self.tamanho_vertice)
        glBegin(GL_POINTS)
        for v in self.vertices:
            glVertex3f(v.x, v.y, v.z)
        glEnd()

    # ------------------------------------------------------------------ morph
    def _centroide(self, face):
        cx = cy = cz = 0.0
        for idx in face:
            v = self.vertices[idx]
            cx += v.x
            cy += v.y
            cz += v.z
        n = len(face)
        return Ponto(cx / n, cy / n, cz / n)

    def associa_faces(self, outro, modo="vizinho"):
        """Casa cada face deste objeto com uma face de `outro`.

        Fase 1 (igual para todos os modos): pareamento 1-para-1 guloso pelo
        centroide mais proximo, sem reutilizar faces enquanto houver opcoes.

        Fase 2: quando os objetos tem numeros de faces diferentes, sobram faces
        sem par. `modo` decide o que fazer com elas:
          - "colapso":   todas vao para a MESMA face do outro objeto. E o
                         comportamento original; produz o colapso num unico
                         ponto (util para demonstrar a limitacao).
          - "vizinho":   cada excedente vai para a face MAIS PROXIMA do outro
                         objeto (repeticao permitida). Os colapsos ficam locais
                         e distribuidos pela superficie -- bem mais agradavel.
          - "aleatorio": cada excedente vai para uma face aleatoria. Fica
                         caotico de proposito, mostrando por que a correspondencia
                         importa.

        Complexidade O(n1 * n2): os centroides sao pre-calculados, mas o custo
        continua quadratico (ver "Limitacoes" no README).
        """
        centroides_self = [self._centroide(f) for f in self.faces]
        centroides_outro = [outro._centroide(f) for f in outro.faces]

        associacoes = []
        usadas = set()
        sem_par = []

        # fase 1: pareamento 1-para-1 guloso (injetivo) por centroide mais proximo
        for face1, c1 in zip(self.faces, centroides_self):
            melhor_i, menor = None, inf
            for i, c2 in enumerate(centroides_outro):
                if i in usadas:
                    continue
                d = (c1.x - c2.x) ** 2 + (c1.y - c2.y) ** 2 + (c1.z - c2.z) ** 2
                if d < menor:
                    menor, melhor_i = d, i
            if melhor_i is None:                      # acabaram as faces livres
                sem_par.append((face1, c1))
            else:
                usadas.add(melhor_i)
                associacoes.append((face1, outro.faces[melhor_i]))

        restantes_outro = [i for i in range(len(outro.faces)) if i not in usadas]

        # fase 2a: self tem faces excedentes -> escolher uma face de `outro`
        for face1, c1 in sem_par:
            if modo == "vizinho":
                face2 = outro.faces[_indice_mais_proximo(c1, centroides_outro)]
            elif modo == "aleatorio":
                face2 = choice(outro.faces)
            else:  # colapso
                face2 = outro.faces[restantes_outro.pop()] if restantes_outro else associacoes[-1][1]
            associacoes.append((face1, face2))

        # fase 2b: outro tem faces excedentes -> escolher uma face de `self`
        for i in restantes_outro:
            face2 = outro.faces[i]
            if modo == "vizinho":
                face1 = self.faces[_indice_mais_proximo(centroides_outro[i], centroides_self)]
            elif modo == "aleatorio":
                face1 = choice(self.faces)
            else:  # colapso
                face1 = associacoes[-1][0] if associacoes else self.faces[0]
            associacoes.append((face1, face2))

        return associacoes

    def emite_morph(self, outro, associacoes, t, r, g, b):
        """Desenha um unico quadro do morph (sem push/pop nem transformacao;
        quem chama controla a matriz de modelo). `t` vai de 0 (este objeto)
        a 1 (o objeto `outro`)."""
        # interpola cada triangulo uma vez e reaproveita nos tres passes
        triangulos = []
        for face1, face2 in associacoes:
            triangulos.append([
                Ponto(
                    (1 - t) * self.vertices[i].x + t * outro.vertices[j].x,
                    (1 - t) * self.vertices[i].y + t * outro.vertices[j].y,
                    (1 - t) * self.vertices[i].z + t * outro.vertices[j].z,
                )
                for i, j in zip(face1, face2)
            ])

        glEnable(GL_LIGHTING)
        glColor3f(r, g, b)
        glBegin(GL_TRIANGLES)
        for tri in triangulos:
            glNormal3f(*_normal_triangulo(*tri))
            for v in tri:
                glVertex3f(v.x, v.y, v.z)
        glEnd()

        glDisable(GL_LIGHTING)
        glColor3f(0, 0, 0)
        glLineWidth(self.largura_aresta)
        for tri in triangulos:
            glBegin(GL_LINE_LOOP)
            for v in tri:
                glVertex3f(v.x, v.y, v.z)
            glEnd()

        glPointSize(self.tamanho_vertice)
        glBegin(GL_POINTS)
        for tri in triangulos:
            for v in tri:
                glVertex3f(v.x, v.y, v.z)
        glEnd()
        glEnable(GL_LIGHTING)
