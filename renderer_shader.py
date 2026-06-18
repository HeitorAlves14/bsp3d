"""
renderer_shader.py  (v2 — compatível com shader_manager v2)
"""

import ctypes
import numpy as np
from OpenGL.GL import *
from collections import defaultdict


STRIDE = 8 * 4   # pos(3) + uv(2) + normal(3) = 8 floats * 4 bytes


def _construir_vbos_por_textura(triangulos):
    grupos = defaultdict(list)
    for t in triangulos:
        nx, ny, nz = t.normal
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
    glBindBuffer(GL_ARRAY_BUFFER, vbo_id)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, STRIDE, ctypes.c_void_p(0))
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, STRIDE, ctypes.c_void_p(12))
    glEnableVertexAttribArray(2)
    glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, STRIDE, ctypes.c_void_p(20))
    glDrawArrays(GL_TRIANGLES, 0, num_verts)
    glDisableVertexAttribArray(0)
    glDisableVertexAttribArray(1)
    glDisableVertexAttribArray(2)
    glBindBuffer(GL_ARRAY_BUFFER, 0)


def _coletar_triangulos_bsp(no, resultado=None):
    if resultado is None:
        resultado = []
    if no is None:
        return resultado
    resultado.extend(no.poligonos)
    _coletar_triangulos_bsp(no.front, resultado)
    _coletar_triangulos_bsp(no.back,  resultado)
    return resultado


class RendererBSP:
    def __init__(self, arvore_bsp, shader_mgr):
        self.arvore  = arvore_bsp
        self.shader  = shader_mgr
        self._vbos   = {}
        print("[Renderer] Construindo VBOs do mapa…")
        todos = _coletar_triangulos_bsp(self.arvore)
        self._vbos = _construir_vbos_por_textura(todos)
        print(f"[Renderer] {len(self._vbos)} grupos de textura prontos.")

    def renderizar(self, pos_camera, frustum,
                   direcao_sol=(0.4, -1.0, 0.3), sol_ativo=True):
        """
        Chame uma vez por frame.
        direcao_sol : direção da luz solar em espaço mundo (da cena para o sol).
        sol_ativo   : False em salas totalmente fechadas.
        """
        self.shader.usar()
        self.shader.configurar_textura(0)
        self.shader.atualizar_lanterna()
        self.shader.configurar_sol(
            direcao_mundo=direcao_sol,
            cor=(1.0, 0.95, 0.80),
            intensidade=0.9,
            ativo=sol_ativo,
        )
        self._percorrer_bsp(self.arvore, pos_camera, frustum)
        self.shader.parar()

    def _percorrer_bsp(self, no, pos_camera, frustum):
        if no is None:
            return
        lado = no.divisor.classificar_ponto(pos_camera)
        if lado in ('FRENTE', 'COPLANAR'):
            self._percorrer_bsp(no.back,  pos_camera, frustum)
            self._desenhar_poligonos(no.poligonos, frustum)
            self._percorrer_bsp(no.front, pos_camera, frustum)
        else:
            self._percorrer_bsp(no.front, pos_camera, frustum)
            self._desenhar_poligonos(no.poligonos, frustum)
            self._percorrer_bsp(no.back,  pos_camera, frustum)

    def _desenhar_poligonos(self, poligonos, frustum):
        grupos = defaultdict(list)
        for t in poligonos:
            if frustum.triangulo_visivel(t):
                grupos[t.textura_id].append(t)
        for tex_id in grupos:
            if tex_id not in self._vbos:
                continue
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, tex_id)
            vbo_id, num_verts = self._vbos[tex_id]
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