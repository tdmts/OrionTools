from tests.minivak import RegelTest, pagina

OPDR = "Labo/RS485/Opdracht.html"
DOCX = "downloads/Labo-RS485-verslag.docx"
KNOP = '<a class="btn btn-primary" href="../../downloads/Labo-RS485-verslag.docx">{}</a>'
VERSLAG = ('<!-- verslag\n<ol class="vragen">\n<li>Meet de spanning.</li>\n</ol>\n-->')


def opdracht(knop="Opdracht downloaden", lead=True, verslag=VERSLAG, extra=""):
    body = ('<p class="lead">Je bouwt een RS485-bus.</p>\n' if lead else "")
    body += (KNOP.format(knop) if knop is not None else "") + "\n" + verslag + extra
    return pagina(body, titel="Opdracht")


class VerslagVerouderd(RegelTest):
    regel = "verslag-stale"

    def test_goed_docx_nieuwer_of_geen_verslag(self):
        self.assertSchoon({OPDR: opdracht(), DOCX: b"PK", "Labo/MS/PacketTracer/Opdracht.html":
                           opdracht(knop=None, verslag="<!-- geen-verslag: een .pka -->")},
                          mtimes={DOCX: 10})

    def test_fout_docx_ouder(self):
        self.assertMeldt({OPDR: opdracht(), DOCX: b"PK"}, (DOCX, "export-verslag Labo/RS485"),
                         mtimes={OPDR: 10})

    def test_fout_docx_ontbreekt_in_submap(self):
        p = "Labo/MS/ProCurve/Opdracht.html"
        tekst = pagina('<p class="lead">x</p><a href="../../../downloads/Labo-MS-ProCurve-verslag.docx">'
                       "Opdracht downloaden</a>" + VERSLAG)
        self.assertMeldt({p: tekst}, (p, "export-verslag Labo/MS/ProCurve"))

    def test_fout_geen_sjabloon_is_waarschuwing(self):
        self.assertMeldt({OPDR: opdracht(knop=None)}, (OPDR, "biedt geen verslagsjabloon aan"),
                         ernst="waarschuwing")


class OnafgeslotenCommentaar(RegelTest):
    regel = "unclosed-comment"

    def test_goed_na_elkaar(self):
        self.assertSchoon({OPDR: opdracht(extra="<!-- AUTEURSNOTITIES -->")})

    def test_fout_genest_en_open(self):
        tekst = pagina("<!-- verslag\n<p>a</p>\n<!-- notitie -->\n<p>b</p>\n<!-- open")
        b = self.bevindingen({OPDR: tekst})
        eerste = tekst[:tekst.index("<!-- verslag")].count("\n") + 1
        laatste = tekst[:tekst.index("<!-- open")].count("\n") + 1
        self.assertEqual([x.regelnr for x in b], [eerste, laatste])


class VerslagMarkup(RegelTest):
    regel = "verslag-markup"

    def test_goed_opdracht_en_zelftest(self):
        # Op een zelftest onder Labo/ hoort een vragenlijst wel op het scherm.
        tabel = ('<table class="verslag-tabel"><thead><tr><th>Pin</th><th>A</th></tr></thead>'
                 "<tr><td>1</td><td></td></tr></table>")
        self.assertSchoon({OPDR: opdracht(verslag=VERSLAG.replace("</ol>", tabel + "</ol>")),
                           "Labo/RS485/Theorie/TestJezelf.html": pagina(
                               '<ol class="vragen"><li>a<div class="oplossing">b</div></li></ol>')})

    def test_fout_vragen_op_het_scherm(self):
        self.assertMeldt({OPDR: opdracht(extra='<ol class="vragen"><li>a</li></ol>'),
                          "Labo/RS485/Theorie/Uitleg.html": pagina(
                              '<div class="verslag-kader">Noteer.</div>')},
                         (OPDR, "'vragen' staat buiten"),
                         ("Labo/RS485/Theorie/Uitleg.html", "'verslag-kader' staat buiten"))

    def test_fout_leeg_verslagblok(self):
        self.assertMeldt({OPDR: opdracht(verslag="<!-- verslag\n<p>Niets.</p>\n-->")},
                         (OPDR, "bevat geen vragenlijst of kader"))

    def test_fout_scheve_tabel(self):
        scheef = ('<table class="verslag-tabel"><thead><tr><th>Pin</th><th>A</th></tr></thead>'
                  "<tr><td>1</td></tr></table>")
        zonder_th = '<table class="verslag-tabel"><tr><td>1</td></tr></table>'
        self.assertMeldt({OPDR: opdracht(verslag=VERSLAG.replace("</ol>", scheef + zonder_th
                                                                 + "</ol>"))},
                         (OPDR, "rij 2: 1 cellen tegenover 2"), (OPDR, "geen <th>"))

    def test_goed_onafgesloten_wordt_overgeslagen(self):
        self.assertSchoon({OPDR: opdracht(extra='<!-- open <ol class="vragen"></ol>')})


class OpdrachtLead(RegelTest):
    regel = "opdracht-lead"

    def test_goed_lead(self):
        self.assertSchoon({OPDR: opdracht()})

    def test_fout_geen_of_in_commentaar(self):
        p = "Labo/B/Opdracht.html"
        self.assertMeldt({OPDR: opdracht(lead=False),
                          p: pagina('<!-- <p class="lead">x</p> -->' + VERSLAG)},
                         (OPDR, 'geen <p class="lead">'), (p, 'geen <p class="lead">'))


class DownloadKnop(RegelTest):
    regel = "download-button"

    def test_goed_opschrift_met_icoon(self):
        self.assertSchoon({OPDR: opdracht('<i class="bi bi-download"></i> Opdracht\n  downloaden')})

    def test_fout_oud_opschrift(self):
        self.assertMeldt({OPDR: opdracht("Opdracht en verslag downloaden")},
                         (OPDR, 'heet "Opdracht en verslag downloaden"'))


class OrionCssWiring(RegelTest):
    regel = "orioncss-wiring"

    def test_goed_site_deck_en_exempt(self):
        self.assertSchoon({OPDR: opdracht(), "Hoorcollege/Sessie1.html": "<html></html>",
                           "pasteInOrion.html": "<html></html>"})

    def test_fout_zonder_orioncss(self):
        p = "Algemeen/Kaal.html"
        self.assertMeldt({p: "<html><body></body></html>"}, (p, "style.css"), (p, "main.js"))


class ChecklistWiring(RegelTest):
    regel = "checklist-wiring"

    @staticmethod
    def checklist(lab="labo1", sync=True):
        s = '<script src="../../checklist-sync.js"></script>' if sync else ""
        init = f"<script>initChecklistSync({{ labId: '{lab}', exerciseId: 'x' }});</script>"
        return pagina('<ul class="checklist"><li>stap</li></ul>' + s + (init if lab else ""))

    def test_goed_eigen_labo(self):
        self.assertSchoon({"Labo1/Exercises/Blink.html": self.checklist()})

    def test_fout_sync_init_en_labo(self):
        self.assertMeldt({"Labo1/Exercises/A.html": self.checklist(sync=False),
                          "Labo1/Exercises/B.html": self.checklist(lab=None),
                          "Labo2/Exercises/C.html": self.checklist()},
                         ("Labo1/Exercises/A.html", "laadt checklist-sync.js niet"),
                         ("Labo1/Exercises/B.html", "labId: 'labo1'"),
                         ("Labo2/Exercises/C.html", "staat in labo2"))
