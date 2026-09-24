"""Bundel de syllabuspagina's tot de PDF die de student downloadt.

    python ../OrionTools/orion.py export-syllabus
    python ../OrionTools/orion.py export-syllabus --html-only   # alleen de bundel, geen Chrome

De uitvoer is <downloads>/<syllabus.pdf uit oriontools.json>, en die is
GECOMMIT: OrionSync spiegelt alleen wat in git zit naar Brightspace. Ze is dus
afgeleid materiaal dat toch in de repo staat, net als de verslagsjablonen, en
de regel syllabus-stale van de check faalt als ze ouder is dan de pagina's
waar ze uit komt.

DE VOLGORDE KOMT UIT HET MANIFEST, niet uit de mappenlijst. Een categorie in
het manifest (syllabus.manifest, standaard reference.js) is een hoofdstuk, een
topic is een sectie, en het hoofdstuknummer volgt uit de plaats van de
categorie in die lijst. Zo staat de volgorde op een plaats, en niet ook nog in
een mappenlijst. Een categorie met genummerd: false (het Voorwoord) krijgt
geen nummer.

Het eerste topic van een hoofdstuk heet Overzicht.html en draagt de kernpunten
en de studievragen. Dat is de opening van het hoofdstuk, dus die pagina krijgt
de hoofdstuktitel als kop en telt niet als sectie: OSI model is 1.1 en niet 1.2.

HOE DE PAGINANUMMERS IN DE INHOUDSTAFEL KOMEN

Chrome kan geen inhoudstafel met paginanummers maken: CSS kent target-counter(),
Chrome niet. Vandaar dat de INHOUD eerst gedrukt wordt en pypdf daarna de tekst
van elke bladzijde terugleest om te zien waar elke kop geland is. Pas dan worden
de cover en de inhoudstafel gedrukt, met die nummers erin.

Het gedrukte nummer telt de cover en de inhoudstafel mee, zoals in de bestaande
syllabus, waar het Voorwoord op 3 staat. Het is dus ook de plaats van het blad
in het document, en wie in zijn viewer naar bladzijde 40 springt, komt uit waar
de inhoudstafel hem stuurt. De prijs is dat de nummers in de inhoudstafel
afhangen van hoe lang de inhoudstafel zelf is; die lengte hangt alleen van het
aantal regels af en niet van de nummers, dus een proefdruk volstaat om ze te
kennen. Zie de lus in main().

Cover, inhoudstafel en inhoud worden apart gedrukt en achteraf aan elkaar
geplakt, want ze hebben elk andere @page-marges. De cover zet zijn tekst op
absolute posities vanaf de bladrand en is nagemeten van de bestaande syllabus.

De kop- en voettekst worden er achteraf op gestempeld met reportlab: Chrome kan
via de commandoregel alleen zijn eigen kop- en voettekst zetten (met datum en
URL erin) en die is niet aan te passen. De Word doet het net zo als hier: het
paginanummer bovenaan, de hoofdstuktitel onderaan.
"""

import argparse
import functools
import html
import io
import json
import os
import re
import shutil
import sys
import tempfile
from collections import namedtuple
from pathlib import Path

from .. import repo
# zoek_chrome, druk_af en stempelletters blijven ook namen van deze module:
# de handout leende ze hier toen de twee nog scripts naast elkaar waren.
from ..chrome import zoek_chrome
from .pdfhulp import druk_af, stempelletters

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    sys.exit("pypdf ontbreekt:  pip install pypdf")

try:
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas
except ImportError:
    sys.exit("reportlab ontbreekt:  pip install reportlab")

# Gezet door main() uit het vak. De functies hieronder lezen ze zoals ze de
# constanten lazen toen dit script nog in de vakrepo stond.
REPO = None
MANIFEST = None        # syllabus.manifest, standaard reference.js
MODULE = "syllabus"    # syllabus.manifest_key: de sleutel erin
BRON = None            # paths.syllabus_src
UIT = None             # paths.downloads / syllabus.pdf
LOGO = None            # syllabus.logo, of None
TITEL = ""             # course.title
COVER = {}             # syllabus.cover

DOCUMENT_RE = re.compile(r"\.(pdf|zip|docx|pptx|xlsx|pka|pkt)$", re.I)

overgeslagen = []


# --------------------------------------------------------- manifest lezen

