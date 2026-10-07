"""Estuda cortes já publicados (Instagram, TikTok, YouTube Shorts) pra extrair o padrão.

Uso:
  python3 estuda.py <pasta-de-saida> <url> [<url> ...]
  python3 estuda.py <pasta-de-saida> --lista urls.txt [--cookies-from-browser chrome]

Pra cada URL gera uma subpasta NN/ com:
  meta.json          id, autor, legenda do post, likes, comentários, views (quando a rede expõe),
                     duração, dimensões, trocas de plano (segundos) e plano médio
  video.mp4, audio.wav
  abertura.jpg       3 quadros, 1 por segundo, dos 3 primeiros segundos (gancho e legenda)
  contato.jpg        folha de contato: 1 quadro a cada 2 s (ritmo, enquadramento, legenda)
  meio.jpg, fim.jpg  quadro do meio e do último segundo e meio (como termina)
  transcricao.txt    frases com [de-ate] em segundos, pra achar a frase de abertura e a virada

Transcrição: usa sherpa-onnx + Whisper (CORTES_WHISPER_DIR apontando pra pasta do modelo
sherpa-onnx-whisper-*) ou, no Mac, o mlx_whisper do venv do kit (CORTES_PY). Sem nenhum dos dois,
pula a transcrição e avisa. As trocas de plano vêm do detector de cena do ffmpeg (limiar 0,30).
"""
import json
import math
import os
import re
import subprocess
import sys
import wave
from pathlib import Path

from comum import VENV_PY, gravar_json

WHISPER_DIR = Path(os.environ.get("CORTES_WHISPER_DIR", "")).expanduser()


def sh(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)


def baixar(url, pasta, extra):
    mp4 = pasta / "video.mp4"
    r = sh(["python3", "-m", "yt_dlp", "--no-warnings", "-J", *extra, url])
    if r.returncode != 0 or not r.stdout.strip():
        return None, r.stderr.strip()[-600:]
    j = json.loads(r.stdout)
    meta = {k: j.get(k) for k in ("id", "webpage_url", "uploader", "channel", "title", "description",
                                  "like_count", "comment_count", "view_count", "repost_count",
                                  "timestamp", "upload_date")}
    if not mp4.exists():
        r = sh(["python3", "-m", "yt_dlp", "--no-warnings", "-o", mp4, *extra, url])
        if not mp4.exists():
            return None, r.stderr.strip()[-600:]
    return meta, None


def quadros(mp4, pasta, dur):
    linhas = max(1, math.ceil(dur / 2 / 5))
    sh(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-vf", f"fps=0.5,scale=270:-1,tile=5x{linhas}:padding=2",
        "-frames:v", "1", pasta / "contato.jpg"])
    sh(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-t", "3", "-vf", "fps=1,scale=540:-1,tile=3x1:padding=2",
        "-frames:v", "1", pasta / "abertura.jpg"])
    sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{dur / 2:.2f}", "-i", mp4, "-frames:v", "1", "-vf", "scale=540:-1", pasta / "meio.jpg"])
    sh(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, dur - 1.5):.2f}", "-i", mp4, "-frames:v", "1", "-vf", "scale=540:-1", pasta / "fim.jpg"])


