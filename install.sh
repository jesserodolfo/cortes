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
py="${CORTES_PY:-$HOME/.cache/editar-reels-venv/bin/python}"
if [ -x "$py" ]; then
  "$py" -c "import mlx_whisper" 2>/dev/null || echo "falta: mlx_whisper no venv ($py)"
else
  echo "falta: python do venv do kit ($py)"
fi
python3 -c "import PIL" 2>/dev/null || echo "falta: Pillow (python3 -m pip install --user pillow)"
