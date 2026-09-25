"""Wat meer dan een regel nodig heeft: de regexen en lezers die ze delen.

Geen Regel in deze module; de runner importeert ze mee en vindt er niets. Alles
hier gebruikt alleen de standaardbibliotheek, net als de rest van de check.
"""

import json
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

COMMENTAAR_RE = re.compile(r"<!--(.*?)-->", re.S)
TAGS_RE = re.compile(r"<[^>]+>")
LEAD_RE = re.compile('<p class="[^"]*lead[^"]*"')

# Een opdracht die bewust geen verslagsjabloon heeft, zegt dat zelf, in een
# <!-- geen-verslag: reden --> op de pagina. De reden hoort daar en niet in een
# lijst in de check, anders verhuist ze weg van de pagina waar ze geldt.
GEEN_VERSLAG_RE = re.compile(r"<!--\s*geen-verslag[\s:]")

_DOCUMENT_EXTS = ("pdf", "zip", "docx?", "pptx?", "xlsx?")


def document_re(ctx):
    """Welke link een document is en geen pagina: vast plus check.remote_document_exts_extra."""
    extra = [re.escape(e.lstrip(".")) for e in ctx.config["check"]["remote_document_exts_extra"]]
    return re.compile(r"\.(" + "|".join(_DOCUMENT_EXTS + tuple(extra)) + r")(?:[?#]|$)", re.I)


def lokaal_doel(bron, url):
    """Het pad waar een relatieve url in bron naar wijst, of None.

    Bewust geen Path.resolve(): dat verbetert op Windows de hoofdletters naar
    wat er op schijf staat, en dan wordt de verbeterde naam gecontroleerd in
    plaats van wat er in de pagina staat. normpath werkt de '..' weg zonder de
    schijf te raadplegen.
    """
    doelpad = unquote(urlparse(url).path)
    if not doelpad:
        return None
    return Path(os.path.normpath(bron.parent / doelpad))


def onafgesloten_commentaren(tekst):
    """De regelnummers van elk <!-- dat niet afgesloten is voor het volgende begint.

    Niet de "-->" in het hele bestand tellen: gewone commentaren brengen hun
    eigen afsluiting mee. Wat telt is of dit blok afgesloten is voor het
    volgende commentaar begint. Zo niet, dan slikt de parser alles ertussen op.
    """
    uit = []
    for opening in re.finditer(r"<!--", tekst):
        i = opening.end()
        sluiting = tekst.find("-->", i)
        volgende = tekst.find("<!--", i)
        if sluiting == -1 or (volgende != -1 and volgende < sluiting):
            uit.append(tekst.count("\n", 0, opening.start()) + 1)
    return uit


def opdracht_paginas(ctx):
    """Elke Opdracht.html, ook een niveau dieper dan de modulemap.

    Meestal staat er een in de modulemap zelf (Labo/<Naam>/Opdracht.html). Een
    module met twee indienmomenten heeft er twee, elk in een eigen submap. Een
    glob op */*/Opdracht.html ziet die tweede laag niet, en dan zwijgen de
    regels stil over allebei in plaats van te klagen.
    """
    if "_opdrachten" not in ctx.__dict__:
        gezien = []
        for patroon in ("*/*/Opdracht.html", "*/*/*/Opdracht.html"):
            for pad in sorted(ctx.root.glob(patroon)):
                if pad not in gezien and not ctx.overgeslagen(pad):
                    gezien.append(pad)
        ctx._opdrachten = gezien
    return ctx._opdrachten


def overview_paginas(ctx):
    return [p for p in sorted(ctx.root.glob("*/*/overview.html")) if not ctx.overgeslagen(p)]


