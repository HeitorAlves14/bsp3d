import pygame
import math
import numpy as np

from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image

from parser_obj import carregar_mapa_blender
from gerenciador_textura import carregar_textura
from bsp.bsp import construir_arvore_bsp, renderizar_bsp
from player import Player
from inimigo import Inimigo
from frustum import Frustum
from hud import desenhar_arma_hud
from particula import Particula
from coletavel import Coletavel
from shader_manager import GerenciadorShader, LuzPontual
from renderer_shader import RendererBSP, RendererProps


# --- CONFIGURAÇÕES DA JANELA ---
LARGURA, ALTURA = 0, 0
yaw, pitch = -90.0, 0.0
vel_mov = 0.8
sensibilidade_mouse = 0.1
bob_amplitude = 0.05
bob_speed = 8.0
bob_phase = 0.0
bob_offset = 0.0
player = Player(x=0.0, y=0.0, z=0.0, largura=0.8, altura=1.8)
frustum = Frustum()
# Variável global para guardar o mapa
triangulos_brutos = []
mapa_triangulos = []
lista_props = []
lista_inimigos = []
lista_particulas = []
lista_coletaveis = []
arvore_bsp = None
# Shader
shader_mgr = None
renderer_bsp = None
renderer_prop = None

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
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)


def atualizar_camera():
    """Calcula a direção do vetor que a câmera está olhando e atualiza a matriz"""
    global yaw, pitch, bob_phase, bob_offset
    
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
    bob_phase += np.linalg.norm(player.velocidade_y) * 0.1
    if np.linalg.norm(player.velocidade_y) > 0.01 and player.on_ground:
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
    
    keys     = pygame.key.get_pressed()
    yaw_rad  = math.radians(yaw)
    forward  = np.array([ math.cos(yaw_rad), 0.0,  math.sin(yaw_rad)], dtype=np.float32)
    right    = np.array([-math.sin(yaw_rad), 0.0,  math.cos(yaw_rad)], dtype=np.float32)
    
    # Próxima posição pretendida
    vel_mov = 0.05 if keys[K_LSHIFT] else 0.1
    pos_tentativa = np.copy(player.pos)

    if keys[K_w]: pos_tentativa += forward * vel_mov # player.velocidade
    if keys[K_s]: pos_tentativa -= forward * vel_mov
    if keys[K_a]: pos_tentativa -= right * vel_mov
    if keys[K_d]: pos_tentativa += right * vel_mov
    if keys[K_SPACE]: player.pular()

    if keys[K_LCTRL]:
        player.agachado = True
        player.altura = player.altura_agachado
    else:
        player.agachado = False
        player.altura = player.altura_normal

    # Movimento horizontal por eixos separados (deslizamento em paredes)
    pos_x = np.array([pos_tentativa[0], player.pos[1], player.pos[2]])
    if not (player.checar_colisao(triangulos_brutos, pos_x) or 
            player.checar_colisao_com_props(lista_props, pos_x)):
        player.pos[0] = pos_tentativa[0]
 
    pos_z = np.array([player.pos[0], player.pos[1], pos_tentativa[2]])
    if not (player.checar_colisao(triangulos_brutos, pos_z) or 
            player.checar_colisao_com_props(lista_props, pos_z)):
        player.pos[2] = pos_tentativa[2]
    
    player.mover_horizontal_com_step(triangulos_brutos, lista_props, pos_x, pos_z)
 
    # Física vertical (gravidade + pulo) — delegado para Ator via Player
    player.atualizar_fisica_vertical(triangulos_brutos, lista_props)
 
    # Câmera shake
    player.atualizar_shake()

