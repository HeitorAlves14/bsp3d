import os
from gerenciador_textura import carregar_textura

def carregar_materiais(caminho_mtl):
    """Lê o arquivo .mtl e carrega todas as texturas associadas na GPU"""
    materiais = {}
    diretorio_base = os.path.dirname(caminho_mtl)
    nome_material_atual = None

    if not os.path.exists(caminho_mtl):
        print(f"[MTL Warning] Arquivo {caminho_mtl} não encontrado.")
        return materiais

    with open(caminho_mtl, 'r') as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith('#'):
                continue

            partes = linha.split()
            comando = partes[0]

            if comando == 'newmtl':
                nome_material_atual = partes[1]
            
            elif comando == 'map_Kd' and nome_material_atual:
                # O caminho da imagem pode ser relativo ou absoluto
                caminho_imagem = " ".join(partes[1:])
                caminho_completo = os.path.join(diretorio_base, caminho_imagem)
                
                # Substitui barras invertidas do Windows por barras normais
                caminho_completo = caminho_completo.replace('\\', '/')

                print(f"[MTL] Carregando textura para {nome_material_atual}: {caminho_completo}")
                try:
                    tex_id = carregar_textura(caminho_completo)
                    materiais[nome_material_atual] = tex_id
                except Exception as e:
                    print(f"[MTL Error] Falha ao carregar imagem {caminho_completo}: {e}")
                    materiais[nome_material_atual] = 0 # Textura nula (branca/padrão)

    return materiais