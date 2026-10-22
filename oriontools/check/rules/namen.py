"""Namen die de student leest: de titel van een oefening, en hoe een opdracht, een test en een QR-code heten."""

import json
import re

from ..regel import Regel
from ._gedeeld import heeft_orion


def naam_re(ctx):
    woorden = "|".join(re.escape(w) for w in ctx.config["check"]["exercise_title_words"])
    return r"(gevorderde|basis|extra|bonus|laatste)?\s*(" + woorden + r")\s*[0-9]"


class OefeningNaam(Regel):
    """Een oefening heet naar wat de student bouwt, niet "Gevorderde oefening 2".

    Een nummer zegt de student niets over wat hij gaat maken, leest als een
    plaatshouder, en betekent niets meer zodra de volgorde verandert. Een label
    zonder nummer ("Begeleide oefening") mag: dat beschrijft de vorm, geen
    plaats in een rij. "deel 1" mag ook, dat noemt een stuk van een taak die al
    een naam heeft.

    Nagekeken: de titels in orion.json (het menu dat de student leest) en de
    <h1> en <title> van elke pagina. Welke woorden een nummer niet mogen
    dragen, zegt check.exercise_title_words (IR voegde "opdracht" toe).
    """

    id = "exercise-name"
    legacy = ("MC:6", "IR:6")

    def van_toepassing(self, ctx):
        if not ctx.config["check"]["exercise_title_words"]:
            return "geen exercise_title_words"
        return True

    def controleer(self, ctx):
        naam = naam_re(ctx)
        titel_re = re.compile(r'"title":\s*"[^"]*' + naam, re.I)
        kop_re = re.compile(r"<(h1|title)>[^<]*" + naam, re.I)
        if heeft_orion(ctx) is True:
            tekst = (ctx.root / "orion.json").read_text(encoding="utf-8")
            for nr, regel in enumerate(tekst.split("\n"), 1):
                if titel_re.search(regel):
                    ctx.fout("orion.json", "generieke titel, noem de oefening naar wat de "
                                           f"student bouwt: {regel.strip()}", regelnr=nr)
        for pad in ctx.paginas:
            for nr, regel in enumerate(ctx.tekst(pad).split("\n"), 1):
                if kop_re.search(regel):
                    ctx.fout(pad, "generieke titel in <h1> of <title>, zeg wat de oefening "
                                  f"bouwt: {regel.strip()}", regelnr=nr)


WOORDEN = {"ungraded": "Verslag", "test": "Test labo"}


def _vorm_re(woorden):
    """De vorm van een naam: een van de drie eerste woorden, de rest, en eventueel (!)."""
    keuze = "|".join(re.escape(w) for w in sorted(
        ("Opdracht", woorden["ungraded"], woorden["test"]), key=len, reverse=True))
    return re.compile(r"^(?P<soort>" + keuze + r") (?P<rest>.+?)(?P<score> \(!\))?$")


def _reeks(rest, namen, vanaf=0):
    """De names waaruit rest bestaat, aan elkaar gezet met " en " in menuvolgorde, of None."""
    for i in range(vanaf, len(namen)):
        n = namen[i]
        if rest == n:
            return [n]
        if rest.startswith(n + " en "):
            verder = _reeks(rest[len(n) + 4:], namen, i + 1)
            if verder:
                return [n] + verder
    return None


