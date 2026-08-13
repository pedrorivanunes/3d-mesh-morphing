"""Morphing 3D entre dois objetos por associacao de faces e interpolacao linear.

Abre tres janelas: o objeto de origem, o de destino e a janela do morph.

Controles (em qualquer janela):
    W / S        rotaciona o objeto em torno de X
    A / D        rotaciona o objeto em torno de Y
    I / J / K / L move a camera (cima / esquerda / baixo / direita)
    O / P        aproxima / afasta (campo de visao)

Somente na janela de MORPH:
    1            escolhe o objeto 1 como origem (destino = objeto 2)
    2            escolhe o objeto 2 como origem (destino = objeto 1)
    ESPACO       inicia a animacao do morph
    M            alterna o modo de tratamento das faces excedentes
                 (vizinho -> aleatorio -> colapso), reanimando na hora
"""

import os
import sys

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

from objeto3d import Objeto3D

# --------------------------------------------------------------------- config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Menu de objetos disponiveis (nome -> arquivo .obj). Troque MODELO_1 / MODELO_2
# para morfar outros pares. Modelos "hard" tem muitas faces e deixam a
# associacao lenta (ver "Limitacoes conhecidas" no README).
MODELOS = {
    "banana":  "models/easy1.obj",
    "arvore":  "models/easy2.obj",
    "animal":  "models/easy3.obj",
    "carro":   "models/hard1.obj",
    "castelo": "models/hard2.obj",
    "humano":  "models/hard3.obj",
}

CORES = {
    "banana":  (1.000, 0.843, 0.000),
    "arvore":  (0.000, 0.392, 0.000),
    "animal":  (0.627, 0.322, 0.176),
    "carro":   (0.863, 0.078, 0.235),
    "castelo": (0.282, 0.239, 0.545),
    "humano":  (0.737, 0.561, 0.561),
}

# par usado por padrao (leve -> anima instantaneo, bom para prints/gif)
MODELO_1 = "banana"
MODELO_2 = "animal"

QUADROS_MORPH = 150          # quadros da animacao
INTERVALO_MS = 16           # ~60 quadros por segundo

# Como tratar as faces excedentes quando os objetos tem numeros de poligonos
# diferentes (alterne ao vivo com a tecla M):
#   "vizinho"   -> excedentes vao para a face mais proxima (colapsos locais; padrao)
#   "colapso"   -> todas na mesma face (colapso num unico ponto; expoe a limitacao)
#   "aleatorio" -> faces aleatorias (caotico; mostra a importancia da correspondencia)
MODOS = ["vizinho", "aleatorio", "colapso"]
MODO_INICIAL = "vizinho"

# Aparencia da malha. Ajuste conforme o modelo: objetos com muitos poligonos
# (os "hard*") ficam mais limpos com arestas finas (ex.: 0.5) e pontos menores;
# objetos leves ficam bem com valores maiores.
LARGURA_ARESTA = 0.5         # espessura do wireframe
TAMANHO_VERTICE = 0.5        # tamanho dos pontos nos vertices

# --------------------------------------------------------------------- estado
obj1 = obj2 = None
cor1 = cor2 = (1, 1, 1)

# estado da janela de morph
morph_origem = None
morph_destino = None
morph_cor_origem = (1, 1, 1)     # cor no inicio da animacao (t = 0)
morph_cor_destino = (1, 1, 1)    # cor no fim da animacao (t = 1)
morph_assoc = None
morph_frame = 0
morph_animando = False
morph_iniciado = False
morph_ang_x = 0.0
morph_ang_y = 0.0
modo_excedente = MODO_INICIAL


class Camera:
    """Camera em orbita fixa olhando para a origem."""

    def __init__(self, posicao, fov):
        self.posicao = list(posicao)
        self.fov = fov

    def aplica(self):
        largura = glutGet(GLUT_WINDOW_WIDTH)
        altura = glutGet(GLUT_WINDOW_HEIGHT) or 1
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(self.fov, largura / altura, 0.01, 50)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(self.posicao[0], self.posicao[1], self.posicao[2],
                  0, 0, 0, 0, 1, 0)