def js_literal(tekst, start):
    """Het JS-objectliteral dat op tekst[start] begint, als Python-object.

    reference.js is JavaScript en geen JSON: sleutels zonder aanhalingstekens,
    enkele aanhalingstekens, commentaar, komma's op het eind. Dit loopt teken
    per teken en weet dus wanneer het in een string zit; een regex die alleen
    de aanhalingstekens omwisselt, struikelt over elke apostrof in een blurb.
    """
    uit = []
    i, n, diepte = start, len(tekst), 0
    while i < n:
        c = tekst[i]
        if c == "/" and i + 1 < n and tekst[i + 1] == "/":
            while i < n and tekst[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and tekst[i + 1] == "*":
            eind = tekst.find("*/", i)
            i = len(tekst) if eind == -1 else eind + 2
            continue
        if c in "'\"":
            aanhaling = c
            stuk = ['"']
            i += 1
            while i < n and tekst[i] != aanhaling:
                if tekst[i] == "\\":
                    stuk.append(tekst[i:i + 2])
                    i += 2
                    continue
                stuk.append('\\"' if tekst[i] == '"' else tekst[i])
                i += 1
            stuk.append('"')
            uit.append("".join(stuk))
            i += 1
            continue
        if c in "{[":
            diepte += 1
        elif c in "}]":
            diepte -= 1
        uit.append(c)
        i += 1
        if diepte == 0 and uit and uit[-1] in "}]":
            break

    ruw = "".join(uit)
    ruw = re.sub(r"([{,]\s*)([A-Za-z_$][\w$]*)\s*:", r'\1"\2":', ruw)
    ruw = re.sub(r",(\s*[}\]])", r"\1", ruw)
    return json.loads(ruw)


def lees_module():
    tekst = MANIFEST.read_text(encoding="utf-8")
    m = re.search(rf"^    {MODULE}:\s*\{{", tekst, re.M)
    if not m:
        sys.exit(f"module '{MODULE}' staat niet in {MANIFEST.name}")
    return js_literal(tekst, m.end() - 1)


# Een sectie van het gedrukte document. soort is "pagina" voor een sectie die
# uit een bronpagina komt, en "oplossingen" voor de sectie die achteraan het
# hoofdstuk uit alle vragenpagina's van dat hoofdstuk afgeleid wordt.
#
# bron is daarom een Path voor een gewone sectie, en voor de oplossingen een
# rij (sectienummer, Path): die sectie hoort bij meer dan een pagina en zet er
# per pagina een tussenkop boven, met het nummer waar de vragen staan.
Sectie = namedtuple("Sectie", "nummer vaste_titel bron tid soort")


def hoofdstukken(module):
    """(nummer of None, titel, [Sectie, ...]) per hoofdstuk."""
    uit = []
    teller = 0
    for categorie in module["categories"]:
        genummerd = categorie.get("genummerd", True)
        if genummerd:
            teller += 1
        nummer = str(teller) if genummerd else None

        secties = []
        sectieteller = 0
        for topic in categorie["topics"]:
            href = topic["href"]
            if DOCUMENT_RE.search(href):
                overgeslagen.append(f"{categorie['name']}: {href} is een document, "
                                    "dat gaat niet in de bundel")
                continue
            pad = Path(os.path.normpath(BRON / href))
            if not pad.exists():
                overgeslagen.append(f"{categorie['name']}: {href} bestaat niet")
                continue
            opening = pad.name.lower() == "overzicht.html" and not secties
            if opening and nummer:
                secties.append(Sectie(None, categorie["name"], pad,
                                      topic["id"], "pagina"))
                continue
            sectieteller += 1
            snummer = f"{nummer}.{sectieteller}" if nummer else None
            secties.append(Sectie(snummer, None, pad, topic["id"], "pagina"))

        # De oplossingen van het hele hoofdstuk staan achteraan, in een sectie.
        # Niet achter elke oefening apart: dan draagt een hoofdstuk driemaal een
        # sectie Oplossingen, en de inhoudstafel zegt driemaal hetzelfde woord
        # zonder te zeggen waarover. Zo staat er een, en staat het antwoord ook
        # niet op het blad na de vraag.
        #
        # Ook hier alles of niets: ontbreekt er ergens in het hoofdstuk een
        # antwoord, dan drukt de export voor dit hoofdstuk niets. oplossingen_uit
        # heeft dan al gezegd om welke vraag het gaat.
        vragenpaginas = [s for s in secties
                         if s.soort == "pagina" and draagt_vragen(s.bron)]
        if vragenpaginas and all(oplossingen_uit(s.bron) for s in vragenpaginas):
            sectieteller += 1
            snummer = f"{nummer}.{sectieteller}" if nummer else None
            secties.append(Sectie(snummer, None,
                                  tuple((s.nummer, s.bron) for s in vragenpaginas),
                                  f"oplossingen-{sectie_slug(categorie['name'])}",
                                  "oplossingen"))
        if secties:
            uit.append((nummer, categorie["name"], secties))
    return uit


# ------------------------------------------------------------ pagina lezen

def container_van(pagina):
    tekst = pagina.read_text(encoding="utf-8")
    m = re.search(r'<div class="container">(.*?)\n    </div>', tekst, re.S)
    if not m:
        sys.exit(f"{pagina}: geen <div class=\"container\"> gevonden")
    return m.group(1)


def kop_en_inhoud(pagina):
    binnen = container_van(pagina)
    m = re.search(r"<h1>(.*?)</h1>", binnen, re.S)
    kop = re.sub(r"\s+", " ", m.group(1)).strip() if m else pagina.stem
    inhoud = binnen[m.end():] if m else binnen
    return kop, inhoud


def verplaats_koppen(fragment):
    """h2 wordt h3 enzovoort: de h1 van de pagina wordt in de bundel een h2."""
    def een(m):
        return f"<{m.group(1)}h{min(int(m.group(2)) + 1, 6)}{m.group(3)}>"
    return re.sub(r"<(/?)h([1-5])([^>]*)>", een, fragment)


# ------------------------------------------------------- afbeeldingen krimpen
#
# Chrome zet elke afbeelding op ware grootte en zonder verlies in de PDF, dus de
# 22 MB aan PNG waar de syllabus naar wijst wordt daar ruim 50 MB. Dat is puur
# gewicht: een PNG van 2254 pixels die op 160mm gedrukt wordt is 358 dpi, en een
# drukker haalt daar niets meer uit dan uit 150.
#
# Krimpen gebeurt HIER en niet in img/, want de site heeft de volle resolutie
# wel nodig: figure-zoom laat de student inzoomen. De bundel wijst dus naar een
# kopie in de werkmap, en img/ blijft wat het is.
#
# De doel-dpi volgt uit --figuur-breedte van de figuur zelf, en dat is meteen
# waarom dit beter uitkomt dan een blanco nabewerking van de PDF achteraf: een
# foto op 160mm mag naar 150 dpi, maar in ICEES dragen de ASCII-tabel van 10.3
# en de zes datasheetbladzijden van 9.5 tekst die een oefening moet kunnen
# lezen. Zulke afbeeldingen staan in syllabus.krimp.onaangeroerd in
# oriontools.json en gaan ongewijzigd mee. Zet je er iets bij, kijk het dan na
# IN de gedrukte PDF en niet op het scherm.
#
# De doel-dpi staat in syllabus.krimp.dpi; 0 krimpt niets.
KRIMP_DPI = 0
ONAANGEROERD = set()
KRIMPBAAR = re.compile(r"[.](png|jpe?g)$", re.I)
krimpmap = None
gekrompen = {}


def krimp(bron, breedte_mm):
    """Een kleinere kopie in de werkmap, of het origineel als dat niet loont."""
    if krimpmap is None or not KRIMPBAAR.search(bron.name):
        return bron
    if bron.name in ONAANGEROERD or not bron.exists():
        return bron
    if bron in gekrompen:
        return gekrompen[bron]
    try:
        from PIL import Image
    except ImportError:
        return bron
    with Image.open(bron) as im:
        w, h = im.size
        doel_w = min(w, int(round((breedte_mm or 160.0) / 25.4 * KRIMP_DPI)))
        # Ook zonder schalen loont het: Chrome zet een PNG als FlateDecode in de
        # PDF, en dat is voor een foto vier tot acht keer zwaarder dan JPEG.
        klein = im.convert("RGB")
        if doel_w < w:
            klein = klein.resize((doel_w, max(1, round(h * doel_w / w))),
                                 Image.LANCZOS)
    uit = krimpmap / f"{len(gekrompen):03d}-{bron.stem}.jpg"
    klein.save(uit, "JPEG", quality=82, optimize=True)
    # Een JPEG van een schermafdruk kan zwaarder uitvallen dan de PNG; dan niet.
    if uit.stat().st_size >= bron.stat().st_size:
        uit.unlink()
        uit = bron
    gekrompen[bron] = uit
    return uit


FIGUUR_BREEDTE = re.compile(r"--figuur-breedte:\s*([\d.]+)mm")


def absolute_paden(fragment, pagina):
    """src en href relatief aan de pagina worden absolute file:-URL's.

    De bundel staat in een tijdelijke map, dus elk relatief pad zou daar zoeken.
    Een rasterafbeelding wijst daarbij naar haar gekrompen kopie; zie krimp().
    """
    # De breedte staat op de <figure> en het pad op de <img> erin, dus het
    # fragment wordt per figuur doorlopen en de breedte onthouden.
    breedte = [None]

    def een(m):
        attr, waarde = m.group(1), m.group(2)
        if re.match(r"(https?:|file:|data:|mailto:|#)", waarde):
            return m.group(0)
        doel = Path(os.path.normpath(pagina.parent / waarde))
        if attr == "src":
            doel = krimp(doel, breedte[0])
        return f'{attr}="{doel.as_uri()}"'

    uit = []
    for stuk in re.split(r"(<figure\b[^>]*>|</figure>)", fragment):
        if stuk.startswith("<figure"):
            b = FIGUUR_BREEDTE.search(stuk)
            breedte[0] = float(b.group(1)) if b else None
        elif stuk == "</figure>":
            breedte[0] = None
        uit.append(re.sub(r'\b(src|href)="([^"]+)"', een, stuk))
    return "".join(uit)


def naamruimte_ids(fragment, prefix):
    """Vijf pagina's met id="het-schema" worden in een document vijf keer dezelfde."""
    return re.sub(r'\bid="([^"]+)"', lambda m: f'id="{prefix}-{m.group(1)}"', fragment)


def zonder_scripts(fragment):
    return re.sub(r"<script\b.*?</script>", "", fragment, flags=re.S | re.I)


# ---------------------------------------------------------- de oplossingen

# HET ANTWOORD STAAT BIJ DE VRAAG, en zowel de PDF als de site leest het daar.
#
# Een vragenlijst is een <ol class="vragen">. Een meerkeuzevraag duidt de juiste
# mogelijkheid aan met class="juist" op de <li>; elke vraag mag daarnaast een
# <div class="oplossing"> dragen met het geschreven antwoord of de toelichting.
# Een open vraag heeft er altijd een, want daar valt niets aan te duiden.
#
# Die twee markeringen zijn de hele bron. De PDF drukt er hieronder een sectie
# Oplossingen uit; oplossingen.js maakt er op de site een uitklap van. Twee
# weergaven van dezelfde inhoud dus, en niet twee plaatsen waar ze staat.
#
# Waarom niet een geschreven oplossingenpagina naast de vragen? Omdat die de
# letter van de mogelijkheid zou moeten herhalen ("2. b"). Verwissel dan ooit
# twee mogelijkheden en die letter is stil fout: aan geen van beide pagina's is
# iets te zien. Door de juiste mogelijkheid zelf te merken, wordt de letter
# geteld op het ogenblik dat er gedrukt wordt en kan hij niet uit de pas lopen.
# Dat de site diezelfde letter een tweede keer telt, in JS, is de prijs ervoor;
# het is een mechanische regel (de hoeveelste <li> draagt juist) en geen inhoud.
#
# EEN OPLOSSING IS EEN <div>, GEEN COMMENTAAR. Ze heeft in <!-- oplossing: -->
# gestaan, en dat was inhoud die per constructie maar een renderer kon zien;
# bovendien vreet een genest --> stil de rest op, zoals het verslagblok in een
# Opdracht.html laat zien. Alles staat in de HTML, en wat er niet op het scherm
# hoort, wordt daar weggenomen en niet weggelaten.
#
# De sectie staat niet in reference.js, en als enige in het gedrukte document.
# Het manifest blijft zeggen waar de vragen staan; de oplossingen zijn eruit
# afgeleid en volgen achteraan het hoofdstuk, zoals het verslagsjabloon uit
# Opdracht.html volgt.
#
# De regel vragen-answered van de check (orion.py check) bewaakt dat elke vraag een antwoord
# draagt, want hieronder is een vraag zonder antwoord alleen een regel "let op".

# De inhoud is proza: een genest <div> zou deze niet-gulzige match afbreken.
OPLOSSING_RE = re.compile(r'<div class="oplossing">(.*?)</div>', re.S)


def lijstitems(fragment, tag):
    """De <li> op het eerste niveau van de eerste <tag> in fragment.

    Geeft (openingstag, inhoud) per item. Met een reguliere expressie alleen
    lukt dat niet: de mogelijkheden van een meerkeuzevraag zijn zelf <li>'s
    binnen het item, dus er moet geteld worden hoe diep we zitten.
    """
    opening = re.search(rf"<{tag}\b[^>]*>", fragment)
    if not opening:
        return []
    rest = fragment[opening.end():]
    items = []
    lijstdiepte = 0   # geneste ul/ol binnen het lopende item
    lidiepte = 0
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
                break             # hier sluit de buitenste lijst
            lijstdiepte -= 1
        else:
            lijstdiepte += 1
    return items


def top_lijsten(fragment):
    """De <ol class="vragen">'s op het eerste niveau, met het nummer waar elk begint.

    Een Test jezelf is in de Word een doorlopende genummerde lijst, maar een
    tussenzin of een tabel ertussen splitst hem in HTML in meerdere <ol>'s. Het
    start-attribuut houdt de nummering dan aan, en hier worden ze weer aan
    elkaar geregen. Zonder dat leest alleen de eerste <ol> mee: de vragen
    daarna raken hun antwoord kwijt zonder dat er iets aan te zien is.

    De klasse beslist wat een vragenlijst is, en niet de plaats op de pagina.
    Een theoriepagina somt ook wel eens genummerd op (UTP, FTP, SFTP staan zo in
    2.2) en de studievragen vooraan een hoofdstuk zijn een <ol> in een info-box;
    geen van beide is iets waar een antwoord bij hoort.
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
            begin = re.search(r'start="(\d+)"', m.group(3))
            begin = int(begin.group(1)) if begin else volgende
            items = lijstitems(fragment[m.start():], "ol")
            uit.append((begin, items))
            volgende = begin + len(items)
        diepte += 1
    return uit


def vragen_van(fragment):
    """(nummer, openingstag, inhoud) per vraag, over alle <ol>'s van de pagina heen."""
    return [(begin + i, tag, inhoud)
            for begin, items in top_lijsten(fragment)
            for i, (tag, inhoud) in enumerate(items)]


def inline(fragment):
    return re.sub(r"\s+", " ", fragment).strip()


def draagt_vragen(pagina):
    """Staat er een vragenlijst op deze pagina?"""
    _, fragment = kop_en_inhoud(pagina)
    return bool(top_lijsten(fragment))


@functools.lru_cache(maxsize=None)
def oplossingen_uit(pagina):
    """De oplossingen van een vragenpagina, of None als er een antwoord ontbreekt.

    Alles of niets, en met opzet. Een lijst waar vraag 3 uit weggevallen is,
    laat de student denken dat hij vraag 3 goed heeft, en dat is erger dan geen
    lijst. Ontbreekt er een antwoord, dan zegt de export welke vraag het is en
    drukt ze voor dat hoofdstuk geen oplossingen.
    """
    _, fragment = kop_en_inhoud(pagina)
    vragen = vragen_van(fragment)
    if not vragen:
        overgeslagen.append(f"{pagina.name}: geen genummerde vragen gevonden")
        return None

    regels, ontbreekt = [], []
    for nummer, _, inhoud in vragen:
        geschreven = OPLOSSING_RE.search(inhoud)
        geschreven = inline(geschreven.group(1)) if geschreven else ""
        keuzes = lijstitems(inhoud, "ul")
        if keuzes:
            juist = [i for i, (tag, _) in enumerate(keuzes)
                     if re.search(r'class="[^"]*\bjuist\b', tag)]
            if len(juist) != 1:
                ontbreekt.append(f"vraag {nummer} heeft {len(juist)} juiste "
                                 "mogelijkheden in plaats van een")
                continue
            # De letter wordt hier geteld en staat nergens geschreven. Wat er
            # eventueel bij staat, is toelichting en niet het antwoord zelf.
            letter = chr(ord("a") + juist[0])
            kern = inline(keuzes[juist[0]][1])
            if geschreven:
                # De mogelijkheid is vaak een los woord ("M12"), en dan plakt de
                # toelichting eraan vast tot er een punt tussen staat.
                if kern and kern[-1] not in ".?!:;":
                    kern += "."
                kern += f" {geschreven}"
            regels.append(f'<li><span class="keuze">{letter}</span>{kern}</li>')
            continue
        if not geschreven:
            ontbreekt.append(f'vraag {nummer} draagt geen <div class="oplossing">')
            continue
        regels.append(f"<li>{geschreven}</li>")

    if ontbreekt:
        for regel in ontbreekt:
            overgeslagen.append(f"{pagina.name}: {regel}")
        overgeslagen.append(f"{pagina.name}: geen oplossingen gedrukt zolang niet "
                            "elke vraag er een heeft")
        return None
    return (f'<ol class="oplossingen" start="{vragen[0][0]}">\n'
            + "\n".join(regels) + "\n</ol>")


def zonder_oplossingen(fragment):
    """De antwoorden uit de vragen halen: ze horen in de oplossingensectie."""
    return OPLOSSING_RE.sub("", fragment)


# --------------------------------------------------------------- de bundel

# Er staat hier geen opmaak. Alles wat zegt hoe het document eruitziet, staat in
# <syllabus_dir>/syllabus.css, en dat bestand wordt hieronder gelinkt met een
# absolute file:-URL, zodat de url()'s erin (de icoontjes van de kaders) tegen
# de repo oplossen en niet tegen de tijdelijke map waar de bundel staat.
#
# OrionCSS wordt hier NIET geladen. Dat is de huisstijl van de site; dit is een
# document met de huisstijl van HOGENT, en twee stylesheets over elkaar zouden
# betekenen dat je bij elke afwijking moet raden welke van de twee wint.
STIJLBLAD = None       # paths.syllabus_dir / syllabus.css, gezet door main()

BUNDEL = """<!DOCTYPE html>
<html lang="nl">

<head>
    <meta charset="UTF-8">
    <title>{titel}</title>
    <link rel="stylesheet" href="{stijlblad}">
</head>

<body>
{inhoud}
</body>

</html>
"""


def bundel(inhoud):
    return BUNDEL.format(titel=html.escape(TITEL), inhoud=inhoud,
                         stijlblad=STIJLBLAD.as_uri())




def sectie_slug(bestandsnaam):
    """TestJezelf -> test-jezelf. De bestandsnaam is PascalCase, zoals overal."""
    met_streepjes = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", bestandsnaam)
    return re.sub(r"[^a-z0-9]+", "-", met_streepjes.lower()).strip("-")


def bouw_inhoud(structuur):
    stukken = []
    for nummer, titel, secties in structuur:
        for snummer, vaste_titel, bron, tid, soort in secties:
            if soort == "oplossingen":
                nr = f'<span class="kop-nr">{snummer}</span>' if snummer else ""
                # Een tussenkop per vragenpagina, met het nummer van de sectie
                # waar die vragen staan. Een student die hier zijn antwoord
                # nakijkt, moet weten welke vragen hij aan het nakijken is, en
                # kan met dat nummer terug.
                delen = []
                for vragen_nr, pagina in bron:
                    kop, _ = kop_en_inhoud(pagina)
                    label = f"{vragen_nr} {kop}" if vragen_nr else kop
                    delen.append(f"<h3>{html.escape(label)}</h3>\n"
                                 + absolute_paden(oplossingen_uit(pagina), pagina))
                fragment = naamruimte_ids("\n".join(delen), tid)
                stukken.append('<section data-sectie="oplossingen">\n'
                               f'<h2 id="{tid}">{nr}Oplossingen</h2>\n'
                               + fragment + "\n</section>")
                continue
            pagina = bron
            kop, fragment = kop_en_inhoud(pagina)
            fragment = zonder_scripts(fragment)
            fragment = zonder_oplossingen(fragment)
            fragment = verplaats_koppen(fragment)
            fragment = absolute_paden(fragment, pagina)
            fragment = naamruimte_ids(fragment, tid)
            # Het nummer krijgt een eigen span, want in de syllabus staat de
            # titel op een vaste tabstop: zonder dat schuift "1.1" hem verder
            # op dan "1" en lijnt geen enkele kop uit met de volgende.
            if vaste_titel is not None:
                # de opening van een hoofdstuk: titel plus de kaders, samen op
                # een eigen bladzijde zoals in de syllabus
                nr = f'<span class="kop-nr">{nummer}</span>' if nummer else ""
                stukken.append(
                    '<div class="hoofdstuk-opening">\n'
                    f'<h1 id="{tid}">{nr}{html.escape(vaste_titel)}</h1>\n'
                    + fragment.strip() + "\n</div>")
                continue
            # Elke sectie zegt in data-sectie welke sectie ze is, afgeleid van de
            # bestandsnaam van haar bronpagina. syllabus.css beslist daarmee wat
            # er met zo'n sectie gebeurt (een Test jezelf begint bijvoorbeeld op
            # een nieuwe bladzijde). Zo staat die keuze in de stylesheet en niet
            # hier, en geldt ze meteen voor elk hoofdstuk.
            if snummer is None:
                kopregel = f'<h1 id="{tid}">{html.escape(kop)}</h1>'
            else:
                kopregel = (f'<h2 id="{tid}"><span class="kop-nr">{snummer}</span>'
                            f"{html.escape(kop)}</h2>")
            # Draagt de sectie vragen, dan staat dat er als data-vragen bij.
            # Ook dit is een mededeling en geen opmaak: syllabus.css beslist wat
            # ermee gebeurt, zoals bij data-sectie.
            merk = ' data-vragen' if draagt_vragen(pagina) else ""
            stukken.append(f'<section data-sectie="{sectie_slug(pagina.stem)}"{merk}>\n'
                           + kopregel + "\n" + fragment.strip() + "\n</section>")
    return "\n\n".join(stukken)


def regels_html(regels):
    """Een regel per element, met een <br> ertussen; een lege regel is een witregel."""
    return "<br>".join(html.escape(r) for r in regels)


def bouw_cover():
    logo = (f'<img class="cover-logo" src="{LOGO.as_uri()}" alt="HOGENT">'
            if LOGO and LOGO.exists() else "")
    return "\n".join([
        '<div class="cover">',
        f'    <div class="cover-opleiding">{html.escape(COVER["opleiding"])}</div>',
        f'    <div class="cover-titel">{html.escape(TITEL)}</div>',
        f'    <div class="cover-auteur">{html.escape(COVER["auteur"])}</div>',
        f'    <div class="cover-departement">{regels_html(COVER["departement"])}</div>',
        f'    <div class="cover-opleidingsvoet">{regels_html(COVER["voet"])}</div>',
        f"    {logo}",
        "</div>",
    ])


def bouw_inhoudstafel(inhoudstafel):
    regels = ['<div class="inhoud-titel">Inhoudstafel</div>', '<table class="toc">']
    for niveau, nummer, titel, bladzijde in inhoudstafel:
        nr = f'<span class="nr">{nummer}</span>' if nummer else ""
        regels.append(f'    <tr class="n{niveau}">'
                      f"<td>{nr}{html.escape(titel)}</td>"
                      f'<td class="pg">{bladzijde}</td></tr>')
    regels.append("</table>")
    return "\n".join(regels)


# ------------------------------------------------------------------ chrome
#
# zoek_chrome komt uit oriontools/chrome.py en druk_af uit pdfhulp.py, want de
# handout drukt op dezelfde manier af.


# ------------------------------------------------ paginanummers terugzoeken

def genormaliseerd(tekst):
    return re.sub(r"\s+", "", tekst).lower()


def zoek_bladzijden(pdf_pad, koppen):
    """Op welke bladzijde staat elke kop? Vooruit zoekend, dus dubbele titels
    (elk hoofdstuk heeft een Test jezelf) landen op de juiste."""
    lezer = PdfReader(str(pdf_pad))
    paginas = [genormaliseerd(p.extract_text() or "") for p in lezer.pages]
    uit = []
    vanaf = 0
    for kop in koppen:
        naald = genormaliseerd(kop)
        gevonden = None
        for i in range(vanaf, len(paginas)):
            if naald in paginas[i]:
                gevonden = i + 1
                vanaf = i
                break
        if gevonden is None:
            overgeslagen.append(f'kop "{kop}" niet teruggevonden in de PDF, '
                                "paginanummer geschat")
            gevonden = uit[-1] if uit else 1
        uit.append(gevonden)
    return uit, len(lezer.pages)


# ------------------------------------------------------- kop- en voettekst

def stempellogo():
    """Het logo op de maat waarop het gedrukt wordt, of None als het er niet is.

    In de voettekst staat het op 19.4mm breed, en het bestand is 3490 pixels
    breed: dat is 4570 dpi. Een kopie op 300 dpi is 229 pixels en scheelt in
    de PDF een factor twintig. img/ blijft ongemoeid, want de cover gebruikt
    hetzelfde bestand wel op ware grootte.
    """
    if not LOGO or not LOGO.exists():
        return None
    try:
        from PIL import Image
        from reportlab.lib.utils import ImageReader
    except ImportError:
        return str(LOGO)
    with Image.open(LOGO) as im:
        doel_w = int(round(19.4 / 25.4 * 300))
        if doel_w >= im.width:
            return str(LOGO)
        klein = im.convert("RGBA").resize(
            (doel_w, max(1, round(im.height * doel_w / im.width))), Image.LANCZOS)
    return ImageReader(klein)


def stempel(bron_pdf, hoofdstuk_per_bladzijde, verschuiving):
    """Paginanummer bovenaan, hoofdstuktitel onderaan, zoals in de Word.

    Het nummer telt de cover en de inhoudstafel mee, zodat het gelijkloopt met
    de inhoudstafel en met wat een viewer als bladzijde aanwijst.
    """
    lezer = PdfReader(str(bron_pdf))
    schrijver = PdfWriter()
    _, vet = stempelletters()

    # EEN canvas voor alle bladzijden, niet een per bladzijde. Dat is geen
    # opruiming maar de zwaarste post van het hele document: reportlab deelt
    # een afbeelding binnen een canvas en embedt ze dus een keer, terwijl een
    # canvas per bladzijde het logo 148 keer meestuurde, telkens op zijn volle
    # 3490 bij 1968 pixels. Dat was 14,3 van de 42 MB.
    buffer = io.BytesIO()
    eerste = lezer.pages[0]
    c = rl_canvas.Canvas(buffer, pagesize=(float(eerste.mediabox.width),
                                           float(eerste.mediabox.height)))
    logo = stempellogo()
    for i, bladzijde in enumerate(lezer.pages):
        breedte = float(bladzijde.mediabox.width)
        hoogte = float(bladzijde.mediabox.height)
        c.setPageSize((breedte, hoogte))

        # Maten van de bestaande syllabus afgemeten: het nummer rechtsboven op
        # 185.1mm, de hoofdstuktitel linksonder in grijs, en het logo rechts
        # ernaast. Alles staat buiten de tekstspiegel van 25 tot 185mm.
        c.setFont(vet, 16)
        c.setFillGray(0)
        c.drawRightString(185.1 * mm, hoogte - 19.6 * mm, str(i + 1 + verschuiving))

        titel = hoofdstuk_per_bladzijde[i] if i < len(hoofdstuk_per_bladzijde) else ""
        if titel:
            c.setFont(vet, 9.5)
            c.setFillGray(0.45)
            c.drawString(27.8 * mm, 19.6 * mm, titel)
        if logo is not None:
            c.drawImage(logo, 165.7 * mm, 16.0 * mm, width=19.4 * mm,
                        height=10.7 * mm, mask="auto")
        c.showPage()
    c.save()
    buffer.seek(0)

    stempels = PdfReader(buffer).pages
    for i, bladzijde in enumerate(lezer.pages):
        bladzijde.merge_page(stempels[i])
        schrijver.add_page(bladzijde)
    return schrijver


# -------------------------------------------------------------------- main

def main(argv=None):
    global REPO, MANIFEST, MODULE, BRON, UIT, LOGO, TITEL, COVER, STIJLBLAD
    global KRIMP_DPI, ONAANGEROERD, krimpmap
    p = argparse.ArgumentParser(
        prog="orion.py export-syllabus",
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", help="waar de PDF heen gaat (standaard: downloads/ "
                                 "en syllabus.pdf uit oriontools.json)")
    p.add_argument("--chrome")
    p.add_argument("--html-only", action="store_true",
                   help="schrijf alleen de gebundelde HTML, start Chrome niet")
    p.add_argument("--keep-html", action="store_true",
                   help="laat de bundel staan naast de PDF")
    repo.voeg_repo_toe(p)
    args = p.parse_args(argv)

    vak = repo.vind(args)
    instelling = vak.config["syllabus"]
    REPO = vak.root
    MANIFEST = REPO / instelling["manifest"]
    MODULE = instelling["manifest_key"] or "syllabus"
    BRON = vak.pad("syllabus_src")
    STIJLBLAD = vak.pad("syllabus_dir") / "syllabus.css"
    LOGO = REPO / instelling["logo"] if instelling["logo"] else None
    TITEL = vak.titel
    COVER = instelling["cover"]
    KRIMP_DPI = instelling["krimp"]["dpi"]
    ONAANGEROERD = set(instelling["krimp"]["onaangeroerd"])
    if args.out:
        UIT = Path(args.out)
    elif instelling["pdf"]:
        UIT = vak.pad("downloads") / instelling["pdf"]
    else:
        sys.exit("geen bestandsnaam: zet syllabus.pdf in oriontools.json of geef --out")

    if not STIJLBLAD.exists():
        # Zonder stylesheet drukt Chrome de bundel gewoon af met de standaard
        # browseropmaak. Dat levert een PDF op die er alleen maar armzalig
        # uitziet en verder nergens over klaagt.
        sys.exit(f"{STIJLBLAD.relative_to(REPO)} ontbreekt; zonder dat bestand "
                 "heeft de PDF geen enkele opmaak.")

    module = lees_module()
    structuur = hoofdstukken(module)
    if not structuur:
        sys.exit("geen enkel hoofdstuk gevonden")

    werk = Path(tempfile.mkdtemp(prefix="syllabus-"))
    if KRIMP_DPI:
        krimpmap = werk / "klein"
        krimpmap.mkdir()
    inhoud_html = werk / "inhoud.html"
    inhoud_html.write_text(bundel(bouw_inhoud(structuur)), encoding="utf-8")

    if args.html_only:
        doel = UIT.with_suffix(".html")
        doel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(inhoud_html, doel)
        print(f"bundel  -> {doel}")
        # Ook hier, want een proefdruk is precies het ogenblik waarop je wil
        # horen dat er een vraag zonder antwoord tussen zit.
        for regel in overgeslagen:
            print(f"  let op: {regel}")
        return 0

    chrome = zoek_chrome(args.chrome)
    body_pdf = werk / "inhoud.pdf"
    druk_af(chrome, inhoud_html, body_pdf)

    # welke koppen zoeken we terug, en wat komt er in de inhoudstafel
    koppen, tafel = [], []
    for nummer, titel, secties in structuur:
        for snummer, vaste_titel, bron, _, soort in secties:
            if soort == "oplossingen":
                koppen.append(f"{snummer} Oplossingen")
                tafel.append([2, snummer, "Oplossingen", None])
            elif vaste_titel is not None or snummer is None:
                kop, _ = kop_en_inhoud(bron)
                zichtbaar = f"{nummer} {vaste_titel}" if nummer else kop
                koppen.append(zichtbaar)
                tafel.append([1, nummer, vaste_titel or kop, None])
            else:
                kop, _ = kop_en_inhoud(bron)
                koppen.append(f"{snummer} {kop}")
                tafel.append([2, snummer, kop, None])

    bladzijden, aantal = zoek_bladzijden(body_pdf, koppen)
    for rij, bladzijde in zip(tafel, bladzijden):
        rij[3] = bladzijde

    # Cover en inhoudstafel gaan samen in een bundel: syllabus.css zet de cover
    # op een eigen @page zonder marges (benoemde pagina), dus ze kunnen in een
    # run zonder elkaars marges over te nemen.
    #
    # Het gedrukte nummer is de plaats in het hele document, cover meegeteld, en
    # niet de plaats in de inhoud. Zo klopt het met wat een lezer in zijn viewer
    # ziet, en het is ook wat de bestaande syllabus doet: daar staat het
    # Voorwoord op 3, na de cover en de inhoudstafel.
    #
    # Daardoor hangen de nummers IN de inhoudstafel af van hoe lang het voorwerk
    # is. Die lengte hangt alleen van het aantal regels af en niet van de nummers
    # erin, dus een keer proefdrukken volstaat om ze te kennen. De lus eromheen
    # is er voor het geval een breder nummer toch een regel doet omslaan.
    voorwerk_html = werk / "voorwerk.html"
    voorwerk_pdf = werk / "voorwerk.pdf"
    verschuiving = 1
    for _ in range(3):
        verschoven = [[n, nr, tt, b + verschuiving] for n, nr, tt, b in tafel]
        voorwerk_html.write_text(
            bundel(bouw_cover() + "\n" + bouw_inhoudstafel(verschoven)),
            encoding="utf-8")
        druk_af(chrome, voorwerk_html, voorwerk_pdf)
        nieuw = len(PdfReader(str(voorwerk_pdf)).pages)
        if nieuw == verschuiving:
            break
        verschuiving = nieuw
    tafel = verschoven

    # hoofdstuktitel per bladzijde, voor de voettekst
    per_bladzijde = [""] * aantal
    hoofdstuk_start = [(rij[3], rij[2]) for rij in tafel if rij[0] == 1]
    for i in range(aantal):
        lopend = ""
        for start, naam in hoofdstuk_start:
            if start <= i + 1 + verschuiving:
                lopend = naam
        per_bladzijde[i] = lopend

    schrijver = PdfWriter()
    for bladzijde in PdfReader(str(voorwerk_pdf)).pages:
        schrijver.add_page(bladzijde)
    for bladzijde in stempel(body_pdf, per_bladzijde, verschuiving).pages:
        schrijver.add_page(bladzijde)

    ouder = None
    for niveau, nummer, titel, bladzijde in tafel:
        naam = f"{nummer} {titel}" if nummer else titel
        doel = bladzijde - 1
        if niveau == 1:
            ouder = schrijver.add_outline_item(naam, doel)
        else:
            schrijver.add_outline_item(naam, doel, parent=ouder)

    doel = UIT
    doel.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(doel, "wb") as f:
            schrijver.write(f)
    except PermissionError:
        # Windows houdt een geopende PDF vast. Dat gebeurt precies wanneer je aan
        # het nakijken bent wat je net liet genereren, dus zeg wat er aan de hand
        # is in plaats van een stack trace.
        sys.exit(f"{doel.name} is vergrendeld; sluit hem in je PDF-lezer en "
                 "draai dit opnieuw, of gebruik --out om ergens anders te schrijven.")

    if args.keep_html:
        for bron in (inhoud_html, voorwerk_html):
            shutil.copy(bron, doel.with_name(f"{doel.stem}-{bron.stem}.html"))
    else:
        shutil.rmtree(werk, ignore_errors=True)

    print(f"{verschuiving} bladzijden voorwerk, {aantal} bladzijden inhoud")
    print(f"pdf     -> {doel.relative_to(REPO) if doel.is_relative_to(REPO) else doel}")
    for regel in overgeslagen:
        print(f"  let op: {regel}")
    return 0
