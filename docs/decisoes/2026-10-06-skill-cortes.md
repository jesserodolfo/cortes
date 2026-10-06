# 2026-10-06 — Skill /cortes

Status: aceita (implementação inicial; ligação com o kit ainda não verificada no Mac)

## Contexto

Quero transformar episódios longos (YouTube, podcast, TikTok) em cortes verticais
prontos pra Reels, Shorts e TikTok, com o comportamento do miqla.app como referência,
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
   | 2 | Transcrever com tempo por palavra | kit `transcreve.py` | JSON do kit |
   | 3 | Normalizar e quebrar em frases | `scripts/frases.py` | `palavras.json`, `frases.txt` |
   | 4 | Claude dá nota aos momentos | o próprio Claude, seguindo `rubrica.md` | `notas.json` |
   | 5 | Tabela pra aprovar | `scripts/tabela.py` | `cortes.md` + `cortes.json` |
   | 6 | Render 9:16 + legenda + export | `scripts/exporta.py` → kit `recorte.swift`, `caps3.py`, `base.py` | `saida/NN-titulo/{reels,shorts,tiktok}/` |

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

5. **Reaproveitar o kit `~/.claude/skills/editar-reels/kit/`** em vez de reescrever:
   `transcreve.py` (transcrição com tempo por palavra), `recorte.swift` (seguir o rosto em
   9:16, Vision no macOS), `caps3.py` (legenda em caixa), `base.py` (utilitários).
   - A skill **não copia** o kit; chama pelo caminho (`CORTES_KIT`, padrão
     `~/.claude/skills/editar-reels/kit`).
   - As linhas de comando de cada script do kit ficam em `kit.json` como modelos
     (`{entrada}`, `{saida}`, `{palavras}`…). **O kit não estava disponível no ambiente
     onde a skill foi escrita**, então os modelos padrão são palpites. Na primeira
     execução no Mac a skill lê o `--help` e o cabeçalho de cada script e corrige o
     `kit.json`. Isso está escrito no SKILL.md como passo 0.
   - O formato da transcrição também é desconhecido; `frases.py` aceita as formas
     comuns (Whisper/faster-whisper/WhisperX `segments[].words[]`, lista plana de
     `{word,start,end}`, ou `{w,s,e}`).

6. **Sem recodificação "shadowban-safe".** Não vamos mexer em fingerprint, espelhar,
   alterar velocidade, inserir ruído nem "reescrever" o corte pra enganar detecção de
   conteúdo repetido. O corte sai fiel ao original; o que muda é só o que serve ao
   espectador (enquadramento vertical e legenda). Motivo: o uso previsto é com
   permissão do dono do conteúdo, e esse tipo de recodificação é evasão de detecção.

7. **Export**: as três plataformas aceitam o mesmo arquivo, então há **uma única
   codificação final** por corte e uma cópia por plataforma, cada uma com seu
   `legenda.txt` (título/descrição/hashtags com o limite de cada rede):
   - 1080×1920, 30 fps, H.264 High, `yuv420p`, CRF 18, AAC 48 kHz 192 kbps,
     `+faststart`, loudness normalizada em −14 LUFS.
   - Duração ≤ 90 s cabe em Reels, Shorts e TikTok.
   - Legenda dentro da zona segura (fora dos 20% de baixo e da coluna de botões à
     direita do TikTok); a posição vertical é passada pro `caps3.py`.
   - Não publica sozinho. Publicação automática (ex.: Zernio) fica pra depois.

## Fora do escopo agora

- Publicação automática e agendamento.
- B-roll, zoom dinâmico, emojis, música.
- Mais de um falante em tela dividida (o `recorte.swift` decide o rosto).

## Teste piloto

Link de um podcast com permissão pra cortar: **pendente** — o pedido veio com o
marcador `<link de um podcast com permissão pra cortar>` em vez do link. Além disso,
o ambiente de nuvem onde a skill foi escrita não tem o kit nem acesso ao YouTube, então o
piloto roda no Mac. Critérios de aceite do piloto:

- [ ] `kit.json` corrigido a partir do `--help` real do kit.
- [ ] Tabela com até 10 cortes, todos entre 30 e 90 s, nenhum começando no meio de palavra.
- [ ] Pelo menos 3 cortes aprovados renderizados com rosto enquadrado e legenda legível.
- [ ] Os três arquivos sobem sem reprocessamento no Reels, Shorts e TikTok.
