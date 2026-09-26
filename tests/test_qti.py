"""export-qti: een vragenpagina als QTI 2.1-zip voor ANS."""

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from oriontools.export import qti

QTI = "{http://www.imsglobal.org/xsd/imsqti_v2p1}"


def vraag(stam, *keuzes, juist=0, oplossing="Omdat."):
    items = "".join(f'<li class="juist">{k}</li>' if i == juist else f"<li>{k}</li>"
                    for i, k in enumerate(keuzes))
    return f'<li>{stam}<ul>{items}</ul><div class="oplossing">{oplossing}</div></li>'


def pagina(*vragen):
    return ('<!DOCTYPE html>\n<html lang="nl">\n<head><title>T</title></head>\n<body>\n'
            f'<h1>Netwerklaag</h1>\n<ol class="vragen">{"".join(vragen)}</ol>\n</body>\n</html>\n')


class ExportQti(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "oriontools.json").write_text(json.dumps({"course": {"code": "T"}}))
        (self.root / ".gitignore").write_text("_toets/\n")
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)

    def schrijf(self, pad, inhoud):
        p = self.root / pad
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(inhoud) if isinstance(inhoud, bytes) else p.write_text(inhoud, encoding="utf-8")

    def export(self, bron, *opties):
        uit = io.StringIO()
        with contextlib.redirect_stdout(uit):
            qti.main([bron, "--repo", str(self.root), *opties])
        return uit.getvalue()

    def zip(self, naam="Toets-qti.zip"):
        return zipfile.ZipFile(self.root / "_toets" / naam)

    def item(self, z, nr=1, pakket="T-Toets"):
        return ElementTree.fromstring(z.read(f"{pakket}-{nr:02d}.xml"))

    def test_goed_juist_wordt_de_correcte_letter(self):
        self.schrijf("_toets/Toets.html", pagina(vraag("Welke laag?", "1", "2", "3", juist=2)))
        self.export("_toets/Toets.html")
        item = self.item(self.zip())
        self.assertEqual(item.find(f".//{QTI}correctResponse/{QTI}value").text, "C")
        keuzes = item.findall(f".//{QTI}simpleChoice")
        self.assertEqual([k.text for k in keuzes], ["1", "2", "3"])
        self.assertNotIn("juist", ElementTree.tostring(item, encoding="unicode"))

    def test_goed_kop_van_de_groep_in_de_titel(self):
        v = vraag("Welke laag?", "1", "2", juist=1)
        self.schrijf("_toets/Toets.html", pagina(v).replace(
            '<ol class="vragen">', '<h2>D1 Lagen</h2>\n<h3>Varianten</h3>\n<ol class="vragen">'
            + v + '</ol>\n<h2>D2 Adressen</h2>\n<ol class="vragen" start="3">'))
        self.export("_toets/Toets.html")
        z = self.zip()
        self.assertEqual(self.item(z, 1).get("title"), "Netwerklaag - D1 Lagen / Varianten - vraag 01")
        self.assertEqual(self.item(z, 3).get("title"), "Netwerklaag - D2 Adressen - vraag 03")

    def test_goed_zonder_kop_alleen_het_nummer(self):
        self.schrijf("_toets/Toets.html", pagina(vraag("Welke laag?", "1", "2", juist=1)))
        self.export("_toets/Toets.html")
        self.assertEqual(self.item(self.zip()).get("title"), "Netwerklaag - vraag 01")

    def test_goed_punt_op_normalmaximum(self):
        # ANS haalt het punt uit normalMaximum, en alleen in QTI 2.x; in 3.0 werd het 0.
        self.schrijf("_toets/Toets.html", pagina(vraag("V?", "a", "b")))
        self.export("_toets/Toets.html")
        item = self.item(self.zip())
        score = next(o for o in item.findall(f"{QTI}outcomeDeclaration") if o.get("identifier") == "SCORE")
        self.assertEqual(score.get("normalMaximum"), "1")
        self.assertNotIn("normal-maximum", self.zip().read("T-Toets-01.xml").decode())

    def test_goed_manifest_in_de_root(self):
        self.schrijf("_toets/Toets.html", pagina(vraag("V?", "a", "b"), vraag("W?", "c", "d")))
        self.export("_toets/Toets.html")
        z = self.zip()
        self.assertEqual(sorted(z.namelist()), ["T-Toets-01.xml", "T-Toets-02.xml", "imsmanifest.xml"])
        manifest = z.read("imsmanifest.xml").decode()
        self.assertIn('identifier="T-Toets-package"', manifest)
        self.assertIn('type="imsqti_item_xmlv2p1"', manifest)

    def test_goed_zonder_feedback_geen_uitleg(self):
        self.schrijf("_toets/Toets.html", pagina(vraag("V?", "a", "b", oplossing="Geheim")))
        self.export("_toets/Toets.html")
        xml = self.zip().read("T-Toets-01.xml").decode()
        self.assertNotIn("Geheim", xml)
        self.assertIn("match_correct", xml)

    def test_goed_feedback_met_de_uitleg(self):
        self.schrijf("_toets/Toets.html",
                     pagina(vraag("V?", "a", "b", oplossing='Zie <a href="X.html">de theorie</a>.')))
        self.export("_toets/Toets.html", "--feedback")
        item = self.item(self.zip())
        feedback = item.find(f"{QTI}modalFeedback")
        self.assertEqual(ElementTree.tostring(feedback, encoding="unicode", method="text").strip(),
                         "Zie de theorie.")
        self.assertIsNone(item.find(f".//{QTI}a"))

    def test_goed_schudden_standaard_en_uit(self):
        self.schrijf("_toets/Toets.html", pagina(vraag("V?", "a", "b")))
        self.export("_toets/Toets.html")
        self.assertIn('shuffle="true"', self.zip().read("T-Toets-01.xml").decode())
        self.export("_toets/Toets.html", "--niet-schudden")
        self.assertIn('shuffle="false"', self.zip().read("T-Toets-01.xml").decode())

    def test_goed_figuur_gaat_mee(self):
        self.schrijf("img/fig.svg", "<svg/>")
        self.schrijf("img/elders.svg", "<svg/>")
        self.schrijf("_toets/Toets.html",
                     pagina(vraag('Wat zie je?<figure><img src="../img/fig.svg" alt="x"></figure>', "a", "b"))
                     .replace("<h1>", '<img src="../img/elders.svg" alt=""><h1>'))
        self.export("_toets/Toets.html")
        z = self.zip()
        self.assertIn("img/fig.svg", z.namelist())
        self.assertNotIn("img/elders.svg", z.namelist())
        self.assertIn('<file href="img/fig.svg"/>', z.read("imsmanifest.xml").decode())
        self.assertIn('<img src="img/fig.svg" alt="x"/>', z.read("T-Toets-01.xml").decode())
        # QTI 2.1 kent geen <figure>: het wordt een <div>.
        xml = z.read("T-Toets-01.xml").decode()
        self.assertNotIn("<figure", xml)
        self.assertIn('<div><img src="img/fig.svg" alt="x"/></div>', xml)

    def test_goed_codeblok_blijft_letterlijk(self):
        code = "interface vlan 10\n  ip address 10.0.0.1 255.0.0.0"
        self.schrijf("_toets/Toets.html", pagina(vraag(f"Wat doet dit?<pre><code>{code}</code></pre>", "a", "b")))
        self.export("_toets/Toets.html")
        pre = self.item(self.zip()).find(f".//{QTI}pre")
        self.assertEqual("".join(pre.itertext()), code)

    def test_goed_open_vraag_overgeslagen(self):
        open_ = '<li>Leg uit.<div class="oplossing">Zo.</div></li>'
        self.schrijf("_toets/Toets.html", pagina(open_, vraag("V?", "a", "b")))
        uit = self.export("_toets/Toets.html")
        self.assertIn("vraag 1 is een open vraag", uit)
        self.assertEqual(sorted(self.zip().namelist()), ["T-Toets-02.xml", "imsmanifest.xml"])

    def test_goed_zelftest_buiten_de_toetsmap(self):
        self.schrijf("Labo/RS485/Theorie/TestJezelf.html", pagina(vraag("V?", "a", "b")))
        self.export("Labo/RS485/Theorie/TestJezelf.html")
        z = self.zip("Labo-RS485-Theorie-TestJezelf-qti.zip")
        self.assertIn("T-Labo-RS485-Theorie-TestJezelf-01.xml", z.namelist())

    def test_goed_vorige_run_blijft_niet_achter(self):
        self.schrijf("_toets/Toets.html", pagina(vraag("V?", "a", "b"), vraag("W?", "c", "d")))
        self.export("_toets/Toets.html")
        self.schrijf("_toets/Toets.html", pagina(vraag("V?", "a", "b")))
        self.export("_toets/Toets.html")
        self.assertNotIn("T-Toets-02.xml", self.zip().namelist())

    def test_fout_twee_juiste_mogelijkheden(self):
        dubbel = '<li>V?<ul><li class="juist">a</li><li class="juist">b</li></ul></li>'
        self.schrijf("_toets/Toets.html", pagina(dubbel))
        with self.assertRaises(SystemExit) as e:
            self.export("_toets/Toets.html")
        self.assertIn("2 mogelijkheden", str(e.exception.code))
        self.assertFalse((self.root / "_toets" / "Toets-qti.zip").exists())

    def test_fout_geen_juiste_mogelijkheid(self):
        self.schrijf("_toets/Toets.html", pagina("<li>V?<ul><li>a</li><li>b</li></ul></li>"))
        with self.assertRaises(SystemExit) as e:
            self.export("_toets/Toets.html")
        self.assertIn("0 mogelijkheden", str(e.exception.code))

    def test_fout_figuur_ontbreekt(self):
        self.schrijf("_toets/Toets.html", pagina(vraag('V?<img src="../img/weg.png" alt="">', "a", "b")))
        with self.assertRaises(SystemExit) as e:
            self.export("_toets/Toets.html")
        self.assertIn("bestaat niet", str(e.exception.code))

    def test_fout_toetsmap_niet_genegeerd(self):
        # Een getrackte toets spiegelt OrionSync naar de cursus.
        (self.root / ".gitignore").write_text("")
        self.schrijf("_toets/Toets.html", pagina(vraag("V?", "a", "b")))
        with self.assertRaises(SystemExit) as e:
            self.export("_toets/Toets.html")
        self.assertIn(".gitignore", str(e.exception.code))
        self.assertFalse((self.root / "_toets" / "Toets-qti.zip").exists())


if __name__ == "__main__":
    unittest.main()
