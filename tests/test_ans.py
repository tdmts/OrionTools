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

from oriontools.ans import client, push, verken

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


if __name__ == "__main__":
    unittest.main()
