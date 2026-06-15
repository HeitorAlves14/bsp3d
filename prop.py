import numpy as np
from OpenGL.GL import *

class Prop:
    def __init__(self, nome, triangulos_locais, posicao_global):
        self.nome = nome
        self.triangulos_locais = triangulos_locais # Recebe os triângulos já processados
        self.pos_original = np.array(posicao_global, dtype=np.float32)
        self.pos = np.array(posicao_global, dtype=np.float32)
        self.pos_alvo = np.array(posicao_global, dtype=np.float32)

        # Configurações de Física da Porta
        self.velocidade_porta = 0.05
        self.distancia_movimento = 2.0  # Quantas unidades a porta vai deslizar
        
        # Máquina de Estados: 'FECHADA', 'ABRINDO', 'ABERTA', 'FECHANDO'
        self.estado = 'FECHADA'
        self.timer_aberta = 0
        self.tempo_espera_aberta = 120  # ~2 segundos a 60 FPS

        # Decodifica as propriedades se for uma porta
        self.eh_porta = "door" in nome.lower()
        if self.eh_porta:
            self._configurar_direcao_porta()
        
        # Calcula a caixa de colisão baseada nesses triângulos
        self.b_min, self.b_max = self._calcular_aabb_local()
    
    def _configurar_direcao_porta(self):
        """
        Descobre a orientação nativa da porta a partir dos seus próprios triângulos
        e calcula o vetor de deslizamento perfeito, mesmo na diagonal.
        """
        if not self.triangulos_locais:
            return

        # 1. Pega o primeiro triângulo da porta para analisar a orientação
        t = self.triangulos_locais[0]
        
        # A normal nos diz para onde a face "olha" (perpendicular)
        normal = t.normal 
        
        # 2. Criamos o vetor de deslizamento horizontal (paralelo à porta)
        # Fazemos o produto vetorial entre a Normal e o vetor Up global (0, 1, 0).
        # Isso nos dá um vetor que corre perfeitamente ao longo da parede da porta!
        direcao_deslizamento = np.cross(normal, np.array([0.0, 1.0, 0.0]))
        
        # Normaliza o vetor para ter tamanho 1
        norma = np.linalg.norm(direcao_deslizamento)
        if norma != 0:
            direcao_deslizamento /= norma

        # 3. Descobre o sinal (+ ou -) baseado na tag do Blender
        sinal = -1.0 if '-' in self.nome else 1.0
        
        # Se a tag pedir movimento vertical (ex: door+y ou door-y), ignoramos a diagonal horizontal
        if 'y' in self.nome.lower():
            vetor_movimento = np.array([0.0, 1.0, 0.0]) * sinal
        else:
            # Caso contrário, ela corre no seu próprio eixo horizontal calculado!
            vetor_movimento = direcao_deslizamento * sinal

        # 4. Define a posição final absoluta no mundo
        self.pos_alvo = self.pos_original + (vetor_movimento * self.distancia_movimento)

    def interagir(self):
        """Ativa a abertura da porta se ela estiver fechada"""
        if self.eh_porta and self.estado == 'FECHADA':
            self.estado = 'ABRINDO'
            print(f"[Porta] {self.nome} abrindo em direção a {self.pos_alvo}")

    def atualizar(self, player=None):
        """Gerencia o movimento e o tempo da porta frame a frame"""
        if not self.eh_porta or self.estado == 'FECHADA':
            return
        
        pos_anterior = np.copy(self.pos)

        if self.estado == 'ABRINDO':
            # Move em direção ao alvo
            vetor_alvo = self.pos_alvo - self.pos
            distancia = np.linalg.norm(vetor_alvo)
            
            if distancia > self.velocidade_porta:
                self.pos += (vetor_alvo / distancia) * self.velocidade_porta
            else:
                self.pos = np.copy(self.pos_alvo)
                self.estado = 'ABERTA'
                self.timer_aberta = 0

        elif self.estado == 'ABERTA':
            # Espera o tempo passar para fechar sozinha
            self.timer_aberta += 1
            if self.timer_aberta >= self.tempo_espera_aberta:
                self.estado = 'FECHANDO'

        elif self.estado == 'FECHANDO':
            # Move de volta para a posição original
            vetor_origem = self.pos_original - self.pos
            distancia = np.linalg.norm(vetor_origem)
            
            if distancia > self.velocidade_porta:
                self.pos += (vetor_origem / distancia) * self.velocidade_porta
            else:
                self.pos = np.copy(self.pos_original)
                self.estado = 'FECHADA'
        # --- SISTEMA PUSH-OUT (EMPURRAR O JOGADOR) ---
        if player is not None:
            p_min, p_max = player.obter_aabb()
            prop_min, prop_max = self.obter_aabb_global()

            # Verifica se houve intersecção com o jogador
            if (p_max[0] >= prop_min[0] and p_min[0] <= prop_max[0] and
                p_max[1] >= prop_min[1] and p_min[1] <= prop_max[1] and
                p_max[2] >= prop_min[2] and p_min[2] <= prop_max[2]):
                
                # SE ESTIVESSE FECHANDO: Ativa o sensor antiesmagamento (estilo elevador)
                if self.estado == 'FECHANDO':
                    self.estado = 'ABRINDO'
                    print(f"[Porta] Obstáculo detectado! Revertendo fechamento de {self.nome}")
                
                # SE ESTIVESSE ABRINDO: Apenas empurra o jogador normalmente
                elif self.estado == 'ABRINDO':
                    vetor_empurrao = self.pos - pos_anterior
                    if np.linalg.norm(vetor_empurrao) > 0:
                        player.pos += vetor_empurrao

    def _calcular_aabb_local(self):
        todas_pos = []
        for t in self.triangulos_locais:
            for v in t.vertices:
                todas_pos.append(v.pos)
        if not todas_pos: return np.zeros(3), np.zeros(3)
        return np.min(todas_pos, axis=0), np.max(todas_pos, axis=0)

    def obter_aabb_global(self):
        return self.b_min + self.pos, self.b_max + self.pos

    def renderizar(self, frustum):
        g_min, g_max = self.obter_aabb_global()
        centro = (g_min + g_max) / 2.0
        
        # Culling de Frustum para o objeto inteiro
        if not frustum.ponto_visivel(centro[0], centro[1], centro[2]):
            return 

        glPushMatrix()
        # Move o objeto para a posição onde ele foi colocado no Blender
        glTranslatef(self.pos[0], self.pos[1], self.pos[2])
        
        for t in self.triangulos_locais:
            glBindTexture(GL_TEXTURE_2D, t.textura_id)
            glBegin(GL_TRIANGLES)
            for v in t.vertices:
                glTexCoord2f(v.uv[0], v.uv[1])
                glVertex3fv(v.pos)
            glEnd()
        
        glPopMatrix()