from tests.minivak import RegelTest, pagina

SRC = "Theorie/Syllabus/Theorie/"
OVZ = SRC + "Inleiding/Overzicht.html"
TJ = SRC + "Inleiding/TestJezelf.html"
PDF = "downloads/T-syllabus.pdf"
CSS = "Theorie/Syllabus/syllabus.css"


def manifest(*topics, sleutel="syllabus"):
    regels = ",\n".join(f"                    {{ id: '{i}', name: '{n}', href: '{h}' }}"
                        for i, n, h in topics)
    return ("window.LAB_REFERENCE = {\n"
            f"    {sleutel}: {{\n        name: 'Syllabus',\n        categories: [\n"
            "            {\n                name: 'Inleiding',\n                topics: [\n"
            f"{regels}\n                ]\n            }}\n        ]\n    }}\n}};\n")


def vragenlijst(*items, start=None):
    attr = f' start="{start}"' if start else ""
    return f'<ol class="vragen"{attr}>\n' + "\n".join(items) + "\n</ol>"


def mk(stam, juist=1, n=3):
    keuzes = "".join(f'<li class="juist">k{i}</li>' if i == juist else f"<li>k{i}</li>"
                     for i in range(n))
    return f"<li>{stam}<ul>{keuzes}</ul></li>"


def open_(stam, antwoord="Het antwoord."):
    oplossing = f'<div class="oplossing">{antwoord}</div>' if antwoord is not None else ""
    return f"<li>{stam}{oplossing}</li>"


class SyllabusManifest(RegelTest):
    regel = "syllabus-manifest"

    def goed(self):
        return {"reference.js": manifest(("ovz", "Overzicht", "Inleiding/Overzicht.html"),
                                         ("tj", "Test jezelf", "Inleiding/TestJezelf.html"),
                                         ("pdf", "Datasheet", "../../../datasheets/a.pdf")),
                OVZ: pagina(), TJ: pagina(), "datasheets/a.pdf": b"%PDF"}

    def test_goed_manifest_dekt_elke_pagina(self):
        self.assertSchoon(self.goed())

    def test_fout_pagina_niet_in_manifest(self):
        b = self.goed()
        b[SRC + "Hoofdstuk2/Overzicht.html"] = pagina()
        self.assertMeldt(b, (SRC + "Hoofdstuk2/Overzicht.html", "staat niet in reference.js"))

    def test_fout_href_id_en_velden(self):
        b = self.goed()
        b["reference.js"] = manifest(("ovz", "Overzicht", "Inleiding/Overzicht.html"),
                                     ("ovz", "Test jezelf", "Inleiding/testjezelf.html"),
                                     ("weg", "", "Inleiding/Weg.html"),
                                     ("abs", "Abs", "https://x.be/a.html"))
        self.assertMeldt(b, ("reference.js", "id 'ovz' komt twee keer voor"),
                         ("reference.js", "hoofdletters kloppen niet"),
                         ("reference.js", "veld 'name' ontbreekt"),
                         ("reference.js", "weg: href bestaat niet"),
                         ("reference.js", "abs: absolute URL"),
                         ("reference.js", "abs: href bestaat niet"),
                         (TJ, "staat niet in reference.js"))

    def test_fout_leeg_en_kapot(self):
        self.assertMeldt({"reference.js": "window.LAB_REFERENCE = {};\n", OVZ: pagina()},
                         ("reference.js", "is leeg"), ernst="waarschuwing")
        self.assertMeldt({"reference.js": "window.LAB_REFERENCE = {\n  syllabus: {}\n};\n"},
                         ("reference.js", "geen enkele module"))

    def test_fout_manifest_ontbreekt_en_labomodule_zonder_theorie(self):
        self.assertMeldt({OVZ: pagina()}, ("reference.js", "ontbreekt"))
        self.assertMeldt({"reference.js": manifest(("a", "A", "A.html"), sleutel="rs485"),
                          "Labo/RS485/overview.html": pagina()},
                         ("reference.js", "module 'rs485' heeft geen Theorie-map"))


class SyllabusVerouderd(RegelTest):
    regel = "syllabus-stale"
    config = {"syllabus": {"pdf": "T-syllabus.pdf"}}

    def test_goed_pdf_nieuwer(self):
        self.assertSchoon({OVZ: pagina(), CSS: "", PDF: b"%PDF"}, mtimes={PDF: 10})

    def test_fout_pagina_of_css_nieuwer(self):
        self.assertMeldt({OVZ: pagina(), CSS: "", PDF: b"%PDF"},
                         (PDF, "ouder dan " + OVZ), mtimes={OVZ: 10})
        self.assertMeldt({OVZ: pagina(), CSS: "", PDF: b"%PDF"},
                         (PDF, "ouder dan " + CSS), mtimes={CSS: 10})

    def test_fout_pdf_ontbreekt_of_niet_ingesteld(self):
        self.assertMeldt({OVZ: pagina()}, (PDF, "bestaat niet"))
        self.assertMeldt({OVZ: pagina()}, ("oriontools.json", "syllabus.pdf is niet ingesteld"),
                         config={"syllabus": {"pdf": ""}})

    def test_goed_niet_met_ci(self):
        self.assertEqual(self.toestand({OVZ: pagina()}, ci=True),
                         ("n.v.t.", "alleen lokaal, niet met --ci"))


