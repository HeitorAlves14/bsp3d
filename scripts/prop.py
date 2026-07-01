import numpy as np
from OpenGL.GL import *
from collections import defaultdict

class Prop:
    def __init__(self, nome, triangulos_locais, posicao_global):
        self.nome = nome
        self.triangulos_locais = triangulos_locais # Recebe os triângulos já processados
        self._grupos_por_textura = defaultdict(list)
        for t in self.triangulos_locais:
            self._grupos_por_textura[t.textura_id].append(t)
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

        # 1. Em vez de pegar o primeiro triângulo da lista (que pode ser uma
        # face fina de espessura/tampa lateral, dependendo de como o Blender
        # exportou), procuramos o triângulo de MAIOR ÁREA. A face larga e
        # visível da porta é sempre muito maior que as faces de espessura,
        # então isso garante que pegamos a normal certa independente da
        # ordem das faces no arquivo .obj.
        t_principal = self.triangulos_locais[0]
        maior_area = -1.0
        for tri in self.triangulos_locais:
            p0, p1, p2 = tri.vertices[0].pos, tri.vertices[1].pos, tri.vertices[2].pos
            area = np.linalg.norm(np.cross(p1 - p0, p2 - p0))
            if area > maior_area:
                maior_area = area
                t_principal = tri

        # A normal nos diz para onde a face "olha" (perpendicular)
        normal = t_principal.normal 
        
        # 2. Criamos o vetor de deslizamento horizontal (paralelo à porta)
        # Fazemos o produto vetorial entre a Normal e o vetor Up global (0, 1, 0).
        # Isso nos dá um vetor que corre perfeitamente ao longo da parede da porta!
        up = np.array([0.0, 1.0, 0.0])

        # Eixo X local da porta
        eixo_x_local = np.cross(normal, up)
        norma_x = np.linalg.norm(eixo_x_local)

        if norma_x > 0:
            eixo_x_local /= norma_x

        # Eixo Z local da porta
        eixo_z_local = normal.copy()
        eixo_z_local[1] = 0.0

        norma_z = np.linalg.norm(eixo_z_local)

        if norma_z > 0:
            eixo_z_local /= norma_z

        sinal = -1.0 if '-' in self.nome else 1.0

        nome_lower = self.nome.lower()

        if 'y' in nome_lower:
            vetor_movimento = np.array([0.0, 1.0, 0.0]) * sinal

        elif 'x' in nome_lower:
            vetor_movimento = eixo_x_local * sinal

        elif 'z' in nome_lower:
            vetor_movimento = eixo_z_local * sinal

        else:
            vetor_movimento = eixo_x_local * sinal

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