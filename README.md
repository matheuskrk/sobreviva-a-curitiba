# Sobreviva a Curitiba!

Jogo de corrida infinita em 3 faixas: uma capivarinha de laranja na cabeça pilota um jet ski pelas ruas alagadas do centro de Curitiba, fugindo de uma onda. As ruas e os prédios são reais, tirados do OpenStreetMap; o percurso é sorteado a cada partida entre praças e pontos da cidade.

Feito para jogar no celular (tela em pé, 9:16): deslize ou toque no lado da tela para trocar de faixa. No computador, use ← →.

## Como jogar localmente

O jogo precisa ser aberto por um servidor (o navegador bloqueia `fetch` de arquivos locais):

```
python3 -m http.server 8000
```

Depois abra http://localhost:8000.

## Estrutura

- `index.html`: o jogo inteiro (three.js carregado do jsDelivr).
- `curitiba.json`: prédios, ruas, praças e rios do centro de Curitiba, exportados do OpenStreetMap e convertidos para metros.
- `assets.json`: modelos 3D low-poly (glTF com o buffer embutido), gerados pelo script do Blender.
- `blender/assets_ps2.py`: gera todos os modelos, com cor por vértice.

Para gerar os modelos de novo:

```
blender -b -P blender/assets_ps2.py -- . --preview
```

## Créditos

Desenvolvido por Matheus dos Anjos ([@mathmath.zip](https://www.instagram.com/mathmath.zip/)) e Matheus Tomiatti ([@matheustomiatti](https://www.instagram.com/matheustomiatti/)).

Mapa e dados das ruas: © [colaboradores do OpenStreetMap](https://www.openstreetmap.org/copyright), sob a licença ODbL.