def ontleed(tekst, naam, namen, woorden=WOORDEN):
    """(soort, deel) van de naam van een dropbox of cijferitem, of (None, wat er niet klopt).

    naam is de "name" van de dichtstbijzijnde module erboven, namen elke name
    in het menu, in volgorde, woorden het eerste woord zonder score en dat van
    een test (check.names). soort is "opdracht", "verslag" of "test", ook als
    de cursus die anders noemt; deel is wat na de dubbelpunt komt, of None.
    """
    zonder, test = woorden["ungraded"], woorden["test"]
    if naam is None:
        return None, ('staat in een module zonder "name"; geef de module erboven de naam '
                      'waar haar opdrachten naar heten')
    m = _vorm_re(woorden).match(tekst)
    if not m:
        return None, f'begint niet met "Opdracht", "{zonder}" of "{test}"'
    soort, rest, score = m.group("soort"), m.group("rest"), bool(m.group("score"))
    if soort == test:
        reeks = _reeks(rest, namen)
        if not reeks or naam not in reeks:
            return None, (f'na "{test}" komen de names van de getoetste modules, met " en " '
                          f'ertussen, in de volgorde van het menu en met "{naam}" erbij')
        if not score:
            return None, f'een test telt mee: "{test} {rest} (!)"'
        return "test", None
    deel = None
    if rest != naam:
        if not rest.startswith(naam + ": "):
            return None, f'na "{soort}" komt "{naam}", de "name" van de module erboven'
        deel = rest[len(naam) + 2:]
        if not deel.strip() or deel != deel.strip():
            return None, "het deel na de dubbelpunt is leeg of begint of eindigt met een spatie"
        if "(" in deel or ")" in deel:
            return None, ('het deel draagt geen haakjes ("deel 2", niet "(deel 2)"): het enige '
                          "haakje in een naam is (!)")
        if not (deel[0].isupper() or deel[0].isdigit()):
            return None, ('het deel begint met een hoofdletter, zoals een titel in het menu: '
                          f'"{soort} {naam}: {deel[0].upper()}{deel[1:]}"')
    if soort == "Opdracht" and not score:
        return None, f'een opdracht zonder (!) telt niet mee en heet "{zonder} {rest}"'
    if soort == zonder and score:
        return None, (f'"{zonder}" telt niet mee; met een score heet het '
                      f'"Opdracht {rest} (!)"')
    return ("opdracht" if soort == "Opdracht" else "verslag"), deel


def qr_titel(soort, deel):
    """De enige juiste titel van een qr-topic, uit wat het scoort."""
    if soort == "test":
        return "QR code: test"
    return f"QR code: {deel}" if deel else "QR code"


