"""Wat er in ANS staat tegenover het vak: verouderde items en theorie zonder vraag.

    python ../OrionTools/orion.py ans-dekking

Enkel lezen: het schrijft niets, in ANS noch in het vak.

WELKE PAGINA'S IN ANS STAAN
---------------------------
Elke pagina met een <ol class="vragen">, ook in paths.toets, maar niet in de
andere staging-mappen. Een pagina staat in ANS wanneer er een vragenbank is
met haar pakketnaam als external_id, de sleutel waarop ans-push haar bank
vindt. Een pagina zonder bank wordt enkel genoemd.

VEROUDERD
---------
Voor een pagina in ANS is dit ans-push --droog: nieuw, gewijzigd en verweesd,
met plan() uit push.py. De hash van een item hangt af van --feedback en
--niet-schudden, en ANS onthoudt niet met welke vlaggen er gepusht is. Daarom
bouwt dit het pakket in elk van de vier combinaties en neemt het die waarin de
meeste items kloppen, bij gelijkstand die zonder vlaggen. Het drukt af welke
het vond: push de pagina daarna met dezelfde, anders geldt elke vraag als
gewijzigd.

DEKKING
-------
ans.dekking in oriontools.json zegt over welke pagina's een vraag in ANS hoort
te staan (DeN: de theorie van de labo's). Een vragenpagina telt daar nooit bij.
Een pagina is gedekt wanneer een item in een bank ernaar wijst, op een van twee
manieren:
- data-bron op de <li> van de vraag, voor een toets in paths.toets (zie
  export-qti, dat een pad weigert dat niet bestaat);
- een link in de <div class="oplossing">, de "Zie ..." van een Test jezelf.
Alleen een vraag die als item in de bank staat, telt: dekking is wat een toets
in ANS kan trekken, niet wat op een pagina staat. Een Test jezelf die niet
gepusht is, dekt dus niets. Een verouderd item telt wel: het staat erin, alleen
in een oudere versie.

Dat de link in de oplossing telt, terwijl de oplossing zelf niet in ANS
aankomt (zie export-qti, IN ANS NAGEKEKEN): de link zegt waarover de vraag
gaat, en dat blijft waar, ook zonder de uitleg erbij.

DOELSTELLINGEN
--------------
Wat een toets moet nagaan, is een doelstelling; een pagina is daar maar een
benadering van. Een gedekte pagina zegt niet dat elke doelstelling een vraag
heeft, en een doelstelling die geen pagina uitlegt, valt in het rapport per
pagina helemaal weg. Daarom volgt er een rapport per doelstelling.

ans.doelstellingen zegt op welke pagina's ze staan (DeN: de overview.html van
elk labo): de <li>'s van de eerste <ol> onder <h2 id="doelstellingen">. Zo'n
<li> noemt met data-bron de theoriepagina's die haar uitleggen, paden vanaf
de root zoals bij een vraag; de check-regel data-bron houdt ze juist. Per
doelstelling meldt dit:
- geen theorie: ze heeft geen data-bron, dus geen pagina legt ze uit;
- theorie, geen vraag in ANS: geen van haar pagina's is gedekt;
- gedekt: minstens een van haar pagina's is dat, zoals hierboven.

Een praktische doelstelling (een bus opbouwen, een Arduino programmeren) staat
er evengoed in: er is geen markering om er een uit te sluiten. Zo'n markering
verbergt precies de doelstelling die uitleg mist. De zendrichting omschakelen
met RE en DE in labo RS485 is praktisch, en had in september 2026 geen theorie.
"""

import argparse
import html
import re
import sys
from fnmatch import fnmatch
from urllib.parse import unquote, urlparse

from .. import repo
from ..check.rules._gedeeld import (BRON_RE, COMMENTAAR_RE, TAGS_RE, doelstellingen,
                                    top_lijsten, vragen)
from ..export import qti
from . import push
from .client import AnsFout, Client

# (schudden, feedback); de standaard van ans-push eerst, want die wint bij gelijkstand.
VLAGGEN = [(True, False), (False, False), (True, True), (False, True)]
HREF_RE = re.compile(r'<a\b[^>]*\bhref="([^"]+)"')
GEEN_THEORIE, GEEN_VRAAG, GEDEKT = "geen theorie", "theorie, geen vraag in ANS", "gedekt"


