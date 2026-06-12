import numpy as np

class Vertice:
    def __init__(self, x, y, z):
        self.pos = np.array([float(x), float(y), float(z)], dtype=np.float32)

class Triangulo:
    def __init__(self, v1, v2, v3, cor=None):
        self.vertices = [v1, v2, v3] # Lista de 3 objetos da classe Vertice
        self.cor = cor if cor else [0.7, 0.7, 0.7] # Cor padrão caso não tenha material
        self.normal = self.calcular_normal()
        self.d = -np.dot(self.normal, self.vertices[0].pos)

    def calcular_normal(self):
        """Calcula o vetor normal do triângulo para sabermos para onde a face aponta"""
        p1 = self.vertices[0].pos
        p2 = self.vertices[1].pos
        p3 = self.vertices[2].pos
        
        # Vetores das arestas
        u = p2 - p1
        v = p3 - p1
        
        # Produto vetorial (Cross Product) para achar a perpendicular
        normal = np.cross(u, v)
        norma = np.linalg.norm(normal)
        
        if norma == 0:
            return np.array([0.0, 1.0, 0.0]) # Evita divisão por zero em triângulos degenerados
        return normal / norma
    
    def classificar_ponto(self, ponto_xyz, tolerancia=0.001):
        """
        Retorna:
        'FRENTE' se o ponto estiver do lado positivo do plano
        'TRAS' se estiver do lado negativo
        'COPLANAR' se estiver exatamente no plano (dentro da tolerância)
        """
        # Distância com sinal = (Normal . Ponto) + D
        distancia = np.dot(self.normal, ponto_xyz) + self.d

        if distancia > tolerancia:
            return 'FRENTE'
        elif distancia < -tolerancia:
            return 'TRAS'
        else:
            return 'COPLANAR'