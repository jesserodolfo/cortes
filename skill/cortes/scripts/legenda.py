#!/usr/bin/env python3
"""Legenda em caixa com o caps3.py do kit, sobreposta com ffmpeg (sem libass/drawtext).

Uso: legenda.py ENTRADA_VERTICAL PALAVRAS.json SAIDA

O caps3.py do kit não aceita argumentos: lê projeto.json do diretório atual e grava
caps/*.png (caixa centrada em cy=1560). Então este adaptador:
  1. agrupa as palavras do corte em blocos curtos (1 bloco = 1 PNG);
  2. monta projeto.json num diretório temporário e roda o caps3.py lá, com o python do venv;
  3. sobrepõe cada PNG no intervalo do seu bloco (overlay com enable=between).

ATENÇÃO: o formato de projeto.json em montar_projeto() ainda não foi conferido com o
caps3.py real (escrito sem acesso ao kit). Se o caps3.py reclamar ou gerar um número de
PNGs diferente do número de blocos, ajuste montar_projeto() e a ordem em ler_pngs().
"""
import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

from comum import KIT, VENV_PY, gravar_json, ler_json, rodar

ALT, CY = 1920, 1560          # cy usado pelo caps3.py do kit
MAX_PALAVRAS, MAX_CHARS = 3, 20
PAUSA_QUEBRA = 0.35           # s de silêncio que fecha um bloco
SEGURA = 0.5                  # bloco fica na tela até o próximo se o buraco for menor que isso
# scripts do kit rodados em ordem no diretório do projeto (ex.: CORTES_CAPS="caps2.py caps3.py")
CAPS = os.environ.get("CORTES_CAPS", "caps3.py").split()


def agrupar(palavras):
    blocos, atual = [], []
    for k, p in enumerate(palavras):
        atual.append(p)
        texto = " ".join(w["w"] for w in atual)
        prox = palavras[k + 1] if k + 1 < len(palavras) else None
        fecha = (prox is None or len(atual) >= MAX_PALAVRAS or p["w"][-1] in ".,?!…:;"
                 or prox["s"] - p["e"] >= PAUSA_QUEBRA
                 or len(texto) + 1 + len(prox["w"]) > MAX_CHARS)
        if fecha:
            blocos.append({"texto": texto, "inicio": atual[0]["s"], "fim": p["e"]})
            atual = []
    for a, b in zip(blocos, blocos[1:]):
        if b["inicio"] - a["fim"] < SEGURA:
            a["fim"] = b["inicio"]
    return [{**b, "inicio": round(b["inicio"], 3), "fim": round(b["fim"], 3)} for b in blocos]


def montar_projeto(blocos):
    """projeto.json pro caps3.py. FORMATO SUPOSTO — conferir com o kit."""
    return {"legendas": [{"texto": b["texto"], "inicio": b["inicio"], "fim": b["fim"]} for b in blocos]}


def ler_pngs(pasta):
    return sorted((pasta / "caps").glob("*.png"))


def gerar_pngs(blocos, tmp):
    gravar_json(tmp / "projeto.json", montar_projeto(blocos))
    for script in CAPS:
        rodar([VENV_PY, KIT / script], cwd=tmp)
    pngs = ler_pngs(tmp)
    if len(pngs) != len(blocos):
        sys.exit(f"caps3.py gerou {len(pngs)} PNGs para {len(blocos)} blocos de legenda; "
                 "conferir montar_projeto() em legenda.py contra o formato real do projeto.json.")
    return pngs


def filtro_overlay(blocos):
    """PNG em tela cheia (altura 1920) vai em 0,0; caixa menor é centrada em x e em cy=1560."""
    partes, anterior = [], "0:v"
    for k, b in enumerate(blocos, 1):
        saida = f"v{k}"
        partes.append(
            f"[{anterior}][{k}:v]overlay=x=(main_w-overlay_w)/2:"
            f"y='if(eq(overlay_h,main_h),0,{CY}-overlay_h/2)':"
            f"enable='between(t,{b['inicio']},{b['fim']})'[{saida}]")
        anterior = saida
    return ";".join(partes), f"[{anterior}]"


def sobrepor(entrada, pngs, blocos, saida):
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", entrada]
    for p in pngs:
        cmd += ["-i", p]
    grafo, ultimo = filtro_overlay(blocos)
    cmd += ["-filter_complex", grafo, "-map", ultimo, "-map", "0:a?", "-c:v", "libx264",
            "-crf", "14", "-preset", "fast", "-c:a", "copy", saida]
    rodar(cmd)


def legendar(entrada, palavras_json, saida):
    blocos = agrupar(ler_json(palavras_json))
    if not blocos:
        shutil.copy2(entrada, saida)
        return saida
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        sobrepor(Path(entrada).resolve(), gerar_pngs(blocos, tmp), blocos, Path(saida).resolve())
    return saida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("palavras")
    ap.add_argument("saida")
    a = ap.parse_args()
    print(legendar(a.entrada, a.palavras, a.saida))


if __name__ == "__main__":
    main()
