#!/usr/bin/env python3
"""Legenda em caixa desenhada pela própria skill (Pillow) e sobreposta com ffmpeg.

Uso: legenda.py ENTRADA_VERTICAL PALAVRAS.json SAIDA

Não depende do kit nem de libass/drawtext (o ffmpeg do Homebrew não tem):
  1. agrupa as palavras do corte em blocos curtos (1 bloco = 1 PNG);
  2. desenha cada bloco como caixa branca arredondada com texto preto em negrito;
  3. sobrepõe cada PNG no intervalo do seu bloco (overlay com enable=between).
Precisa de Pillow no python que roda o script (`python3 -m pip install --user pillow`).
Fonte: CORTES_FONTE, ou a primeira que existir em FONTES.
"""
import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

from comum import ler_json, rodar

LARG = 1080
CY = 1250                     # centro da caixa: 65% da altura, acima da UI de baixo das redes
MAX_PALAVRAS, MAX_CHARS = 3, 20
PAUSA_QUEBRA = 0.35           # s de silêncio que fecha um bloco
SEGURA = 0.5                  # bloco fica na tela até o próximo se o buraco for menor que isso

TAMANHO = 72                  # px da fonte
LARG_MAX = 900                # largura máxima do texto antes de quebrar linha
PAD_X, PAD_Y, RAIO = 36, 22, 26
ENTRELINHA = 1.15
COR_CAIXA, COR_TEXTO = (255, 255, 255, 255), (0, 0, 0, 255)
FONTES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",   # macOS
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux (testes)
]


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


def fonte():
    from PIL import ImageFont
    candidatas = [os.environ["CORTES_FONTE"]] if os.environ.get("CORTES_FONTE") else FONTES
    for f in candidatas:
        if Path(f).exists():
            return ImageFont.truetype(f, TAMANHO)
    sys.exit(f"Nenhuma fonte encontrada em {candidatas}; defina CORTES_FONTE.")


def quebrar_linhas(texto, f):
    linhas = [""]
    for palavra in texto.split():
        teste = (linhas[-1] + " " + palavra).strip()
        if f.getlength(teste) <= LARG_MAX or not linhas[-1]:
            linhas[-1] = teste
        else:
            linhas.append(palavra)
    return linhas


def desenhar(texto, saida, f):
    from PIL import Image, ImageDraw
    linhas = quebrar_linhas(texto, f)
    sobe, desce = f.getmetrics()
    alt_linha = round((sobe + desce) * ENTRELINHA)
    larg_txt = max(f.getlength(l) for l in linhas)
    w = min(LARG, round(larg_txt) + 2 * PAD_X)
    h = alt_linha * len(linhas) - (alt_linha - sobe - desce) + 2 * PAD_Y
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=RAIO, fill=COR_CAIXA)
    for i, linha in enumerate(linhas):
        d.text((w / 2, PAD_Y + i * alt_linha), linha, font=f, fill=COR_TEXTO, anchor="ma")
    img.save(saida)
    return saida


def gerar_pngs(blocos, tmp):
    f = fonte()
    return [desenhar(b["texto"], tmp / f"{k:04d}.png", f) for k, b in enumerate(blocos)]


def filtro_overlay(blocos):
    partes, anterior = [], "0:v"
    for k, b in enumerate(blocos, 1):
        saida = f"v{k}"
        partes.append(
            f"[{anterior}][{k}:v]overlay=x=(main_w-overlay_w)/2:y={CY}-overlay_h/2:"
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
        sobrepor(Path(entrada).resolve(), gerar_pngs(blocos, Path(d)), blocos, Path(saida).resolve())
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
