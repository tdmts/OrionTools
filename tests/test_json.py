"""check --json: de vorm die het paneel leest, en de weigering naast een vlag met eigen uitvoer.

De vorm is een contract met een lezer buiten deze repo. Een sleutel die
verdwijnt of van type verandert, merkt hier niemand op tot het paneel leeg
blijft; daarom staat de volledige sleutelset in de test.
"""

import contextlib
import io
import json

from oriontools.check import runner
from tests.minivak import RegelTest, pagina

P = "Labo/A/Theorie/Pagina.html"
EM = chr(0x2014)  # als code, zodat deze bron zelf geen em-dash draagt
SLEUTELS = {"versie", "repo", "ci", "audit", "fouten", "waarschuwingen", "adviezen",
            "afwijkingen", "bevindingen"}
BEVINDING = {"regel", "ernst", "pad", "regelnr", "boodschap"}


class Json(RegelTest):
    def draai(self, vak, *vlaggen):
        """(exitcode, stdout, stderr) van check met deze vlaggen op het minivak."""
        with contextlib.redirect_stdout(io.StringIO()) as uit, \
                contextlib.redirect_stderr(io.StringIO()) as fout:
            try:
                code = runner.main(["--repo", str(vak.root), *vlaggen])
            except SystemExit as e:
                code = e.code
        return code, uit.getvalue(), fout.getvalue()

    def json(self, vak, *vlaggen):
        code, uit, fout = self.draai(vak, "--json", *vlaggen)
        self.assertEqual(fout, "")
        self.assertTrue(uit.isascii(), "stdout is niet ascii")
        return code, json.loads(uit)

    def assertVorm(self, d):
        self.assertEqual(set(d), SLEUTELS)
        for b in d["bevindingen"]:
            self.assertEqual(set(b), BEVINDING)
            self.assertIn(b["ernst"], {"fout", "waarschuwing", "advies", "afwijking"})
            self.assertNotIn("\\", b["pad"])
            self.assertTrue(b["regelnr"] is None or isinstance(b["regelnr"], int))
        for sleutel, ernst in (("fouten", "fout"), ("waarschuwingen", "waarschuwing"),
                               ("adviezen", "advies"), ("afwijkingen", "afwijking")):
            self.assertEqual(d[sleutel], sum(b["ernst"] == ernst for b in d["bevindingen"]))

    def vakje(self, body):
        return self.vak({P: pagina(body)}, git=True)

    def test_vorm_met_fout_en_waarschuwing(self):
        vak = self.vakje(f'<p>Een bus {EM} twee draden. Dat werkt uiteraard.</p>'
                         '<img src="../../../img/TODO-schema.png" alt="Schema">')
        code, d = self.json(vak)
        self.assertVorm(d)
        self.assertEqual(code, 1)
        self.assertEqual((d["versie"], d["repo"], d["ci"], d["audit"]),
                         (1, vak.root.name, False, False))
        rij = {(b["regel"], b["ernst"], b["pad"]) for b in d["bevindingen"]}
        self.assertIn(("em-dash", "fout", P), rij)
        self.assertIn(("links", "waarschuwing", P), rij)
        self.assertEqual(d["adviezen"], 0, "een auditregel draaide zonder --audit")

    def test_schoon(self):
        code, d = self.json(self.vakje("<p>Tekst.</p>"))
        self.assertVorm(d)
        self.assertEqual((code, d["fouten"], d["bevindingen"]), (0, 0, []))

    def test_audit_is_advies_zonder_invloed_op_de_exitcode(self):
        vak = self.vakje('<!-- audit-skip: lead --><h2 id="pc">Op uw pc</h2>'
                         "<p>Dat werkt uiteraard.</p>")
        code, d = self.json(vak, "--audit")
        self.assertVorm(d)
        self.assertEqual((code, d["audit"], d["fouten"], d["waarschuwingen"]), (0, True, 0, 0))
        regels = {b["regel"]: b for b in d["bevindingen"]}
        self.assertEqual(regels["audit-vulwoord"]["ernst"], "advies")
        self.assertEqual(regels["audit-skip"]["ernst"], "afwijking")
        self.assertIsInstance(regels["audit-u-vorm"]["regelnr"], int)

    def test_ci(self):
        code, d = self.json(self.vakje("<p>Tekst.</p>"), "--ci")
        self.assertTrue(d["ci"])

    def test_exitcode_gelijk_aan_tekst(self):
        for body in ("<p>Tekst.</p>", f"<p>a {EM} b</p>",
                     '<img src="../../../img/TODO-schema.png" alt="Schema">'):
            vak = self.vakje(body)
            for vlaggen in ((), ("--audit",), ("--ci",)):
                with self.subTest(body=body, vlaggen=vlaggen):
                    tekst, _, _ = self.draai(vak, *vlaggen)
                    code, _ = self.json(vak, *vlaggen)
                    self.assertEqual(code, tekst)

    def test_fout_weigert_naast_een_vlag_met_eigen_uitvoer(self):
        bron = pagina(f"<p>a {EM} b</p>")
        vak = self.vak({P: bron}, git=True)
        for vlaggen in (("--hook",), ("--fix", "--force"), ("--rules",), ("--explain", "em-dash")):
            with self.subTest(vlaggen=vlaggen):
                code, uit, fout = self.draai(vak, "--json", *vlaggen)
                self.assertEqual(code, 2)
                self.assertEqual(uit, "")
                self.assertIn(f"--json gaat niet samen met {vlaggen[0]}", fout)
        self.assertEqual((vak.root / P).read_text(encoding="utf-8"), bron,
                         "--json --fix herstelde toch")
