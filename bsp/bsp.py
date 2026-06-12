import numpy as np
from OpenGL.GL import *

class BSPNode:
    def __init__(self, divisor=None):
        self.divisor = divisor    # O Triangulo que define o plano de corte deste nó
        self.front = None         # Próximo BSPNode (ou None) do lado da frente
        self.back = None          # Próximo BSPNode (ou None) do lado de trás
        self.poligonos = []       # Triângulos contidos aqui (coplanares ao divisor)

    def is_leaf(self):
        """Se não tem filhos e não tem divisor, é uma folha (espaço vazio ou sólido)"""
        return self.divisor is None and self.front is None and self.back is None

def escolher_melhor_divisor(triangulos):
    """Analisa os candidatos e retorna o triângulo que gera o melhor equilíbrio com menos cortes"""
    if not triangulos:
        return None
        
    melhor_candidato = triangulos[0]
    menor_pontuacao = float('inf')
    
    # Para mapas muito grandes, você pode amostrar (ex: testar no máximo 50 triângulos)
    # para o compilador não demorar minutos para rodar.
    candidatos_a_testar = triangulos[:50] 

    for candidato in candidatos_a_testar:
        frente_qtd = 0
        tras_qtd = 0
        cortes_qtd = 0
        
        for t in triangulos:
            if t is candidato:
                continue
                
            votos = [candidato.classificar_ponto(v.pos) for v in t.vertices]
            frente = votos.count('FRENTE')
            tras = votos.count('TRAS')
            
            if frente > 0 and tras == 0:
                frente_qtd += 1
            elif tras > 0 and frente == 0:
                tras_qtd += 1
            elif frente == 0 and tras == 0:
                pass # Coplanar não afeta o balanço diretamente
            else:
                cortes_qtd += 1 # O triângulo cruza o plano
                
        # Fórmula da Heurística: Prioriza evitar cortes, depois busca o equilíbrio
        pontuacao = (cortes_qtd * 8) + abs(frente_qtd - tras_qtd)
        
        if pontuacao < menor_pontuacao:
            menor_pontuacao = pontuacao
            melhor_candidato = candidato
            
    return melhor_candidato

def construir_arvore_bsp(triangulos):
    # Condição de parada: se não há triângulos, chegamos ao fim deste ramo
    if not triangulos:
        return None

    # 1. Escolha do divisor (Heurística simples: pegamos o primeiro da lista)
    divisor = escolher_melhor_divisor(triangulos)
    
    no_atual = BSPNode(divisor=divisor)
    # O próprio divisor é coplanar a si mesmo, então ele fica neste nó
    no_atual.poligonos.append(divisor)

    lista_frente = []
    lista_tras = []

    # 2. Classificar e separar o restante dos triângulos
    for t in triangulos:
        # if t is divisor:
        #     continue
        # Classifica os 3 vértices do triângulo atual contra o plano do divisor
        votos = [divisor.classificar_ponto(v.pos) for v in t.vertices]

        # Contagem de onde os vértices estão
        frente = votos.count('FRENTE')
        tras = votos.count('TRAS')

        # Heurística de classificação de triângulos inteiros:
        if frente > 0 and tras == 0:
            # Todos os vértices (ou a maioria sem nenhum atrás) estão na frente
            lista_frente.append(t)
        elif tras > 0 and frente == 0:
            # Todos os vértices estão atrás
            lista_tras.append(t)
        elif frente == 0 and tras == 0:
            # Totalmente coplanar ao plano do divisor
            no_atual.poligonos.append(t)
        else:
            # O triângulo cruza o plano (está dividido).
            # Para fins de debug e simplificação atual, mandamos para o lado
            # onde a maior parte dos seus vértices se encontra.
            if frente >= tras:
                lista_frente.append(t)
            else:
                # lista_frente.append(t)
                lista_tras.append(t)

    # 3. Recursão para construir os sub-ramos da árvore
    no_atual.front = construir_arvore_bsp(lista_frente)
    no_atual.back = construir_arvore_bsp(lista_tras)

    return no_atual

def renderizar_bsp(no, pos_camera):
    """Percorre a árvore recursivamente e desenha os polígonos na ordem correta"""
    if no is None:
        return

    # Se chegamos a um nó folha que contém polígonos (se houver)
    if no.divisor is None:
        for t in no.poligonos:
            desenhar_triangulo(t)
        return

    # Descobre de qual lado do plano do nó atual a câmera está
    lado_camera = no.divisor.classificar_ponto(pos_camera)

    if lado_camera == 'FRENTE' or lado_camera == 'COPLANAR':
        # Se a câmera está na frente, o lado de trás está mais longe.
        # Renderizamos primeiro o que está longe (Trás), depois o nó atual, depois a Frente.
        renderizar_bsp(no.back, pos_camera)
        
        for t in no.poligonos:
            desenhar_triangulo(t)
            
        renderizar_bsp(no.front, pos_camera)
    else:
        # Se a câmera está atrás, o lado da frente está mais longe.
        renderizar_bsp(no.front, pos_camera)
        
        for t in no.poligonos:
            desenhar_triangulo(t)
            
        renderizar_bsp(no.back, pos_camera)

def desenhar_triangulo(t):
    """Função auxiliar para enviar o triângulo ao OpenGL"""
    glBegin(GL_TRIANGLES)
    glColor3fv(t.cor)
    for v in t.vertices:
        glVertex3fv(v.pos)
    glEnd()