"""Maak de toets van een labo aan in ANS, met de instellingen uit oriontools.json.

    python ../OrionTools/orion.py ans-toets Labo/RS485
    python ../OrionTools/orion.py ans-toets Labo/RS485 --droog

EEN TOETS PER MAP
-----------------
Evaluatie.html van DeN geeft elk labo een eigen test, dus een toets hoort bij
een map van het vak. Hij wordt gevonden op zijn external_id in ans.course_id:
de map met streepjes en -Toets (DeN-Labo-RS485-Toets), zoals ans-push een bank
vindt op haar pakketnaam. Er staat dus geen toets-id in oriontools.json. De
naam bij het aanmaken komt uit orion.json: het deel van het menupad dat elke
pagina van de map deelt ("DEN - Labo: RS485 - Toets"). De naam mag je in ANS
wijzigen, de external_id niet, want dan maakt de volgende run een tweede toets.

DE INSTELLINGEN ZIJN DIE VAN ANS
--------------------------------
ans.toets in oriontools.json neemt de velden van de API zonder vertaling over:
assignment_type en summative, de objecten accessibility_settings en
grades_settings, en cover, dat naar /assignments/{id}/cover gaat. Wat een veld
doet, staat in de swagger van ANS; een eigen naam ertussen zou elk veld twee
keer documenteren. Een veld dat niet in de config staat, stuurt dit commando
niet mee: dan geldt de instelling van de school, of wat er in ANS al staat. Een
tikfout in een veldnaam weigert ANS met een 422, want de API aanvaardt geen
onbekende velden.

Datums staan er niet in, en de API aanvaardt ze ook niet in een assignment:
wanneer een toets open staat, loopt via timeslots en publication, en dat
beslist de docent per zittijd, niet de config.

EEN TWEEDE RUN ZET DE CONFIG TERUG
----------------------------------
oriontools.json is de bron. Bestaat de toets al, dan vergelijkt dit commando
elk veld uit de config met wat ANS teruggeeft, en zet het wat verschilt.
Een veld dat je in ANS met de hand wijzigt en dat in de config staat, keert
dus terug; een veld buiten de config blijft zoals het in ANS staat. --droog
toont het verschil per veld en schrijft niets.

Een object als grades_settings gaat bij een PATCH volledig mee: wat ANS al
had, met de velden uit de config erover. De swagger zegt niet of een PATCH
met een deel van het object de rest laat staan of wist, en zo maakt dat niet
uit.

ANS geeft een getal soms als tekst terug (passed_grade "9.99",
grade_lower_limit "0.0"), terwijl de POST een getal aanvaardt. gelijk()
vergelijkt daarom op waarde, niet op type.

Een PATCH per record en per run: een voor de toets, een voor de cover. Dat
blijft onder de vijf wijzigingen per minuut die ANS toelaat.
"""

import argparse
import json
import os
import sys
from pathlib import Path

from .. import repo
from ..export import qti
from .client import AnsFout, Client
from .push import menupad

OBJECTEN = ("accessibility_settings", "grades_settings")
VELDEN = ("assignment_type", "summative")


def toets_id(vak, rel):
    return qti.identifier(f"{vak.code}-{rel.replace('/', '-')}-Toets")


