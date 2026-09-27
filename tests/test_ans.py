"""De ANS-client, zonder net: paginering, 429 en een fout zonder token erin."""

import datetime
import email.message
import io
import json
import unittest
import urllib.error
import urllib.parse

import tempfile
from pathlib import Path

from oriontools.ans import client, dekking, push, toets, verken
from oriontools.export import qti

GEHEIM = "geheim-token-123"


def headers(**waarden):
    h = email.message.Message()
    for sleutel, waarde in waarden.items():
        h[sleutel.replace("_", "-")] = str(waarde)
    return h


class Antwoord(io.BytesIO):
    def __init__(self, data, hdrs):
        super().__init__(json.dumps(data).encode("utf-8"))
        self.headers = hdrs


class Net:
    """Een urlopen die antwoorden uit een lijst geeft en de requests bijhoudt."""

    def __init__(self, *antwoorden):
        self.antwoorden = list(antwoorden)
        self.requests = []

    def __call__(self, req):
        self.requests.append(req)
        antwoord = self.antwoorden.pop(0)
        if isinstance(antwoord, Exception):
            raise antwoord
        return antwoord


def fout(code, tekst="", **hdrs):
    return urllib.error.HTTPError("https://ans.app/x", code, "fout", headers(**hdrs),
                                  io.BytesIO(tekst.encode("utf-8")))


class Client(unittest.TestCase):
    def test_goed_alles_haalt_elke_pagina(self):
        net = Net(Antwoord([{"id": 1}], headers(Total_Pages=2)),
                  Antwoord([{"id": 2}], headers(Total_Pages=2)))
        c = client.Client(GEHEIM, openen=net)
        self.assertEqual(c.alles("/question_banks"), [{"id": 1}, {"id": 2}])
        pagina = [urllib.parse.parse_qs(urllib.parse.urlsplit(r.full_url).query)["page"] for r in net.requests]
        self.assertEqual(pagina, [["1"], ["2"]])
        self.assertEqual(net.requests[0].get_header("Authorization"), f"Bearer {GEHEIM}")

    def test_goed_zonder_total_pages_is_er_een_pagina(self):
        net = Net(Antwoord([{"id": 1}], headers()))
        self.assertEqual(client.Client(GEHEIM, openen=net).alles("/x"), [{"id": 1}])

    def test_goed_429_wacht_en_herhaalt(self):
        gewacht = []
        net = Net(fout(429, RateLimit_Reset=7), Antwoord({"id": 1}, headers()))
        c = client.Client(GEHEIM, openen=net, slapen=gewacht.append)
        self.assertEqual(c.haal("/question_banks/1"), {"id": 1})
        self.assertEqual(gewacht, [8])

    def test_fout_melding_noemt_status_en_reden_maar_nooit_het_token(self):
        net = Net(fout(422, '{"name":["is required"]}'))
        with self.assertRaises(client.AnsFout) as ctx:
            client.Client(GEHEIM, openen=net).haal("/question_banks")
        self.assertEqual(ctx.exception.status, 422)
        self.assertIn("is required", str(ctx.exception))
        self.assertNotIn(GEHEIM, str(ctx.exception))
        self.assertNotIn(GEHEIM, repr(client.Client(GEHEIM, openen=net)))

    def test_fout_zonder_token(self):
        oud_env, oud_bestand = client.os.environ.pop("ANS_TOKEN", None), client.TOKENBESTAND
        client.TOKENBESTAND = client.Path("bestaat/niet")
        try:
            with self.assertRaises(client.AnsFout):
                client.token()
        finally:
            client.TOKENBESTAND = oud_bestand
            if oud_env is not None:
                client.os.environ["ANS_TOKEN"] = oud_env


class Academiejaar(unittest.TestCase):
    def test_goed_september_begint_het_jaar(self):
        self.assertEqual(verken.academiejaar(datetime.date(2026, 9, 1)), 2026)
        self.assertEqual(verken.academiejaar(datetime.date(2027, 8, 31)), 2026)


