---
name: cortes
description: Transforma um episódio longo (link do YouTube, podcast em vídeo ou TikTok) em cortes verticais 9:16 com legenda em caixa pra YouTube Shorts e Facebook (com réplica pra Instagram e TikTok). Baixa com yt-dlp, transcreve com tempo por palavra, dá nota a cada momento (gancho, autonomia, desfecho, ritmo; 30 a 90 s), mostra uma tabela pra aprovar e só então renderiza seguindo o rosto. Use quando o usuário digitar /cortes, colar um link pedindo cortes, ou falar em "cortar podcast", "tirar cortes", "clips do episódio".
---

# /cortes

Do link ao corte aprovado. Decisões e motivos: `docs/decisoes/2026-10-06-skill-cortes.md`
no repositório `cortes`.

Pasta da skill: `~/.claude/skills/cortes` (abaixo, `$S`). Trabalho de cada episódio:
`~/Cortes/<slug-do-episodio>/` (abaixo, `$P`).

## Regras

- **Só corte conteúdo com permissão** do dono. Se o usuário não disse que tem, pergunte antes de baixar.
- **Nunca renderize antes da aprovação** da tabela.
- **Sem recodificação "shadowban-safe"**: não espelhe, não mude velocidade, não adicione ruído
  nem altere o vídeo pra fugir de detecção de conteúdo repetido. Se pedirem, recuse e explique.
- Não publique sozinho. Entrega é a pasta `saida/`.
- **Não edite o kit** `~/.claude/skills/editar-reels/kit`. Diferença de comportamento vira
  adaptador em `$S/scripts/`.

## O que roda onde

| Etapa | Script | Depende de |
|-------|--------|------------|
| Transcrição | `scripts/transcreve.py` (mlx whisper-large-v3-turbo, tempo por palavra, sem `initial_prompt`) | `~/.cache/editar-reels-venv/bin/python` (`CORTES_PY`) |
| Rosto | `scripts/rosto.swift` (Vision, a cada 0,5 s) + `scripts/recorte.py` (suaviza x, crop 9:16 via sendcmd) | `swift` (Xcode Command Line Tools), ffmpeg |
| Legenda | `scripts/legenda.py` → `projeto.json` → kit `caps3.py` → `caps/*.png` → overlay ffmpeg | venv + kit (`CORTES_KIT`) |

O kit não tem `--help`; não tente descobrir argumentos rodando os scripts dele.
Se o `caps3.py` falhar ou gerar um número de PNGs diferente do número de blocos de legenda,
o problema está em `montar_projeto()` de `scripts/legenda.py`: leia o `caps3.py` (só leitura),
ajuste o adaptador e rode `python3 -m unittest discover -s tests` no repositório `cortes`.

## Passo 1 — baixar e transcrever

```bash
python3 $S/scripts/baixa.py "<URL>" $P            # --idioma en, se não for português
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
`final.mp4` + `shorts/` e `facebook/` (destinos principais) e `instagram/`, `tiktok/` (réplica do
mesmo arquivo), cada uma com o `.mp4` e `legenda.txt`.
Extraia um quadro do meio de cada `final.mp4` (`ffmpeg -ss <meio> -i final.mp4 -frames:v 1 quadro.jpg`)
e olhe: rosto enquadrado? legenda legível e fora da área dos botões? Se não, diga qual
e o que ajustar antes de entregar.

Termine com a lista de pastas geradas e a nota de cada corte.
