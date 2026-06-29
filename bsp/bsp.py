import numpy as np
from OpenGL.GL import *

class Plano:
    def __init__(self, p0, p1, p2):
        v1 = p1 - p0
        v2 = p2 - p0
        normal = np.cross(v1, v2)
        norma = np.linalg.norm(normal)
        
        if norma < 1e-6:
            self.normal = np.array([0.0, 1.0, 0.0], dtype=np.float32)
            self.d = 0.0
        else:
            self.normal = normal / norma
            self.d = -np.dot(self.normal, p0)

    def classificar_ponto(self, ponto, epsilon=1e-4):
        dist = np.dot(self.normal, ponto) + self.d
        if dist > epsilon:
            return 'FRENTE'
        elif dist < -epsilon:
            return 'TRAS'
        return 'COPLANAR'


class BSPNode:
    def __init__(self, plano=None):
        self.plano = plano         # Instância da classe Plano
        self.front = None          # Subárvore da frente
        self.back = None           # Subárvore de trás
        self.poligonos = []        # Triângulos coplanares contidos neste nó
        
        # --- NOVO PARA O PVS ---
        self.folha_id = None       # ID único se este nó for uma folha (Leaf)
        self.aabb_min = None       # np.array([x, y, z]) mínimo da caixa delimitadora
        self.aabb_max = None       # np.array([x, y, z]) máximo da caixa delimitadora

    def is_leaf(self):
        # Uma folha na árvore BSP clássica não possui plano divisor nem filhos
        return self.plano is None and self.front is None and self.back is None


def intercalar_vertice(v0, v1, t, classe_triangulo):
    from copy import copy
    novo_v = copy(v0) 
    novo_v.pos = v0.pos + t * (v1.pos - v0.pos)
    if hasattr(v0, 'uv') and v0.uv is not None:
        novo_v.uv = v0.uv + t * (v1.uv - v0.uv)
    return novo_v


def dividir_triangulo(triangulo, plano, lista_frente, lista_tras):
    verts = triangulo.vertices
    votos = [plano.classificar_ponto(v.pos) for v in verts]
    
    votos_limpos = [v if v != 'COPLANAR' else 'FRENTE' for v in votos]
    
    frente_indices = [i for i, v in enumerate(votos_limpos) if v == 'FRENTE']
    tras_indices = [i for i, v in enumerate(votos_limpos) if v == 'TRAS']
    
    from copy import copy
    
    if len(frente_indices) == 1:
        idx_f = frente_indices[0]
        idx_t1 = (idx_f + 1) % 3
        idx_t2 = (idx_f + 2) % 3
        
        vf = verts[idx_f]
        vt1 = verts[idx_t1]
        vt2 = verts[idx_t2]
        
        d_f = np.dot(plano.normal, vf.pos) + plano.d
        d_t1 = np.dot(plano.normal, vt1.pos) + plano.d
        d_t2 = np.dot(plano.normal, vt2.pos) + plano.d
        
        t1 = d_f / (d_f - d_t1)
        t2 = d_f / (d_f - d_t2)
        
        v_int1 = intercalar_vertice(vf, vt1, t1, type(triangulo))
        v_int2 = intercalar_vertice(vf, vt2, t2, type(triangulo))
        
        tf = copy(triangulo)
        tf.vertices = [vf, v_int1, v_int2]
        lista_frente.append(tf)
        
        tt1 = copy(triangulo)
        tt1.vertices = [v_int1, vt1, vt2]
        tt2 = copy(triangulo)
        tt2.vertices = [v_int1, vt2, v_int2]
        lista_tras.append(tt1)
        lista_tras.append(tt2)

    else:
        idx_t = tras_indices[0]
        idx_f1 = (idx_t + 1) % 3
        idx_f2 = (idx_t + 2) % 3
        
        vt = verts[idx_t]
        vf1 = verts[idx_f1]
        vf2 = verts[idx_f2]
        
        d_t = np.dot(plano.normal, vt.pos) + plano.d
        d_f1 = np.dot(plano.normal, vf1.pos) + plano.d
        d_f2 = np.dot(plano.normal, vf2.pos) + plano.d
        
        t1 = d_t / (d_t - d_f1)
        t2 = d_t / (d_t - d_f2)
        
        v_int1 = intercalar_vertice(vt, vf1, t1, type(triangulo))
        v_int2 = intercalar_vertice(vt, vf2, t2, type(triangulo))
        
        tt = copy(triangulo)
        tt.vertices = [vt, v_int1, v_int2]
        lista_tras.append(tt)
        
        tf1 = copy(triangulo)
        tf1.vertices = [v_int1, vf1, vf2]
        tf2 = copy(triangulo)
        tf2.vertices = [v_int1, vf2, v_int2]
        lista_frente.append(tf1)
        lista_frente.append(tf2)


