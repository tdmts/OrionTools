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
