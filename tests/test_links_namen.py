import json

from tests.minivak import RegelTest, menu, pagina

P = "Labo/A/Theorie/Pagina.html"


class Links(RegelTest):
    regel = "links"

    def test_goed_bestaand_en_getrackt(self):
        self.assertSchoon({P: pagina('<img src="../../../img/a.png" alt="">'
                                     '<a href="Andere.html#stap">x</a>'
                                     '<a href="#top">x</a><a href="/d2l/lp/x">x</a>'
                                     '<a href="mailto:a@b.be">x</a><a href="https://x.be/y">x</a>'
                                     '<a href="../../../img/met%20spatie.png">x</a>'),
                           "Labo/A/Theorie/Andere.html": pagina(),
                           "img/a.png": b"png", "img/met spatie.png": b"png"}, git=True)

    def test_fout_bestaat_niet(self):
        self.assertMeldt({P: pagina('<a href="Weg.html">x</a>')}, (P, "wijst nergens heen: Weg.html"),
                         git=True)

    def test_fout_hoofdletters(self):
        self.assertMeldt({P: pagina('<img src="../../../img/A.png" alt="">'), "img/a.png": b"png"},
                         (P, "hoofdletters"), git=True)

    def test_fout_niet_in_git(self):
        self.assertMeldt({P: pagina('<img src="../../../img/a.png" alt="">'), "img/a.png": b"png"},
                         (P, "nog niet in git"), git=True, ongetrackt=["img/a.png"])

    def test_fout_todo_is_waarschuwing(self):
        self.assertMeldt({P: pagina('<img src="../../../img/TODO-schema.png" alt="">')},
                         (P, "nog te maken asset"), ernst="waarschuwing", git=True)

    def test_fout_zonder_git_waarschuwt(self):
        self.assertMeldt({P: pagina()}, (".", "git niet beschikbaar"), ernst="waarschuwing")

    def test_goed_skip_page(self):
        self.assertSchoon({"template.html": pagina('<img src="demo/x.png" alt="">')},
                          {"check": {"skip_pages": ["template.html"]}}, git=True)


class OefeningNaam(RegelTest):
    regel = "exercise-name"

    def test_goed_beschrijvend(self):
        self.assertSchoon({"orion.json": menu("page:" + P).replace("Topic 0", "Begeleide oefening"),
                           P: pagina(titel="Een looplicht, deel 1")})

    def test_fout_menu_en_kop(self):
        m = self.assertMeldt(
            {"orion.json": menu("page:" + P).replace("Topic 0", "Gevorderde oefening 2"),
             P: pagina(titel="Opdracht 3")},
            ("orion.json", "generieke titel"), (P, "<h1> of <title>"), (P, "<h1> of <title>"))
        self.assertEqual(len(m), 3)

    def test_fout_eigen_woorden(self):
        self.assertMeldt({P: pagina(titel="Taak 1", kop="Een looplicht")},
                         (P, "<title>Taak 1</title>"),
                         config={"check": {"exercise_title_words": ["taak"]}})


def _labo(mid, naam, *items, **extra):
    return {"id": mid, "title": f"Labo: {naam}", "name": naam, "items": list(items), **extra}


def _namen_menu(*modules):
    return json.dumps({"modules": list(modules)}, indent=2, ensure_ascii=False)


