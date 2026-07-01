import numpy as np
from OpenGL.GL import *

class Coletavel:
    def __init__(self, x, y, z, tipo, textura_id, quantidade=10, largura=0.6, altura=0.6):
        self.pos = np.array([x, y, z], dtype=np.float32)
        self.tipo = tipo.upper() # 'VIDA', 'MUNICAO', 'CHAVE'
        self.textura_id = textura_id
        self.quantidade = quantidade
        
        self.largura = largura
        self.altura = altura
        
        # Faz o item flutuar levemente para dar efeito de jogo retrô
        self.angulo_animacao = 0.0
        self.pos_y_original = y

    def obter_aabb(self):
        """Retorna a caixa de gatilho do item"""
        meia_l = self.largura / 2.0
        min_box = np.array([self.pos[0] - meia_l, self.pos[1], self.pos[2] - meia_l])
        max_box = np.array([self.pos[0] + meia_l, self.pos[1] + self.altura, self.pos[2] + meia_l])
        return min_box, max_box

    def atualizar(self, player):
        """Faz o item flutuar e checa se o jogador o coletou"""
        # 1. Efeito visual de flutuação senoidal
        self.angulo_animacao += 0.05
        self.pos[1] = self.pos_y_original + (np.sin(self.angulo_animacao) * 0.08)

        # 2. Teste de intersecção AABB contra a AABB do Jogador
        p_min, p_max = player.obter_aabb()
        i_min, i_max = self.obter_aabb()

        colidiu = (p_max[0] >= i_min[0] and p_min[0] <= i_max[0] and
                   p_max[1] >= i_min[1] and p_min[1] <= i_max[1] and
                   p_max[2] >= i_min[2] and p_min[2] <= i_max[2])

        if colidiu:
            # Aplica o benefício dependendo do tipo do item
            if self.tipo == 'VIDA':
                # Supondo que você adicione 'self.vida' no seu player.py
                if hasattr(player, 'vida') and player.vida < 100:
                    player.vida = min(100, player.vida + self.quantidade)
                    print(f"[Coletável] Vida coletada! Nova Vida: {player.vida}")
                    return True # Avisa a engine para deletar o item da cena
            
            elif self.tipo == 'MUNICAO':
                if hasattr(player, 'municao'):
                    player.municao += self.quantidade
                    print(f"[Coletável] Munição coletada! Total: {player.municao}")
                    return True
            
            elif self.tipo == 'CHAVE':
                if hasattr(player, 'chaves'):
                    player.chaves.append(self.quantidade) # Guarda o ID ou nome da chave
                    print(f"[Coletável] Chave [{self.quantidade}] coletada!")
                    return True
                    
        return False # Continua no mapa

    def renderizar(self, frustum):
        """Renderiza o item olhando sempre para a câmera (Billboard)"""
        if not frustum.ponto_visivel(self.pos[0], self.pos[1], self.pos[2]):
            return

        glPushMatrix()
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])

        # Anula a rotação da câmera (Billboard Cilíndrico/Esférico rápido)
        modelview = glGetFloatv(GL_MODELVIEW_MATRIX)
        for i in range(3):
            for j in range(3):
                if i == j: modelview[i][j] = 1.0
                else: modelview[i][j] = 0.0
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