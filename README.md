# Sobreviva a Curitiba!

**Jogue:** https://matheuskrk.github.io/sobreviva-a-curitiba/

O Parque Barigui alagou. Uma capivara de colete sobe no jet ski e foge de uma onda pelas ruas alagadas do centro de Curitiba, para curtir o fim de semana num lugar seco. As ruas e os prédios são reais, tirados do OpenStreetMap; o percurso é sorteado a cada partida entre praças e pontos da cidade.

Corrida infinita em 3 faixas, feita para o celular (tela em pé, 9:16): deslize ou toque no lado da tela para trocar de faixa. No computador, use ← →.

## O que tem no jogo

- **Abertura:** o parque de diversões do Barigui afundando e a rajada de vento que joga a capivara no jet ski.
- **Power-ups:**
  - **Pinhão:** 5 s invencível e mais rápido.
  - **Guarda-chuva:** 8 s sem galhos nem fios dos postes.
  - **Ligeirinho:** 4 s de carona no ônibus.
- **Cidade:** clima que muda (sol, garoa, temporal e neblina), dia e noite com apagões, correnteza do Rio Belém, pontos turísticos sem nome para quem conhece reconhecer, placas de curva, moradores nas boias e a equipe da poda.
- **Lojinha:** coletes, chapéus e jet skis pagos com pinhões (3 por km e 10 por pinhão pego), com prévia antes de comprar.
- **Placar geral:** por distância; só aceita a distância validada pelo servidor.
- **Card para os stories:** no fim de cada partida, com os km e até onde dava para ir saindo do Barigui. Quem passa de 100 km ganha a edição de férias.

## Como jogar localmente

O jogo precisa ser aberto por um servidor (o navegador bloqueia `fetch` de arquivos locais):

```
python3 -m http.server 8000
```

Depois abra http://localhost:8000.

## Estrutura

- `index.html`: o jogo inteiro (three.js carregado do jsDelivr).
- `curitiba.json`: prédios, ruas, praças e rios do centro de Curitiba, exportados do OpenStreetMap e convertidos para metros.
- `assets.glb`: modelos 3D low-poly que o jogo carrega (binário, com normais e cores em 8 bits).
- `assets.json`: saída do script do Blender (glTF com o buffer embutido), de onde sai o `assets.glb`.
- `blender/assets_ps2.py`: gera todos os modelos, com cor por vértice.
- `blender/compacta_assets.py`: converte o `assets.json` no `assets.glb`.
- `supabase/`: SQL do servidor (Supabase):
  - `servidor.sql`: pinhões, loja, partidas e placar validados no servidor.
  - `placar.sql`: tabela do placar.
  - `laranja.sql`: atualização da loja.
- `design/`: conceito visual do menu e dos cards, com exemplos.

Para gerar os modelos de novo:

```
blender -b -P blender/assets_ps2.py -- . --preview
python3 blender/compacta_assets.py
```

## Servidor

O placar e os pinhões ficam num projeto do Supabase. Para montar um do zero:

1. Crie o projeto.
2. Rode no SQL Editor, nesta ordem: `supabase/placar.sql`, `supabase/servidor.sql` e `supabase/laranja.sql`.
3. Coloque a Project URL e a chave publicável em `PLACAR`, no `index.html`.

Sem servidor, o jogo funciona igual, com a lojinha guardada só no aparelho.

## Créditos

Desenvolvido por Matheus dos Anjos ([@mathmath.zip](https://www.instagram.com/mathmath.zip/)) e Matheus Cruz.

Mapa e dados das ruas: © [colaboradores do OpenStreetMap](https://www.openstreetmap.org/copyright), sob a licença ODbL.
