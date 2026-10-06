# 2026-10-06 — Skill /cortes

Status: aceita — revisada no mesmo dia (ver "Revisão: ligação real com o kit")

## Contexto

Quero transformar episódios longos (YouTube, podcast, TikTok) em cortes verticais
prontos pra YouTube Shorts e Facebook (replicados no Instagram e no TikTok), com o comportamento do miqla.app como referência,
mas rodando local, dentro do Claude Code, e com eu aprovando cada corte antes de renderizar.

### O que o miqla.app faz (engenharia reversa)

O site está bloqueado pelo proxy do ambiente de nuvem, então o levantamento veio de
busca e do texto público indexado do site:

- Nome: "Moment IQ for Long-form Analysis".
- Entrada: cola um link (YouTube, podcast, live). Saída: **10 cortes** ordenados por
  "virality score" previsto.
- Pontua **cada momento** do vídeo inteiro e "pesa gancho, ritmo, emoção e desfecho juntos".
- Cada corte sai com legenda automática, **reenquadramento inteligente** (vertical) e nota.
- Diferencial vendido: "cada corte é reescrito — novo enquadramento, legenda, ritmo",
  porque "cortes copia-e-cola são marcados e enterrados". É a recodificação
  "shadowban-safe".

Fontes: [miqla.app](https://miqla.app/), [miqla.app/privacy](https://miqla.app/privacy)
(via resultado de busca; acesso direto bloqueado).

## Decisões

1. **Fluxo** (6 etapas, cada uma com um arquivo de saída que dá pra inspecionar):

   | # | Etapa | Ferramenta | Saída |
   |---|-------|------------|-------|
   | 1 | Baixar | `yt-dlp` (`scripts/baixa.py`) | `fonte.mp4` |
   | 2 | Transcrever com tempo por palavra | `scripts/transcreve.py` (mlx, venv do kit) | `transcricao.json` |
   | 3 | Normalizar e quebrar em frases | `scripts/frases.py` | `palavras.json`, `frases.txt` |
   | 4 | Claude dá nota aos momentos | o próprio Claude, seguindo `rubrica.md` | `notas.json` |
   | 5 | Tabela pra aprovar | `scripts/tabela.py` | `cortes.md` + `cortes.json` |
   | 6 | Render 9:16 + legenda + export | `scripts/exporta.py` → `recorte.py` + `rosto.swift`, `legenda.py` (Pillow) | `saida/NN-titulo/{shorts,facebook,instagram,tiktok}/` |

2. **Quem dá a nota é o Claude da sessão**, não uma chamada de API separada. Ele lê
   `frases.txt` (frases numeradas com `[mm:ss]`) e devolve intervalos por **índice de
   frase**. O script converte índice → tempo exato da palavra. Assim o corte nunca começa
   nem termina no meio de uma palavra, e o Claude não precisa adivinhar segundos.

3. **Rubrica** (inspirada no "gancho, ritmo, emoção, desfecho" do miqla, mais o
   critério que eu pedi de o trecho se sustentar sozinho). Cada critério de 0 a 10:

   | Critério | Peso | Pergunta |
   |----------|------|----------|
   | Gancho | 35% | Os primeiros ~3 s fazem alguém parar de rolar? |
   | Autonomia | 30% | Quem nunca viu o episódio entende sem contexto? |
   | Desfecho | 25% | Termina com conclusão, virada ou frase de efeito, sem ficar pendurado? |
   | Ritmo/emoção | 10% | Tem energia, sem pausas mortas e sem enrolação? |

   Nota final = média ponderada × 10 (0 a 100). Regras fixas, verificadas pelo script:
   **30 a 90 s**, sem sobreposição maior que 50% entre cortes (fica o de nota maior),
   até **10 cortes** na tabela (o mesmo número do miqla).

4. **Aprovação humana obrigatória.** Nada é renderizado antes de eu responder com os
   números aprovados (ex.: `1, 3, 4`). Dá pra ajustar início/fim por frase na resposta.

5. **Reaproveitar o kit `~/.claude/skills/editar-reels/kit/` sem editá-lo.** Onde o kit
   não serve como está, a skill tem um adaptador próprio em `skill/cortes/scripts/`
   (detalhes na revisão abaixo).

6. **Sem recodificação "shadowban-safe".** Não vamos mexer em fingerprint, espelhar,
   alterar velocidade, inserir ruído nem "reescrever" o corte pra enganar detecção de
   conteúdo repetido. O corte sai fiel ao original; o que muda é só o que serve ao
   espectador (enquadramento vertical e legenda). Motivo: o uso previsto é com
   permissão do dono do conteúdo, e esse tipo de recodificação é evasão de detecção.

7. **Export**: destinos principais YouTube Shorts e Facebook (Reels); Instagram e TikTok
   recebem réplica do mesmo arquivo. As quatro redes aceitam o mesmo arquivo, então há **uma única
   codificação final** por corte e uma cópia por plataforma, cada uma com seu
   `legenda.txt` (título/descrição/hashtags com o limite de cada rede):
   - 1080×1920, 30 fps, H.264 High, `yuv420p`, CRF 18, AAC 48 kHz 192 kbps,
     `+faststart`, loudness normalizada em −14 LUFS.
   - Duração ≤ 90 s cabe nas quatro (Shorts, Reels do Facebook e do Instagram, TikTok).
   - Legenda com centro em `CY=1250` (65% da altura), acima da área de botões e descrição das redes.
   - Não publica sozinho. Publicação automática (ex.: Zernio) fica pra depois.

## Fora do escopo agora

- Publicação automática e agendamento.
- B-roll, zoom dinâmico, emojis, música.
- Mais de um falante em tela dividida (o `recorte.swift` decide o rosto).

## Revisão: ligação real com o kit

A primeira versão foi escrita na nuvem, sem acesso ao kit, e chamava os scripts dele com
argumentos inventados (`kit.json`). Pelo que o Jessé conferiu no Mac, o kit funciona assim:

| Script do kit | Como é de verdade | O que a skill faz |
|---------------|-------------------|-------------------|
| `transcreve.py` | Só roda com `~/.cache/editar-reels-venv/bin/python`; `initial_prompt` fixo com vocabulário do canal ("Claude Code, Opus…") | `scripts/transcreve.py` próprio: mlx `whisper-large-v3-turbo`, `word_timestamps=True`, **sem** `initial_prompt`, `condition_on_previous_text=False` (episódio longo), roda com o python do venv |
| `recorte.swift` | **Não segue rosto**; só gera máscara de pessoa | `scripts/rosto.swift` (Vision `VNDetectFaceRectanglesRequest` a cada 0,5 s) + `scripts/recorte.py` (escolhe o rosto, suaviza o x, crop 9:16 com ffmpeg via `sendcmd`) |
| `caps3.py` | Não aceita argumentos: lê `projeto.json` do diretório atual, grava `caps/*.png` (caixa em `cy=1560`); o overlay é feito pelo `final.py` | **Não é usado.** O formato do `projeto.json` não pôde ser conferido, então `scripts/legenda.py` desenha a própria caixa (Pillow: branca, arredondada, texto preto em negrito) e sobrepõe com `overlay`+`enable=between` |
| — | ffmpeg do Homebrew sem libass/drawtext | Legenda só por PNG + `overlay`; nada de `subtitles`/`drawtext` |

`kit.json` foi removido. Do kit, a skill só usa o venv `~/.cache/editar-reels-venv` (mlx_whisper), em `scripts/comum.py` (`CORTES_PY`).

Regras do recorte seguindo o rosto:
- Um rosto por amostra: o maior, mas fica no atual se ele tiver ≥ 60% da largura do maior
  (não pula entre duas pessoas no plano aberto).
- Sem rosto: mantém o último x; nunca houve rosto: centro.
- x pula > 25% da largura entre amostras = troca de câmera: corte seco, sem panorâmica.
- Dentro do plano: média móvel ±1,5 s + zona morta de 3% da largura.

Ainda **não conferido** no Mac: a compilação do `rosto.swift` e a fonte Arial Bold do sistema.

## Teste piloto

Link de um podcast com permissão pra cortar: **pendente** — o pedido veio com o
marcador `<link de um podcast com permissão pra cortar>` em vez do link. Além disso,
o ambiente de nuvem onde a skill foi escrita não tem o kit nem acesso ao YouTube, então o
piloto roda no Mac. Critérios de aceite do piloto:

- [ ] `rosto.swift` compila e acha rosto no episódio.
- [ ] Legenda legível e acima da área de botões no Shorts e no Facebook.
- [ ] Tabela com até 10 cortes, todos entre 30 e 90 s, nenhum começando no meio de palavra.
- [ ] Pelo menos 3 cortes aprovados renderizados com rosto enquadrado e legenda legível.
- [ ] O arquivo sobe sem reprocessamento no YouTube Shorts e no Facebook (e na réplica pro Instagram e TikTok).
