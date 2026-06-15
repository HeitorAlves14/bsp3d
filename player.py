import numpy as np

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
    
    def iniciar_shake(self, intensidade=0.2):
        self.shake_intensidade = intensidade
