import random
from geometria import Vertice, Triangulo

def carregar_obj(caminho_arquivo):
    vertices = []
    triangulos = []

    with open(caminho_arquivo, 'r') as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith('#'):
                continue
            
            partes = linha.split()
            prefixo = partes[0]

            # Se for um vértice (v x y z)
            if prefixo == 'v':
                x, y, z = partes[1:4]
                vertices.append(Vertice(x, y, z))
            
            # Se for uma face (f v1 v2 v3 ...)
            elif prefixo == 'f':
                # Arquivos OBJ podem ter formatos como 'v', 'v/vt' ou 'v/vt/vn'. 
                # Pegamos apenas o primeiro número antes da barra (o índice do vértice).
                indices_face = []
                for p in partes[1:]:
                    idx = int(p.split('/')[0])
                    # Índices negativos no OBJ contam a partir do final
                    if idx < 0:
                        idx = len(vertices) + idx + 1
                    indices_face.append(idx - 1) # Ajusta para indexação zero do Python

                # Como queremos triângulos puros, se a face for um quadrado (quad),
                # nós a dividimos em dois triângulos (Triangulação básica via Fan)
                for i in range(1, len(indices_face) - 1):
                    v1 = vertices[indices_face[0]]
                    v2 = vertices[indices_face[i]]
                    v3 = vertices[indices_face[i + 1]]
                    
                    # Gerar uma cor aleatória por triângulo para nos ajudar no debug visual
                    cor_random = [random.random(), random.random(), random.random()]
                    
                    triangulos.append(Triangulo(v1, v2, v3, cor=cor_random))

    print(f"[Parser] Carregados: {len(vertices)} vértices e {len(triangulos)} triângulos.")
    return triangulos