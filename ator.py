import numpy as np


class Ator:
    """
    Classe base para qualquer entidade física no mundo (Player, Inimigo, etc).
    
    Colisão com o mapa usa os 8 cantos da AABB contra cada triângulo BSP,
    evitando o bug de atravessar paredes em ângulos rasantes que ocorre
    quando se testa apenas o ponto central.
    """

    def __init__(self, x, y, z, largura, altura):
        self.pos        = np.array([x, y, z], dtype=np.float32)
        self.largura    = largura
        self.altura     = altura

        # --- Física vertical (compartilhada por Player e Inimigo) ---
        self.velocidade_y  = 0.0
        self.on_ground     = False
        self.gravidade     = 0.012
        self.max_velocidade_queda = 0.5

        # --- Step-up: altura máxima de degrau/rampa que sobe automaticamente ---
        self.max_step_height = 0.4  # unidades — ajuste conforme escala do mapa

    # ------------------------------------------------------------------
    # AABB
    # ------------------------------------------------------------------

    def obter_aabb(self, pos_teste=None):
        """Retorna (min, max) da caixa de colisão na posição atual ou de teste."""
        pos    = self.pos if pos_teste is None else pos_teste
        meia_l = self.largura / 2.0
        b_min  = np.array([pos[0] - meia_l, pos[1],             pos[2] - meia_l], dtype=np.float32)
        b_max  = np.array([pos[0] + meia_l, pos[1] + self.altura, pos[2] + meia_l], dtype=np.float32)
        return b_min, b_max

    def _cantos_aabb(self, b_min, b_max):
        """Gera os 8 vértices da AABB — usados nos testes de colisão com triângulos."""
        xs = (b_min[0], b_max[0])
        ys = (b_min[1], b_max[1])
        zs = (b_min[2], b_max[2])
        return [np.array([x, y, z], dtype=np.float32)
                for x in xs for y in ys for z in zs]

    # ------------------------------------------------------------------
    # Auxiliar geométrico (estático — não depende de instância)
    # ------------------------------------------------------------------

    @staticmethod
    def _ponto_dentro_do_triangulo(p, a, b, c):
        """
        Coordenadas baricêntricas para checar se o ponto P está dentro do
        triângulo ABC.  Retorna True se estiver dentro (incluindo bordas).
        """
        v0 = c - a;  v1 = b - a;  v2 = p - a
        d00 = np.dot(v0, v0);  d01 = np.dot(v0, v1);  d02 = np.dot(v0, v2)
        d11 = np.dot(v1, v1);  d12 = np.dot(v1, v2)
        denom = d00 * d11 - d01 * d01
        if denom == 0:
            return False
        inv = 1.0 / denom
        u = (d11 * d02 - d01 * d12) * inv
        v = (d00 * d12 - d01 * d02) * inv
        return (u >= 0) and (v >= 0) and (u + v <= 1)

    # ------------------------------------------------------------------
    # Colisão com o mapa (BSP / triângulos brutos)
    # ------------------------------------------------------------------

    def colidindo_com_mapa(self, triangulos, pos_teste):
        """
        Testa os 8 cantos da AABB contra cada triângulo do mapa.

        Fluxo por triângulo:
          1. Descarte rápido via plano infinito (canto mais extremo).
          2. Para cada canto que cruza o plano, projeta-o no plano e verifica
             se a projeção cai dentro do triângulo real.

        Isso resolve o bug de atravessar paredes em ângulos rasantes porque
        um canto da caixa pode estar claramente dentro do triângulo mesmo que
        o centro da AABB não esteja.
        """
        b_min, b_max = self.obter_aabb(pos_teste)
        cantos = self._cantos_aabb(b_min, b_max)

        for t in triangulos:
            # --- 1. Descarte rápido: canto mais extremo vs plano ---
            # O canto "frente" é o que está mais longe na direção da normal;
            # o canto "trás" é o oposto.  Se o canto-trás está na frente do
            # plano OU o canto-frente está atrás, a AABB não toca o plano.
            canto_f = np.where(t.normal >= 0, b_max, b_min)
            canto_t = np.where(t.normal >= 0, b_min, b_max)

            if (t.classificar_ponto(canto_t) == 'FRENTE' or
                    t.classificar_ponto(canto_f) == 'TRAS'):
                continue  # A caixa inteira está de um lado só — sem colisão

            # --- 2. Teste fino: projeta cada canto no plano do triângulo ---
            v1, v2, v3 = t.vertices[0].pos, t.vertices[1].pos, t.vertices[2].pos
            for canto in cantos:
                dist = np.dot(t.normal, canto) + t.d
                # Só testa cantos que estão perto / atravessando o plano
                if abs(dist) > self.largura:
                    continue
                projetado = canto - t.normal * dist
                if self._ponto_dentro_do_triangulo(projetado, v1, v2, v3):
                    return True  # Colisão confirmada

        return False

    # ------------------------------------------------------------------
    # Colisão com props (AABB vs AABB)
    # ------------------------------------------------------------------

    def colidindo_com_props(self, lista_props, pos_teste):
        """
        Teste AABB clássico contra cada prop do cenário.
        Ignora props cuja tampa (topo) está abaixo da base do ator +
        max_step_height — esses são degraus/rampas que o step-up resolve,
        não obstáculos horizontais reais.
        """
        p_min, p_max = self.obter_aabb(pos_teste)
        for prop in lista_props:
            pr_min, pr_max = prop.obter_aabb_global()

            # Separação em algum eixo → sem colisão (teste AABB padrão)
            if not (p_max[0] >= pr_min[0] and p_min[0] <= pr_max[0] and
                    p_max[1] >= pr_min[1] and p_min[1] <= pr_max[1] and
                    p_max[2] >= pr_min[2] and p_min[2] <= pr_max[2]):
                continue

            # O topo do prop está dentro da faixa de step-up?
            # Se sim, o ator pode "escalar" — não é bloqueio horizontal.
            topo_prop  = pr_max[1]
            base_ator  = p_min[1]
            if topo_prop <= base_ator + self.max_step_height:
                continue  # tratado pelo step-up, não por bloqueio lateral

            return True  # obstáculo real — bloqueia

        return False

    # ------------------------------------------------------------------
    # Step-up: subir degraus e rampas automaticamente ao andar
    # ------------------------------------------------------------------

    def _tentar_step_up(self, triangulos, lista_props, pos_horizontal):
        """
        Chamado quando um movimento horizontal puro colidiu.
        Tenta elevar o ator em até max_step_height e refaz o teste.

        Retorna (sucesso, novo_y):
          - sucesso=True  → pode mover; novo_y é a altura após o step
          - sucesso=False → é parede real; bloqueia normalmente
        """
        props = lista_props or []

        # Varre incrementos de Y de baixo para cima dentro da janela de step
        # Passos pequenos garantem que não "teletransportamos" por uma parede fina.
        incremento = 0.05
        passo_y    = incremento
        while passo_y <= self.max_step_height + 1e-4:
            pos_elevada = np.array(
                [pos_horizontal[0], self.pos[1] + passo_y, pos_horizontal[2]],
                dtype=np.float32
            )
            mapa_ok  = not self.colidindo_com_mapa(triangulos, pos_elevada)
            props_ok = not self.colidindo_com_props(props, pos_elevada)

            if mapa_ok and props_ok:
                # Também verifica que há chão logo abaixo (não estamos pulando
                # para o vazio além de uma quina de degrau)
                pos_chao = np.array(
                    [pos_horizontal[0], self.pos[1] + passo_y - self.gravidade, pos_horizontal[2]],
                    dtype=np.float32
                )
                tem_chao = (self.colidindo_com_mapa(triangulos, pos_chao) or
                            self.colidindo_com_props(props, pos_chao))
                if tem_chao or passo_y <= incremento:
                    return True, self.pos[1] + passo_y

            passo_y += incremento

        return False, self.pos[1]

    def mover_horizontal_com_step(self, triangulos, lista_props, pos_tentativa_x, pos_tentativa_z):
        """
        Resolve movimento horizontal (X e Z separados) com step-up automático.
        Substitui os dois blocos de teste de eixo que estavam em processar_entrada()
        e em atualizar_ia().

        Uso:
            self.mover_horizontal_com_step(
                triangulos_brutos, lista_props,
                pos_tentativa_x,   # np.array [novo_x, y_atual, z_atual]
                pos_tentativa_z    # np.array [x_atual, y_atual, novo_z]
            )
        """
        props = lista_props or []

        # --- Eixo X ---
        mapa_x  = self.colidindo_com_mapa(triangulos, pos_tentativa_x)
        props_x = self.colidindo_com_props(props, pos_tentativa_x)

        if not mapa_x and not props_x:
            self.pos[0] = pos_tentativa_x[0]
        elif self.on_ground:
            # Bloqueado — tenta step-up antes de desistir
            ok, novo_y = self._tentar_step_up(triangulos, props, pos_tentativa_x)
            if ok:
                self.pos[0] = pos_tentativa_x[0]
                self.pos[1] = novo_y
                self.on_ground = True   # continua "no chão" após escalar

        # --- Eixo Z (usa Y possivelmente já atualizado pelo step de X) ---
        pos_tentativa_z[1] = self.pos[1]  # sincroniza Y caso step-up de X tenha subido
        mapa_z  = self.colidindo_com_mapa(triangulos, pos_tentativa_z)
        props_z = self.colidindo_com_props(props, pos_tentativa_z)

        if not mapa_z and not props_z:
            self.pos[2] = pos_tentativa_z[2]
        elif self.on_ground:
            ok, novo_y = self._tentar_step_up(triangulos, props, pos_tentativa_z)
            if ok:
                self.pos[2] = pos_tentativa_z[2]
                self.pos[1] = novo_y
                self.on_ground = True

    # ------------------------------------------------------------------
    # Física vertical (reutilizada por Player e Inimigo)
    # ------------------------------------------------------------------

    def aplicar_gravidade(self):
        """Acumula velocidade de queda e limita à velocidade terminal."""
        if not self.on_ground:
            self.velocidade_y -= self.gravidade
            if self.velocidade_y < -self.max_velocidade_queda:
                self.velocidade_y = -self.max_velocidade_queda
        elif self.velocidade_y < 0:
            self.velocidade_y = 0.0

    def resolver_eixo_y(self, triangulos_mapa, lista_props=None):
        """
        Move o ator no eixo Y de acordo com velocidade_y e resolve colisões.
        Deve ser chamado uma vez por frame, após aplicar_gravidade().
        """
        props = lista_props or []
        pos_teste_y = np.array(
            [self.pos[0], self.pos[1] + self.velocidade_y, self.pos[2]],
            dtype=np.float32
        )

        colidiu = (self.colidindo_com_mapa(triangulos_mapa, pos_teste_y) or
                   self.colidindo_com_props(props, pos_teste_y))

        if not colidiu:
            self.pos[1] = pos_teste_y[1]
            self.on_ground = False
        else:
            if self.velocidade_y < 0:   # bateu no chão
                self.on_ground = True
            self.velocidade_y = 0.0     # cancela impulso (chão ou teto)