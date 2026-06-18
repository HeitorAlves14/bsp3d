"""
shader_manager.py  (v2 — sol direcional + N luzes pontuais de sala)
"""

from OpenGL.GL import *
import numpy as np
import math

MAX_POINT_LIGHTS = 8   # limite do array no GLSL; aumente se precisar

# ─────────────────────────────────────────────────────────────────────────────
#  VERTEX SHADER
# ─────────────────────────────────────────────────────────────────────────────
VERTEX_SHADER_SRC = """
#version 120

attribute vec3 a_pos;
attribute vec2 a_uv;
attribute vec3 a_normal;

varying vec2 v_uv;
varying vec3 v_frag_pos;   // espaço câmera
varying vec3 v_normal;
varying vec3 v_world_pos;  // espaço mundo (para luzes de sala)

void main() {
    vec4 cam_pos   = gl_ModelViewMatrix * vec4(a_pos, 1.0);
    v_frag_pos     = cam_pos.xyz;
    v_normal       = normalize(gl_NormalMatrix * a_normal);
    v_uv           = a_uv;
    v_world_pos    = a_pos;              // posição local/mundo antes da view
    gl_Position    = gl_ProjectionMatrix * cam_pos;
}
"""

# ─────────────────────────────────────────────────────────────────────────────
#  FRAGMENT SHADER
# ─────────────────────────────────────────────────────────────────────────────
FRAGMENT_SHADER_SRC = f"""
#version 120

#define MAX_POINT_LIGHTS {MAX_POINT_LIGHTS}

uniform sampler2D u_texture;

// ── Ambiente global ───────────────────────────────────────────────────────
uniform vec3  u_ambient_color;
uniform float u_ambient_strength;

// ── Sol (luz direcional) ──────────────────────────────────────────────────
uniform bool  u_sol_ativo;
uniform vec3  u_sol_direcao;     // vetor normalizado PARA a luz, espaço câmera
uniform vec3  u_sol_cor;
uniform float u_sol_intensidade;

// ── Lanterna do jogador ───────────────────────────────────────────────────
uniform vec3  u_lanterna_pos;    // espaço câmera (normalmente 0,0,0)
uniform vec3  u_lanterna_cor;
uniform float u_lanterna_raio;
uniform float u_lanterna_intensidade;

// ── Luzes pontuais de sala ────────────────────────────────────────────────
// Passadas em coordenadas de MUNDO; o vertex shader expõe v_world_pos
uniform int   u_num_point_lights;
uniform vec3  u_pl_pos[MAX_POINT_LIGHTS];
uniform vec3  u_pl_cor[MAX_POINT_LIGHTS];
uniform float u_pl_raio[MAX_POINT_LIGHTS];
uniform float u_pl_intensidade[MAX_POINT_LIGHTS];

// ── Fog ───────────────────────────────────────────────────────────────────
uniform float u_fog_start;
uniform float u_fog_end;
uniform vec3  u_fog_color;

varying vec2 v_uv;
varying vec3 v_frag_pos;
varying vec3 v_normal;
varying vec3 v_world_pos;

// ── Calcula contribuição de uma luz pontual genérica ─────────────────────
vec3 calc_point_light(vec3 light_world, vec3 cor, float raio, float intensidade,
                      vec3 frag_world, vec3 normal_cam, vec3 view_dir) {{
    // Transforma a posição da luz para espaço câmera usando a mesma matrix
    vec4 lc = gl_ModelViewMatrix * vec4(light_world, 1.0);
    vec3 light_dir = lc.xyz - v_frag_pos;
    float dist     = length(light_dir);
    light_dir      = normalize(light_dir);

    float att = clamp(1.0 - (dist / raio), 0.0, 1.0);
    att        = att * att;

    float diff    = max(dot(normal_cam, light_dir), 0.0);
    vec3  diffuse = cor * diff * att * intensidade;

    vec3  ref  = reflect(-light_dir, normal_cam);
    float spec = pow(max(dot(view_dir, ref), 0.0), 32.0);
    vec3  specular = cor * spec * att * 0.25;

    return diffuse + specular;
}}

void main() {{
    vec4 tex_color = texture2D(u_texture, v_uv);
    if (tex_color.a < 0.1) discard;

    vec3 normal   = normalize(v_normal);
    vec3 view_dir = normalize(-v_frag_pos);

    // ── Ambiente ──────────────────────────────────────────────────────────
    vec3 lighting = u_ambient_color * u_ambient_strength;

    // ── Sol direcional ────────────────────────────────────────────────────
    if (u_sol_ativo) {{
        float diff_sol = max(dot(normal, normalize(u_sol_direcao)), 0.0);
        vec3  ref_sol  = reflect(-normalize(u_sol_direcao), normal);
        float spec_sol = pow(max(dot(view_dir, ref_sol), 0.0), 64.0);
        lighting += u_sol_cor * (diff_sol + spec_sol * 0.15) * u_sol_intensidade;
    }}

    // ── Lanterna do jogador ───────────────────────────────────────────────
    {{
        vec3 light_dir = u_lanterna_pos - v_frag_pos;
        float dist     = length(light_dir);
        light_dir      = normalize(light_dir);
        float att = clamp(1.0 - (dist / u_lanterna_raio), 0.0, 1.0);
        att        = att * att;
        float diff = max(dot(normal, light_dir), 0.0);
        vec3  ref  = reflect(-light_dir, normal);
        float spec = pow(max(dot(view_dir, ref), 0.0), 32.0);
        lighting  += u_lanterna_cor * (diff + spec * 0.3) * att * u_lanterna_intensidade;
    }}

    // ── Luzes pontuais de sala ────────────────────────────────────────────
    for (int i = 0; i < MAX_POINT_LIGHTS; i++) {{
        if (i >= u_num_point_lights) break;
        lighting += calc_point_light(
            u_pl_pos[i], u_pl_cor[i], u_pl_raio[i], u_pl_intensidade[i],
            v_world_pos, normal, view_dir
        );
    }}

    // ── Combina com textura ───────────────────────────────────────────────
    vec3 result = tex_color.rgb * lighting;

    // ── Fog ───────────────────────────────────────────────────────────────
    float frag_dist  = length(v_frag_pos);
    float fog_factor = clamp((frag_dist - u_fog_start) / (u_fog_end - u_fog_start), 0.0, 1.0);
    result           = mix(result, u_fog_color, fog_factor);

    gl_FragColor = vec4(result, tex_color.a);
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Compilação
# ─────────────────────────────────────────────────────────────────────────────

def _compilar_shader(tipo, src):
    s = glCreateShader(tipo)
    glShaderSource(s, src)
    glCompileShader(s)
    if not glGetShaderiv(s, GL_COMPILE_STATUS):
        nome = "VERTEX" if tipo == GL_VERTEX_SHADER else "FRAGMENT"
        raise RuntimeError(f"[Shader] Erro ({nome}):\n{glGetShaderInfoLog(s).decode()}")
    return s

def criar_programa_shader():
    vert = _compilar_shader(GL_VERTEX_SHADER,   VERTEX_SHADER_SRC)
    frag = _compilar_shader(GL_FRAGMENT_SHADER, FRAGMENT_SHADER_SRC)
    prog = glCreateProgram()
    glAttachShader(prog, vert)
    glAttachShader(prog, frag)
    glBindAttribLocation(prog, 0, "a_pos")
    glBindAttribLocation(prog, 1, "a_uv")
    glBindAttribLocation(prog, 2, "a_normal")
    glLinkProgram(prog)
    if not glGetProgramiv(prog, GL_LINK_STATUS):
        raise RuntimeError(f"[Shader] Link:\n{glGetProgramInfoLog(prog).decode()}")
    glDeleteShader(vert)
    glDeleteShader(frag)
    print("[Shader] Programa compilado e linkado.")
    return prog


# ─────────────────────────────────────────────────────────────────────────────
#  Dataclass leve para uma luz de sala
# ─────────────────────────────────────────────────────────────────────────────

class LuzPontual:
    """
    Representa uma lâmpada/tocha numa sala fechada.

    Parâmetros
    ----------
    pos        : (x, y, z) em coordenadas de mundo do Blender
    cor        : (r, g, b) 0..1  — exemplos abaixo
    raio       : alcance em unidades de mundo
    intensidade: multiplicador de brilho

    Cores sugeridas
    ---------------
    Lâmpada fluorescente fria : (0.80, 0.90, 1.00)
    Lâmpada incandescente     : (1.00, 0.75, 0.40)
    Tocha / fogo              : (1.00, 0.50, 0.10)
    Néon verde                : (0.20, 1.00, 0.30)
    Emergência vermelho       : (1.00, 0.10, 0.05)
    """
    def __init__(self, pos, cor=(1.0, 0.75, 0.4), raio=8.0, intensidade=1.2):
        self.pos        = tuple(pos)
        self.cor        = tuple(cor)
        self.raio       = float(raio)
        self.intensidade = float(intensidade)


# ─────────────────────────────────────────────────────────────────────────────
#  Gerenciador principal
# ─────────────────────────────────────────────────────────────────────────────

class GerenciadorShader:
    """
    Uso típico
    ----------
        shader = GerenciadorShader()

        # Uma vez (fora do loop):
        shader.usar()
        shader.configurar_ambiente(cor=(0.10, 0.09, 0.15), forca=0.5)
        shader.configurar_fog(10.0, 35.0, (0.04, 0.03, 0.07))

        shader.configurar_sol(
            direcao_mundo=(0.4, -1.0, 0.3),
            cor=(1.0, 0.95, 0.80),
            intensidade=0.9,
            ativo=True
        )

        shader.definir_luzes_sala([
            LuzPontual(pos=(3.0, 2.5, -5.0),  cor=(0.8, 0.9, 1.0), raio=7.0),
            LuzPontual(pos=(-8.0, 2.5, -12.0), cor=(1.0, 0.5, 0.1), raio=6.0),
        ])
        shader.parar()

        # A cada frame (dentro do loop, antes de renderizar_bsp):
        shader.usar()
        shader.atualizar_lanterna(raio=12.0, intensidade=1.6)
        # (sol e luzes de sala não precisam ser reatualizados todo frame
        #  a não ser que mudem)
    """

    def __init__(self):
        self.prog = criar_programa_shader()
        self._num_point_lights = 0

    # ── controle básico ────────────────────────────────────────────────────
    def usar(self):   glUseProgram(self.prog)
    def parar(self):  glUseProgram(0)

    def _loc(self, name):
        return glGetUniformLocation(self.prog, name)

    def _set_int(self, n, v):   glUniform1i(self._loc(n), int(v))
    def _set_float(self, n, v): glUniform1f(self._loc(n), float(v))
    def _set_vec3(self, n, x, y, z): glUniform3f(self._loc(n), x, y, z)
    def _set_bool(self, n, v):  glUniform1i(self._loc(n), 1 if v else 0)

    # ── ambiente ──────────────────────────────────────────────────────────
    def configurar_ambiente(self, cor=(0.12, 0.10, 0.18), forca=0.55):
        self._set_vec3("u_ambient_color", *cor)
        self._set_float("u_ambient_strength", forca)

    # ── fog ───────────────────────────────────────────────────────────────
    def configurar_fog(self, inicio=10.0, fim=35.0, cor=(0.04, 0.03, 0.07)):
        self._set_float("u_fog_start", inicio)
        self._set_float("u_fog_end",   fim)
        self._set_vec3("u_fog_color",  *cor)

    def configurar_textura(self, unit=0):
        self._set_int("u_texture", unit)

    # ── sol ───────────────────────────────────────────────────────────────
    def configurar_sol(self, direcao_mundo=(0.4, -1.0, 0.3),
                       cor=(1.0, 0.95, 0.80), intensidade=0.9, ativo=True):
        """
        direcao_mundo: vetor apontando DA cena PARA o sol (será normalizado).
        O shader transforma para espaço câmera automaticamente via NormalMatrix.
        Chame com ativo=False para desligar o sol em áreas cobertas/internas.
        """
        self._set_bool("u_sol_ativo", ativo)
        if not ativo:
            return
        d = np.array(direcao_mundo, dtype=np.float32)
        norma = np.linalg.norm(d)
        if norma > 0:
            d /= norma
        # Transforma a direção do sol para espaço câmera
        mv = glGetFloatv(GL_MODELVIEW_MATRIX)            # 4x4 column-major
        mv3 = np.array(mv[:3, :3], dtype=np.float32)    # só rotação
        d_cam = mv3 @ d
        n = np.linalg.norm(d_cam)
        if n > 0:
            d_cam /= n
        self._set_vec3("u_sol_direcao", *d_cam)
        self._set_vec3("u_sol_cor", *cor)
        self._set_float("u_sol_intensidade", intensidade)

    # ── lanterna do jogador ───────────────────────────────────────────────
    def atualizar_lanterna(self, offset=(0.3, -0.2, 0.0),
                           cor=(1.0, 0.88, 0.65),
                           raio=13.0, intensidade=1.8):
        """
        Chame todo frame. offset em espaço câmera:
          (0,0,0)       = centro da câmera
          (0.3,-0.2,0)  = levemente à direita e abaixo (simula mão com tocha)
        """
        self._set_vec3("u_lanterna_pos", *offset)
        self._set_vec3("u_lanterna_cor", *cor)
        self._set_float("u_lanterna_raio", raio)
        self._set_float("u_lanterna_intensidade", intensidade)

    # ── luzes pontuais de sala ─────────────────────────────────────────────
    def definir_luzes_sala(self, luzes: list):
        """
        Recebe lista de LuzPontual. Máximo MAX_POINT_LIGHTS itens.
        Chame UMA VEZ ao carregar o mapa (ou quando as luzes mudarem).
        As posições ficam em coordenadas de mundo — o shader transforma
        internamente usando gl_ModelViewMatrix.
        """
        n = min(len(luzes), MAX_POINT_LIGHTS)
        self._set_int("u_num_point_lights", n)
        self._num_point_lights = n
        for i, luz in enumerate(luzes[:n]):
            self._set_vec3(f"u_pl_pos[{i}]",        *luz.pos)
            self._set_vec3(f"u_pl_cor[{i}]",        *luz.cor)
            self._set_float(f"u_pl_raio[{i}]",      luz.raio)
            self._set_float(f"u_pl_intensidade[{i}]", luz.intensidade)
        print(f"[Shader] {n} luz(es) de sala registradas.")