class OrionNamen(RegelTest):
    regel = "orion-names"

    def test_goed_alle_vormen(self):
        self.assertSchoon({"orion.json": _namen_menu(
            _labo("a", "Managed switch",
                  {"id": "pt", "title": "Packet Tracer", "items": [
                      {"id": "d1", "dropbox": "Opdracht Managed switch: Packet Tracer (!)"},
                      {"id": "q1", "title": "QR code: Packet Tracer",
                       "qr": {"dropbox": "Opdracht Managed switch: Packet Tracer (!)"}}]},
                  {"id": "d2", "dropbox": "Verslag Managed switch: Deel 2"}),
            _labo("b", "TCP/IP",
                  {"id": "rpi", "title": "Je Raspberry Pi klaarzetten", "name": "Raspberry Pi",
                   "items": [{"id": "d3", "dropbox": "Verslag Raspberry Pi"}]},
                  {"id": "d4", "dropbox": "Opdracht TCP/IP (!)"},
                  {"id": "q4", "title": "QR code", "qr": {"dropbox": "Opdracht TCP/IP (!)"}},
                  {"id": "q5", "title": "QR code: test",
                   "qr": {"grade": "Test labo Managed switch en TCP/IP (!)"}}),
            _labo("c", "Visie", {"id": "d5", "dropbox": "Test labo Visie (!)"},
                  {"id": "q6", "title": "QR code: test", "qr": {"dropbox": "Test labo Visie (!)"}}),
            {"id": "alg", "title": "Algemeen", "items": [{"id": "p", "title": "P", "page": "a.html"}]})})

    def test_fout_dropbox(self):
        self.assertMeldt({"orion.json": _namen_menu(
            _labo("a", "RAPID",
                  {"id": "d1", "dropbox": "Opdracht RAPID: Shift"},
                  {"id": "d2", "dropbox": "Verslag RAPID: Shift (!)"},
                  {"id": "d3", "dropbox": "Opdracht Rapid: Shift (!)"},
                  {"id": "d4", "dropbox": "Opdracht RAPID: TCP/IP (deel 1) (!)"},
                  {"id": "d5", "dropbox": "Indienen RAPID"},
                  {"id": "d6", "dropbox": "Test labo RAPID"}),
            {"id": "x", "title": "Test 1", "items": [{"id": "d7", "dropbox": "Test 1 (!)"}]})},
            ("orion.json", 'een opdracht zonder (!) telt niet mee en heet "Verslag RAPID: Shift"'),
            ("orion.json", 'met een score heet het "Opdracht RAPID: Shift (!)"'),
            ("orion.json", 'na "Opdracht" komt "RAPID"'),
            ("orion.json", "het deel draagt geen haakjes"),
            ("orion.json", 'begint niet met "Opdracht", "Verslag" of "Test labo"'),
            ("orion.json", 'een test telt mee: "Test labo RAPID (!)"'),
            ("orion.json", 'dropbox "Test 1 (!)": staat in een module zonder "name"'))

    def test_fout_test_noemt_andere_modules(self):
        self.assertMeldt({"orion.json": _namen_menu(
            _labo("a", "Linux Basis"), _labo("b", "Linux Geavanceerd",
                  {"id": "q1", "title": "QR code: test",
                   "qr": {"grade": "Test labo Linux Basis en Geavanceerd (!)"}},
                  {"id": "q2", "title": "QR code: test",
                   "qr": {"grade": "Test labo Linux Geavanceerd en Linux Basis (!)"}},
                  {"id": "q3", "title": "QR code: test", "qr": {"grade": "Test labo Linux Basis (!)"}},
                  {"id": "q4", "title": "QR code: test", "qr": {"grade": "Verslag Linux Geavanceerd"}}))},
            ("orion.json", "qr-topic 'q1': cijferitem \"Test labo Linux Basis en Geavanceerd (!)\": na \"Test labo\""),
            ("orion.json", "qr-topic 'q2': cijferitem"),
            ("orion.json", "qr-topic 'q3': cijferitem"),
            ("orion.json", "qr-topic 'q4': cijferitem \"Verslag Linux Geavanceerd\" is een verslag"))

    def test_fout_qr_titel(self):
        self.assertMeldt({"orion.json": _namen_menu(
            _labo("a", "Assemblage",
                  {"id": "d1", "dropbox": "Opdracht Assemblage: Inventaris (!)"},
                  {"id": "q1", "title": "QR code: inventaris", "qr": {"dropbox": "Opdracht Assemblage: Inventaris (!)"}},
                  {"id": "d2", "dropbox": "Opdracht Assemblage (!)"},
                  {"id": "q2", "title": "QR code: opdracht", "qr": {"dropbox": "Opdracht Assemblage (!)"}},
                  {"id": "q3", "title": "QR code", "qr": {"grade": "Test labo Assemblage (!)"}}))},
            ("orion.json", "qr-topic 'q1' heet \"QR code: inventaris\", hoort \"QR code: Inventaris\""),
            ("orion.json", "qr-topic 'q2' heet \"QR code: opdracht\", hoort \"QR code\""),
            ("orion.json", "qr-topic 'q3' heet \"QR code\", hoort \"QR code: test\""))

    def test_fout_deel_kleine_letter(self):
        self.assertMeldt({"orion.json": _namen_menu(
            _labo("a", "RS485",
                  {"id": "d1", "dropbox": "Opdracht RS485: oefeningen (!)"},
                  {"id": "q1", "title": "QR code: oefeningen", "qr": {"dropbox": "Opdracht RS485: oefeningen (!)"}},
                  {"id": "d2", "dropbox": "Verslag RS485: deel 2"},
                  {"id": "d3", "dropbox": "Opdracht RS485: BIOS en UEFI (!)"},
                  {"id": "d4", "dropbox": "Verslag RS485: 2 kanalen"}))},
            ("orion.json", 'het deel begint met een hoofdletter, zoals een titel in het menu: '
                           '"Opdracht RS485: Oefeningen"'),
            ("orion.json", '"Verslag RS485: Deel 2"'))

    def test_goed_eigen_woorden(self):
        self.assertSchoon({"orion.json": _namen_menu(
            _labo("a", "RAPID",
                  {"id": "d1", "dropbox": "Oefening RAPID: Shift"},
                  {"id": "d2", "dropbox": "Opdracht RAPID: Palletizeren (!)"},
                  {"id": "q2", "title": "QR code: Palletizeren", "qr": {"dropbox": "Opdracht RAPID: Palletizeren (!)"}}),
            {"id": "t1", "title": "Test 1", "name": "1", "items": [
                {"id": "d3", "dropbox": "Test 1 (!)"},
                {"id": "q3", "title": "QR code: test", "qr": {"dropbox": "Test 1 (!)"}}]})},
            config={"check": {"names": {"ungraded": "Oefening", "test": "Test"}}})

    def test_fout_eigen_woorden(self):
        self.assertMeldt({"orion.json": _namen_menu(
            _labo("a", "RAPID",
                  {"id": "d1", "dropbox": "Opdracht RAPID: Shift"},
                  {"id": "d2", "dropbox": "Verslag RAPID: Shift"},
                  {"id": "d3", "dropbox": "Oefening RAPID: Shift (!)"},
                  {"id": "d4", "dropbox": "Test labo RAPID (!)"}),
            {"id": "t1", "title": "Test 1", "name": "1", "items": [
                {"id": "d5", "dropbox": "Test 1"},
                {"id": "q5", "title": "QR code", "qr": {"dropbox": "Test 1 (!)"}}]})},
            ("orion.json", 'een opdracht zonder (!) telt niet mee en heet "Oefening RAPID: Shift"'),
            ("orion.json", 'dropbox "Verslag RAPID: Shift": begint niet met "Opdracht", "Oefening" of "Test"'),
            ("orion.json", '"Oefening" telt niet mee; met een score heet het "Opdracht RAPID: Shift (!)"'),
            ("orion.json", 'dropbox "Test labo RAPID (!)": na "Test" komen de names'),
            ("orion.json", 'een test telt mee: "Test 1 (!)"'),
            config={"check": {"names": {"ungraded": "Oefening", "test": "Test"}}})

    def test_fout_eigen_woorden_botsen(self):
        self.assertMeldt({"orion.json": _namen_menu(_labo("a", "RAPID"))},
                         ("oriontools.json", "check.names"),
                         config={"check": {"names": {"ungraded": "Opdracht"}}})

    def test_fout_wijst_de_regel_aan(self):
        menu_ = _namen_menu(_labo("a", "A", {"id": "q", "title": "QR", "qr": {"grade": "Test labo A (!)"}}))
        [b] = self.bevindingen({"orion.json": menu_})
        self.assertIn('"id": "q"', menu_.split("\n")[b.regelnr - 1])

    def test_fout_name_zelf(self):
        self.assertMeldt({"orion.json": _namen_menu(
            {"id": "a", "title": "Labo: RS485", "name": "RS485: oefeningen", "items": []})},
            ("orion.json", "module 'a': \"name\" moet een tekst zijn zonder dubbelpunt of haakjes"))
