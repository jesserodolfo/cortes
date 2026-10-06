"""Utilitários compartilhados pelos scripts da skill /cortes."""
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
# Python do venv do kit editar-reels (tem mlx_whisper); só a transcrição usa.
VENV_PY = Path(os.environ.get("CORTES_PY", "~/.cache/editar-reels-venv/bin/python")).expanduser()


def ler_json(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def gravar_json(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
        f.write("\n")


def mmss(seg):
    m, s = divmod(max(seg, 0), 60)
    return f"{int(m):02d}:{s:04.1f}"


def rodar(cmd, **kw):
    print("+ " + " ".join(shlex.quote(str(c)) for c in cmd), file=sys.stderr)
    subprocess.run([str(c) for c in cmd], check=True, **kw)

