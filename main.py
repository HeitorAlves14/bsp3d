import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from paser_obj import carregar_obj
from bsp.bsp import construir_arvore_bsp, renderizar_bsp
from player import Player
import math
import numpy as np

# --- CONFIGURAÇÕES DA JANELA ---
LARGURA, ALTURA = 0, 0 # 800, 600

# --- CONFIGURAÇÕES DA CÂMERA ---
# Posição inicial no espaço (X, Y, Z)
# cam_x, cam_y, cam_z = 0.0, 0.0, 5.0
# Rotação da câmera (Yaw: olhar para os lados, Pitch: olhar para cima/baixo)
yaw, pitch = -90.0, 0.0
velocidade_mov = 0.02
sensibilidade_mouse = 0.1
bob_amplitude = 0.05
bob_speed = 8.0
bob_phase = 0.0
bob_offset = 0.0
player = Player(x=0.0, y=0.0, z=0.0, largura=0.8, altura=1.8)
# Variável global para guardar o mapa
triangulos_brutos = []
mapa_triangulos = []
arvore_bsp = None

def inicializar_opengl():
    """Configura o estado inicial do OpenGL"""
    glEnable(GL_DEPTH_TEST) # Ativa o Z-Buffer (essencial para 3D)
    
    # Configura a Matriz de Projeção (Perspectiva)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    # fov, aspect ratio, near, far
    # Isso aqui é bem interessante
    gluPerspective(90, (LARGURA / ALTURA), 0.01, 100.0)
    
    # Muda para a Matriz de Desenho (Modelview)
    glMatrixMode(GL_MODELVIEW)
    # Habilita o descarte de faces
    glEnable(GL_CULL_FACE)

    # Define que as faces de trás são as que devem ser descartadas (padrão)
    glCullFace(GL_BACK)

    # Define a ordem dos vértices para a face da frente (ex: sentido anti-horário)
    glFrontFace(GL_CCW)


def atualizar_camera():
    """Calcula a direção do vetor que a câmera está olhando e atualiza a matriz"""
    global yaw, pitch, bob_phase, bob_offset #, cam_x, cam_y, cam_z 
    
    # Limita o olhar para cima/baixo para não capotar a câmera
    pitch = max(-89.0, min(89.0, pitch))
    
    # Conversão de Graus para Radianos (Matemática de Esferas)
    yaw_rad = math.radians(yaw)
    pitch_rad = math.radians(pitch)
    
    # Calcula o vetor "Forward" (Para onde estamos olhando)
    dir_x = math.cos(yaw_rad) * math.cos(pitch_rad)
    dir_y = math.sin(pitch_rad)
    dir_z = math.sin(yaw_rad) * math.cos(pitch_rad)
    
    glLoadIdentity()
    # gluLookAt(
    #     player.pos[0], player.pos[1] + player.altura - 0.2, player.pos[2], 
    #     player.pos[0] + dir_x, player.pos[1] + player.altura - 0.2 + dir_y, player.pos[2] + dir_z, 
    #     0.0, 1.0, 0.0
    # )
    bob_phase += np.linalg.norm(player.velocidade) * 0.1
    if np.linalg.norm(player.velocidade) > 0.01 and player.on_ground:
        target_offset = math.sin(bob_phase * bob_speed) * bob_amplitude
    else:
        target_offset = 0.0

    # interpolação suave
    bob_offset = bob_offset * 0.9 + target_offset * 0.1

    gluLookAt(
        player.pos[0] + player.shake_offset[0],
        player.pos[1] + player.altura - 0.2 + bob_offset + player.shake_offset[1],
        player.pos[2] + player.shake_offset[2],
        player.pos[0] + dir_x + player.shake_offset[0],
        player.pos[1] + player.altura - 0.2 + dir_y + bob_offset + player.shake_offset[1],
        player.pos[2] + dir_z + player.shake_offset[2],
        0.0, 1.0, 0.0
    )


