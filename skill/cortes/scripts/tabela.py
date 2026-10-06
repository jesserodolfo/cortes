#!/usr/bin/env python3
"""Etapa 5: valida as notas do Claude e monta a tabela de cortes pra aprovar.

Uso: tabela.py PASTA
Lê PASTA/frases.json e PASTA/notas.json; grava PASTA/cortes.json e PASTA/cortes.md.

notas.json é uma lista de momentos:
  {"de": 12, "ate": 31, "gancho": 8, "autonomia": 9, "desfecho": 7, "ritmo": 6,
   "titulo": "...", "motivo": "...", "descricao": "...", "hashtags": ["..."]}
"de"/"ate" são índices de frase (inclusivos) de frases.txt.
"""
import argparse
import sys
from pathlib import Path

from comum import gravar_json, ler_json, mmss

PESOS = {"gancho": 0.35, "autonomia": 0.30, "desfecho": 0.25, "ritmo": 0.10}
DUR_MIN, DUR_MAX = 30.0, 90.0
MAX_CORTES = 10
SOBREPOSICAO_MAX = 0.5   # fração do corte mais curto
FOLGA_INI, FOLGA_FIM = 0.15, 0.35  # respiro antes da 1ª e depois da última palavra


def nota(m):
    for c in PESOS:
        v = m.get(c)
        if not isinstance(v, (int, float)) or not 0 <= v <= 10:
            raise ValueError(f"'{c}' precisa ser número de 0 a 10 (veio {v!r})")
    return round(sum(m[c] * p for c, p in PESOS.items()) * 10)


def montar(frases, notas):
    aceitos, rejeitados = [], []
    for k, m in enumerate(notas):
        try:
            de, ate = int(m["de"]), int(m["ate"])
            if not 0 <= de <= ate < len(frases):
                raise ValueError(f"frases {de}–{ate} fora de 0–{len(frases) - 1}")
            n = nota(m)
        except (KeyError, ValueError, TypeError) as e:
            rejeitados.append(f"momento {k}: {e}")
            continue
        ini = max(frases[de]["s"] - FOLGA_INI, frases[de - 1]["e"] if de else 0.0, 0.0)
        fim = frases[ate]["e"] + FOLGA_FIM
        if ate + 1 < len(frases):
            fim = min(fim, frases[ate + 1]["s"])
        dur = fim - ini
        if not DUR_MIN <= dur <= DUR_MAX:
            rejeitados.append(f"momento {k} (frases {de}–{ate}): {dur:.1f}s fora de 30–90s")
            continue
        aceitos.append({**m, "de": de, "ate": ate, "inicio": round(ini, 3), "fim": round(fim, 3),
                        "duracao": round(dur, 1), "nota": n,
                        "abertura": frases[de]["texto"]})

    aceitos.sort(key=lambda c: -c["nota"])
    escolhidos = []
    for c in aceitos:
        conflito = next((o for o in escolhidos
                         if min(c["fim"], o["fim"]) - max(c["inicio"], o["inicio"])
                         > SOBREPOSICAO_MAX * min(c["duracao"], o["duracao"])), None)
        if conflito:
            rejeitados.append(f"'{c.get('titulo', '')}' sobrepõe '{conflito.get('titulo', '')}' (nota maior)")
        elif len(escolhidos) < MAX_CORTES:
            escolhidos.append(c)
    for n, c in enumerate(escolhidos, 1):
        c["n"] = n
    return escolhidos, rejeitados


def markdown(cortes):
    linhas = ["| # | Nota | Duração | Trecho | Título | Abre com | G/A/D/R | Por quê |",
              "|---|------|---------|--------|--------|----------|---------|---------|"]
    for c in cortes:
        abre = c["abertura"]
        abre = abre if len(abre) <= 70 else abre[:67] + "..."
        linhas.append(
            f"| {c['n']} | **{c['nota']}** | {c['duracao']:.0f}s | {mmss(c['inicio'])}–{mmss(c['fim'])} "
            f"| {c.get('titulo', '')} | “{abre}” "
            f"| {c['gancho']}/{c['autonomia']}/{c['desfecho']}/{c['ritmo']} | {c.get('motivo', '')} |")
    return "\n".join(linhas) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta", type=Path)
    a = ap.parse_args()
    cortes, rejeitados = montar(ler_json(a.pasta / "frases.json"), ler_json(a.pasta / "notas.json"))
    gravar_json(a.pasta / "cortes.json", cortes)
    tabela = markdown(cortes)
    (a.pasta / "cortes.md").write_text(tabela, encoding="utf-8")
    print(tabela)
    for r in rejeitados:
        print("descartado: " + r, file=sys.stderr)
    if not cortes:
        sys.exit("Nenhum corte válido.")


if __name__ == "__main__":
    main()
