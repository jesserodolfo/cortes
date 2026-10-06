import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skill" / "cortes" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import frases  # noqa: E402
import tabela  # noqa: E402
import exporta  # noqa: E402


def transcricao_falsa(n_frases=40, palavras_por_frase=8, dur_palavra=0.4, pausa=0.8):
    """Whisper-like: segments[].words[]; cada frase ~3,2 s + pausa."""
    t, segs = 0.0, []
    for f in range(n_frases):
        words = []
        for k in range(palavras_por_frase):
            w = f"p{f}_{k}" + ("." if k == palavras_por_frase - 1 else "")
            words.append({"word": " " + w, "start": round(t, 3), "end": round(t + dur_palavra, 3)})
            t += dur_palavra
        t += pausa
        segs.append({"words": words})
    return {"segments": segs}


class TestFrases(unittest.TestCase):
    def test_normaliza_formatos(self):
        self.assertEqual(frases.normalizar([{"w": "oi", "s": 0, "e": 1}]), [{"w": "oi", "s": 0.0, "e": 1.0}])
        self.assertEqual(len(frases.normalizar(transcricao_falsa(2, 3))), 6)
        self.assertEqual(len(frases.normalizar({"words": [{"text": "a", "start": 0, "end": .2}]})), 1)

    def test_quebra_por_pontuacao(self):
        fr = frases.quebrar(frases.normalizar(transcricao_falsa(5, 4)))
        self.assertEqual(len(fr), 5)
        self.assertTrue(fr[0]["texto"].endswith("."))

    def test_frase_longa_quebrada(self):
        pal = [{"w": f"x{i}", "s": i * 0.5, "e": i * 0.5 + 0.4} for i in range(100)]  # 50 s sem pontuação
        pal[60]["e"] = 30.0; pal[61]["s"] = 30.5  # noqa: E702
        fr = frases.quebrar(pal)
        self.assertTrue(all(f["e"] - f["s"] <= frases.FRASE_MAX for f in fr))
        self.assertEqual(sum(f["p1"] - f["p0"] + 1 for f in fr), 100)


class TestTabela(unittest.TestCase):
    def setUp(self):
        self.fr = frases.quebrar(frases.normalizar(transcricao_falsa()))  # 4 s por frase

    def m(self, de, ate, g=8, **kw):
        return {"de": de, "ate": ate, "gancho": g, "autonomia": 7, "desfecho": 6, "ritmo": 5,
                "titulo": f"t{de}", **kw}

    def test_nota_e_duracao(self):
        cortes, rej = tabela.montar(self.fr, [self.m(0, 9)])
        self.assertEqual(rej, [])
        self.assertEqual(cortes[0]["nota"], round((8 * .35 + 7 * .3 + 6 * .25 + 5 * .1) * 10))
        self.assertTrue(30 <= cortes[0]["duracao"] <= 90)
        # começa antes da 1ª palavra e não invade a frase seguinte
        self.assertLess(cortes[0]["inicio"], self.fr[0]["s"] + 1e-9)
        self.assertLessEqual(cortes[0]["fim"], self.fr[10]["s"])

    def test_rejeita_curto_longo_e_invalido(self):
        cortes, rej = tabela.montar(self.fr, [self.m(0, 2), self.m(0, 30), self.m(0, 9, g=11), {"de": 1}])
        self.assertEqual(cortes, [])
        self.assertEqual(len(rej), 4)

    def test_sobreposicao_fica_maior_nota(self):
        cortes, rej = tabela.montar(self.fr, [self.m(0, 9, g=3), self.m(2, 11, g=9), self.m(20, 29)])
        self.assertEqual([c["de"] for c in cortes], [2, 20])
        self.assertEqual(len(rej), 1)

    def test_maximo_dez(self):
        fr = frases.quebrar(frases.normalizar(transcricao_falsa(200)))
        notas = [self.m(i, i + 9) for i in range(0, 190, 10)]
        cortes, _ = tabela.montar(fr, notas)
        self.assertEqual(len(cortes), 10)
        self.assertEqual([c["n"] for c in cortes], list(range(1, 11)))


class TestExporta(unittest.TestCase):
    def test_texto_post(self):
        c = {"titulo": "T" * 120, "descricao": "d", "hashtags": ["#a"]}
        self.assertLessEqual(len(exporta.texto_post(c, "shorts")), 100)
        self.assertIn("#a", exporta.texto_post(c, "facebook"))

    def test_palavras_relativas(self):
        pal = [{"w": "a", "s": 9.0, "e": 9.5}, {"w": "b", "s": 10.2, "e": 10.6}, {"w": "c", "s": 50, "e": 51}]
        self.assertEqual(exporta.palavras_do_corte(pal, 10.0, 40.0), [{"w": "b", "s": 0.2, "e": 0.6}])

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg ausente")
    def test_ponta_a_ponta_sem_kit(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30:duration=50",
                            "-f", "lavfi", "-i", "sine=frequency=440:duration=50", "-shortest",
                            "-c:v", "libx264", "-c:a", "aac", str(p / "fonte.mp4")], check=True)
            (p / "transcricao.json").write_text(json.dumps(transcricao_falsa(12)))
            s = [sys.executable]
            subprocess.run(s + [str(SCRIPTS / "frases.py"), str(p / "transcricao.json"), str(p)], check=True)
            (p / "notas.json").write_text(json.dumps([{"de": 0, "ate": 9, "gancho": 8, "autonomia": 8,
                                                      "desfecho": 8, "ritmo": 8, "titulo": "Teste Ação"}]))
            subprocess.run(s + [str(SCRIPTS / "tabela.py"), str(p)], check=True, capture_output=True)
            subprocess.run(s + [str(SCRIPTS / "exporta.py"), str(p), "--aprovados", "1", "--sem-kit"], check=True)
            out = p / "saida" / "01-teste-acao"
            info = json.loads(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "stream=width,height:format=duration",
                 "-of", "json", str(out / "final.mp4")], capture_output=True, text=True, check=True).stdout)
            self.assertEqual((info["streams"][0]["width"], info["streams"][0]["height"]), (1080, 1920))
            self.assertTrue(30 <= float(info["format"]["duration"]) <= 90)
            for plat in ("shorts", "facebook", "instagram", "tiktok"):
                self.assertTrue((out / plat / "teste-acao.mp4").exists())
                self.assertTrue((out / plat / "legenda.txt").read_text().startswith("Teste Ação"))


if __name__ == "__main__":
    unittest.main()
