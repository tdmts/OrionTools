from tests.minivak import RegelTest, menu, pagina

P = "Labo/A/Theorie/Pagina.html"
W = "waarschuwing"


def woordtest(regel, fout, goed, fragment):
    """Een testklasse voor een regel op een woordenlijst: een woord uit de lijst, en proza zonder."""

    class Woordregel(RegelTest):
        def test_goed_proza(self):
            self.assertSchoon({P: pagina(f"<p>{goed}</p>")})

        def test_fout_woord(self):
            self.assertMeldt({P: pagina(f"<p>{fout}</p>")}, (P, fragment), ernst=W)

        def test_goed_audit_skip(self):
            skip = regel.removeprefix("audit-")
            self.assertSchoon({P: pagina(f"<!-- audit-skip: {skip} --><p>{fout}</p>")})

    Woordregel.regel = regel
    Woordregel.__name__ = Woordregel.__qualname__ = "Woordregel_" + regel.replace("-", "_")
    return Woordregel


Verkleinwoord = woordtest("audit-verkleinwoord", "Druk op het knopje.",
                          "Zet de haakjes netjes.", "'knopje'")
NoordNederlands = woordtest("audit-noord-nederlands", "Dat kun je meten.",
                            "Dat kan je best meten.", "'kun je'")
Vulwoord = woordtest("audit-vulwoord", "Dat werkt uiteraard.", "Een natuurlijke keuze.",
                     "'uiteraard'")


class AuditSkip(RegelTest):
    regel = "audit-skip"

    def test_goed_geldige_skip_is_afwijking(self):
        self.assertMeldt({P: pagina("<!-- audit-skip: lead, figure -->")},
                         (P, "audit-skip: figure"), (P, "audit-skip: lead"), ernst="afwijking")

    def test_goed_zonder_skip(self):
        self.assertSchoon({P: pagina()})

    def test_fout_onbekende_naam(self):
        self.assertMeldt({P: pagina("<!-- audit-skip: figuur -->")},
                         (P, "onbekende audit-skip 'figuur'"), ernst=W)


class AuditCodeKlasse(RegelTest):
    regel = "audit-code-class"

    def test_goed_volledig_en_plaintext(self):
        self.assertSchoon({P: pagina(
            '<pre class="code-wrapper linenumbers show-language language-cpp"></pre>'
            '<pre class="code-wrapper linenumbers language-plaintext"></pre>')})

    def test_fout_ontbrekende_klassen(self):
        self.assertMeldt({P: pagina(
            '<pre class="code-wrapper"></pre>'
            '<pre class="code-wrapper show-language language-cpp"></pre>'
            '<pre class="code-wrapper linenumbers language-cpp"></pre>'
            '<pre class="code-wrapper linenumbers show-language language-plaintext"></pre>')},
            (P, "heeft geen language-*"), (P, "zonder linenumbers"), (P, "zonder show-language"),
            (P, "plaintext-blok met show-language"), ernst=W)

    def test_fout_taal_buiten_de_lijst(self):
        self.assertMeldt({P: pagina(
            '<pre class="code-wrapper linenumbers show-language language-python"></pre>')},
            (P, "huisstijl: language-cpp"), ernst=W,
            config={"check": {"audit": {"code_languages": ["cpp"]}}})


class AuditLeadOpener(RegelTest):
    regel = "audit-lead-opener"

    def test_goed_taak(self):
        self.assertSchoon({P: pagina('<p class="lead">In deze oefening bouw je een looplicht.</p>')})

    def test_fout_formule_en_extra(self):
        self.assertMeldt({P: pagina('<p class="lead">Een <code>x</code>. Hier lees je hoe.</p>'),
                          "Labo/A/B.html": pagina('<p class="lead">Kortom: de bus.</p>')},
                         (P, "vaste formule"), ("Labo/A/B.html", "vaste formule"), ernst=W,
                         config={"check": {"audit": {"stock_lead_extra": ["Kortom:"]}}})


class AuditLedSpelling(RegelTest):
    regel = "audit-led-spelling"

    def test_goed_code_en_kleine_letters(self):
        self.assertSchoon({P: pagina("<p>De led brandt.</p>\n"
                                     '<pre class="code-wrapper"><code>int pinLED = 13;\n'
                                     'Serial.println("LED:1");</code></pre>')})

    def test_fout_proza_en_menu_een_per_bestand(self):
        self.assertMeldt({P: pagina("<p>De LED brandt.</p>\n<li>Twee LEDs.</li>"),
                          "orion.json": menu("page:" + P).replace("Topic 0", "RGB LED")},
                         (P, "'LED' in de proza"), ("orion.json", "'LED' in de proza"), ernst=W)


