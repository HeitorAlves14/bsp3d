import numpy as np
import math
from OpenGL.GL import *
from ator import Ator


class Inimigo(Ator):
    """
    Inimigo com IA de perseguição, colisão completa e gravidade.
    Herda toda a lógica de AABB, colisão com mapa/props e física
    vertical de Ator — sem duplicar código.
    """

    def __init__(self, x, y, z, textura_id, largura=0.8, altura=1.8):
        super().__init__(x, y, z, largura, altura)
        self.textura_id = textura_id
        self.velocidade = 0.05
        self.vida       = 100

    # ------------------------------------------------------------------
    # Colisão entre atores (jogador ↔ inimigo, inimigo ↔ inimigo)
    # ------------------------------------------------------------------

    def colidindo_com_outros_atores(self, player, lista_inimigos, pos_teste):
        """AABB vs AABB contra o jogador e os outros inimigos."""
        p_min, p_max = self.obter_aabb(pos_teste)

        # Teste contra o jogador
        pl_min, pl_max = player.obter_aabb()
        if (p_max[0] >= pl_min[0] and p_min[0] <= pl_max[0] and
                p_max[1] >= pl_min[1] and p_min[1] <= pl_max[1] and
                p_max[2] >= pl_min[2] and p_min[2] <= pl_max[2]):
            return True

        # Teste contra outros inimigos
        for outro in lista_inimigos:
            if outro is self:
                continue
            o_min, o_max = outro.obter_aabb()
            if (p_max[0] >= o_min[0] and p_min[0] <= o_max[0] and
                    p_max[1] >= o_min[1] and p_min[1] <= o_max[1] and
                    p_max[2] >= o_min[2] and p_min[2] <= o_max[2]):
                return True

        return False

    # ------------------------------------------------------------------
    # IA + física
    # ------------------------------------------------------------------

    def atualizar_ia(self, player, triangulos_mapa, lista_props, lista_inimigos):
        """
        Movimento horizontal de perseguição com step-up + física vertical com gravidade.
        """
        # ---------- Gravidade ----------
        self.aplicar_gravidade()
        self.resolver_eixo_y(triangulos_mapa, lista_props)

        # ---------- Perseguição horizontal ----------
        vetor = np.array(
            [player.pos[0] - self.pos[0], 0.0, player.pos[2] - self.pos[2]],
            dtype=np.float32
        )
        distancia = np.linalg.norm(vetor)
        if distancia < 1.1 or distancia > 25.0:
            return

        direcao       = vetor / distancia
        pos_tentativa = self.pos + direcao * self.velocidade

        # Filtra colisão com outros atores antes de passar para o step-up
        pos_x = np.array([pos_tentativa[0], self.pos[1], self.pos[2]], dtype=np.float32)
        pos_z = np.array([self.pos[0],       self.pos[1], pos_tentativa[2]], dtype=np.float32)

        # Bloqueia se colidir com jogador ou outros inimigos (sem step-up nesses casos)
        if not self.colidindo_com_outros_atores(player, lista_inimigos, pos_x):
            self.mover_horizontal_com_step(triangulos_mapa, lista_props, pos_x, pos_z)
        elif not self.colidindo_com_outros_atores(player, lista_inimigos, pos_z):
            pos_x_neutro = np.array([self.pos[0], self.pos[1], self.pos[2]], dtype=np.float32)
            self.mover_horizontal_com_step(triangulos_mapa, lista_props, pos_x_neutro, pos_z)

    # ------------------------------------------------------------------
    # Renderização (billboard que sempre olha para a câmera)
    # ------------------------------------------------------------------

    def renderizar(self, frustum):
        centro_y = self.pos[1] + self.altura / 2.0
        if not frustum.ponto_visivel(self.pos[0], centro_y, self.pos[2]):
            return

        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])

        # Zera a rotação da modelview para que o sprite sempre olhe para a câmera
        mv = glGetFloatv(GL_MODELVIEW_MATRIX)
        for i in range(3):
            for j in range(3):
                mv[i][j] = 1.0 if i == j else (0.0 if i != 1 and j != 1 else mv[i][j])
        glLoadMatrixf(mv)

        glBindTexture(GL_TEXTURE_2D, self.textura_id)
        meia_l = self.largura / 2.0
        glBegin(GL_QUADS)
        glTexCoord2f(0.0, 0.0); glVertex3f(-meia_l, 0.0,        0.0)
        glTexCoord2f(1.0, 0.0); glVertex3f( meia_l, 0.0,        0.0)
        glTexCoord2f(1.0, 1.0); glVertex3f( meia_l, self.altura, 0.0)
        glTexCoord2f(0.0, 1.0); glVertex3f(-meia_l, self.altura, 0.0)
        glEnd()

        glPopMatrix()