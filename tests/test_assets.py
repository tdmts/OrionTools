from tests.minivak import RegelTest, pagina

P = "Algemeen/Pagina.html"


class BrightspaceHotlink(RegelTest):
    regel = "brightspace-hotlink"

    def test_goed_relatief(self):
        self.assertSchoon({P: pagina('<a href="../datasheets/ds.pdf">ds</a>')})

    def test_fout_pad_en_url(self):
        self.assertMeldt({P: pagina('<img src="/content/enforced/15640-X/img/a.png">'),
                          "Algemeen/B.html": pagina(
                              '<a href="https://orion.hogent.be/content/enforced/1/a.pdf">a</a>')},
                         (P, "hotlinkt"), ("Algemeen/B.html", "hotlinkt"))


class ExterneAfbeelding(RegelTest):
    regel = "remote-image"

    def test_goed_eigen_img(self):
        self.assertSchoon({P: pagina('<img src="../img/a.png" alt="">')})

    def test_fout_http_en_https(self):
        self.assertMeldt({P: pagina('<img src="https://x.be/a.png" alt="">\n'
                                    '<img alt="" src="http://x.be/b.png">')},
                         (P, "https://x.be/a.png"), (P, "http://x.be/b.png"))


class ExternDocument(RegelTest):
    regel = "remote-document"

    def test_goed_webpagina(self):
        self.assertSchoon({P: pagina('<a href="https://www.ti.com/product/MAX485">MAX485</a>')})

    def test_fout_pdf_met_query(self):
        self.assertMeldt({P: pagina('<a href="https://www.ti.com/lit/ds/max485.pdf?ts=1">ds</a>')},
                         (P, "max485.pdf"))

    def test_fout_extra_extensie(self):
        self.assertMeldt({P: pagina('<a href="https://x.be/start.pka">start</a>')},
                         (P, "start.pka"),
                         config={"check": {"remote_document_exts_extra": [".pka"]}})


class YoutubeReferrer(RegelTest):
    regel = "youtube-referrer"

    def test_goed_met_policy(self):
        self.assertSchoon({P: pagina(
            '<iframe src="https://www.youtube.com/embed/x" '
            'referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>')})

    def test_fout_zonder_policy(self):
        self.assertMeldt({P: pagina(
            '<iframe src="https://www.youtube-nocookie.com/embed/x" allowfullscreen></iframe>')},
            (P, "error 153"))


class ChamiloLink(RegelTest):
    regel = "chamilo-link"

    def test_goed_geen_chamilo(self):
        self.assertSchoon({P: pagina('<a href="https://www.hogent.be/">HOGENT</a>')})

    def test_fout_href_en_src(self):
        self.assertMeldt({P: pagina(
            '<a href="https://chamilo.hogent.be/index.php?a=1&amp;b=2">x</a>\n'
            '<img src="https://chamilo.hogent.be/img.png" alt="">')},
            (P, "index.php"), (P, "img.png"))


class VreemdeAssets(RegelTest):
    regel = "foreign-assets"

    def test_goed_orioncss_en_eigen_script(self):
        # Een relatief script is van de repo zelf; een deck en een exempt-pagina
        # laden wat ze willen.
        deck = '<link rel="stylesheet" href="https://cdn.example/x.css">'
        self.assertSchoon({P: pagina('<script src="script.js"></script>'),
                           "Hoorcollege/Sessie1.html": deck,
                           "pasteInOrion.html": deck})

    def test_fout_oude_template(self):
        self.assertMeldt({P: pagina(
            '<link href="/shared/HTML-Template-Library/x.css" rel="stylesheet">\n'
            '<script src="https://code.jquery.com/jquery.js"></script>\n'
            '<script src="//cdn.example/bootstrap.js"></script>')},
            (P, "/shared/HTML-Template-Library/x.css"), (P, "jquery.js"), (P, "bootstrap.js"))
