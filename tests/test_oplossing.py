"""De invultabel van export-oplossing: welke regel in welke rij belandt."""

import contextlib
import io
import unittest

from oriontools.export import oplossing


def tabel(*rijen, koppen=("Gegeven", "Waarde"), klasse="verslag-tabel"):
    kop = "".join(f"<th>{k}</th>" for k in koppen)
    romp = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in rij) + "</tr>" for rij in rijen)
    return f'<table class="{klasse}"><thead><tr>{kop}</tr></thead><tbody>{romp}</tbody></table>'


BITS = tabel(("IP-adres", "", "", "", ""), ("Na de AND", "", "", "", ""),
             koppen=("", "8", "4", "2", "1"), klasse="verslag-tabel bits")


def vraag(regels, *tabellen):
    """De HTML van vraag 1 met deze tabellen en deze regels als antwoord."""
    lijst = oplossing.parse_fragment(
        f'<ol class="vragen"><li>Vul aan.{"".join(tabellen)}</li></ol>').children[0]
    antwoord = oplossing.Antwoord("1")
    antwoord.regels = regels
    staat = {"vraag": 0, "gezien": set()}
    uit = []
    oplossing.vragenlijst(lijst, uit, {"1": antwoord}, staat, None, "x.md")
    return "".join(uit)


def cellen(html):
    return [c.inner_text() for c in oplossing.parse_fragment(html).find_all("td")]


class Invultabel(unittest.TestCase):
    def assertSlaatAf(self, tekst, *args):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as fout:
            vraag(*args)
        self.assertIn(tekst, str(fout.exception))

    def test_goed_label_kiest_de_rij_niet_de_volgorde(self):
        html = vraag(["Masker: 255.0.0.0", "Adres: 10.0.0.1"], tabel(("Adres", ""), ("Masker", "")))
        self.assertEqual(cellen(html), ["Adres", "10.0.0.1", "Masker", "255.0.0.0"])

    def test_goed_dubbel_label_in_de_volgorde_van_de_opdracht(self):
        html = vraag(["Masker: a", "Na de AND: b", "Masker: c", "Na de AND: d"],
                     tabel(("Masker", ""), ("Na de AND", ""), ("Masker", ""), ("Na de AND", "")))
        self.assertEqual(cellen(html), ["Masker", "a", "Na de AND", "b", "Masker", "c", "Na de AND", "d"])

    def test_goed_twee_tabellen_met_een_witregel_ertussen(self):
        html = vraag(["IP-adres: 1010", "Na de AND: 1000", "", "Na de AND: 8"],
                     BITS, tabel(("Na de AND", ""), koppen=("", "Decimaal")))
        self.assertEqual(cellen(html), ["IP-adres", "1", "0", "1", "0",
                                        "Na de AND", "1", "0", "0", "0", "Na de AND", "8"])

    def test_goed_bits_met_punten_en_spaties(self):
        self.assertEqual(cellen(vraag(["IP-adres: 10.1 0", "Na de AND: 1|0|0|0"], BITS))[:5],
                         ["IP-adres", "1", "0", "1", "0"])

    def test_goed_rij_zonder_label_vult_ook_de_eerste_cel(self):
        html = vraag([": dlink | 10", ": dlink-5GHz | 44"],
                     tabel(("", ""), ("", ""), koppen=("SSID", "Kanaal")))
        self.assertEqual(cellen(html), ["dlink", "10", "dlink-5GHz", "44"])

    def test_goed_voorgedrukte_cel_wijkt_voor_het_antwoord(self):
        html = vraag(["Router: 192.168.0.1 | nee"],
                     tabel(("Router", "", "ja / nee"), koppen=("Wat", "Adres", "Bereikbaar")))
        self.assertEqual(cellen(html), ["Router", "192.168.0.1", "nee"])

    def test_fout_rij_zonder_antwoord(self):
        self.assertSlaatAf("geen antwoord voor deze rijen: Masker",
                           ["Adres: 10.0.0.1"], tabel(("Adres", ""), ("Masker", "")))

    def test_fout_regel_zonder_rij(self):
        self.assertSlaatAf("geen rij (meer): Adres",
                           ["Adres: 10.0.0.1", "Adres: 10.0.0.2"], tabel(("Adres", "")))

    def test_fout_te_weinig_bits(self):
        self.assertSlaatAf("draagt 3 waarden, de tabel heeft er 4 nodig, een bit per kolom",
                           ["IP-adres: 101", "Na de AND: 1000"], BITS)

    def test_fout_tekst_onder_de_tabel(self):
        self.assertSlaatAf("onder een kader hoort niets",
                           ["Adres: 10.0.0.1", "", "Dat is het adres van de router."],
                           tabel(("Adres", "")))


if __name__ == "__main__":
    unittest.main()