def orion_doelen(ctx):
    """(doelen, fout): elk topic in orion.json dat naar de repo wijst, als (soort, pad).

    Een dropbox wijst naar niets in de repo en telt dus niet mee. Het bestand
    wordt een keer gelezen; alleen orion-targets meldt een kapot bestand, zodat
    het maar een keer in de uitvoer staat.
    """
    if "_orion" in ctx.__dict__:
        return ctx._orion
    doelen, fout = [], None
    try:
        doc = json.loads((ctx.root / "orion.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        fout = "ontbreekt, dus OrionSync maakt geen enkel topic"
        doc = {}
    except json.JSONDecodeError as e:
        fout = f"geen geldige JSON: {e}"
        doc = {}

    def loop(item):
        for kind in item.get("items", []):
            loop(kind)
        for soort in ("page", "file"):
            if isinstance(item.get(soort), str):
                doelen.append((soort, item[soort]))

    for module in doc.get("modules", []):
        loop(module)
    ctx._orion = (doelen, fout)
    return ctx._orion


def heeft_orion(ctx):
    return True if (ctx.root / "orion.json").is_file() else "geen orion.json"


def syllabus_paginas(ctx):
    bron = ctx.vak.pad("syllabus_src")
    if not bron.is_dir():
        return []
    return sorted(p for p in bron.rglob("*.html") if not ctx.overgeslagen(p))


def heeft_syllabus(ctx):
    if syllabus_paginas(ctx):
        return True
    return f"geen html onder {ctx.config['paths']['syllabus_src']}"


def heeft_opdracht(ctx):
    return True if opdracht_paginas(ctx) else "geen Opdracht.html"


# ------------------------------------------------ vragenlijsten

def lijstitems(fragment, tag):
    """De <li> op het eerste niveau van de eerste <tag>, als (openingstag, inhoud).

    Dezelfde telling als in de syllabusexport, en om dezelfde reden: de
    mogelijkheden van een meerkeuzevraag zijn zelf <li>'s binnen het item, dus
    een reguliere expressie alleen komt er niet uit. De check heeft haar eigen
    kopie omdat ze op een kale checkout draait, zonder pypdf en zonder Chrome.
    """
    opening = re.search(rf"<{tag}\b[^>]*>", fragment)
    if not opening:
        return []
    rest = fragment[opening.end():]
    items = []
    lijstdiepte = lidiepte = 0
    start = tagtekst = None
    for m in re.finditer(r"<(/?)(ul|ol|li)\b[^>]*>", rest):
        sluit, naam = m.group(1) == "/", m.group(2)
        if naam == "li":
            if sluit:
                if lidiepte == 1 and lijstdiepte == 0 and start is not None:
                    items.append((tagtekst, rest[start:m.start()]))
                    start = None
                lidiepte = max(0, lidiepte - 1)
            else:
                lidiepte += 1
                if lidiepte == 1 and lijstdiepte == 0:
                    start, tagtekst = m.end(), m.group(0)
        elif sluit:
            if lijstdiepte == 0:
                break
            lijstdiepte -= 1
        else:
            lijstdiepte += 1
    return items


def top_lijsten(fragment):
    """De <ol class="vragen">'s op het eerste niveau, als (begin, items, gedeclareerd, verwacht).

    Een Test jezelf is in de Word een doorlopende genummerde lijst, maar een
    tussenzin of een tabel ertussen splitst hem in HTML in meerdere <ol>'s. Het
    start-attribuut houdt de nummering dan aan, en hier worden ze weer aan
    elkaar geregen. Zonder dat leest alleen de eerste <ol> mee: de vragen
    daarna raken hun antwoord kwijt zonder dat er iets aan te zien is.

    De klasse zegt wat een vragenlijst is: een theoriepagina somt ook genummerd
    op, en de studievragen vooraan een hoofdstuk zijn een <ol> in een info-box.
    Zonder start telt begin hier door (verwacht), zodat de vraagnummers in een
    melding kloppen met wat de export zou drukken.
    """
    uit = []
    diepte = 0
    volgende = 1
    for m in re.finditer(r"<(/?)(ul|ol)\b([^>]*)>", fragment):
        if m.group(1) == "/":
            diepte = max(0, diepte - 1)
            continue
        if (diepte == 0 and m.group(2) == "ol"
                and re.search(r'class="[^"]*\bvragen\b', m.group(3))):
            gedeclareerd = re.search(r'start="(\d+)"', m.group(3))
            begin = int(gedeclareerd.group(1)) if gedeclareerd else volgende
            items = lijstitems(fragment[m.start():], "ol")
            uit.append((begin, items, gedeclareerd is not None, volgende))
            volgende = begin + len(items)
        diepte += 1
    return uit


def vragen(fragment):
    """(nummer, openingstag, inhoud) per vraag, over alle <ol>'s van de pagina heen."""
    return [(begin + i, tag, inhoud)
            for begin, items, _, _ in top_lijsten(fragment)
            for i, (tag, inhoud) in enumerate(items)]


def vragen_paginas(ctx):
    """(pagina, tekst) voor elke pagina met een vragenlijst, in de syllabus en daarbuiten.

    Een labo-zelftest (Labo/<Naam>/Theorie/TestJezelf.html) is dezelfde soort
    vragenlijst als een syllabuspagina, en main.js bouwt er het antwoord uit
    op de site. Een vraag zonder li.juist krijgt daar stil geen antwoord.

    De tekst is zonder commentaar: in het verslagblok van een Opdracht.html
    betekent class="vragen" een vraag die de student in de docx beantwoordt,
    en daar hoort geen antwoord bij (zie verslag-markup).
    """
    if "_vragen" not in ctx.__dict__:
        uit = []
        for pad in sorted(set(ctx.paginas) | set(syllabus_paginas(ctx))):
            tekst = COMMENTAAR_RE.sub("", ctx.tekst(pad))
            if top_lijsten(tekst):
                uit.append((pad, tekst))
        ctx._vragen = uit
    return ctx._vragen


def heeft_vragen(ctx):
    return True if vragen_paginas(ctx) else 'geen <ol class="vragen">'
