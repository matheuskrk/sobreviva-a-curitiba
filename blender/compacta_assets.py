"""Converte assets.json (glTF com o buffer em base64, saída do assets_ps2.py) em assets.glb binário e enxuto.

O que muda nos modelos:
- tira TEXCOORD_0 (o jogo não usa textura nos modelos);
- normais em int8 normalizado (KHR_mesh_quantization, que o GLTFLoader do three.js lê sem decodificador extra);
- cores por vértice em uint8 normalizado.
Posições e índices ficam como estão (o jogo usa a geometria direto, sem a transformação do nó).

Uso, na pasta do jogo:
    python3 blender/compacta_assets.py
"""
import base64
import json
import os
import struct
import sys

import numpy as np

PASTA = sys.argv[1] if len(sys.argv) > 1 else '.'
ENTRADA = os.path.join(PASTA, 'assets.json')
SAIDA = os.path.join(PASTA, 'assets.glb')

COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}

g = json.load(open(ENTRADA))
buf = base64.b64decode(g['buffers'][0]['uri'].split(',', 1)[1])


def le(acc):
    """Lê um accessor como array numpy (count x n), respeitando byteStride."""
    bv = g['bufferViews'][acc['bufferView']]
    dt = np.dtype(COMP[acc['componentType']])
    n = NCOMP[acc['type']]
    ini = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
    stride = bv.get('byteStride', dt.itemsize * n)
    a = np.ndarray((acc['count'], n), dtype=dt, buffer=buf, offset=ini, strides=(stride, dt.itemsize))
    a = a.astype(np.float32) if acc.get('normalized') else a.copy()
    if acc.get('normalized'):
        a /= float(np.iinfo(dt).max)
    return a


novo = bytearray()
views, accs = [], []


def grava(dados, alvo, stride=None):
    while len(novo) % 4:
        novo.append(0)
    bv = {'buffer': 0, 'byteOffset': len(novo), 'byteLength': len(dados)}
    if alvo:
        bv['target'] = alvo
    if stride:
        bv['byteStride'] = stride
    novo.extend(dados)
    views.append(bv)
    return len(views) - 1


def novo_acc(antigo, nome):
    a = le(antigo)
    acc = {'count': antigo['count'], 'type': antigo['type']}
    if nome == 'NORMAL':
        q = np.clip(np.round(a * 127), -127, 127).astype(np.int8)
        q4 = np.zeros((len(q), 4), np.int8)  # cada vértice alinhado em 4 bytes, como o glTF exige
        q4[:, :3] = q
        acc.update(bufferView=grava(q4.tobytes(), 34962, 4), componentType=5120, normalized=True)
    elif nome == 'COLOR_0':
        q = np.clip(np.round(a * 255), 0, 255).astype(np.uint8)
        if q.shape[1] == 3:
            q4 = np.full((len(q), 4), 255, np.uint8)
            q4[:, :3] = q
            acc.update(bufferView=grava(q4.tobytes(), 34962, 4), componentType=5121, normalized=True, type='VEC4')
        else:
            acc.update(bufferView=grava(q.tobytes(), 34962), componentType=5121, normalized=True)
    elif nome == 'INDICES':
        acc.update(bufferView=grava(a.tobytes(), 34963), componentType=antigo['componentType'])
    else:
        acc.update(bufferView=grava(a.astype(COMP[antigo['componentType']]).tobytes(), 34962), componentType=antigo['componentType'])
        for k in ('min', 'max'):
            if k in antigo:
                acc[k] = antigo[k]
    accs.append(acc)
    return len(accs) - 1


for m in g['meshes']:
    for p in m['primitives']:
        p['attributes'] = {k: novo_acc(g['accessors'][v], k) for k, v in p['attributes'].items() if k != 'TEXCOORD_0'}
        if 'indices' in p:
            p['indices'] = novo_acc(g['accessors'][p['indices']], 'INDICES')

g['accessors'], g['bufferViews'] = accs, views
while len(novo) % 4:
    novo.append(0)
g['buffers'] = [{'byteLength': len(novo)}]
for k in ('extensionsUsed', 'extensionsRequired'):
    g[k] = sorted(set(g.get(k, [])) | {'KHR_mesh_quantization'})

js = json.dumps(g, separators=(',', ':')).encode()
js += b' ' * (-len(js) % 4)
glb = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(novo))
glb += struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(novo), 0x004E4942) + bytes(novo)
open(SAIDA, 'wb').write(glb)
print(f'{SAIDA}: {len(glb) / 1e6:.2f} MB (era {os.path.getsize(ENTRADA) / 1e6:.2f} MB)')
