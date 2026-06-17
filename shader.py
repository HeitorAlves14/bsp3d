from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader

class Shader:
    def __init__(self, vertex_path, fragment_path):
        self.program = self._carregar_e_compilar(vertex_path, fragment_path)

    def _carregar_e_compilar(self, vertex_path, fragment_path):
        # Lê o código fonte dos arquivos
        with open(vertex_path, 'r') as f:
            vertex_src = f.read()
        with open(fragment_path, 'r') as f:
            fragment_src = f.read()

        try:
            # Compila o Vertex e o Fragment Shader e os une em um único programa
            vs = compileShader(vertex_src, GL_VERTEX_SHADER)
            fs = compileShader(fragment_src, GL_FRAGMENT_SHADER)
            program = compileProgram(vs, fs)
            return program
        except Exception as e:
            print(f"[Erro de Compilação no Shader]:\n{e}")
            return 0

    def usar(self):
        """Ativa este shader para os próximos objetos que serão desenhados"""
        glUseProgram(self.program)

    def desligar(self):
        """Volta para o pipeline padrão do OpenGL"""
        glUseProgram(0)

    def set_uniform_f(self, nome, valor):
        """Passa uma variável float simples para dentro do shader"""
        loc = glGetUniformLocation(self.program, nome)
        if loc != -1:
            glUniform1f(loc, valor)