---
name: cortes
description: Transforma um episódio longo (link do YouTube, podcast em vídeo ou TikTok) em cortes verticais 9:16 com legenda em caixa pra Reels, Shorts e TikTok. Baixa com yt-dlp, transcreve com tempo por palavra, dá nota a cada momento (gancho, autonomia, desfecho, ritmo; 30 a 90 s), mostra uma tabela pra aprovar e só então renderiza seguindo o rosto. Use quando o usuário digitar /cortes, colar um link pedindo cortes, ou falar em "cortar podcast", "tirar cortes", "clips do episódio".
---

# /cortes

Do link ao corte aprovado. Decisões e motivos: `docs/decisoes/2026-10-06-skill-cortes.md`
no repositório `cortes`.

Pasta da skill: `~/.claude/skills/cortes` (abaixo, `$S`). Kit reaproveitado:
`$CORTES_KIT`, padrão `~/.claude/skills/editar-reels/kit` (`transcreve.py`, `base.py`,
`caps3.py`, `recorte.swift`). Trabalho de cada episódio: `~/Cortes/<slug-do-episodio>/` (abaixo, `$P`).

## Regras

- **Só corte conteúdo com permissão** do dono. Se o usuário não disse que tem, pergunte antes de baixar.
- **Nunca renderize antes da aprovação** da tabela.
- **Sem recodificação "shadowban-safe"**: não espelhe, não mude velocidade, não adicione ruído
  nem altere o vídeo pra fugir de detecção de conteúdo repetido. Se pedirem, recuse e explique.
- Não publique sozinho. Entrega é a pasta `saida/`.

## Passo 0 — conferir o kit (primeira vez, ou se `kit.json` tiver `"_verificado": false`)

1. Confirme que existem `$CORTES_KIT/transcreve.py`, `caps3.py`, `recorte.swift`, `base.py`.
2. Leia o cabeçalho de cada um e rode `--help` quando houver.
3. Ajuste os modelos em `$S/kit.json` pra linha de comando real. Campos disponíveis:
   `{kit}` `{entrada}` `{saida}` `{palavras}` `{posicao_y}`.
   - `transcreve`: vídeo → JSON com tempo por palavra (`{saida}`).
   - `recorte`: trecho horizontal → vertical 9:16 seguindo o rosto.
   - `legenda`: vertical + `{palavras}` → vídeo com legenda em caixa.
     `{palavras}` é JSON `[{"w","s","e"}]` com tempo relativo ao início do corte.
     Se o `caps3.py` esperar outro formato, escreva um adaptador pequeno em `$S/scripts/`
     em vez de mudar o kit.
4. Troque `"_verificado"` pra `true`.

## Passo 1 — baixar e transcrever

```bash
python3 $S/scripts/baixa.py "<URL>" $P
python3 $S/scripts/frases.py $P/transcricao.json $P
```

Se a fonte não tiver vídeo (podcast só em áudio), pare e peça a versão em vídeo.

## Passo 2 — dar nota aos momentos

Leia `$S/rubrica.md` e depois `$P/frases.txt` **inteiro** (use offset/limit se for longo).
Escreva `$P/notas.json` com 15 a 25 candidatos no formato da rubrica.

## Passo 3 — tabela pra aprovar

```bash
python3 $S/scripts/tabela.py $P
```

Mostre ao usuário a tabela (`$P/cortes.md`) exatamente como saiu, com a legenda
`G/A/D/R = gancho/autonomia/desfecho/ritmo`. Se o script descartar momentos
(fora de 30–90 s, sobrepostos), corrija `notas.json` e rode de novo antes de mostrar.

Pergunte quais aprovar. Aceite respostas como `1, 3, 4` ou ajustes
(`2 começando uma frase antes`, `5 mais curto`). Para ajustes, edite `de`/`ate` em
`notas.json`, rode `tabela.py` de novo e mostre a linha nova (a numeração pode mudar).

## Passo 4 — renderizar e exportar

```bash
python3 $S/scripts/exporta.py $P --aprovados 1,3,4
```

Saída por corte em `$P/saida/NN-titulo/`:
`final.mp4` + `reels/`, `shorts/`, `tiktok/` (cada uma com o `.mp4` e `legenda.txt`).
Extraia um quadro do meio de cada `final.mp4` (`ffmpeg -ss <meio> -i final.mp4 -frames:v 1 quadro.jpg`)
e olhe: rosto enquadrado? legenda legível e fora da área dos botões? Se não, diga qual
e o que ajustar antes de entregar.

Termine com a lista de pastas geradas e a nota de cada corte.