class Push(unittest.TestCase):
    def test_goed_import_upload_zonder_token_en_wacht_op_de_job(self):
        net = Net(Antwoord({"put_url": "https://store.example/x.zip?sig=1",
                            "background_job": {"id": 5, "status": "initialized"}}, headers()),
                  Antwoord({}, headers()),
                  Antwoord({"id": 5, "status": "pending"}, headers()),
                  Antwoord({"id": 5, "status": "done"}, headers()))
        gewacht = []
        job = push.importeer(client.Client(GEHEIM, openen=net), 7, "x.zip", b"PK", slapen=gewacht.append)
        self.assertEqual(job["status"], "done")
        self.assertEqual([r.get_method() for r in net.requests], ["GET", "PUT", "PATCH", "GET"])
        self.assertIsNone(net.requests[1].get_header("Authorization"))
        self.assertEqual(json.loads(net.requests[2].data), {"status": "pending"})
        self.assertEqual(gewacht, [push.WACHT])

    def test_goed_hash_van_een_item_volgt_zijn_figuur(self):
        xml = b'<item><img src="img/a.png"/></item>'
        een = push.items_van({"X-01.xml": xml, "img/a.png": b"1", "imsmanifest.xml": b""})
        twee = push.items_van({"X-01.xml": xml, "img/a.png": b"2", "imsmanifest.xml": b""})
        self.assertEqual(list(een), ["X-01"])
        self.assertNotEqual(een, twee)

    def test_goed_banknaam_volgt_het_menu(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "orion.json").write_text(json.dumps({"modules": [
                {"title": "4. Labo: RS485", "items": [
                    {"title": "Theorie", "items": [{"title": "Test jezelf", "page": "Labo/RS485/T.html"}]}]}]}),
                encoding="utf-8")
            self.assertEqual(push.menupad(Path(d), "Labo/RS485/T.html"), ["Labo: RS485", "Theorie", "Test jezelf"])
            self.assertIsNone(push.menupad(Path(d), "_toets/X.html"))
            vak = type("Vak", (), {"root": Path(d), "code": "DeN"})()
            self.assertEqual(push.banknaam(vak, "Labo/RS485/T.html", "Negeer"),
                             "DEN - Labo: RS485 - Theorie - Test jezelf")
            self.assertEqual(push.banknaam(vak, "_toets/X.html", "Toets labo X"), "DEN - Toets labo X")
            self.assertEqual(push.banknaam(vak, "_toets/X.html"), "DEN - _toets - X")

    def test_goed_plan_vervangt_alleen_wat_anders_is(self):
        doel = {"P-01": "p#1@a", "P-02": "p#2@b", "P-03": "p#3@c"}
        bestaande = [{"id": 1, "qti_identifier": "P-01", "external_id": "p#1@a"},
                     {"id": 2, "qti_identifier": "P-02", "external_id": "p#2@oud"},
                     {"id": 4, "qti_identifier": "P-04", "external_id": "p#4@d"},
                     {"id": 5, "qti_identifier": "P-X-01", "external_id": None},
                     {"id": 6, "qti_identifier": None, "external_id": None}]
        nieuw, gewijzigd, verweesd = push.plan(doel, bestaande, "P")
        self.assertEqual(nieuw, ["P-03"])
        self.assertEqual([e["id"] for e in gewijzigd], [2])
        self.assertEqual([e["id"] for e in verweesd], [4])

    def test_fout_twee_banken_met_dezelfde_external_id(self):
        net = Net(Antwoord([{"id": 1, "external_id": "E"}, {"id": 2, "external_id": "E"}], headers()))
        with self.assertRaises(client.AnsFout):
            push.zoek_bank(client.Client(GEHEIM, openen=net), "E")


