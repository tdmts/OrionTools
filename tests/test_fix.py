"""check --fix: het herschrijft bestanden, dus elke herstelling heeft een vaste uitkomst.

Na het herstel draait de regel die de fout meldde opnieuw en moet ze zwijgen;
wat buiten een codeblok staat, blijft byte voor byte staan.
"""

import contextlib
import io
import subprocess
import unittest

from oriontools.check import fix
from oriontools.check.context import Context
from oriontools.check.regel import REGISTER
from tests.minivak import RegelTest, pagina

P = "Labo/A/Theorie/Code.html"
EM = chr(0x2014)  # als code, zodat deze bron zelf geen em-dash draagt


class Spatieer(unittest.TestCase):
    def test_operatoren(self):
        for voor, na in [
            ("int macht=1;", "int macht = 1;"),
            ("for(byte i=0;i&lt;10;i++)", "for (byte i = 0; i &lt; 10; i++)"),
            ("if(a==b&amp;&amp;c!=d)", "if (a == b &amp;&amp; c != d)"),
            ("f(a,b);", "f(a, b);"),
            ("x=-1;", "x = -1;"),
        ]:
            with self.subTest(voor=voor):
                self.assertEqual(fix.spatieer(voor), na)

    def test_blijft_staan(self):
        for regel in [
            'Serial.print("a=b,c");',       # een string is data
            "x = 1; // a,b,c",              # commentaar blijft proza
            "x+=1;",                        # samengestelde toekenning
            "p->waarde = 1 << 3;",          # -> en << nooit gespatieerd
            "#include <Wire.h>",
            "<p>i=9;</p>",                  # een ruwe tag is proza
            "int x=1",                      # eindigt niet op ;{}(),
        ]:
            with self.subTest(regel=regel):
                self.assertEqual(fix.spatieer(regel), regel)

    def test_commentaar_na_code(self):
        self.assertEqual(fix.spatieer("x=1; // a,b"), "x = 1; // a,b")


class Herstel(RegelTest):
    def herstel(self, vak, force=True):
        ctx = Context(vak)
        with contextlib.redirect_stdout(io.StringIO()) as uit, \
                contextlib.redirect_stderr(io.StringIO()) as fout:
            code = fix.herstel(ctx, force=force)
        return code, uit.getvalue() + fout.getvalue()

    def stil(self, vak, *regels):
        ctx = Context(vak)
        for rid in regels:
            ctx._huidige_regel = rid
            REGISTER[rid]().controleer(ctx)
        return [(b.regel, b.boodschap) for b in ctx.bevindingen if b.ernst == "fout"]

    def test_pagina(self):
        body = (f"<p>Een bus {EM} twee draden.</p>\n"
                '<pre class="code-wrapper linenumbers show-language language-cpp"><code>'
                "void setup() {\n    int macht=1;\n}</code></pre>\n"
                "<script>var a=1;</script>\n"
                '<iframe src="https://www.youtube.com/embed/x" allowfullscreen></iframe>\n'
                '<script src="../../../oplossingen.js"></script>')
        vak = self.vak({P: pagina(body)})
        code, uit = self.herstel(vak)
        self.assertEqual(code, 0)
        tekst = (vak.root / P).read_text(encoding="utf-8")
        self.assertIn("<p>Een bus, twee draden.</p>", tekst)
        self.assertIn("<code>void setup()\n{\n    int macht = 1;\n}", tekst)
        self.assertIn("<script>var a=1;</script>", tekst)
        self.assertIn('referrerpolicy="strict-origin-when-cross-origin" allowfullscreen', tekst)
        self.assertNotIn("oplossingen.js", tekst)
        for wat in ("em-dash", "Allman", "operatorspaties", "referrerpolicy", "reveal-script"):
            self.assertIn(wat, uit)
        self.assertEqual(self.stil(vak, "em-dash", "code-style", "youtube-referrer",
                                   "reveal-script-retired"), [])

    def test_crlf_blijft(self):
        tekst = pagina('<pre class="code-wrapper language-cpp"><code>void f() {\n}</code></pre>')
        vak = self.vak({P: tekst.replace("\n", "\r\n").encode()})
        self.herstel(vak)
        nieuw = (vak.root / P).read_bytes()
        self.assertIn(b"void f()\r\n{\r\n}", nieuw)
        self.assertNotIn(b"\r\r", nieuw)
        self.assertEqual(nieuw.count(b"\n"), nieuw.count(b"\r\n"))

    def test_zonder_codetalen_geen_codeherstel(self):
        tekst = pagina('<pre class="code-wrapper language-cpp"><code>x=1;</code></pre>')
        vak = self.vak({P: tekst}, {"check": {"code_style_languages": []}})
        self.herstel(vak)
        self.assertEqual((vak.root / P).read_text(encoding="utf-8"), tekst)

    def test_staget_ongetrackte_asset(self):
        vak = self.vak({P: pagina('<img src="../../../img/a.png" alt="">'), "img/a.png": b"png",
                        "img/b.png": b"png"}, git=True, ongetrackt=["img/a.png", "img/b.png"])
        code, uit = self.herstel(vak)
        self.assertEqual(code, 0)
        getrackt = subprocess.run(["git", "ls-files"], cwd=vak.root, capture_output=True,
                                  text=True).stdout.split()
        self.assertIn("img/a.png", getrackt)
        self.assertNotIn("img/b.png", getrackt, "wat niemand aanwijst, blijft ongetrackt")

    def test_vuile_tree_zonder_force(self):
        tekst = pagina(f"<p>a {EM} b</p>")
        vak = self.vak({P: tekst}, git=True)
        code, uit = self.herstel(vak, force=False)
        self.assertEqual(code, 2)
        self.assertIn("schone tree", uit)
        self.assertEqual((vak.root / P).read_text(encoding="utf-8"), tekst)
