#!/usr/bin/env python3
"""Etapa 3: normaliza a transcrição do kit e quebra em frases numeradas.

Uso: frases.py transcricao.json PASTA
Saídas em PASTA:
  palavras.json  lista [{"w", "s", "e"}] em segundos
  frases.json    lista [{"i", "s", "e", "p0", "p1", "texto"}] (p0/p1 = índices em palavras)
  frases.txt     uma frase por linha: "012 [03:21.4] texto" — é isto que o Claude lê
"""
import argparse
import sys
from pathlib import Path

from comum import gravar_json, ler_json, mmss

PAUSA_FIM = 0.7      # pausa (s) que encerra uma frase mesmo sem pontuação
FRASE_MAX = 20.0     # frase mais longa que isso é quebrada na maior pausa interna


def _palavra(d):
    w = d.get("word", d.get("w", d.get("text")))
    s = d.get("start", d.get("s"))
    e = d.get("end", d.get("e"))
    if w is None or s is None or e is None:
        return None
    return {"w": str(w).strip(), "s": float(s), "e": float(e)}


def normalizar(dados):
    """Aceita Whisper/faster-whisper/WhisperX (segments[].words[]), lista plana ou {words: [...]}."""
    if isinstance(dados, dict):
        if "segments" in dados:
            brutas = [w for seg in dados["segments"] for w in seg.get("words", [])]
        elif "words" in dados:
            brutas = dados["words"]
        elif "palavras" in dados:
            brutas = dados["palavras"]
        else:
            sys.exit(f"Formato de transcrição desconhecido (chaves: {list(dados)[:8]})")
    else:
        brutas = dados
    palavras = [p for p in map(_palavra, brutas) if p and p["w"]]
    if not palavras:
        sys.exit("Transcrição sem palavras com tempo. O transcreve.py gerou tempo por palavra?")
    palavras.sort(key=lambda p: p["s"])
    return palavras


def quebrar(palavras):
    frases, ini = [], 0
    for k, p in enumerate(palavras):
        ultima = k == len(palavras) - 1
        pausa = 0 if ultima else palavras[k + 1]["s"] - p["e"]
        if ultima or p["w"][-1] in ".?!…" or pausa >= PAUSA_FIM:
            frases.append((ini, k))
            ini = k + 1
    # frases muito longas: quebra recursivamente na maior pausa interna
    saida = []
    pilha = list(reversed(frases))
    while pilha:
        a, b = pilha.pop()
        if palavras[b]["e"] - palavras[a]["s"] <= FRASE_MAX or b - a < 2:
            saida.append((a, b))
            continue
        corte = max(range(a, b), key=lambda k: palavras[k + 1]["s"] - palavras[k]["e"])
        pilha.extend([(corte + 1, b), (a, corte)])
    return [
        {"i": i, "s": palavras[a]["s"], "e": palavras[b]["e"], "p0": a, "p1": b,
         "texto": " ".join(p["w"] for p in palavras[a:b + 1])}
        for i, (a, b) in enumerate(saida)
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcricao", type=Path)
    ap.add_argument("pasta", type=Path)
    a = ap.parse_args()
    palavras = normalizar(ler_json(a.transcricao))
    frases = quebrar(palavras)
    gravar_json(a.pasta / "palavras.json", palavras)
    gravar_json(a.pasta / "frases.json", frases)
    with open(a.pasta / "frases.txt", "w", encoding="utf-8") as f:
        for fr in frases:
            f.write(f"{fr['i']:03d} [{mmss(fr['s'])}] {fr['texto']}\n")
    print(f"{len(palavras)} palavras, {len(frases)} frases, "
          f"{mmss(palavras[-1]['e'])} de áudio -> {a.pasta / 'frases.txt'}")


if __name__ == "__main__":
    main()