def main():
    global yaw, pitch, triangulos_brutos, arvore_bsp, shader_mgr
    global lista_coletaveis, lista_props, lista_inimigos, lista_particulas
    global LARGURA, ALTURA
    
    pygame.init()
    screen = pygame.display.set_mode((0,0), DOUBLEBUF | OPENGL | FULLSCREEN)
    pygame.display.set_caption("BSP Engine Engine - Debug Room")
    
    # Prende o mouse na janela e o esconde
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)
    # info = pygame.display.Info()
    LARGURA, ALTURA = screen.get_size()
    
    inicializar_opengl()

    clock = pygame.time.Clock()

    glEnable(GL_TEXTURE_2D) # Comando crucial que liga as texturas no OpenGL
    
    # Carregue qualquer imagem quadrada (ex: 256x256 ou 512x512 pixels) para teste 
    
    # Carrega o mapa passando o ID da textura
    triangulos_brutos, lista_props = carregar_mapa_blender("rua.obj")
    
    # Carrega a imagem do monstro (garanta que o OpenGL esteja com GL_BLEND ativo para transparência!)
    id_tex_inimigo = carregar_textura("options.png")
    
    lista_inimigos = [
        Inimigo(x=5.0, y=1.0, z=-5.0, textura_id=id_tex_inimigo),
        Inimigo(x=-3.0, y=1.0, z=-8.0, textura_id=id_tex_inimigo)
    ]
    tex_arma_idle = carregar_textura("options.png")
    tex_arma_shoot = carregar_textura("muito engracado.png")

    # Carrega as imagens dos itens (PNGs transparentes)
    tex_kit_medico = carregar_textura("gidao.png")
    tex_municao = carregar_textura("gidao.png")
    
    lista_coletaveis = [
        Coletavel(x=2.0, y=0.0, z=-3.0, tipo='VIDA', textura_id=tex_kit_medico, quantidade=25),
        Coletavel(x=-4.0, y=0.0, z=-6.0, tipo='MUNICAO', textura_id=tex_municao, quantidade=15)
    ]
    
    print("[BSP] Compilando árvore com suporte a texturas...")
    arvore_bsp = construir_arvore_bsp(triangulos_brutos)
    print("[BSP] Pronto!")
    
    shader_mgr = GerenciadorShader()

    shader_mgr.usar()
    shader_mgr.configurar_ambiente(cor=(0.10, 0.09, 0.15), forca=5.50)
    shader_mgr.configurar_fog(inicio=50.0, fim=100.0, cor=(0.04, 0.03, 0.07))

    luzes_sala = [
        # Sala 1 — lâmpada fluorescente fria (corredor interno)
        LuzPontual(
            pos=(3.0, 2.5, -5.0),
            cor=(0.80, 0.90, 1.00),   # branco-azulado
            raio=8.0,
            intensidade=1.4,
        ),
        # # Sala 2 — tocha na parede (sala medieval / dungeon)
        # LuzPontual(
        #     pos=(-8.0, 1.8, -12.0),
        #     cor=(1.00, 0.50, 0.10),   # laranja fogo
        #     raio=6.0,
        #     intensidade=1.8,
        # ),
        # Sala 3 — luz de emergência (corredor de fuga)
        # LuzPontual(
        #     pos=(0.0, 2.5, 0.0),
        #     cor=(1.00, 0.10, 0.05),   # vermelho emergência
        #     raio=5.0,
        #     intensidade=1.2,
        # ),
            # Adicione quantas quiser até MAX_POINT_LIGHTS (padrão = 8)
    ]
    shader_mgr.definir_luzes_sala(luzes_sala)
    shader_mgr.parar()

    

    renderer_bsp   = RendererBSP(arvore_bsp, shader_mgr)
    renderer_props = RendererProps(lista_props, shader_mgr)
    
    sol_visivel = True
    executando = True
    while executando:
        for event in pygame.event.get():
            if event.type == QUIT:
                executando = False
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    executando = False
                if event.key == K_e:
                    for prop in lista_props:
                        if prop.eh_porta:
                            # Calcula a distância em linha reta entre o player e a porta
                            distancia = np.linalg.norm(player.pos - prop.pos)
                            
                            # Se estiver a menos de 3 unidades de distância, ativa a porta!
                            if distancia < 3.0:
                                prop.interagir()
                if event.key == K_q:
                    player.iniciar_shake()

            if event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    if not player.esta_atirando:
                        player.esta_atirando = True
                        player.timer_tiro = 0
                        
                        # Dispara o raio e pega as informações do impacto
                        pos_impacto, foi_fatal = player.disparar_raio(yaw, pitch, lista_inimigos)
                        
                        if pos_impacto is not None:
                            # Escolhe a cor do sangue (Ex: Vermelho [1.0, 0.0, 0.0])
                            cor_sangue = (1.0, 0.0, 0.0) if not foi_fatal else (0.8, 0.1, 0.0)
                            quantidade = 25 if not foi_fatal else 60 # Mais partículas se morrer
                            
                            # Instancia as partículas na memória
                            for _ in range(quantidade):
                                lista_particulas.append(Particula(pos_impacto[0], pos_impacto[1], pos_impacto[2], cor_sangue))
                
        # --- ROTAÇÃO COM O MOUSE ---
        mouse_dx, mouse_dy = pygame.mouse.get_rel()
        yaw += mouse_dx * sensibilidade_mouse
        pitch -= mouse_dy * sensibilidade_mouse # Invertido para o olhar padrão FPS
        
        # --- MOVIMENTAÇÃO ---
        processar_entrada()
        for prop in lista_props: prop.atualizar(player)
        # pos_player_atual = np.array([player.pos[0], player.pos[1], player.pos[2]], dtype=np.float32)
        for inimigo in lista_inimigos:
            inimigo.atualizar_ia(player, triangulos_brutos, lista_props, lista_inimigos)
        lista_coletaveis = [item for item in lista_coletaveis if not item.atualizar(player)]
        lista_particulas = [p for p in lista_particulas if p.atualizar()]
        # --- RENDERIZAÇÃO ---
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        atualizar_camera()
        frustum.atualizar()

        # 1. Desenha o chão e paredes ordenados e filtrados pelo Frustum na BSP
        renderer_bsp.renderizar(
            player.pos,
            frustum,
            direcao_sol=(0.0, 90.0, 0.0),   # ← ajuste para o ângulo do seu sol
            sol_ativo=sol_visivel,
        )
        # Gerencia o tempo que a animação de tiro fica na tela
        if player.esta_atirando:
            player.timer_tiro += 1
            if player.timer_tiro > 15: # ~1/4 de segundo de animação
                player.esta_atirando = False
        
        renderer_props.renderizar_todos(lista_props, frustum, sol_ativo=sol_visivel)
        for prop in lista_props:
            prop.atualizar(player)
        
        for inimigo in lista_inimigos:
            inimigo.renderizar(frustum)
        for item in lista_coletaveis:
            item.renderizar(frustum)
        glPushAttrib(GL_CURRENT_BIT)
        for particula in lista_particulas:
            particula.renderizar()
        glPopAttrib()
            
        # NOVO: Desenha a arma 2D na tela por cima do cenário 3D
        desenhar_arma_hud(tex_arma_idle, tex_arma_shoot, player.esta_atirando, player.timer_tiro, LARGURA, ALTURA)

        pygame.display.flip()
        clock.tick(60) # Mantém estável em 60 FPS

    pygame.quit()

if __name__ == "__main__":
    main()