cam1 = Camera([3.0, 1.5, 3.0], 30)
cam2 = Camera([3.0, 1.5, 3.0], 30)
cam3 = Camera([3.0, 1.5, 3.0], 30)


# ------------------------------------------------------------ setup do OpenGL
def define_luz():
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


def configura_gl():
    """Configura o contexto GL da janela ativa (chamado por janela)."""
    glClearColor(0.12, 0.12, 0.15, 1.0)
    glClearDepth(1.0)
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LESS)
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    # empurra as faces preenchidas levemente para tras, para que o wireframe
    # e os vertices apareçam nitidos por cima (evita z-fighting)
    glEnable(GL_POLYGON_OFFSET_FILL)
    glPolygonOffset(1.0, 1.0)
    define_luz()


# ------------------------------------------------------------------- cenario
def desenha_ladrilho():
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


def desenha_piso():
    glPushMatrix()
    glTranslated(-20, -1, -10)
    for _ in range(-20, 20):
        glPushMatrix()
        for _ in range(-20, 20):
            desenha_ladrilho()
            glTranslated(0, 0, 1)
        glPopMatrix()
        glTranslated(1, 0, 0)
    glPopMatrix()


# -------------------------------------------------------------- callbacks GL
def desenha_janela1():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    cam1.aplica()
    desenha_piso()
    obj1.desenha(*cor1)
    glutSwapBuffers()


def desenha_janela2():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    cam2.aplica()
    desenha_piso()
    obj2.desenha(*cor2)
    glutSwapBuffers()


def desenha_morph():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    cam3.aplica()
    desenha_piso()

    glPushMatrix()
    glRotatef(morph_ang_x, 1, 0, 0)
    glRotatef(morph_ang_y, 0, 1, 0)
    if morph_iniciado and morph_assoc is not None:
        t = min(morph_frame / QUADROS_MORPH, 1.0)
        # a cor tambem interpola: origem (t=0) -> destino (t=1)
        r = (1 - t) * morph_cor_origem[0] + t * morph_cor_destino[0]
        g = (1 - t) * morph_cor_origem[1] + t * morph_cor_destino[1]
        b = (1 - t) * morph_cor_origem[2] + t * morph_cor_destino[2]
        morph_origem.emite_morph(morph_destino, morph_assoc, t, r, g, b)
    elif morph_origem is not None:
        # antes de iniciar: mostra o objeto de origem estatico com sua cor
        morph_origem.emite_estatico(*morph_cor_origem)
    glPopMatrix()

    glutSwapBuffers()


def reshape(largura, altura):
    glViewport(0, 0, largura, max(altura, 1))


def passo_morph(_):
    """Avanca um quadro da animacao via timer (nao bloqueia o event loop)."""
    global morph_frame, morph_animando
    if not morph_animando:
        return
    if morph_frame < QUADROS_MORPH:
        morph_frame += 1
        glutPostRedisplay()
        glutTimerFunc(INTERVALO_MS, passo_morph, 0)
    else:
        morph_animando = False          # terminou: mantem o ultimo quadro
        glutPostRedisplay()


# ------------------------------------------------------------------ teclado
def _controle_camera(key, cam):
    if key == b'i':
        cam.posicao[1] += 0.5
    elif key == b'k':
        cam.posicao[1] -= 0.5
    elif key == b'j':
        cam.posicao[0] -= 0.5
    elif key == b'l':
        cam.posicao[0] += 0.5
    elif key == b'o':
        cam.fov = max(cam.fov - 1, 5)
    elif key == b'p':
        cam.fov = min(cam.fov + 1, 100)


def teclado1(key, x, y):
    if key == b'w':
        obj1.ang_x += 2
    elif key == b's':
        obj1.ang_x -= 2
    elif key == b'a':
        obj1.ang_y += 2
    elif key == b'd':
        obj1.ang_y -= 2
    else:
        _controle_camera(key, cam1)
    glutPostRedisplay()