VRAGEN = """<ol class="vragen">
<li data-bron="Labo/A/Theorie/X.html Labo/A/Theorie/Y.html">Stam?<ul><li class="juist">a</li><li>b</li></ul></li>
<li>Stam?<ul><li class="juist">a</li><li>b</li></ul>
<div class="oplossing">Zie <a href="../Theorie/Z.html#kop" target="_blank">Z</a>,
<a href="https://example.com/x.html">extern</a> en <a href="#boven">boven</a>.</div></li>
<li>Open vraag.</li>
</ol>"""


class Dekking(unittest.TestCase):
    def test_goed_bronnen_uit_data_bron(self):
        self.assertEqual(qti.bronnen(VRAGEN), {1: ["Labo/A/Theorie/X.html", "Labo/A/Theorie/Y.html"]})

    def test_fout_data_bron_die_niet_bestaat_stopt_de_export(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "Labo/A/Theorie").mkdir(parents=True)
            (Path(d) / "Labo/A/Theorie/X.html").write_text("", encoding="utf-8")
            with self.assertRaises(qti.Fout) as ctx:
                qti.controleer_bronnen(VRAGEN, Path(d))
            self.assertIn("Y.html", str(ctx.exception))
            self.assertNotIn("X.html", str(ctx.exception))

    def test_goed_verwijzingen_uit_data_bron_en_de_oplossing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            pagina = root / "Labo/A/Toets/T.html"
            self.assertEqual(dekking.verwijzingen(pagina, VRAGEN, root),
                             {1: {"Labo/A/Theorie/X.html", "Labo/A/Theorie/Y.html"},
                              2: {"Labo/A/Theorie/Z.html"}})

    def test_goed_vlaggen_volgen_de_bank_en_anders_de_standaard(self):
        geen, niet_schudden = dekking.VLAGGEN[0], dekking.VLAGGEN[1]
        doelen = {v: {"P-01": f"p#1@{i}", "P-02": f"p#2@{i}"} for i, v in enumerate(dekking.VLAGGEN)}
        bank = [{"qti_identifier": "P-01", "external_id": "p#1@1"},
                {"qti_identifier": "P-02", "external_id": "p#2@1"}]
        self.assertEqual(dekking.beste(doelen, bank), niet_schudden)
        self.assertEqual(dekking.beste(doelen, []), geen)
        self.assertEqual(dekking.vlaggen(geen), "geen")
        self.assertEqual(dekking.vlaggen((False, True)), "--niet-schudden --feedback")


HUB = """<h2 id="leerstof">Leerstof</h2>
<ol><li>Geen doelstelling.</li></ol>
<h2 id="doelstellingen">Doelstellingen</h2>
<p>Op het einde van dit labo kan je:</p>
<!-- <ol><li>Uitgezet.</li></ol> -->
<ol>
<li>Een bus opbouwen</li>
<li data-bron="Labo/A/Theorie/X.html">Uitleggen <strong>waarom</strong> differential signaling
    minder gevoelig is voor ruis dan single ended signaling</li>
<li data-bron="Labo/A/Theorie/Y.html Labo/A/Theorie/Z.html">Simplex en duplex</li>
</ol>
<h2 id="evaluatie">Evaluatie</h2>
<ol><li>Ook geen.</li></ol>"""


class Doelstellingen(unittest.TestCase):
    def test_goed_elke_stand(self):
        rijen = dekking.per_doelstelling(HUB, {"Labo/A/Theorie/Z.html": ["T.html vraag 1"]})
        self.assertEqual([(n, s) for n, s, _ in rijen],
                         [(1, dekking.GEEN_THEORIE), (2, dekking.GEEN_VRAAG), (3, dekking.GEDEKT)])
        self.assertEqual(rijen[1][2], "Uitleggen waarom differential signaling minder gevoelig is ...")

    def test_goed_zonder_kop_geen_doelstellingen(self):
        self.assertEqual(dekking.per_doelstelling("<ol><li>Iets.</li></ol>", {}), [])


