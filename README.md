# cortes

Skill `/cortes` do Claude Code: link de episódio → cortes verticais 9:16 com legenda,
com nota por momento e aprovação antes de renderizar. Comportamento inspirado no miqla.app,
sem a recodificação "shadowban-safe".

- Decisão e fluxo: [`docs/decisoes/2026-10-06-skill-cortes.md`](docs/decisoes/2026-10-06-skill-cortes.md)
- Skill: [`skill/cortes/SKILL.md`](skill/cortes/SKILL.md)

## Instalar (Mac)

```bash
brew install yt-dlp ffmpeg
./install.sh
```

Depois, no Claude Code: `/cortes <link>`. Na primeira vez a skill confere o kit
`~/.claude/skills/editar-reels/kit` e ajusta `skill/cortes/kit.json`.

## Testes

```bash
python3 -m unittest discover -s tests
```
