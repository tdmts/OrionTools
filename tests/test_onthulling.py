from tests.minivak import RegelTest, pagina

P = "Labo0/Exercises/Knipperlicht.html"
OPLOSSING = '<div class="solution-container"><p>De code.</p></div>'


class SolutionPlaatsing(RegelTest):
    regel = "solution-placement"

    def test_goed_onder_oplossing(self):
        self.assertSchoon({P: pagina('<h2 id="opdracht">Opdracht</h2>\n<p>Bouw.</p>\n'
                                     f'<h2 id="oplossing-code">Code</h2>\n{OPLOSSING}')})

    def test_fout_onder_andere_h2_en_zonder_h2(self):
        tekst = pagina(f'{OPLOSSING}\n<h2 id="hint">Hint</h2>\n{OPLOSSING}\n'
                       f'<h2>Zonder id</h2>\n{OPLOSSING}')
        m = self.assertMeldt({P: tekst}, (P, "geen enkele <h2>"), (P, '<h2 id="hint">'),
                             (P, '<h2 id="(no id)">'))
        self.assertTrue(all("accordion-item" in x[2] for x in m))


class SpoilerRetired(RegelTest):
    regel = "spoiler-retired"

    def test_goed_accordion(self):
        self.assertSchoon({P: pagina('<div class="accordion-item"><div class="title">Hint</div>'
                                     "<p>Denk aan de weerstand.</p></div>")})

    def test_fout_spoiler(self):
        self.assertMeldt({P: pagina('<div class="spoiler-container"><p>b</p></div>')},
                         (P, "met pensioen"))


class RevealScriptRetired(RegelTest):
    regel = "reveal-script-retired"

    def test_goed_alleen_orioncss(self):
        self.assertSchoon({P: pagina()})

    def test_fout_bestand_en_include(self):
        self.assertMeldt({"oplossingen.js": "", "solution-reveal.js": "",
                          P: pagina('<script src="../../oplossingen.js"></script>'),
                          "Labo0/B.html": pagina('<script defer src="solution-reveal.js"></script>')},
                         ("oplossingen.js", "verwijder het bestand"),
                         ("solution-reveal.js", "verwijder het bestand"),
                         (P, "laadt oplossingen.js"), ("Labo0/B.html", "laadt solution-reveal.js"))