CFG = {"assignment_type": "Quiz", "summative": True,
       "accessibility_settings": {"attempts": 1},
       "grades_settings": {"passed_grade": 9.99, "grade_lower_limit": "0", "guess_correction": True},
       "cover": {"_uitleg": "commentaar", "shuffle_choices": True, "description_before": "<div>x</div>"}}


class Toets(unittest.TestCase):
    def test_goed_nieuwe_toets_krijgt_alles_uit_de_config_zonder_commentaar(self):
        body, cover, regels = toets.plan(CFG, {}, {})
        self.assertEqual(body, {"assignment_type": "Quiz", "summative": True,
                                "accessibility_settings": {"attempts": 1},
                                "grades_settings": CFG["grades_settings"]})
        self.assertEqual(cover, {"shuffle_choices": True, "description_before": "<div>x</div>"})
        self.assertEqual(len(regels), 8)

    def test_goed_getal_als_tekst_is_geen_verschil(self):
        bestaand = {"name": "T", "assignment_type": "Quiz", "summative": True,
                    "accessibility_settings": {"attempts": 1, "notes": False},
                    "grades_settings": {"passed_grade": "9.99", "grade_lower_limit": "0.0",
                                        "guess_correction": True, "rounding": "two_decimal"}}
        cover = {"shuffle_choices": True, "description_before": "<div>x</div>", "display_headers": True}
        self.assertEqual(toets.plan(CFG, bestaand, cover), (None, None, []))

    def test_goed_een_object_gaat_volledig_mee(self):
        bestaand = {"name": "T", "assignment_type": "Quiz", "summative": True,
                    "accessibility_settings": {"attempts": 1},
                    "grades_settings": {"passed_grade": "9.99", "grade_lower_limit": "0.0",
                                        "guess_correction": False, "rounding": "two_decimal"}}
        body, cover, regels = toets.plan(CFG, bestaand, {"shuffle_choices": False, "description_before": "<div>x</div>"})
        self.assertEqual(body, {"grades_settings": {"passed_grade": 9.99, "grade_lower_limit": "0",
                                                    "guess_correction": True, "rounding": "two_decimal"}})
        self.assertEqual(cover, {"shuffle_choices": True})
        self.assertEqual([r[0] for r in regels], ["grades_settings.guess_correction", "cover.shuffle_choices"])

    def test_fout_waar_en_een_zijn_niet_gelijk(self):
        self.assertFalse(toets.gelijk(True, 1))
        self.assertFalse(toets.gelijk(None, 0))
        self.assertTrue(toets.gelijk("20.0", 20))

    def test_goed_naam_en_id_volgen_de_map(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "orion.json").write_text(json.dumps({"modules": [
                {"title": "4. Labo: RS485", "items": [
                    {"title": "Inleiding", "page": "Labo/RS485/overview.html"},
                    {"title": "Theorie", "items": [{"title": "Test jezelf", "page": "Labo/RS485/Theorie/T.html"}]}]},
                {"title": "5. Labo: RS", "items": [{"title": "Inleiding", "page": "Labo/RS/overview.html"}]}]}),
                encoding="utf-8")
            vak = type("Vak", (), {"root": Path(d), "code": "DeN"})()
            self.assertEqual(toets.toetsnaam(vak, "Labo/RS485"), "DEN - Labo: RS485 - Toets")
            self.assertEqual(toets.toets_id(vak, "Labo/RS485"), "DeN-Labo-RS485-Toets")

    def test_fout_twee_toetsen_met_dezelfde_external_id(self):
        net = Net(Antwoord([{"id": 1, "external_id": "E"}, {"id": 2, "external_id": "E"},
                            {"id": 3, "external_id": "E", "trashed": True}], headers()))
        with self.assertRaises(client.AnsFout):
            toets.zoek_toets(client.Client(GEHEIM, openen=net), 9, "E")


if __name__ == "__main__":
    unittest.main()
