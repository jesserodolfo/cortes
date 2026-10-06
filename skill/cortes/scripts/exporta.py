#!/usr/bin/env python3
"""Etapa 6: renderiza os cortes aprovados em 9:16 com legenda e exporta por plataforma.

Uso: exporta.py PASTA --aprovados 1,3,4 [--sem-kit]

Para cada corte aprovado (número da tabela em cortes.md):
  1. recorta o trecho da fonte (re-encode, corte exato no tempo da palavra)
  2. recorte.py (+ rosto.swift) -> vertical 9:16 seguindo o rosto
  3. legenda.py (+ kit caps3.py) -> legenda em caixa (palavras com tempo relativo ao corte)
  4. codificação final única (1080x1920, 30 fps, H.264, AAC, -14 LUFS, faststart)
  5. copia para reels/, shorts/, tiktok/ com o texto de postagem de cada rede

--sem-kit só serve pra testar o encadeamento sem Swift e sem o kit: corte central, sem legenda.
"""
import argparse
import re
import shutil
import sys
import unicodedata
from pathlib import Path

from comum import gravar_json, ler_json, rodar
from legenda import legendar
from recorte import recortar

LARG, ALT, FPS = 1080, 1920, 30

PLATAFORMAS = {
    # nome: (limite de caracteres do texto, hashtags extras)
    "reels": (2200, []),
    "shorts": (100, ["#Shorts"]),   # título do Shorts: 100 caracteres
    "tiktok": (2200, []),
}


def slug(txt, n=40):
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", txt.lower()).strip("-")[:n] or "corte"


def texto_post(corte, plataforma):
    limite, extras = PLATAFORMAS[plataforma]
    tags = " ".join(list(corte.get("hashtags", [])) + extras)
    if plataforma == "shorts":
        base = corte.get("titulo", "")
        corpo = f"{base} {tags}".strip()
    else:
        partes = [corte.get("titulo", ""), corte.get("descricao", ""), tags]
        corpo = "\n\n".join(p for p in partes if p)
    return corpo[:limite]


def palavras_do_corte(palavras, ini, fim):
    return [{"w": p["w"], "s": round(max(p["s"] - ini, 0), 3), "e": round(min(p["e"], fim) - ini, 3)}
            for p in palavras if p["e"] > ini and p["s"] < fim]


def final(entrada, saida):
    filtro = (f"scale={LARG}:{ALT}:force_original_aspect_ratio=increase,"
              f"crop={LARG}:{ALT},setsar=1,fps={FPS}")
    rodar(["ffmpeg", "-y", "-v", "error", "-i", entrada, "-vf", filtro,
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
           "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "18",
           "-preset", "slow", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", saida])


def exportar(pasta, corte, palavras, sem_kit):
    destino = pasta / "saida" / f"{corte['n']:02d}-{slug(corte.get('titulo', ''))}"
    tmp = destino / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    ini, fim = corte["inicio"], corte["fim"]

    trecho = tmp / "1-trecho.mp4"
    rodar(["ffmpeg", "-y", "-v", "error", "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}",
           "-i", pasta / "fonte.mp4", "-c:v", "libx264", "-crf", "14", "-preset", "fast",
           "-c:a", "aac", "-b:a", "256k", trecho])
    pal = tmp / "palavras.json"
    gravar_json(pal, palavras_do_corte(palavras, ini, fim))

    if sem_kit:
        legendado = trecho  # final() já faz o corte central 9:16
    else:
        vertical, legendado = tmp / "2-vertical.mp4", tmp / "3-legendado.mp4"
        recortar(trecho, vertical)
        legendar(vertical, pal, legendado)

    mestre = destino / "final.mp4"
    final(legendado, mestre)
    for plat in PLATAFORMAS:
        d = destino / plat
        d.mkdir(exist_ok=True)
        shutil.copy2(mestre, d / f"{slug(corte.get('titulo', ''))}.mp4")
        (d / "legenda.txt").write_text(texto_post(corte, plat) + "\n", encoding="utf-8")
    return destino


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta", type=Path)
    ap.add_argument("--aprovados", required=True, help="números da tabela, ex.: 1,3,4")
    ap.add_argument("--sem-kit", action="store_true")
    a = ap.parse_args()

    cortes = {c["n"]: c for c in ler_json(a.pasta / "cortes.json")}
    try:
        numeros = [int(x) for x in a.aprovados.replace(" ", "").split(",") if x]
    except ValueError:
        sys.exit("--aprovados precisa ser uma lista de números, ex.: 1,3,4")
    faltando = [n for n in numeros if n not in cortes]
    if faltando:
        sys.exit(f"Cortes inexistentes na tabela: {faltando}")
    palavras = ler_json(a.pasta / "palavras.json")
    for n in numeros:
        print(exportar(a.pasta, cortes[n], palavras, a.sem_kit))


if __name__ == "__main__":
    main()