class VragenBeantwoord(RegelTest):
    regel = "vragen-answered"

    def test_goed_syllabus_en_labo(self):
        lijst = vragenlijst(mk("Welke?"), open_("Waarom?"))
        self.assertSchoon({TJ: pagina(lijst), "Labo/A/Theorie/TestJezelf.html": pagina(lijst)})

    def test_fout_nul_of_twee_juist(self):
        lijst = vragenlijst(mk("Nul?", juist=-1), mk("Een?"),
                            '<li>Twee?<ul><li class="juist">a</li><li class="juist">b</li></ul></li>')
        self.assertMeldt({TJ: pagina(lijst)}, (TJ, "vraag 1 heeft 0 mogelijkheden"),
                         (TJ, "vraag 3 heeft 2 mogelijkheden"))

    def test_fout_open_zonder_oplossing_in_labo(self):
        p = "Labo/A/Theorie/TestJezelf.html"
        m = self.assertMeldt({p: pagina(vragenlijst(open_("Waarom?", None), open_("Hoe?", " ")))},
                             (p, "vraag 1 is een open vraag"), (p, "vraag 2 is een open vraag"))
        self.assertIn("main.js", m[0][2])

    def test_fout_nummer_telt_door_over_start(self):
        tekst = pagina(vragenlijst(mk("a"), mk("b")) + "<p>Tussenzin.</p>"
                       + vragenlijst(mk("c", juist=-1), start=3))
        self.assertMeldt({TJ: tekst}, (TJ, "vraag 3 heeft 0"))

    def test_goed_verslagblok_telt_niet(self):
        # In een verslagcommentaar is een vraag er een voor de docx, zonder antwoord.
        self.assertSchoon({TJ: pagina(vragenlijst(mk("a"))),
                           "Labo/A/Opdracht.html": pagina(
                               "<!-- verslag\n" + vragenlijst(open_("Meet.", None)) + "\n-->")})


class VragenNummering(RegelTest):
    regel = "vragen-numbering"

    def test_goed_start_loopt_door(self):
        self.assertSchoon({TJ: pagina(vragenlijst(mk("a"), mk("b")) + "<p>Tussenzin.</p>"
                                      + vragenlijst(mk("c"), start=3))})

    def test_fout_start_ontbreekt(self):
        self.assertMeldt({TJ: pagina(vragenlijst(mk("a"), mk("b")) + vragenlijst(mk("c")))},
                         (TJ, 'mist start="3"'))

    def test_fout_start_springt_in_labo(self):
        p = "Labo/A/Theorie/TestJezelf.html"
        self.assertMeldt({p: pagina(vragenlijst(mk("a")) + vragenlijst(mk("b"), start=5))},
                         (p, 'begint op start="5"'))


class VragenKlasse(RegelTest):
    regel = "vragen-class"

    def test_goed_met_klasse_of_zonder_invulruimte(self):
        self.assertSchoon({TJ: pagina(vragenlijst(open_('Leg uit.<table class="invulruimte">'
                                                        "</table>"))),
                           OVZ: pagina("<ol><li>Een stap.</li></ol>")})

    def test_fout_invulruimte_zonder_klasse(self):
        self.assertMeldt({OVZ: pagina('<ol><li>Leg uit.<table class="invulruimte"></table></li>'
                                      '<li>Nog.<table class="invulruimte"></table></li></ol>')},
                         (OVZ, 'zonder class="vragen"'))


class ImporterGok(RegelTest):
    regel = "importer-guess"

    def test_goed_zonder_gok(self):
        self.assertSchoon({OVZ: pagina("<table><tr><th>a</th></tr></table>")})

    def test_fout_gok_met_regelnummer(self):
        tekst = pagina('<table data-geraden="kopregel uit tblLook">\n</table>')
        b = self.bevindingen({OVZ: tekst})
        self.assertEqual([(b_.pad, b_.regelnr) for b_ in b],
                         [(OVZ, tekst[:tekst.index("data-geraden")].count("\n") + 1)])
        self.assertIn("kopregel uit tblLook", b[0].boodschap)


class WeesAfbeelding(RegelTest):
    regel = "orphan-image"
    config = {"syllabus": {"logo": "img/syllabus-logo.png"}}

    def test_goed_gebruikt_in_html_css_of_logo(self):
        self.assertSchoon({"img/syllabus-01.png": b"png", "img/syllabus-02.png": b"png",
                           "img/syllabus-logo.png": b"png", "img/los.png": b"png",
                           OVZ: pagina('<img src="../../../../img/syllabus-01.png" alt="">'),
                           CSS: ".kader { background: url(../../img/syllabus-02.png); }"})

    def test_fout_niet_gebruikt(self):
        self.assertMeldt({"img/syllabus-01.png": b"png", OVZ: pagina(),
                          "_incoming/Oud.html": '<img src="../img/syllabus-01.png">'},
                         ("img/syllabus-01.png", "geen enkele pagina gebruikt hem"))
