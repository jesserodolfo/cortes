"""Testes dos adaptadores (transcreve, recorte, legenda) sem mlx, Swift ou o kit real."""
import json
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "skill" / "cortes" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import frases  # noqa: E402
import legenda  # noqa: E402
import recorte  # noqa: E402
import transcreve  # noqa: E402

TEM_FFMPEG = bool(shutil.which("ffmpeg"))


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


def cor_em(video, t, x=None, y=None):
    """RGB médio do quadro em t (ou do pixel x,y)."""
    vf = "scale=1:1" if x is None else f"crop=2:2:{x}:{y}"
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(video), "-frames:v", "1",
                          "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return tuple(out[:3])


class TestTranscreve(unittest.TestCase):
    def test_sem_initial_prompt_e_formato(self):
        falso = types.SimpleNamespace(transcribe=mock.Mock(return_value={
            "language": "pt",
            "segments": [{"start": 0, "end": 1, "text": " Olá mundo.",
                          "words": [{"word": " Olá", "start": 0.0, "end": 0.4, "probability": .9},
                                    {"word": " mundo.", "start": 0.5, "end": 1.0, "probability": .9}]}]}))
        with mock.patch.dict(sys.modules, {"mlx_whisper": falso}):
            r = transcreve.transcrever("x.mp4")
        kw = falso.transcribe.call_args.kwargs
        self.assertNotIn("initial_prompt", kw)
        self.assertTrue(kw["word_timestamps"])
        self.assertEqual(kw["path_or_hf_repo"], "mlx-community/whisper-large-v3-turbo")
        self.assertEqual([p["w"] for p in frases.normalizar(r)], ["Olá", "mundo."])


class TestRecorte(unittest.TestCase):
    def a(self, *rostos):
        return {"rostos": [{"x": x, "y": .5, "w": w, "h": w} for x, w in rostos]}

    def test_escolhe_maior_mas_fica_no_atual(self):
        am = [self.a((0.3, 0.10)), self.a((0.3, 0.09), (0.7, 0.12)), self.a((0.3, 0.05), (0.7, 0.12)), self.a()]
        self.assertEqual(recorte.escolher(am), [0.3, 0.3, 0.7, None])

    def test_preencher(self):
        self.assertEqual(recorte.preencher([None, 0.4, None, 0.6]), [0.4, 0.4, 0.4, 0.6])
        self.assertEqual(recorte.preencher([None, None]), [0.5, 0.5])

    def test_suaviza_sem_atravessar_troca_de_camera(self):
        xs = [0.30, 0.32, 0.29, 0.31, 0.30, 0.80, 0.81, 0.79, 0.80]
        s = recorte.suavizar(xs, 0.5)
        self.assertTrue(all(abs(v - 0.30) < 0.03 for v in s[:5]))
        self.assertTrue(all(abs(v - 0.80) < 0.03 for v in s[5:]))
        self.assertEqual(len(set(s[:5])), 1, "zona morta: câmera parada no plano 1")

    def test_x_por_quadro_dentro_da_imagem(self):
        px = recorte.x_por_quadro([0.0, 1.0], 0.5, 1.0, 1280, 404)
        self.assertEqual(px[0], 0)
        self.assertEqual(px[-1], 1280 - 404)
        self.assertTrue(all(p % 2 == 0 and 0 <= p <= 876 for p in px))

    @unittest.skipUnless(TEM_FFMPEG, "ffmpeg ausente")
    def test_ffmpeg_segue_x(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            ff("-f", "lavfi", "-i", "color=red:s=640x720:d=6:r=30", "-f", "lavfi", "-i",
               "color=blue:s=640x720:d=6:r=30", "-filter_complex", "hstack", "-pix_fmt", "yuv420p", d / "in.mp4")
            am = [{"t": i / 2, **self.a((0.25 if i < 6 else 0.75, 0.1))} for i in range(12)]
            (d / "r.json").write_text(json.dumps({"largura": 1280, "altura": 720, "passo": 0.5, "amostras": am}))
            recorte.recortar(d / "in.mp4", d / "out.mp4", d / "r.json")
            self.assertGreater(cor_em(d / "out.mp4", 1)[0], 200)   # esquerda: vermelho
            self.assertGreater(cor_em(d / "out.mp4", 5)[2], 200)   # direita: azul
            self.assertEqual(recorte.sondar(d / "out.mp4")[:2], (1080, 1920))


CAPS_FALSO = '''
import json, pathlib, subprocess
p = json.load(open("projeto.json"))
pathlib.Path("caps").mkdir()
for i, _ in enumerate(p["legendas"]):
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=yellow:s=800x200",
                    "-frames:v", "1", f"caps/{i:03d}.png"], check=True)
'''


class TestLegenda(unittest.TestCase):
    def test_agrupar(self):
        pal = [{"w": w, "s": i * .3, "e": i * .3 + .25} for i, w in enumerate(
            "isso é muito importante, porque ninguém fala".split())]
        pal[-1]["s"] += 1.0; pal[-1]["e"] += 1.0  # noqa: E702
        b = legenda.agrupar(pal)
        self.assertEqual([x["texto"] for x in b], ["isso é muito", "importante,", "porque ninguém", "fala"])
        self.assertEqual(b[0]["fim"], b[1]["inicio"], "bloco segura até o próximo")
        self.assertLess(b[2]["fim"], b[3]["inicio"], "pausa longa: tela limpa")

    @unittest.skipUnless(TEM_FFMPEG, "ffmpeg ausente")
    def test_caps_e_overlay(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "caps3.py").write_text(CAPS_FALSO)
            ff("-f", "lavfi", "-i", "color=black:s=1080x1920:d=4:r=30", "-pix_fmt", "yuv420p", d / "v.mp4")
            pal = [{"w": "oi", "s": 0.5, "e": 1.0}, {"w": "gente.", "s": 1.1, "e": 1.5},
                   {"w": "tchau.", "s": 3.0, "e": 3.4}]
            (d / "p.json").write_text(json.dumps(pal))
            with mock.patch.object(legenda, "KIT", d), mock.patch.object(legenda, "VENV_PY", Path(sys.executable)):
                legenda.legendar(d / "v.mp4", d / "p.json", d / "out.mp4")
            self.assertGreater(cor_em(d / "out.mp4", 1.2, 540, 1560)[0], 200)  # caixa em cy=1560
            self.assertLess(cor_em(d / "out.mp4", 2.5, 540, 1560)[0], 30)      # pausa: sem legenda
            self.assertLess(cor_em(d / "out.mp4", 1.2, 540, 1300)[0], 30)      # caixa não vaza pra cima

    def test_numero_de_pngs_errado_para(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "caps3.py").write_text("import pathlib; pathlib.Path('caps').mkdir()")
            with mock.patch.object(legenda, "KIT", d), mock.patch.object(legenda, "VENV_PY", Path(sys.executable)):
                with self.assertRaises(SystemExit):
                    legenda.gerar_pngs([{"texto": "a", "inicio": 0, "fim": 1}], d)


if __name__ == "__main__":
    unittest.main()
