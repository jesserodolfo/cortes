# Rubrica de nota dos momentos

Leia `frases.txt` inteiro (em blocos, se for longo) antes de dar qualquer nota. Procure
momentos de **30 a 90 s** e descreva cada um pelo índice da primeira e da última frase.
Proponha de 15 a 25 candidatos; o script descarta os inválidos e fica com os 10 melhores.

## Critérios (0 a 10 cada)

**Gancho (35%)** — os primeiros ~3 s fazem alguém parar de rolar?
- 9–10: abre com afirmação forte, contradição, número, pergunta direta ou o pico emocional.
- 5–6: começa no assunto, mas sem tensão.
- 0–3: começa com "então", "e aí", resposta a uma pergunta que não aparece, ou apresentação.
- Se o melhor gancho está duas frases depois, **comece o corte nele**.

**Autonomia (30%)** — quem nunca viu o episódio entende sem contexto?
- Penalize: "como eu falei", "isso aí", "ele" sem antecedente, piada interna,
  resposta sem a pergunta. Se a pergunta do entrevistador é necessária, inclua a frase dela.

**Desfecho (25%)** — termina numa conclusão, virada, punchline ou frase citável?
- Corte na frase que fecha a ideia. Nunca no meio de uma lista ou de uma história.

**Ritmo/emoção (10%)** — energia, riso, indignação, revelação; pouca enrolação e pausa morta.

Nota final = (0,35·G + 0,30·A + 0,25·D + 0,10·R) × 10. O script calcula; não escreva a nota.

## Formato de `notas.json`

```json
[
  {
    "de": 112, "ate": 131,
    "gancho": 9, "autonomia": 8, "desfecho": 7, "ritmo": 8,
    "titulo": "Até 60 caracteres, como texto de capa",
    "motivo": "Uma frase: por que funciona sozinho",
    "descricao": "1–2 frases pra legenda do post, na voz do canal",
    "hashtags": ["#podcast", "#tema"]
  }
]
```

## Não faça

- Não invente fala que não está na transcrição (título e descrição resumem o que foi dito).
- Não junte trechos distantes num corte só: cada corte é contínuo.
- Não dê 9–10 em tudo. Use a escala inteira; a tabela serve pra eu escolher.
