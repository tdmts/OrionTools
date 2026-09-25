import json

from tests.minivak import RegelTest, menu, pagina

INL = "Labo/RS485/overview.html"
OPDR = "Labo/RS485/Opdracht.html"
PDF = "datasheets/max485.pdf"


class OrionDoelen(RegelTest):
    regel = "orion-targets"

    def test_goed_page_file_dropbox_todo(self):
        doc = json.loads(menu("page:" + INL, "file:" + PDF, "file:img/TODO-schema.png"))
        doc["modules"][0]["items"].append({"id": "verslag", "title": "Verslag", "dropbox": "V"})
        self.assertSchoon({"orion.json": json.dumps(doc), INL: pagina(), PDF: b"%PDF"}, git=True)

    def test_fout_bestaat_niet_en_geen_html(self):
        self.assertMeldt({"orion.json": menu("page:Labo/Weg.html", "page:" + PDF), PDF: b"%PDF"},
                         ("orion.json", "page bestaat niet: Labo/Weg.html"),
                         ("orion.json", 'page is geen html, gebruik "file"'), git=True)

    def test_fout_geen_kaal_pad(self):
        self.assertMeldt({"orion.json": menu("page:./" + INL, "page:Labo//RS485/overview.html",
                                             "page:Labo/../" + INL), INL: pagina()},
                         ("orion.json", "./Labo"), ("orion.json", "Labo//RS485"),
                         ("orion.json", "Labo/../Labo"), git=True)

    def test_fout_hoofdletters(self):
        self.assertMeldt({"orion.json": menu("page:Labo/rs485/overview.html"), INL: pagina()},
                         ("orion.json", "hoofdletters"), git=True)

    def test_fout_niet_in_git(self):
        self.assertMeldt({"orion.json": menu("page:" + INL), INL: pagina()},
                         ("orion.json", "zit niet in git"), git=True, ongetrackt=[INL])

    def test_fout_kapotte_json(self):
        self.assertMeldt({"orion.json": "{"}, ("orion.json", "geen geldige JSON"))


class OrionIds(RegelTest):
    regel = "orion-ids"

    def test_goed_kebab_en_uniek(self):
        self.assertSchoon({"orion.json": menu("page:" + INL, "page:" + OPDR)})

    def test_fout_vorm_en_dubbel(self):
        doc = {"modules": [{"id": "Labo_RS485", "items": [{"id": "inl"}, {"id": "inl"}]}]}
        self.assertMeldt({"orion.json": json.dumps(doc)},
                         ("orion.json", "id 'Labo_RS485' mag alleen"),
                         ("orion.json", "id 'inl' komt twee keer voor"))


class OrionWees(RegelTest):
    regel = "orion-orphan"

    def test_goed_alles_in_het_menu(self):
        # Buiten orphan_roots en een exempt-pagina tellen niet.
        self.assertSchoon({"orion.json": menu("page:" + INL), INL: pagina(),
                           "Algemeen/Los.html": pagina(), "Labo/pasteInOrion.html": pagina()})

    def test_fout_wees(self):
        self.assertMeldt({"orion.json": menu("page:" + INL), INL: pagina(), OPDR: pagina()},
                         (OPDR, "staat niet als page in orion.json"))

    def test_fout_verkeerde_hoofdletter_dekt_niet(self):
        self.assertMeldt({"orion.json": menu("page:Labo/RS485/Overview.html"), INL: pagina()},
                         (INL, "staat niet als page"))

    def test_fout_eigen_wortels(self):
        self.assertMeldt({"orion.json": menu(), "Algemeen/Los.html": pagina()},
                         ("Algemeen/Los.html", "staat niet als page"),
                         config={"check": {"orphan_roots": ["."]}})


class TopicGrens(RegelTest):
    regel = "topic-frame"

    def test_goed_blank_commentaar_pdf_anker(self):
        body = ('<a href="Opdracht.html" target="_blank">opdracht</a>'
                '<!-- <a href="Opdracht.html">x</a> -->'
                '<a href="../../datasheets/max485.pdf">ds</a><a href="#doel">doel</a>'
                '<a href="overview.html#doel">hier</a><a href="Bestaat-niet.html">x</a>')
        self.assertSchoon({"orion.json": menu("page:" + INL), INL: pagina(body), OPDR: pagina(),
                           PDF: b"%PDF"})

    def test_fout_zelfde_frame(self):
        self.assertMeldt({"orion.json": menu("page:" + INL), INL: pagina(
            '<a class="btn" href="Opdracht.html?x=1#top">opdracht</a>'), OPDR: pagina()},
            (INL, "linkt in de iframe naar Labo/RS485/Opdracht.html"))
