"""
renderer_shader.py  (v3 — Adaptado para a nova BSP com Planos e VBOs por Nó)
"""

import ctypes
import numpy as np
from OpenGL.GL import *
from collections import defaultdict
from bsp.bsp import determinar_folha_ponto  # <-- Importe a função que criamos

# pos(3) + uv(2) + normal(3) = 8 floats * 4 bytes = 32 bytes
STRIDE = 8 * 4   


def _construir_vbos_por_textura(triangulos):
    """Gera buffers OpenGL (VBO) agrupados por ID de textura para um conjunto de triângulos"""
    grupos = defaultdict(list)
    for t in triangulos:
        # Usamos a normal calculada ou a do triângulo
        nx, ny, nz = t.normal if hasattr(t, 'normal') else (0.0, 1.0, 0.0)
        for v in t.vertices:
            grupos[t.textura_id].extend([
                v.pos[0], v.pos[1], v.pos[2],
                v.uv[0],  v.uv[1],
                nx, ny, nz,
            ])
            
    vbos = {}
    for tex_id, dados in grupos.items():
        arr = np.array(dados, dtype=np.float32)
        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, arr.nbytes, arr, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        vbos[tex_id] = (vbo, len(dados) // 8)
    return vbos


def _desenhar_vbo(vbo_id, num_verts):
    """Ativa os atributos de vértice e renderiza o buffer via arrays na GPU"""
    glBindBuffer(GL_ARRAY_BUFFER, vbo_id)
    
    # Atributo 0: Posição (X, Y, Z)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, STRIDE, ctypes.c_void_p(0))
    
    # Atributo 1: Coordenadas UV (U, V)
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, STRIDE, ctypes.c_void_p(12)) # 3 floats * 4 bytes
    
    # Atributo 2: Normais (NX, NY, NZ)
    glEnableVertexAttribArray(2)
    glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, STRIDE, ctypes.c_void_p(20)) # (3+2) floats * 4 bytes
    
    glDrawArrays(GL_TRIANGLES, 0, num_verts)
    
    glDisableVertexAttribArray(0)
    glDisableVertexAttribArray(1)
    glDisableVertexAttribArray(2)
    glBindBuffer(GL_ARRAY_BUFFER, 0)

class RendererBSP:
    def __init__(self, arvore_bsp, shader_mgr, tabela_pvs=None):
        self.arvore  = arvore_bsp
        self.shader  = shader_mgr
        # Armazena a tabela PVS (pode ser um dicionário que mapeia folha_id -> lista de folhas visíveis)
        self.tabela_pvs = tabela_pvs 
        
        print("[Renderer] Inicializando e gerando VBOs locais para a árvore BSP…")
        self._gerar_vbos_da_arvore(self.arvore)
        print("[Renderer] Árvore BSP indexada na GPU com sucesso.")

    def _gerar_vbos_da_arvore(self, no):
        if no is None:
            return
        if no.poligonos:
            no.vbos_locais = _construir_vbos_por_textura(no.poligonos)
        else:
            no.vbos_locais = {}
        self._gerar_vbos_da_arvore(no.front)
        self._gerar_vbos_da_arvore(no.back)

    def renderizar(self, pos_camera, frustum,
                   direcao_sol=(0.4, -1.0, 0.3), sol_ativo=True):
        self.shader.usar()
        self.shader.configurar_textura(0)
        self.shader.atualizar_lanterna()
        self.shader.configurar_sol(
            direcao_mundo=direcao_sol,
            cor=(1.0, 0.95, 0.80),
            intensidade=0.9,
            ativo=sol_ativo,
        )
        
        # --- NOVO: DETERMINA A FOLHA ATUAL DO JOGADOR ---
        folha_atual = determinar_folha_ponto(self.arvore, pos_camera)
        
        # Inicia a travessia estrita passando a folha_atual obtida pelo classificar_ponto interno
        self._percorrer_bsp(self.arvore, pos_camera, frustum, folha_atual)
        self.shader.parar()

    def _percorrer_bsp(self, no, pos_camera, frustum, folha_atual):
        if no is None:
            return
        
        # --- FILTRO PVS ---
        # Se a tabela PVS existir e este nó for uma folha invisível para a folha_atual, descarte imediatamente
        if self.tabela_pvs and no.is_leaf():
            visiveis = self.tabela_pvs.get(folha_atual, [])
            if no.folha_id not in visiveis:
                return # PVS barrou! Não renderiza nada desta sub-árvore/folha.

        # --- CORREÇÃO DO ERRO ---
        # Se o nó for uma folha legítima (espaço vazio), ele não tem plano divisor.
        # Desenhamos os polígonos coplanares dele (se houver) e paramos a descida por este ramo.
        if no.plano is None:
            self._desenhar_no_bsp(no, frustum)
            return

        # Se o nó possui um plano, classifica a câmera e decide a ordem de renderização (Back-to-Front)
        lado = no.plano.classificar_ponto(pos_camera)
        
        if lado in ('FRENTE', 'COPLANAR'):
            self._percorrer_bsp(no.back,  pos_camera, frustum, folha_atual)
            self._desenhar_no_bsp(no, frustum)
            self._percorrer_bsp(no.front, pos_camera, frustum, folha_atual)
        else:
            self._percorrer_bsp(no.front, pos_camera, frustum, folha_atual)
            self._desenhar_no_bsp(no, frustum)
            self._percorrer_bsp(no.back,  pos_camera, frustum, folha_atual)

    def _desenhar_no_bsp(self, no, frustum):
        if not hasattr(no, 'vbos_locais') or not no.vbos_locais:
            return

        algum_visivel = False
        for t in no.poligonos:
            if frustum.triangulo_visivel(t):
                algum_visivel = True
                break
        
        if not algum_visivel:
            return

        for tex_id, (vbo_id, num_verts) in no.vbos_locais.items():
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, tex_id)
            _desenhar_vbo(vbo_id, num_verts)

class RendererProps:
    def __init__(self, lista_props, shader_mgr):
        self.shader = shader_mgr
        self._cache = {}
        for prop in lista_props:
            self._cache[id(prop)] = _construir_vbos_por_textura(prop.triangulos_locais)

    def renderizar_todos(self, lista_props, frustum, sol_ativo=True):
        self.shader.usar()
        self.shader.configurar_textura(0)
        self.shader.atualizar_lanterna()
        self.shader.configurar_sol(ativo=sol_ativo)
        for prop in lista_props:
            self._renderizar_prop(prop, frustum)
        self.shader.parar()

    def _renderizar_prop(self, prop, frustum):
        g_min, g_max = prop.obter_aabb_global()
        if not frustum.aabb_visivel(g_min, g_max):
            return
        vbos = self._cache.get(id(prop), {})
        if not vbos:
            return
        glPushMatrix()
        glTranslatef(*prop.pos)
        for tex_id, (vbo_id, num_verts) in vbos.items():
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, tex_id)
            _desenhar_vbo(vbo_id, num_verts)
        glPopMatrix()