def html_van(vak, met_toets):
    """(pad, rel) van elke html in het vak, buiten .git en de staging; paths.toets als met_toets."""
    staging = set(vak.config["staging"])
    toets = vak.pad("toets")
    for pad in sorted(vak.root.rglob("*.html")):
        delen = pad.relative_to(vak.root).parts
        if ".git" in delen or "node_modules" in delen:
            continue
        if staging.intersection(delen) and not (met_toets and toets in pad.parents):
            continue
        yield pad, pad.relative_to(vak.root).as_posix()


def vragenpaginas(vak):
    uit = []
    for pad, rel in html_van(vak, met_toets=True):
        tekst = pad.read_text(encoding="utf-8")
        if top_lijsten(COMMENTAAR_RE.sub("", tekst)):
            uit.append((pad, rel, tekst))
    return uit


def te_dekken(vak, eigen):
    """De pagina's uit ans.dekking, zonder de vragenpagina's (eigen)."""
    patronen = vak.config["ans"]["dekking"]
    return [rel for _, rel in html_van(vak, met_toets=False)
            if rel not in eigen and any(fnmatch(rel, p) for p in patronen)]


def verwijzingen(pagina, tekst, root):
    """{vraagnummer: {pad}}: waarover elke vraag gaat, uit data-bron en de links in haar oplossing."""
    uit = {n: set(paden) for n, paden in qti.bronnen(tekst).items()}
    for nummer, _, inhoud in vragen(COMMENTAAR_RE.sub("", tekst)):
        for oplossing in qti.OPLOSSING_RE.findall(inhoud):
            for href in HREF_RE.findall(oplossing):
                deel = urlparse(html.unescape(href))
                if deel.scheme or deel.netloc or not deel.path or deel.path.startswith("/"):
                    continue
                doel = (pagina.parent / unquote(deel.path)).resolve()
                try:
                    uit.setdefault(nummer, set()).add(doel.relative_to(root).as_posix())
                except ValueError:
                    pass  # buiten het vak
    return uit


def kort(inhoud, lengte=60):
    """De tekst van een <li> op een regel, afgebroken op een woord."""
    tekst = " ".join(html.unescape(TAGS_RE.sub("", inhoud)).split())
    if len(tekst) <= lengte:
        return tekst
    return tekst[:lengte].rsplit(" ", 1)[0] + " ..."


def per_doelstelling(tekst, gedekt):
    """(nummer, stand, korte tekst) per doelstelling op een pagina; gedekt is {pad: ...}."""
    uit = []
    for nummer, tag, inhoud in doelstellingen(COMMENTAAR_RE.sub("", tekst)):
        m = BRON_RE.search(tag)
        paden = [html.unescape(p) for p in m.group(1).split()] if m else []
        if not paden:
            stand = GEEN_THEORIE
        elif any(p in gedekt for p in paden):
            stand = GEDEKT
        else:
            stand = GEEN_VRAAG
        uit.append((nummer, stand, kort(inhoud)))
    return uit


def beste(doelen, bestaande):
    """De vlaggen waarvan de meeste items kloppen met de bank; bij gelijkstand de eerste."""
    ext = {e.get("qti_identifier"): e.get("external_id") for e in bestaande}
    return max(doelen, key=lambda v: sum(ext.get(q) == w for q, w in doelen[v].items()))


def vlaggen(v):
    schudden, feedback = v
    return " ".join([*([] if schudden else ["--niet-schudden"]), *(["--feedback"] if feedback else [])]) or "geen"


def banken(client):
    """{external_id: [bank]} van elke vragenbank die niet getrasht is."""
    uit = {}
    for b in client.alles("/question_banks"):
        if b.get("external_id") and not b.get("trashed"):
            uit.setdefault(b["external_id"], []).append(b)
    return uit


