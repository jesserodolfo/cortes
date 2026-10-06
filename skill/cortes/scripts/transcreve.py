#!/usr/bin/env python3
"""Etapa 2: transcreve com mlx-whisper (large-v3-turbo) e tempo por palavra.

Roda com o python do venv do kit (tem mlx_whisper): baixa.py já chama assim.
Uso: ~/.cache/editar-reels-venv/bin/python transcreve.py ENTRADA SAIDA.json [--idioma pt]

Diferente do kit/transcreve.py: sem initial_prompt (o do kit é vocabulário do canal
do Jessé e enviesaria a transcrição de outros podcasts).
"""
import argparse
import json
import sys

MODELO = "mlx-community/whisper-large-v3-turbo"


def transcrever(entrada, idioma="pt"):
    try:
        import mlx_whisper
    except ImportError:
        sys.exit("mlx_whisper não encontrado. Rode com ~/.cache/editar-reels-venv/bin/python.")
    r = mlx_whisper.transcribe(
        str(entrada),
        path_or_hf_repo=MODELO,
        language=idioma,
        word_timestamps=True,
        # episódios longos: sem condicionar no texto anterior, evita laço de alucinação
        condition_on_previous_text=False,
    )
    return {
        "modelo": MODELO,
        "idioma": r.get("language", idioma),
        "segments": [
            {"start": s["start"], "end": s["end"], "text": s["text"],
             "words": [{"word": w["word"], "start": w["start"], "end": w["end"]}
                       for w in s.get("words", [])]}
            for s in r["segments"]
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("saida")
    ap.add_argument("--idioma", default="pt")
    a = ap.parse_args()
    dados = transcrever(a.entrada, a.idioma)
    with open(a.saida, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False)
    n = sum(len(s["words"]) for s in dados["segments"])
    print(f"{n} palavras -> {a.saida}")


if __name__ == "__main__":
    main()
