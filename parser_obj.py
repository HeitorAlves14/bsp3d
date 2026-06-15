import os
import numpy as np
from geometria import Vertice, Triangulo
from parser_mtl import carregar_materiais
from prop import Prop

def carregar_mapa_blender(caminho_arquivo):
    vertices_pos_global = []
    vertices_uv_global = []
    
    # Dicionários temporários para agrupar as faces por objeto do Blender
    objetos_faces = {}
    nome_objeto_atual = "Mundo_Estrutural"
    objetos_faces[nome_objeto_atual] = []

    banco_materiais = {}
    textura_atual_id = 0
    diretorio_base = os.path.dirname(caminho_arquivo)

    with open(caminho_arquivo, 'r') as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith('#'):
                continue
            
            partes = linha.split()
            prefixo = partes[0]

            if prefixo == 'mtllib':
                caminho_mtl = os.path.join(diretorio_base, partes[1]).replace('\\', '/')
                banco_materiais = carregar_materiais(caminho_mtl)

            elif prefixo == 'usemtl':
                nome_mat = partes[1]
                textura_atual_id = banco_materiais.get(nome_mat, 0)

            elif prefixo == 'v':
                vertices_pos_global.append([float(partes[1]), float(partes[2]), float(partes[3])])
            
            elif prefixo == 'vt':
                vertices_uv_global.append([float(partes[1]), float(partes[2])])

            # Detectou um novo objeto do Blender!
            elif prefixo == 'o':
                nome_objeto_atual = partes[1]
                objetos_faces[nome_objeto_atual] = []

            elif prefixo == 'f':
                # Guarda a face e o ID da textura atual no objeto correspondente
                objetos_faces[nome_objeto_atual].append((partes[1:], textura_atual_id))

    # --- AGORA SEPARAMOS O QUE É MUNDO E O QUE É PROP ---
    triangulos_bsp = []
    lista_props = []

    for nome_obj, faces in objetos_faces.items():
        if not faces:
            continue

        # Se o objeto começar com "Prop_", ele vira uma entidade dinâmica fora da BSP
        if nome_obj.startswith("Prop_"):
            triangulos_locais = []
            todos_pontos = []

            # Passo 1: Construir os triângulos brutos no espaço do mundo para achar o centro
            for dados_face, tex_id in faces:
                vertices_face = []
                for p in dados_face:
                    dados = p.split('/')
                    idx_v = int(dados[0]) - 1
                    u, v = vertices_uv_global[int(dados[1]) - 1] if len(dados) > 1 and dados[1] else (0.0, 0.0)
                    
                    pos_xyz = vertices_pos_global[idx_v]
                    todos_pontos.append(pos_xyz)
                    vertices_face.append((pos_xyz, u, v))

                for i in range(1, len(vertices_face) - 1):
                    triangulos_locais.append((vertices_face[0], vertices_face[i], vertices_face[i+1], tex_id))

            # Passo 2: Achar o centro do objeto (Média aritmética das posições)
            centro_objeto = np.mean(todos_pontos, axis=0)

            # Passo 3: Subtrair o centro de cada vértice para que o modelo fique local (origem em 0,0,0)
            triangulos_finais_prop = []
            for t in triangulos_locais:
                v_objetos = []
                for pos_xyz, u, v in [t[0], t[1], t[2]]:
                    pos_local = np.array(pos_xyz) - centro_objeto
                    v_objetos.append(Vertice(pos_local[0], pos_local[1], pos_local[2], u, v))
                
                triangulos_finais_prop.append(Triangulo(v_objetos[0], v_objetos[1], v_objetos[2], textura_id=t[3]))

            # Cria a entidade Prop passando sua posição real coletada do Blender
            novo_prop = Prop(nome_obj, triangulos_finais_prop, centro_objeto)
            lista_props.append(novo_prop)
            print(f"[Parser] Prop Criado: '{nome_obj}' na posição {centro_objeto}")

        else:
            # Se não começar com "Prop_", vai direto para o cenário estrutural da árvore BSP
            for dados_face, tex_id in faces:
                vertices_face = []
                for p in dados_face:
                    dados = p.split('/')
                    idx_v = int(dados[0]) - 1
                    u, v = vertices_uv_global[int(dados[1]) - 1] if len(dados) > 1 and dados[1] else (0.0, 0.0)
                    
                    x, y, z = vertices_pos_global[idx_v]
                    vertices_face.append(Vertice(x, y, z, u, v))

                for i in range(1, len(vertices_face) - 1):
                    triangulos_bsp.append(Triangulo(vertices_face[0], vertices_face[i], vertices_face[i+1], textura_id=tex_id))

    print(f"[Parser] Concluído: {len(triangulos_bsp)} triângulos estruturais e {len(lista_props)} props independentes.")
    return triangulos_bsp, lista_props