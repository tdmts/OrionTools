from tests.minivak import RegelTest, pagina

P = "Labo/A/Theorie/Code.html"
EM = chr(0x2014)  # als code, zodat deze bron zelf geen em-dash draagt


def blok(code, taal="cpp"):
    return (f'<pre class="code-wrapper linenumbers show-language language-{taal}"><code>'
            f"{code}</code></pre>")


class EmDash(RegelTest):
    regel = "em-dash"

    def test_goed_komma(self):
        self.assertSchoon({P: pagina("<p>Een bus, twee draden.</p><p>Van 1-2 V.</p>")})

    def test_fout_teken_en_entiteit_een_per_pagina(self):
        self.assertMeldt({P: pagina(f"<p>Een bus {EM} twee draden {EM} en meer.</p>"),
                          "Labo/A/B.html": pagina("<p>Een bus &mdash; twee draden.</p>")},
                         (P, "em-dash"), ("Labo/A/B.html", "em-dash"))

    def test_fout_ook_op_skip_page(self):
        # Een stijlgids zet de huisstijl voor wat eruit gekopieerd wordt.
        self.assertMeldt({"template.html": pagina(f"<p>a {EM} b</p>")}, ("template.html", "em-dash"),
                         config={"check": {"skip_pages": ["template.html"]}})


class CodeStijl(RegelTest):
    regel = "code-style"

    def test_goed_allman_en_spaties(self):
        code = ("void setup()\n{\n    int macht = 1;\n    for (byte i = 0; i &lt; 10; i++)\n"
                "    {\n        macht = macht * 2;\n    }\n    int t[] = {1, 2};\n}")
        self.assertSchoon({P: pagina(blok(code))})

    def test_goed_andere_taal_en_proza(self):
        # IOS-configuratie wordt letterlijk overgenomen; een decimale komma in
        # proza en inline <code> zijn geen code.
        self.assertSchoon({P: pagina(blok("interface vlan1\n ip address 10.0.0.1 255.0.0.0",
                                          "plaintext")
                                     + "\n<p>Bij 0,17 Hz is <code>i=9</code>.</p>")})

    def test_fout_kr_accolade(self):
        m = self.assertMeldt({P: pagina(blok("void loop() {\n}\n"))}, (P, "K&R"))
        self.assertIn("void loop() {", m[0][2])

    def test_fout_ingeklapte_body(self):
        self.assertMeldt({P: pagina(blok("void f()\n{\n    if (x) { doe(); }\n}"))},
                         (P, "K&R"))

    def test_fout_krappe_operatoren(self):
        self.assertMeldt({P: pagina(blok("void f()\n{\n    int macht=1;\n    f(a,b);\n}"))},
                         (P, "(="), (P, "(,)"))

    def test_fout_regelnummer_is_die_van_het_bestand(self):
        tekst = pagina(blok("void f()\n{\n    x=1;\n}"))
        verwacht = next(i for i, r in enumerate(tekst.split("\n"), 1) if "x=1" in r)
        self.assertEqual([b.regelnr for b in self.bevindingen({P: tekst})], [verwacht])

    def test_goed_niet_van_toepassing_zonder_talen(self):
        stand, reden = self.toestand({P: pagina()}, {"check": {"code_style_languages": []}})
        self.assertEqual((stand, reden), ("n.v.t.", "geen code_style_languages"))
