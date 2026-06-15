from OpenGL.GL import *

def desenhar_arma_hud(textura_normal, textura_disparo, atirando, timer, largura_tela, altura_tela):
    """Muda para o modo 2D e desenha a arma centralizada na parte inferior da tela"""
    
    # 1. Salva matrizes e muda para Projeção Ortográfica (2D)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, largura_tela, 0, altura_tela, -1, 1)
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Desativa o teste de profundidade para a arma não sumir atrás das paredes
    glDisable(GL_DEPTH_TEST)
    
    # Escolhe o frame baseado no timer de disparo (Animação de tiro rápida)
    tex_id = textura_disparo if (atirando and timer < 10) else textura_normal
    glBindTexture(GL_TEXTURE_2D, tex_id)

    # Configura o tamanho e posição da arma na tela
    tam_w = 256
    tam_h = 256
    x_centro = (largura_tela / 2) - (tam_w / 2)
    y_base = 0 # Fundo da tela

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0); glVertex2f(x_centro, y_base)
    glTexCoord2f(1.0, 0.0); glVertex2f(x_centro + tam_w, y_base)
    glTexCoord2f(1.0, 1.0); glVertex2f(x_centro + tam_w, y_base + tam_h)
    glTexCoord2f(0.0, 1.0); glVertex2f(x_centro, y_base + tam_h)
    glEnd()

    # 2. Restaura o estado 3D do OpenGL para o próximo frame
    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()