def processar_entrada():
    """Gerencia a movimentação livre baseada nas teclas pressionadas"""
    global yaw, triangulos_brutos
    
    keys = pygame.key.get_pressed()
    yaw_rad = math.radians(yaw)

    # --- APLICAR GRAVIDADE ---
    if not player.on_ground:
        player.velocidade_y -= player.gravidade
        # Limita a velocidade máxima de queda (terminal velocity) para não atravessar o chão por bugs
        if player.velocidade_y < -0.5:
            player.velocidade_y = -0.5
    else:
        # Pequena força nula ou residual para mantê-lo colado ao chão nas checagens
        if player.velocidade_y < 0:
            player.velocidade_y = 0.0
    
    # Direções de movimento baseadas no plano XZ (horizontal)
    forward = np.array([math.cos(yaw_rad), 0.0, math.sin(yaw_rad)], dtype=np.float32)
    right = np.array([-math.sin(yaw_rad), 0.0, math.cos(yaw_rad)], dtype=np.float32)
    
    # Próxima posição pretendida
    # pos_tentativa = np.copy(player.pos)
    
    velocidade_mov = 0.01 if keys[K_LSHIFT] else 0.03
    if keys[K_w]: player.velocidade += forward * velocidade_mov
    if keys[K_s]: player.velocidade -= forward * velocidade_mov
    if keys[K_a]: player.velocidade -= right * velocidade_mov
    if keys[K_d]: player.velocidade += right * velocidade_mov
    if keys[K_SPACE]: player.pular()
    if keys[K_LCTRL]:
        player.agachado = True
        player.altura = player.altura_agachado
    else:
        player.agachado = False
        player.altura = player.altura_normal
    player.velocidade *= player.friccao

    # Próxima posição
    pos_tentativa = player.pos + player.velocidade
        
    # Sistema de colisão por eixos separados (permite deslizar nas paredes!)
    # Testa movimento no Eixo X
    pos_teste_x = np.array([pos_tentativa[0], player.pos[1], player.pos[2]])
    if not player.checar_colisao(triangulos_brutos, pos_teste_x):
        player.pos[0] = pos_tentativa[0]
        
    # Testa movimento no Eixo Z
    pos_teste_z = np.array([player.pos[0], player.pos[1], pos_tentativa[2]])
    if not player.checar_colisao(triangulos_brutos, pos_teste_z):
        player.pos[2] = pos_tentativa[2]

    # --- DEBUG DE VOO LIVRE ---
    # Teclas de voo livre para Debug (Ignoram colisão vertical por enquanto)
    # if keys[K_SPACE]:  player.pos[1] += velocidade_mov
    # if keys[K_LSHIFT]: player.pos[1] -= velocidade_mov
    # --- ... ---

    # 3. TESTE NO EIXO Y (FÍSICA VERTICAL: QUEDA E PULO)
    # Movemos o jogador temporariamente no eixo Y de acordo com a sua velocidade atual
    pos_teste_y = np.array([player.pos[0], player.pos[1] + player.velocidade_y, player.pos[2]])
    
    if not player.checar_colisao(triangulos_brutos, pos_teste_y):
        # Se não colidiu com nada, ele está a mover-se no ar (a cair ou a subir no pulo)
        player.pos[1] = pos_teste_y[1]
        player.on_ground = False
    else:
        # Se colidiu movendo-se para baixo, significa que bateu no CHÃO
        if player.velocidade_y < 0:
            player.on_ground = True
            # player.pos[1] = math.floor(player.pos[1])
            player.velocidade_y = 0.0
        # Se colidiu movendo-se para cima, bateu com a cabeça no TETO
        elif player.velocidade_y > 0:
            player.velocidade_y = 0.0 # Cancela o impulso para cima e começa a cair
    
    if player.shake_intensidade > 0.01:
        # Gera deslocamento aleatório em X e Y
        player.shake_offset[0] = (np.random.rand() - 0.5) * player.shake_intensidade
        player.shake_offset[1] = (np.random.rand() - 0.5) * player.shake_intensidade
        player.shake_offset[2] = 0.0
        
        # Decai suavemente
        player.shake_intensidade *= player.shake_decay
    else:
        player.shake_offset[:] = 0.0


def desenhar_entidades():
    """Percorre a lista de triângulos importados e desenha no OpenGL"""
    glBegin(GL_TRIANGLES)
    for triangulo in mapa_triangulos:
        # Aplica a cor gerada para esse triângulo
        glColor3fv(triangulo.cor)
        
        # Passa os 3 vértices do triângulo para o pipeline
        for vertice in triangulo.vertices:
            glVertex3fv(vertice.pos)
    glEnd()

def main():
    global yaw, pitch, triangulos_brutos, arvore_bsp
    global LARGURA, ALTURA
    
    pygame.init()
    screen = pygame.display.set_mode((0,0), DOUBLEBUF | OPENGL | FULLSCREEN)
    triangulos_brutos = carregar_obj("escritorio.obj")
    mapa_triangulos = carregar_obj("osakat.obj")
    arvore_bsp = construir_arvore_bsp(triangulos_brutos)
    pygame.display.set_caption("BSP Engine Engine - Debug Room")
    
    # Prende o mouse na janela e o esconde
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)
    # info = pygame.display.Info()
    LARGURA, ALTURA = screen.get_size()
    
    inicializar_opengl()
    clock = pygame.time.Clock()
    
    executando = True
    while executando:
        for event in pygame.event.get():
            if event.type == QUIT:
                executando = False
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    executando = False
                if event.key == K_e:
                    player.iniciar_shake()
                
        # --- ROTAÇÃO COM O MOUSE ---
        mouse_dx, mouse_dy = pygame.mouse.get_rel()
        yaw += mouse_dx * sensibilidade_mouse
        pitch -= mouse_dy * sensibilidade_mouse # Invertido para o olhar padrão FPS
        
        # --- MOVIMENTAÇÃO ---
        processar_entrada()
        
        # --- RENDERIZAÇÃO ---
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        atualizar_camera()
        # desenhar_sala_debug()
        # desenhar_mapa_blender()
        # pos_camera = np.array([cam_x, cam_y, cam_z], dtype=np.float32)
        # if len(triangulos_brutos) > 0:
        #     lado = triangulos_brutos[0].classificar_ponto(pos_camera)
        #     print(f"A câmera está na: {lado} do primeiro triângulo", end="\r")
        desenhar_entidades()
        renderizar_bsp(arvore_bsp, player.pos)
        
        pygame.display.flip()
        clock.tick(60) # Mantém estável em 60 FPS

    pygame.quit()

if __name__ == "__main__":
    main()