def teclado2(key, x, y):
    if key == b'w':
        obj2.ang_x += 2
    elif key == b's':
        obj2.ang_x -= 2
    elif key == b'a':
        obj2.ang_y += 2
    elif key == b'd':
        obj2.ang_y -= 2
    else:
        _controle_camera(key, cam2)
    glutPostRedisplay()


def teclado3(key, x, y):
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
        _seleciona_origem(1)
    elif key == b'2':
        _seleciona_origem(2)
    elif key == b' ':
        _inicia_morph()
    elif key == b'm':
        _cicla_modo()
    else:
        _controle_camera(key, cam3)
    glutPostRedisplay()


def _seleciona_origem(escolha):
    global morph_origem, morph_destino, morph_cor_origem, morph_cor_destino
    global morph_iniciado, morph_animando, morph_frame, morph_assoc
    if escolha == 1:
        morph_origem, morph_destino = obj1, obj2
        morph_cor_origem, morph_cor_destino = cor1, cor2
    else:
        morph_origem, morph_destino = obj2, obj1
        morph_cor_origem, morph_cor_destino = cor2, cor1
    morph_iniciado = False
    morph_animando = False
    morph_frame = 0
    morph_assoc = None
    print(f"[morph] objeto {escolha} selecionado -- pressione ESPACO para animar.")


def _inicia_morph():
    global morph_assoc, morph_frame, morph_animando, morph_iniciado
    if morph_origem is None:
        print("[morph] escolha 1 ou 2 antes de iniciar.")
        return
    if morph_animando:
        return
    print(f"[morph] calculando associacao de faces (modo: {modo_excedente})...")
    morph_assoc = morph_origem.associa_faces(morph_destino, modo_excedente)
    morph_frame = 0
    morph_iniciado = True
    morph_animando = True
    glutTimerFunc(INTERVALO_MS, passo_morph, 0)
    print(f"[morph] animando ({len(morph_assoc)} pares de faces).")


def _cicla_modo():
    global modo_excedente, morph_animando
    modo_excedente = MODOS[(MODOS.index(modo_excedente) + 1) % len(MODOS)]
    print(f"[morph] modo de faces excedentes: {modo_excedente}")
    if morph_origem is not None:
        morph_animando = False        # permite recomputar e reanimar na hora
        _inicia_morph()


# --------------------------------------------------------------------- boot
def carrega_modelos():
    global obj1, obj2, cor1, cor2
    caminho1 = os.path.join(BASE_DIR, MODELOS[MODELO_1])
    caminho2 = os.path.join(BASE_DIR, MODELOS[MODELO_2])
    obj1 = Objeto3D().carrega(caminho1)
    obj1.normaliza()
    obj1.color = CORES[MODELO_1]
    obj2 = Objeto3D().carrega(caminho2)
    obj2.normaliza()
    obj2.color = CORES[MODELO_2]
    for obj in (obj1, obj2):
        obj.largura_aresta = LARGURA_ARESTA
        obj.tamanho_vertice = TAMANHO_VERTICE
    cor1 = CORES[MODELO_1]
    cor2 = CORES[MODELO_2]


def _cria_janela(titulo, posicao, display_func, teclado_func):
    glutInitWindowPosition(*posicao)
    glutCreateWindow(titulo)
    glutDisplayFunc(display_func)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(teclado_func)
    configura_gl()


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_RGBA | GLUT_DEPTH | GLUT_DOUBLE)
    glutInitWindowSize(500, 500)

    carrega_modelos()

    _cria_janela("Morph 3D - Objeto 1 (origem)", (100, 120), desenha_janela1, teclado1)
    _cria_janela("Morph 3D - Objeto 2 (destino)", (640, 120), desenha_janela2, teclado2)
    _cria_janela("Morph 3D - Resultado", (1180, 120), desenha_morph, teclado3)

    print(__doc__)
    glutMainLoop()


if __name__ == "__main__":
    main()
