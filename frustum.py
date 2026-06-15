import numpy as np
from OpenGL.GL import *

class Frustum:
    def __init__(self):
        # Guardará os 6 planos. Cada plano é um array [A, B, C, D]
        self.planos = np.zeros((6, 4), dtype=np.float32)

    def atualizar(self):
        """Extrai as matrizes atuais do OpenGL e calcula os 6 planos do Frustum"""
        # Pega a matriz Modelview e Projeção atuais da GPU
        proj = glGetFloatv(GL_PROJECTION_MATRIX)
        modl = glGetFloatv(GL_MODELVIEW_MATRIX)

        # Multiplica as duas matrizes (Combinação de visualização e projeção)
        clip = np.matmul(modl, proj)

        # Extrai os planos (Direita, Esquerda, Baixo, Cima, Longe, Perto)
        self.planos[0] = clip[:, 3] - clip[:, 0] # Direita
        self.planos[1] = clip[:, 3] + clip[:, 0] # Esquerda
        self.planos[2] = clip[:, 3] + clip[:, 1] # Baixo
        self.planos[3] = clip[:, 3] - clip[:, 1] # Cima
        self.planos[4] = clip[:, 3] - clip[:, 2] # Longe
        self.planos[5] = clip[:, 3] + clip[:, 2] # Perto

        # Normaliza as equações dos planos para que a matemática de distância funcione
        for i in range(6):
            norma = np.linalg.norm(self.planos[i, :3])
            if norma != 0:
                self.planos[i] /= norma

    def ponto_visivel(self, x, y, z):
        """Verifica se um único ponto está dentro do Frustum"""
        for i in range(6):
            # Se a distância com sinal for menor que zero, o ponto está atrás do plano (fora do Frustum)
            if self.planos[i, 0] * x + self.planos[i, 1] * y + self.planos[i, 2] * z + self.planos[i, 3] <= 0:
                return False
        return True

    def triangulo_visivel(self, triangulo):
        """
        Retorna True se pelo menos um dos vértices do triângulo estiver dentro do Frustum.
        (Abordagem simples e rápida para engines retro).
        """
        for v in triangulo.vertices:
            if self.ponto_visivel(v.pos[0], v.pos[1], v.pos[2]):
                return True
        return False