def pagina_menupaden(root, rel):
    """Het menupad van elke pagina van orion.json onder de map rel."""
    try:
        doc = json.loads((root / "orion.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    paginas = []

    def loop(items):
        for item in items:
            pagina = item.get("page") or ""
            if pagina.startswith(rel + "/"):
                paginas.append(pagina)
            loop(item.get("items", []))

    loop(doc.get("modules", []))
    return [p for p in (menupad(root, pagina) for pagina in paginas) if p]


def toetsnaam(vak, rel):
    paden = pagina_menupaden(vak.root, rel)
    gedeeld = list(Path(rel).parts)
    if paden:
        gedeeld = os.path.commonprefix(paden) or gedeeld
    return " - ".join([vak.code.upper(), *gedeeld, "Toets"])


def gelijk(a, b):
    """Dezelfde waarde, ook als ANS een getal als tekst teruggeeft."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b  # in Python is True == 1
    if a == b:
        return True
    if a is None or b is None:
        return False
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return False


def verschil(gewenst, huidig):
    """[(veld, huidig, gewenst)] voor elk veld van gewenst dat anders is.

    Een veld met _ vooraan is commentaar, zoals elders in oriontools.json.
    config.py slaat het over in een tabel met vaste sleutels, maar niet in een
    vrije zoals cover, en ANS weigert elk veld dat het niet kent.
    """
    return [(k, huidig.get(k), v) for k, v in gewenst.items()
            if not k.startswith("_") and not gelijk(v, huidig.get(k))]


def plan(cfg, toets, cover):
    """Wat een run verandert: (toets-body, cover-body, regels).

    toets en cover zijn wat ANS teruggeeft, of {} voor een toets die nog niet
    bestaat; dan is alles uit de config een verandering. Een body is None als
    er niets te veranderen valt, en de toets-body draagt geen name. regels zegt
    per veld wat er verandert, voor --droog en voor de uitvoer.
    """
    regels = []
    body = {}
    for k in VELDEN:
        if cfg.get(k) is not None and not gelijk(cfg[k], toets.get(k)):
            regels.append((k, toets.get(k), cfg[k]))
            body[k] = cfg[k]
    for k in OBJECTEN:
        huidig = toets.get(k) or {}
        anders = verschil(cfg.get(k) or {}, huidig)
        if anders:
            regels += [(f"{k}.{veld}", oud, nieuw) for veld, oud, nieuw in anders]
            body[k] = {**huidig, **{veld: v for veld, v in cfg[k].items() if not veld.startswith("_")}}
    cover_anders = verschil(cfg.get("cover") or {}, cover or {})
    regels += [(f"cover.{veld}", oud, nieuw) for veld, oud, nieuw in cover_anders]
    cover_body = {veld: nieuw for veld, _, nieuw in cover_anders} or None
    return body or None, cover_body, regels


def zoek_toets(client, course_id, external_id):
    toetsen = [t for t in client.alles(f"/courses/{course_id}/assignments")
               if t.get("external_id") == external_id and not t.get("trashed")]
    if len(toetsen) > 1:
        raise AnsFout(f"{len(toetsen)} toetsen met external_id {external_id}: "
                      + ", ".join(str(t["id"]) for t in toetsen) + ". Zet er een op trashed.")
    return toetsen[0] if toetsen else None


def kort(waarde, lengte=60):
    tekst = repr(waarde)
    return tekst if len(tekst) <= lengte else tekst[:lengte - 3] + "..."


def main(argv=None):
    parser = argparse.ArgumentParser(prog="orion.py ans-toets", description=__doc__.split("\n")[0])
    repo.voeg_repo_toe(parser)
    parser.add_argument("map", type=Path, help="de map van het labo, bv. Labo/RS485")
    parser.add_argument("--droog", action="store_true", help="alleen lezen en tonen wat er zou gebeuren")
    args = parser.parse_args(argv)
    vak = repo.vind(args)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ans = vak.config["ans"]
    if not ans["course_id"]:
        sys.exit("ans-toets: ans.course_id staat niet in oriontools.json (zoek hem met ans-verken)")
    cfg = ans["toets"]
    kaart = args.map if args.map.is_absolute() else (Path.cwd() / args.map)
    if not kaart.is_dir():
        kaart = vak.root / args.map
    kaart = kaart.resolve()
    if not kaart.is_dir():
        sys.exit(f"ans-toets: {args.map} is geen map")
    rel = kaart.relative_to(vak.root).as_posix()
    ext = toets_id(vak, rel)

    try:
        client = Client()
        toets = zoek_toets(client, ans["course_id"], ext)
        cover = client.haal(f"/assignments/{toets['id']}/cover") if toets else None
    except AnsFout as e:
        sys.exit(f"ans-toets: {e}")

    body, cover_body, regels = plan(cfg, toets or {}, cover or {})
    if toets:
        print(f"toets: {toets['id']} {toets['name']} ({ext})")
    else:
        naam = toetsnaam(vak, rel)
        print(f"toets: nieuw, {naam} ({ext}) in cursus {ans['course_id']}")
    if toets and not regels:
        print("  alles zoals in oriontools.json")
        return 0
    for veld, oud, nieuw in regels:
        print(f"  {veld}: {kort(oud)} -> {kort(nieuw)}")
    if args.droog:
        return 0

    try:
        if not toets:
            toets, _ = client.vraag("POST", f"/courses/{ans['course_id']}/assignments",
                                    body={"name": naam, "external_id": ext, **(body or {})})
            print(f"  toets aangemaakt: {toets['id']}")
        elif body:
            # name staat als verplicht in de swagger, ook bij een PATCH
            client.vraag("PATCH", f"/assignments/{toets['id']}", body={"name": toets["name"], **body})
        if cover_body:
            client.vraag("PATCH", f"/assignments/{toets['id']}/cover", body=cover_body)
        # Nog eens lezen: een veld dat ANS stil anders opslaat, valt zo op.
        toets = client.haal(f"/assignments/{toets['id']}")
        cover = client.haal(f"/assignments/{toets['id']}/cover")
    except AnsFout as e:
        sys.exit(f"ans-toets: {e}")
    _, _, blijft = plan(cfg, toets, cover)
    print(f"  {len(regels)} velden gezet")
    for veld, oud, nieuw in blijft:
        print(f"  let op: {veld} is na het zetten {kort(oud)}, niet {kort(nieuw)}")
    return 1 if blijft else 0


if __name__ == "__main__":
    sys.exit(main())