class OrionNamen(Regel):
    """Een dropbox, een test en een QR-code heten volgens een vaste vorm, met de naam van hun module.

    Beslist op 19 oktober 2026, voor elke cursus:

        Opdracht <name>[: <deel>] (!)      een dropbox met een score
        Verslag <name>[: <deel>]           een dropbox zonder score
        Test labo <name>[ en <name>] (!)   een test, als dropbox of als cijferitem (qr.grade)
        QR code[: <deel>]                  de QR-code van een opdracht, met het deel van haar dropbox
        QR code: test                      de QR-code van een test

    <name> is het veld "name" van de dichtstbijzijnde module erboven in
    orion.json, niet haar titel: een titel als "Labo: Assemblage + BIOS/UEFI"
    of "Robot: tool" is gemaakt voor het menu, de naam moet ook in een
    cijferlijst passen. Met dat veld heeft elke dropbox precies een juiste naam
    en rekent de regel die uit, in plaats van een patroon te raden. Een
    submodule met een eigen name (een tweede labo binnen een labo) geeft die
    aan alles eronder.

    Het eerste woord zegt wat het is, (!) zegt dat het meetelt, en die twee
    moeten overeenkomen: een Opdracht heeft (!), een Verslag niet. Een test
    noemt de modules die hij toetst in de volgorde van het menu, en de module
    waar hij staat is er een van. Een deel draagt geen haakjes ("deel 2", niet
    "(deel 2)"), zodat het enige haakje in een naam het (!) is.

    Een deel begint met een hoofdletter of een cijfer (beslist op 22 oktober
    2026), zoals elke titel in het menu: het is meestal de titel van de
    opdrachtpagina erboven. De regel kan dat nakijken zonder woordenlijst; een
    kleine letter zou een lijst eigennamen per cursus vragen (Physics, Packet
    Tracer), en dan raadt de regel weer.

    Twee woorden zijn per cursus in te stellen in check.names, omdat ze zeggen
    wat de student inlevert (beslist op 22 oktober 2026): "ungraded" voor een
    dropbox zonder score (standaard "Verslag"; IR levert een RobotStudio-backup
    in en zegt "Oefening") en "test" (standaard "Test labo"; IR zegt "Test", en
    zijn testmodules heten "1" en "2", zodat "Test 1 (!)" uitkomt). De vorm
    blijft voor elke cursus dezelfde en de regel rekent nog altijd een naam uit.

    Een QR-code heet naar het deel van wat ze scoort, letterlijk, zodat de
    student bij twee codes in een module ziet welke bij welke opdracht hoort.

    Of de dropbox echt een cijferitem heeft en dat cijferitem dezelfde naam
    draagt, weet alleen Orion: dat controleert de sync (src/gradenames.js in
    OrionSync). Een cijferitem dat orion.json niet noemt, ziet deze regel niet.
    """

    id = "orion-names"

    def van_toepassing(self, ctx):
        return heeft_orion(ctx)

    def controleer(self, ctx):
        tekst = (ctx.root / "orion.json").read_text(encoding="utf-8")
        try:
            doc = json.loads(tekst)
        except ValueError:
            return  # orion-targets meldt een kapot bestand
        if not isinstance(doc, dict) or not isinstance(doc.get("modules"), list):
            return
        regels = tekst.split("\n")

        def regelnr(waarde):
            zoek = json.dumps(waarde, ensure_ascii=False)
            return next((nr for nr, r in enumerate(regels, 1) if zoek in r), None)

        namen, topics = [], []

        def loop(item, naam):
            if not isinstance(item, dict):
                return
            if not isinstance(item.get("items"), list):
                topics.append((item, naam))
                return
            eigen = item.get("name")
            if eigen is not None:
                if (not isinstance(eigen, str) or not eigen.strip() or eigen != eigen.strip()
                        or any(t in eigen for t in ":()")):
                    ctx.fout("orion.json", f"module '{item.get('id')}': \"name\" moet een tekst "
                                           "zijn zonder dubbelpunt of haakjes",
                             regelnr=regelnr(item.get("id")))
                else:
                    naam = eigen
                    if eigen not in namen:
                        namen.append(eigen)
            for kind in item["items"]:
                loop(kind, naam)

        for module in doc["modules"]:
            loop(module, None)

        woorden = ctx.config["check"]["names"]
        gekozen = ["Opdracht", woorden["ungraded"], woorden["test"]]
        if any(not w.strip() or w != w.strip() or "(" in w or ":" in w for w in gekozen) \
                or len(set(gekozen)) < 3:
            ctx.fout("oriontools.json", 'check.names: "ungraded" en "test" zijn twee '
                                        'verschillende woorden, geen "Opdracht", zonder '
                                        "dubbelpunt of haakjes")
            return

        dropboxen = {}
        for t, naam in topics:
            d = t.get("dropbox")
            if not isinstance(d, str):
                continue
            soort, deel = ontleed(d, naam, namen, woorden)
            if soort is None:
                ctx.fout("orion.json", f'dropbox "{d}": {deel}', regelnr=regelnr(d))
            else:
                dropboxen[d] = (soort, deel)

        for t, naam in topics:
            qr = t.get("qr")
            if not isinstance(qr, dict):
                continue  # orion-qr meldt de vorm
            waar = f"qr-topic '{t.get('id')}'"
            if isinstance(qr.get("dropbox"), str):
                gescoord = dropboxen.get(qr["dropbox"])
                if gescoord is None:
                    continue  # de dropbox is hierboven of door orion-qr al gemeld
            elif isinstance(qr.get("grade"), str):
                soort, deel = ontleed(qr["grade"], naam, namen, woorden)
                if soort is None:
                    ctx.fout("orion.json", f'{waar}: cijferitem "{qr["grade"]}": {deel}',
                             regelnr=regelnr(qr["grade"]))
                    continue
                if soort == "verslag":
                    ctx.fout("orion.json", f'{waar}: cijferitem "{qr["grade"]}" is een '
                                           f'{woorden["ungraded"].lower()}, en die krijgt geen score',
                             regelnr=regelnr(qr["grade"]))
                    continue
                gescoord = (soort, deel)
            else:
                continue
            verwacht = qr_titel(*gescoord)
            if t.get("title") != verwacht:
                ctx.fout("orion.json", f'{waar} heet "{t.get("title")}", hoort "{verwacht}"',
                         regelnr=regelnr(t.get("id")))
