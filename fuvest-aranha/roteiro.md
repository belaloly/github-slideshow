# A aranha e a teia (FUVEST, Questão 59): roteiro de narração

Vídeo: `aranha_fuvest_q59.mp4` (1920×1080, 30 fps, 4min11s, sem áudio).
A coluna **Tempo** mostra quando cada cena começa. As falas são sugestões, use o seu jeito.
Se precisar de mais tempo em algum trecho, congele o quadro na edição: o fim de cada cena fica parado.

| Tempo | O que aparece | Sugestão de fala |
|---|---|---|
| 0:00 | Título | "Vamos resolver a questão da aranha da FUVEST usando só matemática do Fundamental II." |
| 0:06 | A aranha na teia acende 2 patas → seta; 2 opostas → X; 4 patas → seta; 2 pares opostos → X | "Relembrando as regras: com 2 bolinhas, a aranha anda na direção média… a não ser que elas sejam opostas. Com 4 bolinhas, ela só fica parada se forem dois pares de opostas." |
| 0:31 | As patas somem, as pontas viram vértices e o octógono se desenha | "Repara: as pontas das 8 patas formam um octógono regular, e a aranha está no centro." |
| **PARTE 1: duas bolinhas** | | |
| 0:41 | Acende 1-2 (lado azul), depois 1-4 (diagonal verde) | "Acender 2 patas é escolher 2 vértices. Ligando os dois, ou temos um lado ou uma diagonal." |
| 0:52 | Os 8 lados vão se acendendo um por um (contador 1 → 8) | "Lados: 1, 2, 3… 8 lados, ou seja, 8 pares de patas vizinhas." |
| 1:01 | Do vértice 1: X nos vizinhos 2 e 8, saem 5 diagonais | "Do vértice 1 não dá para ligar nele mesmo nem nos 2 vizinhos. Sobram 8 − 3 = 5 diagonais." |
| 1:14 | Diagonais saindo de todos os vértices; elas escurecem quando são contadas pela 2ª vez | "8 vértices vezes 5 dá 40… mas cada diagonal foi contada duas vezes, uma em cada ponta. 40 ÷ 2 = 20. É a fórmula d = n(n − 3)/2." |
| 1:28 | Octógono completo: 8 + 20 = 28 | "Juntando: 8 lados mais 20 diagonais, 28 jeitos de acender 2 patas." |
| 1:36 | Os 4 diâmetros ficam vermelhos, com X no centro; 28 − 4 = 24 | "Mas patas opostas não fazem a aranha andar. São os diâmetros, que passam pelo centro: 4. Então 28 − 4 = 24." |
| 1:48 | Quadro de conferência: 3 fileiras de 8 + 4 opostas | "Conferindo: 8 vizinhas, 8 pulando 1, 8 pulando 2. Dá 24. E as opostas ficam de fora." |
| **PARTE 2: quatro bolinhas** | | |
| 2:01 | Ideia do formato; a "fita" com as patas 1 a 8 | "Com 4 patas, a ideia é: escolho um formato e giro ele pelas 8 posições. Para enxergar o formato, leio as patas a partir da 1, como uma fita que fecha em círculo." |
| 2:12 | **4 juntas**: gira devagar, 8 miniaturas aparecem | "Primeiro, as 4 juntas. Girando, temos 8 posições diferentes: 8." |
| 2:22 | **1, pula 1, 3 juntas** | "Agora começo com uma, pulo uma e vêm 3 juntas: mais 8." |
| 2:31 | **1, pula 2, 3 juntas** | "Pulando 2: mais 8." |
| 2:40 | **1, pula 3, 3 juntas** | "Pulando 3: mais 8. Aqui já temos 8 + 24 = 32." |
| 2:48 | "Acabou? Ainda NÃO!" | "Será que acabou? Não! Faltam os formatos que não têm 3 patas juntas." |
| 2:54 | **2 juntas, pula 1, 2 juntas** | "Dois pares de juntas, pulando 1 entre eles: 8 posições. Pular 3 é o mesmo formato visto pelo outro lado." |
| 3:03 | **2 juntas, pula 2, 2 juntas**: X, gira e repete depois de 4 | "Pulando 2, os pares ficam opostos: a aranha não anda. E girando, repete depois de só 4 posições." |
| 3:11 | **2 juntas + 2 sozinhas (a)** | "Agora 2 juntas e 2 sozinhas. As 4 patas apagadas se dividem em 1, 1 e 2, e esse 2 pode ficar em 3 lugares. Primeiro jeito: 8." |
| 3:20 | **2 juntas + 2 sozinhas (b)** | "Segundo jeito: mais 8." |
| 3:28 | **2 juntas + 2 sozinhas (c)** | "Terceiro jeito: mais 8. Total: 64." |
| 3:37 | **Todas separadas**: X, repete depois de 2 | "E todas separadas formam 2 pares opostos: não se move, e só tem 2 posições." |
| 3:44 | Quadro com as 64 miniaturas + 6 que não se movem | "Conferindo: são 8 formatos vezes 8 posições, 64. E os 6 que não se movem completam as 70 escolhas possíveis." |
| 3:59 | 24 + 64 = 88, Alternativa A | "Então: 24 com duas bolinhas, 64 com quatro… 88 combinações. Alternativa A!" |

## Por que a contagem das 4 patas fecha

Toda escolha de 4 patas pertence a exatamente um destes grupos (olhando quais patas acesas são vizinhas):

| Grupo | Formatos | Posições | Combinações |
|---|---|---|---|
| 4 juntas | 1 | 8 | 8 |
| 1 sozinha + 3 juntas (pula 1, 2 ou 3) | 3 | 8 cada | 24 |
| 2 juntas + 2 juntas (pula 1) | 1 | 8 | 8 |
| 2 juntas + 2 sozinhas | 3 | 8 cada | 24 |
| **Se move** | **8** | | **64** |
| 2 juntas + 2 juntas (pula 2): pares opostos | 1 | 4 | 4 (não se move) |
| Todas separadas: pares opostos | 1 | 2 | 2 (não se move) |

Conferência para o professor (Ensino Médio): C(8,4) = 70 = 64 + 6 e C(8,2) = 28 = 24 + 4.

## Como gerar o vídeo de novo

```bash
pip install pycairo          # precisa também de ffmpeg e da fonte Inter
python3 render.py --timeline # tempos das cenas
python3 render.py            # gera aranha_fuvest_q59.mp4
```
