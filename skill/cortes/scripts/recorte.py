#!/usr/bin/env python3
"""Corte 9:16 seguindo o rosto: rosto.swift dá as caixas, aqui suaviza o x e o ffmpeg corta.

Uso: recorte.py ENTRADA SAIDA [--rostos rostos.json]
Sem --rostos, roda `swift rosto.swift` antes (precisa do Xcode Command Line Tools).

- Escolhe um rosto por amostra: o maior, mas fica no rosto anterior se ele ainda for
  grande o bastante (evita ficar pulando entre duas pessoas no plano aberto).
- Sem rosto: repete o último x (ou o próximo, no começo; centro se nunca houver rosto).
- Pulo grande de uma amostra pra outra = troca de câmera: corta seco, sem panorâmica.
- Dentro de cada plano: média móvel de ±1,5 s e zona morta pra não tremer.
- O x de cada quadro vai pro filtro crop via sendcmd (o ffmpeg do Homebrew não precisa de libass).
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from comum import ler_json, rodar

LARG, ALT, FPS = 1080, 1920, 30
JANELA = 1.5         # s de cada lado na média móvel
ZONA_MORTA = 0.03    # fração da largura da fonte que o rosto pode andar sem a câmera seguir
PULO_CORTE = 0.25    # fração da largura que, num passo só, indica troca de câmera
FICA_NO_ATUAL = 0.6  # fica no rosto atual se ele tiver ao menos 60% da largura do maior
PERTO = 0.15         # distância (fração da largura) pra considerar "o mesmo rosto"


def escolher(amostras):
    """Uma posição x (0–1) ou None por amostra."""
    xs, atual = [], None
    for a in amostras:
        rostos = a.get("rostos") or []
        if not rostos:
            xs.append(None)
            continue
        maior = max(rostos, key=lambda r: r["w"])
        if atual is not None:
            perto = [r for r in rostos if abs(r["x"] - atual) < PERTO]
            if perto:
                mesmo = max(perto, key=lambda r: r["w"])
                if mesmo["w"] >= FICA_NO_ATUAL * maior["w"]:
                    maior = mesmo
        atual = maior["x"]
        xs.append(atual)
    return xs


def preencher(xs):
    if all(x is None for x in xs):
        return [0.5] * len(xs)
    primeiro = next(x for x in xs if x is not None)
    saida, ultimo = [], primeiro
    for x in xs:
        ultimo = x if x is not None else ultimo
        saida.append(ultimo)
    return saida


def planos(xs):
    """Índices [ini, fim) de cada plano, quebrando onde o x pula demais."""
    cortes = [0] + [i for i in range(1, len(xs)) if abs(xs[i] - xs[i - 1]) > PULO_CORTE] + [len(xs)]
    return list(zip(cortes, cortes[1:]))


def suavizar(xs, passo):
    raio = max(1, round(JANELA / passo))
    saida = []
    for a, b in planos(xs):
        trecho = xs[a:b]
        media = [sum(trecho[max(0, i - raio):i + raio + 1]) / len(trecho[max(0, i - raio):i + raio + 1])
                 for i in range(len(trecho))]
        cam = media[0]
        for m in media:
            if abs(m - cam) > ZONA_MORTA:
                cam = m - ZONA_MORTA if m > cam else m + ZONA_MORTA
            saida.append(cam)
    return saida


def x_por_quadro(xs, passo, duracao, larg, larg_corte):
    """x em pixels (par, dentro da imagem) pra cada quadro. Interpola dentro do plano, corte seco entre planos."""
    limites = {a for a, _ in planos(xs)} - {0}
    res = []
    for q in range(int(duracao * FPS) + 1):
        t = q / FPS
        i = min(int(t / passo), len(xs) - 1)
        f = t / passo - i
        if i + 1 < len(xs) and (i + 1) not in limites:
            xc = xs[i] + (xs[i + 1] - xs[i]) * f
        elif i + 1 < len(xs) and f >= 0.5:   # troca de câmera: no meio do intervalo
            xc = xs[i + 1]
        else:
            xc = xs[i]
        px = min(max(xc * larg - larg_corte / 2, 0), larg - larg_corte)
        res.append(int(px) // 2 * 2)
    return res


def comandos_sendcmd(xs_px):
    linhas, anterior = [], None
    for q, x in enumerate(xs_px):
        if x != anterior:
            linhas.append(f"{q / FPS:.4f} crop@r x {x};")
            anterior = x
    return "\n".join(linhas) + "\n"


def sondar(entrada):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:format=duration", "-of", "json", str(entrada)],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    return d["streams"][0]["width"], d["streams"][0]["height"], float(d["format"]["duration"])


def recortar(entrada, saida, rostos_json=None):
    entrada, saida = Path(entrada).resolve(), Path(saida).resolve()
    larg, alt, dur = sondar(entrada)
    if rostos_json is None:
        rostos_json = saida.with_suffix(".rostos.json")
        rodar(["swift", Path(__file__).with_name("rosto.swift"), entrada, rostos_json])
    r = ler_json(rostos_json)
    larg_corte = min(larg, int(alt * 9 / 16) // 2 * 2)
    xs = suavizar(preencher(escolher(r["amostras"])), r["passo"]) if r["amostras"] else [0.5]
    px = x_por_quadro(xs, r["passo"], dur, larg, larg_corte)
    with tempfile.TemporaryDirectory() as tmp:
        # caminho relativo dentro do filtro: evita escapar ':' e aspas do caminho
        Path(tmp, "x.cmd").write_text(comandos_sendcmd(px))
        filtro = (f"sendcmd=f=x.cmd,crop@r=w={larg_corte}:h={alt}:x={px[0]}:y=0,"
                  f"scale={LARG}:{ALT}:flags=lanczos,setsar=1")
        rodar(["ffmpeg", "-y", "-v", "error", "-i", entrada, "-vf", filtro, "-c:v", "libx264",
               "-crf", "14", "-preset", "fast", "-c:a", "copy", saida], cwd=tmp)
    return saida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("saida")
    ap.add_argument("--rostos")
    a = ap.parse_args()
    print(recortar(a.entrada, a.saida, a.rostos))


if __name__ == "__main__":
    main()
