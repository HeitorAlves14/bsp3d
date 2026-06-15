import pygame
from OpenGL.GL import *

def carregar_textura(caminho_arquivo):
    """Carrega uma imagem usando Pygame e registra como textura no OpenGL"""
    superficie = pygame.image.load(caminho_arquivo)
    # Converte a imagem para string de pixels (RGBA)
    dados_textura = pygame.image.tostring(superficie, "RGBA", True)
    largura = superficie.get_width()
    altura = superficie.get_height()

    # Gera um ID único para a textura no OpenGL
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)

    # Configura os filtros de renderização (importante para o visual retrô pixulado ou suave)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST) # GL_NEAREST dá efeito Pixel Art (Doom)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    
    # Envia os dados de pixel para o OpenGL
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, largura, altura, 0, GL_RGBA, GL_UNSIGNED_BYTE, dados_textura)
    
    return tex_id