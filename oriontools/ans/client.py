"""Een dunne client op de ANS-API v2, met enkel de standaardbibliotheek.

De documentatie is de swagger van ANS (https://ans.app/api/v2); wat daar
staat, herhaalt dit bestand niet. Wat hier staat, is wat de swagger zegt over
het verkeer zelf en wat elk commando dus op dezelfde manier moet doen.

HET TOKEN STAAT BUITEN ELKE REPO
--------------------------------
OrionTools is publiek, en een vakrepo spiegelt OrionSync naar de cursus. Een
token in een van de twee is een token dat iemand anders leest. Het komt dus
uit de omgeving: ANS_TOKEN, anders het bestand ~/.orion/ans-token. Een
bestand werkt zonder VS Code te herstarten, wat een omgevingsvariabele wel
vraagt. Een token maak je aan op https://ans.app/users/api_tokens, en de API
geeft wat jouw rol in ANS mag, niet meer. Dit bestand drukt het token nooit af,
ook niet in een foutmelding.

PAGINERING
----------
Een lijst komt in pagina's van hoogstens 100. De header Total-Pages zegt hoeveel
er zijn; alles() haalt ze allemaal. Zonder die header is er een pagina.

429 EN DE LIMIET PER RECORD
---------------------------
Boven de limiet van het contract antwoordt ANS met 429 en zegt RateLimit-Reset
hoeveel seconden je moet wachten. De client wacht dan en probeert opnieuw.
Daarnaast mag een gebruiker een record hoogstens vijf keer per minuut wijzigen.
Dat is geen zaak van de client maar van wie schrijft: bundel de wijzigingen
aan een record in een request, in plaats van een PATCH per veld.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASIS = "https://ans.app/api/v2"
TOKENBESTAND = Path.home() / ".orion" / "ans-token"
POGINGEN = 3


class AnsFout(Exception):
    """Een antwoord van ANS dat geen succes is, of geen token."""

    def __init__(self, bericht, status=None):
        super().__init__(bericht)
        self.status = status


def token():
    """Het token uit ANS_TOKEN of ~/.orion/ans-token."""
    waarde = os.environ.get("ANS_TOKEN", "").strip()
    if not waarde and TOKENBESTAND.is_file():
        waarde = TOKENBESTAND.read_text(encoding="utf-8").strip()
    if not waarde:
        raise AnsFout(f"geen ANS-token: zet ANS_TOKEN of schrijf het in {TOKENBESTAND}. "
                      "Een token maak je aan op https://ans.app/users/api_tokens.")
    return waarde


class Client:
    def __init__(self, sleutel=None, basis=BASIS, openen=None, slapen=time.sleep):
        self._sleutel = sleutel or token()
        self.basis = basis.rstrip("/")
        # Te vervangen in een test, zodat die niet over het net gaat.
        self._openen = openen or urllib.request.urlopen
        self._slapen = slapen

    def __repr__(self):
        return f"Client({self.basis})"  # zonder het token

    def vraag(self, methode, pad, params=None, body=None):
        """Een request; geeft (json, headers). Wacht en herhaalt bij 429."""
        url = self.basis + pad
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = None if body is None else json.dumps(body).encode("utf-8")
        for poging in range(POGINGEN):
            req = urllib.request.Request(url, data=data, method=methode)
            req.add_header("Authorization", f"Bearer {self._sleutel}")
            req.add_header("Accept", "application/json")
            req.add_header("User-Agent", "OrionTools")
            if data is not None:
                req.add_header("Content-Type", "application/json")
            try:
                with self._openen(req) as antwoord:
                    inhoud = antwoord.read()
                    headers = dict(antwoord.headers)
            except urllib.error.HTTPError as e:
                if e.code == 429 and poging < POGINGEN - 1:
                    self._slapen(int(e.headers.get("RateLimit-Reset") or 60) + 1)
                    continue
                raise AnsFout(f"{methode} {pad}: {e.code} {_reden(e)}", e.code) from None
            except urllib.error.URLError as e:
                raise AnsFout(f"{methode} {pad}: ANS niet bereikbaar ({e.reason})") from None
            return (json.loads(inhoud) if inhoud.strip() else None), headers
        raise AssertionError("onbereikbaar")

    def upload(self, put_url, data):
        """PUT data naar een put_url van ANS. Die is zelf ondertekend en wijst
        naar de object store, niet naar de API: het token gaat dus niet mee."""
        req = urllib.request.Request(put_url, data=data, method="PUT")
        req.add_header("Content-Type", "application/zip")
        try:
            with self._openen(req) as antwoord:
                antwoord.read()
        except urllib.error.HTTPError as e:
            raise AnsFout(f"upload naar de object store: {e.code} {_reden(e)}", e.code) from None
        except urllib.error.URLError as e:
            raise AnsFout(f"upload naar de object store: niet bereikbaar ({e.reason})") from None

    def haal(self, pad, **params):
        return self.vraag("GET", pad, params or None)[0]

    def alles(self, pad, **params):
        """Elke pagina van een lijst, als een lijst."""
        uit, pagina = [], 1
        while True:
            deel, headers = self.vraag("GET", pad, {**params, "limit": 100, "page": pagina})
            uit.extend(deel or [])
            totaal = int(_header(headers, "Total-Pages") or 1)
            if pagina >= totaal:
                return uit
            pagina += 1


def _header(headers, naam):
    for sleutel, waarde in headers.items():
        if sleutel.lower() == naam.lower():
            return waarde
    return None


def _reden(e):
    """De foutboodschap van ANS, kort. Een 422 zegt welk veld niet deugt."""
    try:
        tekst = e.read().decode("utf-8", "replace").strip()
    except Exception:
        tekst = ""
    return (tekst[:300] or e.reason or "").replace("\n", " ")