class AuditIdentifierTaal(RegelTest):
    regel = "audit-identifier-taal"
    config = {"check": {"audit": {"identifier_words": ["pinLed", "buttonPin"]}}}

    def test_goed_proza_en_nederlands(self):
        self.assertSchoon({P: pagina("<p>Vroeger heette het pinLed.</p>\n"
                                     '<pre class="code-wrapper"><code>const int ledPin = 13;\n'
                                     "x.pinLed = 1;</code></pre>")})

    def test_fout_engelse_identifier(self):
        m = self.bevindingen({P: pagina('<pre class="code-wrapper"><code>int a;\n'
                                        "const int buttonPin = 2;\npinLed = 1;</code></pre>")})
        self.assertEqual(len(m), 1, "een melding per bestand")
        self.assertIn("buttonPin = 2", m[0].boodschap)

    def test_goed_niet_zonder_woorden(self):
        self.assertEqual(self.toestand({P: pagina()}, {"check": {"audit": {"identifier_words": []}}}),
                         ("n.v.t.", "geen check.audit.identifier_words"))


class AuditUVorm(RegelTest):
    regel = "audit-u-vorm"

    def test_goed_je_vorm(self):
        self.assertSchoon({P: pagina("<p>Je kan de u-bocht meten.</p>")})

    def test_fout_u_vorm_per_regel(self):
        self.assertMeldt({P: pagina("<p>U kunt meten.</p>\n<p>Neem uw multimeter.</p>")},
                         (P, "U kunt"), (P, "uw multimeter"), ernst=W)


class AuditLead(RegelTest):
    regel = "audit-lead"
    config = {"check": {"audit": {"lead_patterns": ["Labo/*/overview.html"]}}}

    def test_goed_lead_of_buiten_patroon(self):
        self.assertSchoon({"Labo/A/overview.html": pagina('<p class="lead">Over de bus.</p>'),
                           P: pagina()})

    def test_fout_geen_lead(self):
        self.assertMeldt({"Labo/A/overview.html": pagina()},
                         ("Labo/A/overview.html", 'geen <p class="lead">'), ernst=W)

    def test_goed_ongetrackt_klad_telt_niet(self):
        self.assertSchoon({"Labo/A/overview.html": pagina('<p class="lead">x</p>'),
                           "Labo/B/overview.html": pagina()}, git=True,
                          ongetrackt=["Labo/B/overview.html"])


class AuditFiguur(RegelTest):
    regel = "audit-figure"

    def test_goed_figure_en_tabelcel(self):
        self.assertSchoon({P: pagina('<figure><img src="a.png" alt=""></figure>\n'
                                     '<table><tr><td><img src="b.png" alt=""></td></tr></table>')})

    def test_fout_kale_afbeelding(self):
        self.assertMeldt({P: pagina('<figure><img src="a.png" alt=""></figure>\n'
                                    '<p><img src="b.png" alt=""></p>')},
                         (P, "2 <img> buiten een tabel maar 1 <figure>"), ernst=W)


OEF = "Labo0/Exercises/Blink.html"


class AuditIndienen(RegelTest):
    regel = "audit-indienen"
    config = {"check": {"audit": {"exercise_patterns": ["Labo*/Exercises/*.html"]}}}

    def test_goed_vaste_tekst(self):
        self.assertSchoon({OEF: pagina('<h2 id="indienen">Indienen</h2>\n'
                                       "<p>Sla je oefening op.</p>"), P: pagina()})

    def test_fout_geen_sectie_of_andere_tekst(self):
        b = "Labo0/Exercises/B.html"
        self.assertMeldt({OEF: pagina(), b: pagina('<h2 id="indienen">Indienen</h2>'
                                                   "<p>Dien in via Brightspace.</p>")},
                         (OEF, 'geen <h2 id="indienen">'), (b, "niet de vaste"), ernst=W)


class AuditOplossing(RegelTest):
    regel = "audit-oplossing"
    config = AuditIndienen.config

    def test_goed_met_oplossing(self):
        self.assertSchoon({OEF: pagina('<h2 id="oplossing">Oplossing</h2>')})

    def test_fout_zonder_oplossing(self):
        self.assertMeldt({OEF: pagina('<h2 id="oplossing-code">Code</h2>')},
                         (OEF, 'geen <h2 id="oplossing">'), ernst=W)

    def test_goed_niet_zonder_patronen(self):
        self.assertEqual(self.toestand({OEF: pagina()},
                                       {"check": {"audit": {"exercise_patterns": []}}}),
                         ("n.v.t.", "geen check.audit.exercise_patterns"))
