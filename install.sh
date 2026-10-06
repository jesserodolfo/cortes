#!/usr/bin/env bash
# Liga a skill deste repositório em ~/.claude/skills/cortes (link simbólico: editar aqui vale lá).
set -euo pipefail
origem="$(cd "$(dirname "$0")" && pwd)/skill/cortes"
destino="$HOME/.claude/skills/cortes"
mkdir -p "$HOME/.claude/skills"
if [ -e "$destino" ] && [ ! -L "$destino" ]; then
  echo "$destino já existe e não é link; mova ou apague antes." >&2; exit 1
fi
ln -sfn "$origem" "$destino"
echo "ok: $destino -> $origem"
for f in yt-dlp ffmpeg ffprobe swift; do command -v "$f" >/dev/null || echo "falta: $f"; done
kit="${CORTES_KIT:-$HOME/.claude/skills/editar-reels/kit}"
for f in transcreve.py base.py caps3.py recorte.swift; do [ -f "$kit/$f" ] || echo "falta no kit: $kit/$f"; done