def trocas_de_plano(mp4):
    r = sh(["ffmpeg", "-v", "info", "-i", mp4, "-vf", "select='gt(scene,0.30)',showinfo", "-f", "null", "-"])
    return [round(float(t), 2) for t in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


def segmentos_por_silencio(amostras, sr):
    """Divide o áudio em trechos de fala separados por silêncio >= 0,35 s (máx. 12 s cada)."""
    import numpy as np
    jan = int(0.05 * sr)
    energia = np.array([np.sqrt(np.mean(amostras[i:i + jan] ** 2)) for i in range(0, len(amostras), jan)])
    limiar = max(0.01, float(np.percentile(energia, 20)) * 1.5)
    segs, ini, sil = [], None, 0
    for i, e in enumerate(energia):
        t = i * 0.05
        if e > limiar:
            ini = t if ini is None else ini
            sil = 0
        else:
            sil += 1
            if ini is not None and sil * 0.05 >= 0.35:
                segs.append((ini, t))
                ini = None
    if ini is not None:
        segs.append((ini, len(energia) * 0.05))
    saida = []
    for a, b in segs:
        while b - a > 12:
            saida.append((a, a + 10))
            a += 10
        if b - a >= 0.3:
            saida.append((a, b))
    return saida


def transcrever_sherpa(wav):
    import numpy as np
    import sherpa_onnx
    enc = next(WHISPER_DIR.glob("*-encoder*.onnx"))
    dec = next(WHISPER_DIR.glob("*-decoder*.onnx"))
    tok = next(WHISPER_DIR.glob("*-tokens.txt"))
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=str(enc), decoder=str(dec), tokens=str(tok),
                                                     language="pt", task="transcribe", num_threads=4)
    w = wave.open(str(wav))
    sr = w.getframerate()
    am = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    frases = []
    for a, b in segmentos_por_silencio(am, sr):
        st = rec.create_stream()
        st.accept_waveform(sr, am[int(max(0, a - 0.15) * sr):int(min(len(am), (b + 0.25) * sr))])
        rec.decode_stream(st)
        txt = st.result.text.strip()
        if txt:
            frases.append({"de": round(a, 2), "ate": round(b, 2), "texto": txt})
    return frases


def transcrever_mlx(wav):
    codigo = (
        "import json,sys,mlx_whisper;"
        "r=mlx_whisper.transcribe(sys.argv[1],path_or_hf_repo='mlx-community/whisper-large-v3-turbo',language='pt');"
        "print(json.dumps([{'de':round(s['start'],2),'ate':round(s['end'],2),'texto':s['text'].strip()} for s in r['segments']],ensure_ascii=False))"
    )
    r = sh([VENV_PY, "-c", codigo, wav])
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def transcrever(wav):
    if WHISPER_DIR.is_dir():
        return transcrever_sherpa(wav), "sherpa-onnx"
    if VENV_PY.exists():
        t = transcrever_mlx(wav)
        if t is not None:
            return t, "mlx_whisper"
    return None, None


def estudar(url, pasta, extra):
    pasta.mkdir(parents=True, exist_ok=True)
    meta, erro = baixar(url, pasta, extra)
    if erro:
        gravar_json(pasta / "meta.json", {"url": url, "erro": erro})
        return f"ERRO  {url}\n      {erro.splitlines()[-1] if erro else ''}"
    mp4 = pasta / "video.mp4"
    p = json.loads(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,codec_type",
                       "-of", "json", mp4]).stdout)
    dur = float(p["format"]["duration"])
    meta["duracao_s"] = round(dur, 2)
    meta["dim"] = [[s.get("width"), s.get("height")] for s in p["streams"] if s["codec_type"] == "video"]
    meta["trocas_de_plano"] = trocas_de_plano(mp4)
    meta["plano_medio_s"] = round(dur / (len(meta["trocas_de_plano"]) + 1), 2)
    wav = pasta / "audio.wav"
    sh(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-ac", "1", "-ar", "16000", wav])
    quadros(mp4, pasta, dur)
    frases, motor = transcrever(wav)
    meta["transcricao"] = motor or "não transcrito (sem CORTES_WHISPER_DIR nem venv do kit)"
    if frases:
        gravar_json(pasta / "transcricao.json", frases)
        with open(pasta / "transcricao.txt", "w", encoding="utf-8") as f:
            for t in frases:
                f.write(f"[{t['de']:6.2f}-{t['ate']:6.2f}] {t['texto']}\n")
    gravar_json(pasta / "meta.json", meta)
    return (f"OK    {url}\n      {dur:.1f} s, {len(meta['trocas_de_plano'])} trocas de plano "
            f"(plano médio {meta['plano_medio_s']} s), {len(frases or [])} frases, "
            f"likes={meta.get('like_count')} coment={meta.get('comment_count')} views={meta.get('view_count')}")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    saida = Path(argv[0]).expanduser()
    urls, extra, args = [], [], argv[1:]
    while args:
        a = args.pop(0)
        if a == "--lista":
            urls += [l.strip() for l in open(args.pop(0), encoding="utf-8") if l.strip() and not l.startswith("#")]
        elif a == "--cookies-from-browser":
            extra += [a, args.pop(0)]
        else:
            urls.append(a)
    linhas = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}", file=sys.stderr)
        linhas.append(estudar(url, saida / f"{i:02d}", extra))
    (saida / "resumo.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