def verouderd(vak, pagina, rel, naam, bestaande):
    """De regels over een pagina in ANS: wat een push zou doen, en met welke vlaggen."""
    try:
        doelen = {v: push.doel_van(qti.bouw(pagina, vak.root, f"{vak.code}-{naam}", *v)[0], rel)
                  for v in VLAGGEN}
    except qti.Fout as e:
        return ["  het pakket bouwt niet, dus niets te vergelijken:",
                *(f"    {r}" for r in str(e).splitlines())]
    v = beste(doelen, bestaande)
    nieuw, gewijzigd, verweesd = push.plan(doelen[v], bestaande, qti.identifier(f"{vak.code}-{naam}"))
    regel = (f"  vlaggen: {vlaggen(v)}; {len(nieuw)} nieuw, {len(gewijzigd)} gewijzigd, "
             f"{len(doelen[v]) - len(nieuw) - len(gewijzigd)} ongewijzigd")
    uit = [regel]
    if gewijzigd:
        uit.append("  gewijzigd: vraag " + ", ".join(str(push.nummer(e["qti_identifier"])) for e in gewijzigd))
    if nieuw:
        uit.append("  nieuw: vraag " + ", ".join(str(push.nummer(q)) for q in nieuw))
    uit += [f"  verweesd: item {e['id']} ({e['name']}) staat niet meer op de pagina" for e in verweesd]
    return uit


def main(argv=None):
    parser = argparse.ArgumentParser(prog="orion.py ans-dekking", description=__doc__.split("\n")[0])
    repo.voeg_repo_toe(parser)
    args = parser.parse_args(argv)
    vak = repo.vind(args)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    paginas = vragenpaginas(vak)
    try:
        client = Client()
        per_ext = banken(client)
    except AnsFout as e:
        sys.exit(f"ans-dekking: {e}")

    gedekt, niet_in_ans = {}, []
    print("In ANS")
    for pagina, rel, tekst in paginas:
        naam = qti.naam_van(pagina, vak.root, vak.pad("toets"))
        pakket = qti.identifier(f"{vak.code}-{naam}")
        gevonden = per_ext.get(pakket, [])
        if not gevonden:
            niet_in_ans.append(rel)
            continue
        if len(gevonden) > 1:
            print(f"{rel}: {len(gevonden)} vragenbanken met external_id {pakket} ("
                  + ", ".join(str(b["id"]) for b in gevonden) + "); zet er een op trashed")
            continue
        bank = gevonden[0]
        try:
            bestaande = push.oefeningen(client, bank["id"])
        except AnsFout as e:
            sys.exit(f"ans-dekking: {e}")
        print(f"{rel}: bank {bank['id']} {bank['name']}, {len(bestaande)} items")
        for r in verouderd(vak, pagina, rel, naam, bestaande):
            print(r)
        in_bank = {e.get("qti_identifier") for e in bestaande}
        for nummer, paden in verwijzingen(pagina, tekst, vak.root).items():
            if f"{pakket}-{nummer:02d}" in in_bank:
                for p in paden:
                    gedekt.setdefault(p, []).append(f"{rel} vraag {nummer}")

    if niet_in_ans:
        print(f"\nNiet in ANS: {len(niet_in_ans)} vragenpagina's")
        for rel in niet_in_ans:
            print(f"  {rel}")

    if not vak.config["ans"]["dekking"]:
        print("\nDekking: ans.dekking is leeg in oriontools.json")
    else:
        doel = te_dekken(vak, {rel for _, rel, _ in paginas})
        zonder = [rel for rel in doel if rel not in gedekt]
        print(f"\nDekking: {len(doel) - len(zonder)} van {len(doel)} pagina's uit ans.dekking "
              "hebben een vraag in ANS")
        for rel in zonder:
            print(f"  zonder vraag: {rel}")

    patronen = vak.config["ans"]["doelstellingen"]
    if not patronen:
        return 0
    rapport = [(rel, per_doelstelling(pad.read_text(encoding="utf-8"), gedekt))
               for pad, rel in html_van(vak, met_toets=False)
               if any(fnmatch(rel, p) for p in patronen)]
    alle = [stand for _, rijen in rapport for _, stand, _ in rijen]
    print(f"\nDoelstellingen: {alle.count(GEDEKT)} van {len(alle)} hebben een vraag in ANS, "
          f"{alle.count(GEEN_THEORIE)} hebben geen theorie")
    for rel, rijen in rapport:
        if not rijen:
            print(f'{rel}: geen <ol> onder <h2 id="doelstellingen">')
            continue
        print(rel)
        for nummer, stand, tekst in rijen:
            print(f"  {nummer} {stand}: {tekst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
