import numpy as np
import math
from OpenGL.GL import *

class Inimigo:
    def __init__(self, x, y, z, textura_id, largura=0.8, altura=1.8):
        self.pos = np.array([x, y, z], dtype=np.float32)
        self.textura_id = textura_id
        self.largura = largura
        self.altura = altura
        
        self.velocidade = 0.025
        self.vida = 100

    def obter_aabb(self, pos_teste=None):
        """Retorna a caixa de colisão baseada na posição atual ou em uma de teste"""
        posicao = self.pos if pos_teste is None else pos_teste
        meia_l = self.largura / 2.0
        min_box = np.array([posicao[0] - meia_l, posicao[1], posicao[2] - meia_l])
        max_box = np.array([posicao[0] + meia_l, posicao[1] + self.altura, posicao[2] + meia_l])
        return min_box, max_box

    def _ponto_dentro_do_triangulo(self, p, a, b, c):
        """Auxiliar matemático idêntico ao do jogador para checar planos"""
        v0 = c - a
        v1 = b - a
        v2 = p - a
        dot00 = np.dot(v0, v0)
        dot01 = np.dot(v0, v1)
        dot02 = np.dot(v0, v2)
        dot11 = np.dot(v1, v1)
        dot12 = np.dot(v1, v2)
        invDenom = 1.0 / (dot00 * dot11 - dot01 * dot01) if (dot00 * dot11 - dot01 * dot01) != 0 else 0
        u = (dot11 * dot02 - dot01 * dot12) * invDenom
        v = (dot00 * dot12 - dot01 * dot02) * invDenom
        return (u >= 0) and (v >= 0) and (u + v < 1)

    def colidindo_com_mapa(self, triangulos_mapa, pos_teste):
        """Varre os triângulos estruturais da BSP para bloquear o monstro nas paredes"""
        b_min, b_max = self.obter_aabb(pos_teste)
        centro = np.array([pos_teste[0], pos_teste[1] + (self.altura / 2.0), pos_teste[2]])

        for t in triangulos_mapa:
            canto_frente = np.zeros(3)
            canto_tras = np.zeros(3)
            for i in range(3):
                if t.normal[i] >= 0:
                    canto_frente[i] = b_max[i]
                    canto_tras[i] = b_min[i]
                else:
                    canto_frente[i] = b_min[i]
                    canto_tras[i] = b_max[i]

            if t.classificar_ponto(canto_tras) == 'FRENTE' or t.classificar_ponto(canto_frente) == 'TRAS':
                continue 

            distancia_ao_plano = np.dot(t.normal, centro) + t.d
            ponto_projetado = centro - (t.normal * distancia_ao_plano)
            if self._ponto_dentro_do_triangulo(ponto_projetado, t.vertices[0].pos, t.vertices[1].pos, t.vertices[2].pos):
                return True
        return False

    def colidindo_com_props(self, lista_props, pos_teste):
        """Impede o monstro de atravessar os objetos (mesas, cadeiras, portas)"""
        p_min, p_max = self.obter_aabb(pos_teste)
        for prop in lista_props:
            prop_min, prop_max = prop.obter_aabb_global()
            if (p_max[0] >= prop_min[0] and p_min[0] <= prop_max[0] and
                p_max[1] >= prop_min[1] and p_min[1] <= prop_max[1] and
                p_max[2] >= prop_min[2] and p_min[2] <= prop_max[2]):
                return True
        return False

    def colidindo_com_outros_atores(self, player, lista_inimigos, pos_teste):
        """Evita que o monstro entre dentro do jogador ou de outros monstros"""
        p_min, p_max = self.obter_aabb(pos_teste)
        
        # 1. Teste contra o Jogador
        pl_min, pl_max = player.obter_aabb()
        if (p_max[0] >= pl_min[0] and p_min[0] <= pl_max[0] and
            p_max[1] >= pl_min[1] and p_min[1] <= pl_max[1] and
            p_max[2] >= pl_min[2] and p_min[2] <= pl_max[2]):
            return True

        # 2. Teste contra os Outros Inimigos (Evita empilhamento)
        for outro in lista_inimigos:
            if outro is self: # Não testa contra si mesmo
                continue
            out_min, out_max = outro.obter_aabb()
            if (p_max[0] >= out_min[0] and p_min[0] <= out_max[0] and
                p_max[1] >= out_min[1] and p_min[1] <= out_max[1] and
                p_max[2] >= out_min[2] and p_min[2] <= out_max[2]):
                return True

        return False

    def atualizar_ia(self, player, triangulos_mapa, lista_props, lista_inimigos):
        """Lógica de IA com movimentação separada por eixos para contornar paredes"""
        vetor_ate_player = np.array([player.pos[0] - self.pos[0], 0.0, player.pos[2] - self.pos[2]], dtype=np.float32)
        distancia = np.linalg.norm(vetor_ate_player)

        # Se o monstro estiver colado no jogador (distância de ataque) ou longe demais, ele para
        if distancia < 1.1 or distancia > 25.0:
            return

        direcao = vetor_ate_player / distancia
        pos_tentativa = self.pos + direcao * self.velocidade

        # --- MOVIMENTAÇÃO DESLIZANTE SEPARADA POR EIXOS (IGUAL À DO JOGADOR) ---
        
        # 1. TENTA ANDAR NO EIXO X
        pos_teste_x = np.array([pos_tentativa[0], self.pos[1], self.pos[2]])
        if not (self.colidindo_com_mapa(triangulos_mapa, pos_teste_x) or 
                self.colidindo_com_props(lista_props, pos_teste_x) or
                self.colidindo_com_outros_atores(player, lista_inimigos, pos_teste_x)):
            self.pos[0] = pos_tentativa[0]

        # 2. TENTA ANDAR NO EIXO Z
        pos_teste_z = np.array([self.pos[0], self.pos[1], pos_tentativa[2]])
        if not (self.colidindo_com_mapa(triangulos_mapa, pos_teste_z) or 
                self.colidindo_com_props(lista_props, pos_teste_z) or
                self.colidindo_com_outros_atores(player, lista_inimigos, pos_teste_z)):
            self.pos[2] = pos_tentativa[2]

    def renderizar(self, frustum):
        if not frustum.ponto_visivel(self.pos[0], self.pos[1] + (self.altura/2.0), self.pos[2]):
            return

        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])

        modelview = glGetFloatv(GL_MODELVIEW_MATRIX)
        for i in range(3):
            for j in range(3):
                if i == j: modelview[i][j] = 1.0
                else:
                    if i != 1 and j != 1: modelview[i][j] = 0.0

        glLoadMatrixf(modelview)
        glBindTexture(GL_TEXTURE_2D, self.textura_id)
        
        meia_l = self.largura / 2.0
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 0.0); glVertex3f(-meia_l, 0.0, 0.0)
        glTexCoord2f(1.0, 0.0); glVertex3f(meia_l, 0.0, 0.0)
        glTexCoord2f(1.0, 1.0); glVertex3f(meia_l, self.altura, 0.0)
        glTexCoord2f(0.0, 1.0); glVertex3f(-meia_l, self.altura, 0.0)
        glEnd()

        glPopMatrix()