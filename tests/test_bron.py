from tests.minivak import RegelTest, pagina

HUB = "Labo/A/overview.html"
THEORIE = "Labo/A/Theorie/X.html"


def hub(*bronnen):
    items = "\n".join(f'<li data-bron="{b}">Doel.</li>' for b in bronnen)
    return pagina(f'<h2 id="doelstellingen">Doelstellingen</h2>\n<ol>\n{items}\n</ol>')


class DataBron(RegelTest):
    regel = "data-bron"

    def test_goed_pad_vanaf_de_root(self):
        self.assertSchoon({HUB: hub(THEORIE, f"{THEORIE} Labo/A/Theorie/Y.html"),
                           THEORIE: pagina(), "Labo/A/Theorie/Y.html": pagina()})

    def test_goed_commentaar_telt_niet(self):
        self.assertSchoon({HUB: hub(THEORIE) + '<!-- <li data-bron="weg.html"> -->',
                           THEORIE: pagina()})

    def test_fout_bestaat_niet_of_verkeerde_hoofdletters(self):
        # Op een hoofdletterongevoelige schijf is de tweede een fout in de
        # hoofdletters, elders een pad dat niet bestaat; allebei een fout.
        self.assertMeldt({HUB: hub("Labo/A/Theorie/Z.html", "Labo/A/theorie/X.html"),
                          THEORIE: pagina()},
                         (HUB, "Z.html bestaat niet"), (HUB, "Labo/A/theorie/X.html"))

    def test_fout_geen_pad_vanaf_de_root(self):
        self.assertMeldt({HUB: hub("../A/Theorie/X.html", "Labo/A/./Theorie/X.html", ""),
                          THEORIE: pagina()},
                         (HUB, "../A/Theorie/X.html is geen pad vanaf de root"),
                         (HUB, "Labo/A/./Theorie/X.html is geen pad vanaf de root"),
                         (HUB, "lege data-bron"))

    def test_niet_van_toepassing_zonder_data_bron(self):
        self.assertEqual(self.toestand({HUB: pagina()})[0], "n.v.t.")
