from tests.minivak import RegelTest, pagina

HUB = "Labo/RS485/overview.html"
OPDR = "Labo/RS485/Opdracht.html"


def lead(tekst):
    return f'<p class="lead">{tekst}</p>'


class GeenVerloop(RegelTest):
    regel = "no-verloop"

    def test_goed_zonder_verloop(self):
        self.assertSchoon({HUB: pagina('<h2 id="doel">Doelstellingen</h2>'
                                       '<!-- <h2 id="verloop">Verloop</h2> -->')})

    def test_fout_kop_en_stappen(self):
        self.assertMeldt({HUB: pagina('<h2>Verloop</h2><div class="steps-container"></div>'),
                          "Labo/B/overview.html": pagina('<h3 id="verloop">Zo ga je te werk</h3>')},
                         (HUB, "kop Verloop"), (HUB, "steps-container"),
                         ("Labo/B/overview.html", "kop Verloop"))

    def test_goed_geen_hub(self):
        # Een overview.html op de verkeerde diepte is geen hub.
        self.assertEqual(self.toestand({"Labo/overview.html": pagina()}),
                         ("n.v.t.", "geen overview.html"))


class GeenSessietelling(RegelTest):
    regel = "no-session-count"

    def test_goed_werkafspraak(self):
        self.assertSchoon({HUB: pagina("<p>Zorg dat je klaar bent voor het einde van een "
                                       "sessie. De planning staat bij Planning labo.</p>")})

    def test_fout_telling(self):
        self.assertMeldt({HUB: pagina("<p>Voor dit labo zijn <strong>twee sessies</strong> "
                                      "voorzien.</p>")}, (HUB, "sessietelling"))

    def test_fout_cijfer(self):
        self.assertMeldt({HUB: pagina("<p>Er is 1 sessie voorzien.</p>")}, (HUB, "sessietelling"))


class GeenGewicht(RegelTest):
    regel = "no-weight"

    def test_goed_zonder_gewicht(self):
        self.assertSchoon({HUB: pagina("<p>Een test gesloten boek.</p><!-- [60%] -->")})

    def test_fout_gewicht(self):
        self.assertMeldt({HUB: pagina("<h2>Evaluatie [ 60 % ]</h2>")}, (HUB, "gewicht"))


class DubbeleLead(RegelTest):
    regel = "duplicate-lead"

    def test_goed_zes_woorden(self):
        self.assertSchoon({HUB: pagina(lead("Je bouwt een bus met twee draden en drie nodes.")),
                           OPDR: pagina(lead("Vandaag: een bus met twee draden en vier leds "
                                             "aansturen."))})

    def test_fout_zeven_woorden(self):
        self.assertMeldt({HUB: pagina(lead("Je bouwt een bus met twee draden en drie nodes.")),
                          OPDR: pagina(lead("Vandaag: een bus met twee draden en drie leds "
                                            "aansturen."))},
                         (HUB, '"een bus met twee draden en drie" met ' + OPDR))

    def test_fout_opdracht_in_submap(self):
        zin = "Je configureert een HP ProCurve via de seriele console en een terminal."
        sub = "Labo/RS485/ProCurve/Opdracht.html"
        self.assertMeldt({HUB: pagina(lead(zin)), sub: pagina(lead(zin))}, (HUB, sub))

    def test_goed_tags_en_commentaar_tellen_niet(self):
        self.assertSchoon({HUB: pagina("<!--" + lead("a b c d e f g h") + "-->"
                                       + lead("Iets <em>anders</em> over de bus.")),
                           OPDR: pagina(lead("a b c d e f g h"))})