def escolher_melhor_divisor(triangulos):
    if not triangulos:
        return None
        
    melhor_candidato = triangulos[0]
    menor_pontuacao = float('inf')
    candidatos_a_testar = triangulos[:30] 

    for candidato in candidatos_a_testar:
        p0, p1, p2 = candidato.vertices[0].pos, candidato.vertices[1].pos, candidato.vertices[2].pos
        plano_temp = Plano(p0, p1, p2)
        
        frente_qtd = 0
        tras_qtd = 0
        cortes_qtd = 0
        
        for t in triangulos:
            if t is candidato:
                continue
                
            votos = [plano_temp.classificar_ponto(v.pos) for v in t.vertices]
            frente = votos.count('FRENTE')
            tras = votos.count('TRAS')
            
            if frente > 0 and tras == 0:
                frente_qtd += 1
            elif tras > 0 and frente == 0:
                tras_qtd += 1
            elif frente == 0 and tras == 0:
                pass 
            else:
                cortes_qtd += 1 
                
        pontuacao = (cortes_qtd * 12) + abs(frente_qtd - tras_qtd)
        
        if pontuacao < menor_pontuacao:
            menor_pontuacao = pontuacao
            melhor_candidato = candidato
            
    return melhor_candidato


def _construir_bsp_recursivo(triangulos):
    """Função interna para construir a geometria crua da árvore"""
    if not triangulos:
        # Se não há triângulos, criamos um nó folha vazio (espaço navegável)
        return BSPNode()

    divisor = escolher_melhor_divisor(triangulos)
    p0, p1, p2 = divisor.vertices[0].pos, divisor.vertices[1].pos, divisor.vertices[2].pos
    plano_divisor = Plano(p0, p1, p2)
    
    no_atual = BSPNode(plano=plano_divisor)
    no_atual.poligonos.append(divisor)

    lista_frente = []
    lista_tras = []

    for t in triangulos:
        if t is divisor:
            continue

        votos = [plano_divisor.classificar_ponto(v.pos) for v in t.vertices]
        frente = votos.count('FRENTE')
        tras = votos.count('TRAS')

        if frente > 0 and tras == 0:
            lista_frente.append(t)
        elif tras > 0 and frente == 0:
            lista_tras.append(t)
        elif frente == 0 and tras == 0:
            no_atual.poligonos.append(t)
        else:
            dividir_triangulo(t, plano_divisor, lista_frente, lista_tras)

    no_atual.front = _construir_bsp_recursivo(lista_frente)
    no_atual.back = _construir_bsp_recursivo(lista_tras)

    return no_atual


def _indexar_folhas(no, contador_id=0):
    """Percorre a árvore aplicando IDs únicos sequenciais nas folhas (Leaves)"""
    if no is None:
        return contador_id
        
    if no.is_leaf():
        no.folha_id = contador_id
        contador_id += 1
        return contador_id
        
    contador_id = _indexar_folhas(no.front, contador_id)
    contador_id = _indexar_folhas(no.back, contador_id)
    return contador_id


def construir_arvore_bsp(triangulos):
    """Função principal chamada pela main.py"""
    print("[BSP] Compilando geometria inicial...")
    raiz = _construir_bsp_recursivo(triangulos)
    
    print("[PVS] Indexando folhas para visibilidade...")
    total_folhas = _indexar_folhas(raiz, 0)
    raiz.total_folhas = total_folhas
    
    print("[AABB] Gerando caixas delimitadoras para Frustum Culling otimizado...")
    _calcular_aabbs_da_arvore(raiz)
    
    print(f"[BSP] Pronto! Total de folhas: {total_folhas}")
    return raiz


# --- FUNÇÃO DE BUSCA DO JOGADOR ---
def _calcular_aabbs_da_arvore(no):
    """Calcula a AABB de cada nó de baixo para cima englobando seus polígonos e filhos"""
    if no is None:
        return None, None
        
    # Inicializa os limites com valores extremos reversos
    p_min = np.array([float('inf'), float('inf'), float('inf')], dtype=np.float32)
    p_max = np.array([float('-inf'), float('-inf'), float('-inf')], dtype=np.float32)
    
    # 1. Expande a caixa com os triângulos contidos neste nó
    for t in no.poligonos:
        for v in t.vertices:
            p_min = np.minimum(p_min, v.pos)
            p_max = np.maximum(p_max, v.pos)
            
    # 2. Expande com a AABB da subárvore da frente
    if no.front:
        f_min, f_max = _calcular_aabbs_da_arvore(no.front)
        if f_min is not None:
            p_min = np.minimum(p_min, f_min)
            p_max = np.maximum(p_max, f_max)
            
    # 3. Expande com a AABB da subárvore de trás
    if no.back:
        b_min, b_max = _calcular_aabbs_da_arvore(no.back)
        if b_min is not None:
            p_min = np.minimum(p_min, b_min)
            p_max = np.maximum(p_max, b_max)
            
    # Se o nó for uma folha completamente vazia sem polígonos, retorna None
    if np.any(p_min == float('inf')):
        return None, None
        
    no.aabb_min = p_min
    no.aabb_max = p_max
    return p_min, p_max


