import numpy as np
import math
from ator import Ator


class Player(Ator):
    """
    Jogador em primeira pessoa.
    Herda AABB, colisão com mapa/props e física vertical de Ator.
    Mantém suas funcionalidades exclusivas: pulo, agachamento, arma,
    câmera shake, inventário.
    """

    def __init__(self, x, y, z, largura=1.0, altura=2.0):
        super().__init__(x, y, z, largura, altura)

        # --- Dimensões variáveis (agachamento) ---
        self.altura_normal   = altura
        self.altura_agachado = altura * 0.5
        self.agachado        = False

        # --- Física do pulo ---
        self.forca_pulo = 0.25
        # max_step_height herdado de Ator (0.4) — ajuste aqui se quiser valor diferente para o player

        # --- Câmera shake ---
        self.shake_intensidade = 0.0
        self.shake_decay       = 0.9
        self.shake_offset      = np.zeros(3, dtype=np.float32)

        # --- Combate ---
        self.esta_atirando = False
        self.timer_tiro    = 0
        self.dano_arma     = 35

        # --- Status ---
        self.vida    = 100
        self.municao = 20
        self.chaves  = []

        # --- Velocidade horizontal (para o bob de câmera) ---
        self.velocidade = np.zeros(3, dtype=np.float32)
        self.friccao    = 0.85

    # ------------------------------------------------------------------
    # Pulo
    # ------------------------------------------------------------------

    def pular(self):
        if self.on_ground:
            self.velocidade_y = self.forca_pulo
            self.on_ground    = False

    # ------------------------------------------------------------------
    # Colisão extra: props (AABB vs AABB)
    # NOTA: colidindo_com_props já existe em Ator; este método é um alias
    # para manter compatibilidade com chamadas antigas em main.py que
    # passavam lista_props como segundo argumento de checar_colisao.
    # ------------------------------------------------------------------

    def checar_colisao(self, triangulos_mapa, pos_teste):
        """
        Compatibilidade com o main.py existente.
        Testa colisão com o mapa usando os 8 cantos da AABB (via Ator).
        """
        return self.colidindo_com_mapa(triangulos_mapa, pos_teste)

    def checar_colisao_com_props(self, lista_props, pos_teste):
        return self.colidindo_com_props(lista_props, pos_teste)

    # ------------------------------------------------------------------
    # Física vertical — wrapper que chama os métodos de Ator
    # ------------------------------------------------------------------

    def atualizar_fisica_vertical(self, triangulos_mapa, lista_props=None):
        """
        Chame uma vez por frame em main.py, no lugar do bloco de
        'pos_teste_y' que estava embutido em processar_entrada().
        """
        self.aplicar_gravidade()
        self.resolver_eixo_y(triangulos_mapa, lista_props)

    # ------------------------------------------------------------------
    # Câmera shake
    # ------------------------------------------------------------------

    def iniciar_shake(self, intensidade=0.2):
        self.shake_intensidade = intensidade

    def atualizar_shake(self):
        if self.shake_intensidade > 0.01:
            self.shake_offset[0] = (np.random.rand() - 0.5) * self.shake_intensidade
            self.shake_offset[1] = (np.random.rand() - 0.5) * self.shake_intensidade
            self.shake_offset[2] = 0.0
            self.shake_intensidade *= self.shake_decay
        else:
            self.shake_offset[:] = 0.0

    # ------------------------------------------------------------------
    # Raycasting para tiro
    # ------------------------------------------------------------------

    def disparar_raio(self, yaw, pitch, lista_inimigos):
        yaw_rad   = math.radians(yaw)
        pitch_rad = math.radians(pitch)

        dir_x = math.cos(yaw_rad) * math.cos(pitch_rad)
        dir_y = math.sin(pitch_rad)
        dir_z = math.sin(yaw_rad) * math.cos(pitch_rad)
        direcao = np.array([dir_x, dir_y, dir_z], dtype=np.float32)

        origem = np.copy(self.pos)
        origem[1] += self.altura * 0.8

        inimigo_atingido = None
        menor_dist       = float('inf')

        for inimigo in lista_inimigos:
            b_min, b_max = inimigo.obter_aabb()

            def slab(axis):
                d = direcao[axis]
                if d == 0:
                    return float('-inf'), float('inf')
                t0 = (b_min[axis] - origem[axis]) / d
                t1 = (b_max[axis] - origem[axis]) / d
                return (t0, t1) if t0 < t1 else (t1, t0)

            txn, txx = slab(0)
            tyn, tyx = slab(1)
            tzn, tzx = slab(2)

            tmin = max(txn, tyn, tzn)
            tmax = min(txx, tyx, tzx)

            if tmax <= 0 or tmin > tmax:
                continue
            if tmin < menor_dist:
                menor_dist       = tmin
                inimigo_atingido = inimigo

        if inimigo_atingido:
            inimigo_atingido.vida -= self.dano_arma
            print(f"[Combate] Acertou! Vida: {inimigo_atingido.vida}")

            pos_impacto    = np.copy(inimigo_atingido.pos)
            pos_impacto[1] += inimigo_atingido.altura * 0.5

            if inimigo_atingido.vida <= 0:
                print("[Combate] Inimigo eliminado!")
                lista_inimigos.remove(inimigo_atingido)
                return pos_impacto, True

            return pos_impacto, False

        return None, False