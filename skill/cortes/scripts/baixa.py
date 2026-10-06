#!/usr/bin/env python3
"""Etapa 1: baixa o vídeo com yt-dlp e transcreve (scripts/transcreve.py no venv do kit).

Uso: baixa.py URL PASTA [--idioma pt] [--sem-transcricao]
Saídas em PASTA: fonte.mp4, fonte.info.json, transcricao.json
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from comum import VENV_PY, rodar


def tem_video(arquivo):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
         "stream=codec_type", "-of", "json", str(arquivo)],
        capture_output=True, text=True, check=True).stdout
    return bool(json.loads(out).get("streams"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("pasta", type=Path)
    ap.add_argument("--idioma", default="pt")
    ap.add_argument("--sem-transcricao", action="store_true")
    a = ap.parse_args()

    if not shutil.which("yt-dlp"):
        sys.exit("yt-dlp não encontrado. Instale com: brew install yt-dlp")
    a.pasta.mkdir(parents=True, exist_ok=True)
    fonte = a.pasta / "fonte.mp4"
    if not fonte.exists():
        rodar(["yt-dlp", "-f", "bv*[height<=1080]+ba/b[height<=1080]/b",
               "--merge-output-format", "mp4", "--write-info-json", "--no-playlist",
               "-o", str(a.pasta / "fonte.%(ext)s"), a.url])
    if not tem_video(fonte):
        sys.exit("A fonte não tem vídeo (podcast só de áudio). Não dá pra seguir rosto; "
                 "use a versão em vídeo do episódio.")

    if not a.sem_transcricao:
        saida = a.pasta / "transcricao.json"
        if not saida.exists():
            if not VENV_PY.exists():
                sys.exit(f"Python do venv não encontrado: {VENV_PY} (defina CORTES_PY)")
            rodar([VENV_PY, Path(__file__).with_name("transcreve.py"), fonte, saida,
                   "--idioma", a.idioma])
    print(fonte)


if __name__ == "__main__":
    main()
