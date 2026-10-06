"""Utilitários compartilhados pelos scripts da skill /cortes."""
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
KIT_PADRAO = Path(os.environ.get("CORTES_KIT", "~/.claude/skills/editar-reels/kit")).expanduser()


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


def comando_kit(nome, kit_json=None, **valores):
    """Monta a linha de comando de um script do kit a partir do modelo em kit.json.

    O modelo é quebrado com shlex antes de substituir os campos, então caminhos com
    espaço não quebram o comando.
    """
    cfg = ler_json(kit_json or SKILL_DIR / "kit.json")
    modelo = cfg.get(nome)
    if not modelo:
        sys.exit(f"kit.json não tem o comando '{nome}'")
    valores.setdefault("kit", str(KIT_PADRAO))
    return [parte.format(**valores) for parte in shlex.split(modelo)]
