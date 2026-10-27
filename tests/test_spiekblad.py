from tests.minivak import RegelTest

PAGINA = "Labo/Lx/Theorie/Spiekblad.html"
PDF = "downloads/Labo-Lx-spiekblad.pdf"


def pagina(link=True):
    knop = ('<div class="download-container"><a href="../../../downloads/Labo-Lx-spiekblad.pdf" '
            'target="_blank" rel="noopener">Spiekblad downloaden</a><ul><li>x</li></ul></div>'
            if link else "")
    return ('<!DOCTYPE html>\n<html lang="nl">\n<head><title>Spiekblad</title></head>\n'
            f'<body><div class="container"><h1>Spiekblad</h1>{knop}</div></body>\n</html>\n')


class SpiekbladVerouderd(RegelTest):
    regel = "spiekblad-stale"

    def setUp(self):
        self.huisstijl()

    def test_goed_pdf_nieuwer_dan_alles(self):
        self.assertSchoon({PAGINA: pagina(), PDF: b"%PDF"}, mtimes={PDF: 10})

    def test_goed_spiekblad_zonder_link(self):
        # Niet elk labo wil een afdruk; zonder link doet de pagina niet mee.
        self.assertSchoon({PAGINA: pagina(link=False)}, mtimes={PAGINA: 10})

    def test_fout_pdf_ontbreekt(self):
        self.assertMeldt({PAGINA: pagina()},
                         (PAGINA, "export-spiekblad Labo/Lx"))

    def test_fout_pagina_nieuwer(self):
        self.assertMeldt({PAGINA: pagina(), PDF: b"%PDF"},
                         (PDF, "ouder dan Labo/Lx/Theorie/Spiekblad.html"), mtimes={PAGINA: 10})

    def test_fout_stijlblad_nieuwer(self):
        self.huisstijl({"spiekblad.css": 20})
        self.assertMeldt({PAGINA: pagina(), PDF: b"%PDF"},
                         (PDF, "/spiekblad.css; draai"), mtimes={PDF: 10})

    def test_goed_niet_met_ci_of_zonder_spiekblad(self):
        self.assertEqual(self.toestand({PAGINA: pagina(), PDF: b"%PDF"}, ci=True)[0], "n.v.t.")
        self.assertEqual(self.toestand({"Labo/Lx/overview.html": pagina(link=False)}),
                         ("n.v.t.", "geen Spiekblad.html"))
