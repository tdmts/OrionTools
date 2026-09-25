from tests.minivak import RegelTest

DECK = "Hoorcollege/Sessie1.html"
PDF = "downloads/T-handout-sessie-1.pdf"


def deck(body=""):
    return ('<!DOCTYPE html>\n<html lang="nl">\n<head>\n'
            '<link rel="stylesheet" href="https://tdmts.github.io/OrionCSS/hoorcollege.css">\n'
            '</head>\n<body>\n'
            f'<section class="slide"><h2>Slide</h2>{body}</section>\n</body>\n</html>\n')


def bestanden(**extra):
    return {DECK: deck('<img src="../img/fig.svg" alt="">'), "img/fig.svg": "<svg/>",
            PDF: b"%PDF", **extra}


class HandoutVerouderd(RegelTest):
    regel = "handout-stale"
    config = {"handout": {"prefix": "T-handout-"}}

    def setUp(self):
        self.huisstijl()

    def test_goed_pdf_nieuwer_dan_alles(self):
        self.assertSchoon(bestanden(), mtimes={PDF: 10})

    def test_goed_deck_zonder_handout(self):
        # Een nieuw deck heeft nog niets om mee te vergelijken.
        self.assertSchoon(bestanden(**{"Hoorcollege/Sessie2.html": deck()}),
                          mtimes={PDF: 10, "Hoorcollege/Sessie2.html": 20})

    def test_fout_deck_nieuwer(self):
        self.assertMeldt(bestanden(), (PDF, "ouder dan Hoorcollege/Sessie1.html"),
                         mtimes={DECK: 10})

    def test_fout_stijlblad_nieuwer(self):
        # Ze staan buiten het vak, in OrionTools en in OrionCSS.
        for naam in ("handout.css", "hoorcollege.css"):
            with self.subTest(naam):
                self.huisstijl({naam: 20})
                self.assertMeldt(bestanden(), (PDF, f"/{naam}; draai"), mtimes={PDF: 10})

    def test_goed_stijlblad_ontbreekt(self):
        # Zonder checkout van OrionCSS naast OrionTools is er niets om mee te
        # vergelijken; de export zegt dan zelf dat het bestand ontbreekt.
        self.huisstijl()["hoorcollege.css"].unlink()
        self.assertSchoon(bestanden(), mtimes={PDF: 10})

    def test_fout_figuur_nieuwer_een_keer(self):
        # Een melding per handout, ook als meer bronnen nieuwer zijn.
        self.assertMeldt(bestanden(), (PDF, "ouder dan"),
                         mtimes={"img/fig.svg": 10, DECK: 10})
        self.assertMeldt(bestanden(), (PDF, "ouder dan img/fig.svg"), mtimes={"img/fig.svg": 10})

    def test_goed_figuur_van_een_ander_deck(self):
        extra = {"Hoorcollege/Sessie2.html": deck('<img src="../img/ander.svg" alt="">'),
                 "img/ander.svg": "<svg/>"}
        self.assertSchoon(bestanden(**extra),
                          mtimes={PDF: 10, "img/ander.svg": 20, "Hoorcollege/Sessie2.html": 5})

    def test_goed_niet_met_ci_of_zonder_prefix(self):
        self.assertEqual(self.toestand(bestanden(), ci=True)[0], "n.v.t.")
        self.assertEqual(self.toestand(bestanden(), {"handout": {"prefix": ""}}),
                         ("n.v.t.", "handout.prefix is niet ingesteld"))
