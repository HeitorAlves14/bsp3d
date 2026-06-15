import numpy as np
import random
from OpenGL.GL import *

class Particula:
    def __init__(self, x, y, z, cor):
        self.pos = np.array([x, y, z], dtype=np.float32)
        
        # Velocidade aleatória explodindo para todas as direções
        self.vel = np.array([
            random.uniform(-0.08, 0.08),
            random.uniform(-0.02, 0.12), # Força um pouco mais para cima
            random.uniform(-0.08, 0.08)
        ], dtype=np.float32)
        
        self.cor = cor # Tupla (R, G, B, A)
        self.vida = 1.0 # Começa em 100% de vida
        self.velocidade_envelhecimento = random.uniform(0.02, 0.04)
        self.tamanho = random.uniform(0.05, 0.12)

    def atualizar(self):
        """Atualiza a física da partícula (movimento, gravidade e fricção)"""
        # Aplica o movimento
        self.pos += self.vel
        
        # Aplica uma leve gravidade para fazê-las cair
        self.vel[1] -= 0.004
        
        # Fricção do ar (reduz a velocidade horizontal aos poucos)
        self.vel[0] *= 0.95
        self.vel[2] *= 0.95
        
        # Envelhece a partícula
        self.vida -= self.velocidade_envelhecimento
        return self.vida > 0 # Retorna Falso se a partícula morreu

    def renderizar(self):
        """Desenha a partícula como um Billboard puro voltado para a câmera"""
        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])

        # Anula a rotação da câmera (Billboard Cilíndrico/Esférico rápido)
        modelview = glGetFloatv(GL_MODELVIEW_MATRIX)
        for i in range(3):
            for j in range(3):
                modelview[i][j] = 1.0 if i == j else 0.0
        glLoadMatrixf(modelview)

        # Desativa texturas temporariamente para desenhar um quadrado de cor sólida
        glDisable(GL_TEXTURE_2D)
        
        # Aplica a cor sumindo gradualmente conforme a vida cai (Alpha dinâmico)
        glColor4f(self.cor[0], self.cor[1], self.cor[2], self.vida)

        meia_l = self.tamanho / 2.0
        glBegin(GL_QUADS)
        glVertex3f(-meia_l, -meia_l, 0.0)
        glVertex3f(meia_l, -meia_l, 0.0)
        glVertex3f(meia_l, meia_l, 0.0)
        glVertex3f(-meia_l, meia_l, 0.0)
        glEnd()

        glEnable(GL_TEXTURE_2D) # Reativa as texturas para o resto do jogo
        glPopMatrix()