def determinar_folha_ponto(no, ponto):
    if no is None:
        return None
    if no.is_leaf():
        return no.folha_id
    if no.plano is None:
        return None
        
    lado = no.plano.classificar_ponto(ponto)
    if lado in ('FRENTE', 'COPLANAR'):
        return determinar_folha_ponto(no.front, ponto)
    else:
        return determinar_folha_ponto(no.back, ponto)

# ---------------------------------------------------------------------------
# CONSULTA ESPACIAL ACELERADA — colisão via BSP em vez de lista bruta
# ---------------------------------------------------------------------------

def _triangulo_relevante(t, ponto, raio_xz, raio_y):
    """
    Critério de relevância correto para triângulos grandes (chão, teto, paredes).

    O problema com "distância ao centro" é que um chão de 20x20 unidades tem
    seu centro a metros do ator — mas a superfície está logo abaixo dele.

    Solução: medir a distância ao PLANO do triângulo (signed distance) e a
    distância horizontal ao AABB do triângulo separadamente.

      - dist_plano pequena → o ator está perto da superfície (Y relevante)
      - projeção XZ dentro da AABB + margem → o ator está sobre o triângulo
    """
    # 1. Distância com sinal do ponto ao plano do triângulo
    dist_plano = abs(np.dot(t.normal, ponto) + t.d)

    # Triângulos predominantemente horizontais (chão/teto): normal.y dominante
    # → usa raio_y para distância ao plano, raio_xz para proximidade lateral
    normal_y = abs(t.normal[1])

    if normal_y > 0.5:
        # Superfície horizontal — o critério crítico é a distância vertical ao plano
        if dist_plano > raio_y:
            return False
        # Verifica se o ator está sobre a AABB XZ do triângulo (+ margem)
        xs = [v.pos[0] for v in t.vertices]
        zs = [v.pos[2] for v in t.vertices]
        margem = raio_xz * 0.5
        if (ponto[0] < min(xs) - margem or ponto[0] > max(xs) + margem or
                ponto[2] < min(zs) - margem or ponto[2] > max(zs) + margem):
            return False
        return True
    else:
        # Superfície vertical (parede) — distância ao plano é proximidade lateral
        if dist_plano > raio_xz:
            return False
        # Verifica extensão vertical
        ys = [v.pos[1] for v in t.vertices]
        if ponto[1] > max(ys) + raio_y or ponto[1] < min(ys) - raio_y:
            return False
        return True


def coletar_triangulos_proximos(no, ponto, raio_xz=3.0, raio_y=4.0):
    """
    Coleta triângulos relevantes para colisão descendo a árvore BSP.

    Usa critérios separados por eixo:
      - raio_xz: distância horizontal para paredes e extensão XZ para chão/teto
      - raio_y:  distância vertical ao plano para superfícies horizontais

    Isso resolve o problema de chão/teto serem ignorados com raio pequeno
    (porque o centro do triângulo fica longe) sem precisar usar raio grande
    globalmente (o que incluiria triângulos desnecessários e custosos).

    Uso em main.py:
        tri = coletar_triangulos_proximos(arvore_bsp, player.pos)
        player.mover_horizontal_com_step(tri, lista_props, pos_x, pos_z)
        player.atualizar_fisica_vertical(tri, lista_props)
    """
    if no is None:
        return []

    resultado = []

    for t in no.poligonos:
        if _triangulo_relevante(t, ponto, raio_xz, raio_y):
            resultado.append(t)

    if no.plano is None:
        return resultado

    # Distância com sinal ao plano divisor deste nó
    dist = np.dot(no.plano.normal, ponto) + no.plano.d

    # Usa o raio adequado ao tipo do plano divisor para decidir se desce um ou dois lados
    normal_y_divisor = abs(no.plano.normal[1])
    raio_decisao = raio_y if normal_y_divisor > 0.5 else raio_xz

    if dist > raio_decisao:
        resultado += coletar_triangulos_proximos(no.front, ponto, raio_xz, raio_y)
    elif dist < -raio_decisao:
        resultado += coletar_triangulos_proximos(no.back,  ponto, raio_xz, raio_y)
    else:
        resultado += coletar_triangulos_proximos(no.front, ponto, raio_xz, raio_y)
        resultado += coletar_triangulos_proximos(no.back,  ponto, raio_xz, raio_y)

    return resultado