"""De ANS-client, zonder net: paginering, 429 en een fout zonder token erin."""

import datetime
import email.message
import io
import json
import unittest
import urllib.error
import urllib.parse

from oriontools.ans import client, verken

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


if __name__ == "__main__":
    unittest.main()
