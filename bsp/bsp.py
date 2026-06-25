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
    
    print("[PVS] Indexando folhas convexas da sub-árvore...")
    total_folhas = _indexar_folhas(raiz, 0)
    print(f"[PVS] Concluído! Total de folhas indexadas para visibilidade: {total_folhas}")
    
    # Guardamos o total de folhas na raiz para sabermos o tamanho da matriz futuramente
    raiz.total_folhas = total_folhas
    return raiz


# --- FUNÇÃO DE BUSCA DO JOGADOR ---
def determinar_folha_ponto(no, ponto):
    """Navega recursivamente para encontrar qual folha_id engloba a posição dada"""
    if no is None:
        return None
        
    if no.is_leaf():
        return no.folha_id
        
    # Classifica a posição (ex: a câmera do Player) em relação ao plano divisor do nó
    lado = no.plano.classificar_ponto(ponto)
    
    if lado in ('FRENTE', 'COPLANAR'):
        return determinar_folha_ponto(no.front, ponto)
    else:
        return determinar_folha_ponto(no.back, ponto)