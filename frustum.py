import numpy as np
from OpenGL.GL import *

class Frustum:
    def __init__(self):
        # Guardará os 6 planos. Cada plano é um array [A, B, C, D]
        self.planos = np.zeros((6, 4), dtype=np.float32)

    def atualizar(self):
        """Extrai as matrizes atuais do OpenGL e calcula os 6 planos do Frustum"""
        proj = glGetFloatv(GL_PROJECTION_MATRIX)
        modl = glGetFloatv(GL_MODELVIEW_MATRIX)

        # Combinação de visualização e projeção
        clip = np.matmul(modl, proj)

        # Extrai os planos (Direita, Esquerda, Baixo, Cima, Longe, Perto)
        self.planos[0] = clip[:, 3] - clip[:, 0] # Direita
        self.planos[1] = clip[:, 3] + clip[:, 0] # Esquerda
        self.planos[2] = clip[:, 3] + clip[:, 1] # Baixo
        self.planos[3] = clip[:, 3] - clip[:, 1] # Cima
        self.planos[4] = clip[:, 3] - clip[:, 2] # Longe
        self.planos[5] = clip[:, 3] + clip[:, 2] # Perto

        # Normaliza os planos
        for i in range(6):
            norma = np.linalg.norm(self.planos[i, :3])
            if norma != 0:
                self.planos[i] /= norma

    def ponto_visivel(self, x, y, z):
        """Verifica se um único ponto está dentro do Frustum"""
        for i in range(6):
            if self.planos[i, 0] * x + self.planos[i, 1] * y + self.planos[i, 2] * z + self.planos[i, 3] <= 0:
                return False
        return True

    def aabb_visivel(self, b_min, b_max):
        """
        Retorna True se QUALQUER parte da caixa (AABB) estiver dentro do Frustum.
        Usa o teste do vértice mais favorável para otimização extrema.
        """
        for i in range(6):
            plano = self.planos[i]
            
            # Encontra o "vértice positivo" (o canto da caixa mais voltado para o plano)
            px = b_max[0] if plano[0] > 0 else b_min[0]
            py = b_max[1] if plano[1] > 0 else b_min[1]
            pz = b_max[2] if plano[2] > 0 else b_min[2]
            
            # Se o canto mais favorável estiver atrás do plano, a caixa inteira está fora
            if (plano[0] * px + plano[1] * py + plano[2] * pz + plano[3]) < 0:
                return False
        return True

    def triangulo_visivel(self, triangulo):
        """
        Retorna True se a AABB do triângulo interceptar o Frustum.
        Muito mais seguro do que checar apenas vértices isolados!
        """
        # Cria uma AABB rápida para o triângulo
        posicoes = [v.pos for v in triangulo.vertices]
        b_min = np.min(posicoes, axis=0)
        b_max = np.max(posicoes, axis=0)
        
        return self.aabb_visivel(b_min, b_max)