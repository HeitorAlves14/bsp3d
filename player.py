import numpy as np
import math

class Player:
    def __init__(self, x, y, z, largura=1.0, altura=2.0):
        self.pos = np.array([x, y, z], dtype=np.float32)
        self.largura = largura
        self.altura = altura
        self.agachado = False
        self.altura_normal = altura
        self.altura_agachado = altura * 0.5
        # --- VARIÁVEIS DE FÍSICA ---
        self.velocidade_y = 0.0
        self.on_ground = False
        self.forca_pulo = 0.25
        self.gravidade = 0.012
        self.max_step_height = 0.35
        # --- VARIÁVEIS DE CAMERA ---
        self.shake_intensidade = 0.0
        self.shake_decay = 0.9
        self.shake_offset = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        # --- SISTEMA DE COMBATE ---
        self.esta_atirando = False
        self.timer_tiro = 0
        self.dano_arma = 35
        # --- STATUS DO JOGADOR ---
        self.vida = 100
        self.municao = 20
        self.chaves = [] # Lista de chaves coletadas (ex: ['vermelha', 'azul'])

        
    def obter_aabb(self, pos_especifica=None):
        """Retorna os limites mínimos e máximos da AABB do jogador"""
        posicao = self.pos if pos_especifica is None else pos_especifica
        meia_l = self.largura / 2.0
        min_box = np.array([posicao[0] - meia_l, posicao[1], posicao[2] - meia_l])
        max_box = np.array([posicao[0] + meia_l, posicao[1] + self.altura, posicao[2] + meia_l])
        return min_box, max_box

    def _ponto_dentro_do_triangulo(self, p, a, b, c):
        """Usa o método dos produtos vetoriais para checar se o ponto P está dentro do triângulo ABC"""
        # Vetores das arestas
        v0 = c - a
        v1 = b - a
        v2 = p - a

        # Computa os produtos escalares necessários para coordenadas baricêntricas
        dot00 = np.dot(v0, v0)
        dot01 = np.dot(v0, v1)
        dot02 = np.dot(v0, v2)
        dot11 = np.dot(v1, v1)
        dot12 = np.dot(v1, v2)

        # Computa as coordenadas baricêntricas (u, v)
        denominador = (dot00 * dot11 - dot01 * dot01)
        if denominador == 0:
            return False
            
        inv_denominador = 1.0 / denominador
        u = (dot11 * dot02 - dot01 * dot12) * inv_denominador
        v = (dot00 * dot12 - dot01 * dot02) * inv_denominador

        # Se u >= 0, v >= 0 e u + v <= 1, o ponto está matematicamente dentro do triângulo
        return (u >= 0) and (v >= 0) and (u + v <= 1)

    def checar_colisao(self, triangulos_mapa, pos_teste):
        meia_l = self.largura / 2.0
        b_min = np.array([pos_teste[0] - meia_l, pos_teste[1], pos_teste[2] - meia_l])
        b_max = np.array([pos_teste[0] + meia_l, pos_teste[1] + self.altura, pos_teste[2] + meia_l])

        # Ponto central da colisão do jogador (centro da AABB)
        centro_player = np.array([pos_teste[0], pos_teste[1] + (self.altura / 2.0), pos_teste[2]])

        for t in triangulos_mapa:
            # 1. TESTE DO PLANO INFINITO
            canto_frente = np.zeros(3)
            canto_tras = np.zeros(3)
            for i in range(3):
                if t.normal[i] >= 0:
                    canto_frente[i] = b_max[i]
                    canto_tras[i] = b_min[i]
                else:
                    canto_frente[i] = b_min[i]
                    canto_tras[i] = b_max[i]

            # Se os cantos extremos não cruzam o plano, pula para o próximo triângulo
            if t.classificar_ponto(canto_tras) == 'FRENTE' or t.classificar_ponto(canto_frente) == 'TRAS':
                continue 

            # 2. PROJEÇÃO E TESTE DE BORDA (Substitui o raio mágico antigo)
            # Calcula a distância exata do centro do player até o plano do triângulo
            distancia_ao_plano = np.dot(t.normal, centro_player) + t.d
            
            # Projeta o centro do player diretamente em cima do plano da parede
            ponto_projetado = centro_player - (t.normal * distancia_ao_plano)

            # Verifica se esse ponto de impacto projetado está dentro dos limites reais dos vértices
            v1, v2, v3 = t.vertices[0].pos, t.vertices[1].pos, t.vertices[2].pos
            if self._ponto_dentro_do_triangulo(ponto_projetado, v1, v2, v3):
                # Se colidiu com o plano E o ponto está dentro do triângulo, houve colisão!
                return True
                
        return False

    def checar_colisao_com_props(self, lista_props, pos_teste):
        """
        Verifica se a AABB do jogador na 'pos_teste' está interceptando
        a AABB global de algum dos objetos (props) do cenário.
        """
        meia_l = self.largura / 2.0
        # Cria os limites da caixa do jogador para o teste
        p_min = np.array([pos_teste[0] - meia_l, pos_teste[1], pos_teste[2] - meia_l])
        p_max = np.array([pos_teste[0] + meia_l, pos_teste[1] + self.altura, pos_teste[2] + meia_l])

        for prop in lista_props:
            # Pega a caixa de colisão do objeto posicionada no mundo 3D
            prop_min, prop_max = prop.obter_aabb_global()

            # Teste de sobreposição AABB clássico:
            # Se houver separação em QUALQUER um dos eixos, não há colisão.
            colisao_x = p_max[0] >= prop_min[0] and p_min[0] <= prop_max[0]
            colisao_y = p_max[1] >= prop_min[1] and p_min[1] <= prop_max[1]
            colisao_z = p_max[2] >= prop_min[2] and p_min[2] <= prop_max[2]

            # Se houver sobreposição simultânea em todos os eixos, colidiu!
            if colisao_x and colisao_y and colisao_z:
                return True # Colisão detectada com este prop específico

        return False # Caminho livre de objetos

    def pular(self):
        """Ativa o pulo se o jogador estiver firmemente no chão"""
        if self.on_ground:
            self.velocidade_y = self.forca_pulo
            self.on_ground = False
    
    def disparar_raio(self, yaw, pitch, lista_inimigos):
        """Dispara um raio do centro da câmera e verifica se acertou algum inimigo"""
        # 1. Calcula o vetor direção 3D para onde o jogador está olhando
        yaw_rad = math.radians(yaw)
        pitch_rad = math.radians(pitch)
        
        dir_x = math.cos(yaw_rad) * math.cos(pitch_rad)
        dir_y = math.sin(pitch_rad)
        dir_z = math.sin(yaw_rad) * math.cos(pitch_rad)
        direcao_raio = np.array([dir_x, dir_y, dir_z], dtype=np.float32)
        
        origem_raio = np.copy(self.pos)
        origem_raio[1] += self.altura * 0.8 # Altura dos olhos do jogador

        inimigo_atingido = None
        menor_distancia = float('inf')

        # 2. Testa contra a AABB de cada inimigo
        for inimigo in lista_inimigos:
            b_min, b_max = inimigo.obter_aabb()
            
            # Algoritmo de intersecção Raio-AABB
            tmin = (b_min[0] - origem_raio[0]) / direcao_raio[0] if direcao_raio[0] != 0 else float('-inf')
            tmax = (b_max[0] - origem_raio[0]) / direcao_raio[0] if direcao_raio[0] != 0 else float('inf')
            if tmin > tmax: tmin, tmax = tmax, tmin

            tymin = (b_min[1] - origem_raio[1]) / direcao_raio[1] if direcao_raio[1] != 0 else float('-inf')
            tymax = (b_max[1] - origem_raio[1]) / direcao_raio[1] if direcao_raio[1] != 0 else float('inf')
            if tymin > tymax: tymin, tymax = tymax, tymin

            if (tmin > tymax) or (tymin > tmax): continue
            if tymin > tmin: tmin = tymin
            if tymax < tmax: tmax = tymax

            tzmin = (b_min[2] - origem_raio[2]) / direcao_raio[2] if direcao_raio[2] != 0 else float('-inf')
            tzmax = (b_max[2] - origem_raio[2]) / direcao_raio[2] if direcao_raio[2] != 0 else float('inf')
            if tzmin > tzmax: tzmin, tzmax = tzmax, tzmin

            if (tmin > tzmax) or (tzmin > max(tmin, tmax)): continue
            if tzmin > tmin: tmin = tzmin
            if tzmax < tmax: tmax = tzmax

            # Se tmax > 0, o raio interceptou a caixa do inimigo!
            if tmax > 0 and tmin < menor_distancia:
                menor_distancia = tmin
                inimigo_atingido = inimigo

        # 3. Aplica o dano se acertou alguém
        # ... (cálculo de intersecção Raio-AABB anterior) ...

        # 3. Aplica o dano se acertou alguém
        if inimigo_atingido:
            inimigo_atingido.vida -= self.dano_arma
            print(f"[Combate] Acertou o inimigo! Vida restante: {inimigo_atingido.vida}")
            
            # RETORNA A POSIÇÃO DO IMPACTO PARA GERAR AS PARTÍCULAS
            # Usamos a posição central estimada do impacto no monstro
            pos_impacto = np.copy(inimigo_atingido.pos)
            pos_impacto[1] += inimigo_atingido.altura * 0.5 # Altura do peito
            
            if inimigo_atingido.vida <= 0:
                print("[Combate] Inimigo Eliminado!")
                lista_inimigos.remove(inimigo_atingido)
                return pos_impacto, True # Impacto fatal
                
            return pos_impacto, False # Impacto normal
            
        return None, False # Errou o tiro
    
    def iniciar_shake(self, intensidade=0.2):
        self.shake_intensidade = intensidade
