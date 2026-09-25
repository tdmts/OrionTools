"""De syllabus: HTML-pagina's waar een PDF uit gedrukt wordt."""

import os
import re
from pathlib import Path

from ..regel import Regel
from ._gedeeld import (document_re, heeft_syllabus, lijstitems, syllabus_paginas,
                       top_lijsten, vragen)

# Een leeg manifest en een kapot manifest zien er voor de parser hetzelfde uit:
# allebei nul modules. Ze betekenen niet hetzelfde; zie SyllabusManifest.
LEEG_MANIFEST_RE = re.compile(r"window\.LAB_REFERENCE\s*=\s*\{\s*\}\s*;")


def _moduleblokken(tekst):
    """Het manifest is JS, geen JSON; wat nodig is, komt eruit met regexen.

    Dat is grof, maar het alternatief is een JS-parser meeslepen voor een
    bestand dat we zelf schrijven en dat een vaste vorm heeft: vier spaties voor
    de modulesleutel, en per topic id, name en href tussen enkele aanhalingstekens.
    """
    for mod in re.finditer(r"^    (\w+):\s*\{", tekst, re.M):
        start = i = mod.end()
        diepte = 1
        while i < len(tekst) and diepte:
            if tekst[i] == "{":
                diepte += 1
            elif tekst[i] == "}":
                diepte -= 1
            i += 1
        yield mod.group(1), tekst[start:i]


def _theoriemap(ctx, naam):
    """De map waar de hrefs van module naam relatief aan zijn.

    De mapnaam is niet af te leiden uit de sleutel (rs485 -> RS485), dus wordt
    de map gezocht waarvan de kleine-letterversie overeenkomt, onder paths.labo
    en naast paths.syllabus_dir. Is dat de syllabusmap zelf, dan is het
    paths.syllabus_src; anders de Theorie/ van die labomap.
    """
    syllabus_dir = ctx.vak.pad("syllabus_dir")
    labo = ctx.vak.pad("labo")
    theorie = labo / naam.upper() / "Theorie"
    for basis in (labo, syllabus_dir.parent):
        if not basis.is_dir():
            continue
        for kandidaat in basis.iterdir():
            if kandidaat.is_dir() and kandidaat.name.lower() == naam:
                theorie = (ctx.vak.pad("syllabus_src") if kandidaat == syllabus_dir
                           else kandidaat / "Theorie")
    return theorie


class SyllabusManifest(Regel):
    """Het manifest van de syllabus (reference.js) klopt met de bestanden.

    Elke href erin is relatief, bestaat met exact dezelfde hoofdletters, en
    heeft een unieke id; id, name en href zijn aanwezig en niet leeg; elke
    module heeft minstens een categorie. En elke pagina onder
    paths.syllabus_src staat in het manifest: een pagina die er niet in staat,
    komt niet in de syllabus-PDF, terwijl ze op het scherm gewoon opent.

    Er wordt recursief gezocht en op het volledige pad vergeleken: de syllabus
    zet een map per hoofdstuk, en zes hoofdstukken hebben elk een
    Overzicht.html; op bestandsnaam zou de ene de andere afdekken.

    Een leeg manifest (window.LAB_REFERENCE = {};) is een waarschuwing en geen
    fout. Dat is de repo op dag nul, voor het eerste hoofdstuk ingevoerd is: nog
    niet publiceerbaar, en de melding verdwijnt vanzelf zodra er een hoofdstuk
    in staat. Een manifest waar de parser niets in vindt terwijl het niet leeg
    is, blijft een fout: de rest van de regel hangt aan die parse, en een
    stukgelopen regex zou elke controle eronder leeg en dus groen maken.
    """

    id = "syllabus-manifest"
    legacy = ("DeN:2", "ICEES:2")

    def van_toepassing(self, ctx):
        if (ctx.root / ctx.config["syllabus"]["manifest"]).is_file():
            return True
        return heeft_syllabus(ctx)

    def controleer(self, ctx):
        naam_manifest = ctx.config["syllabus"]["manifest"]
        manifest = ctx.root / naam_manifest
        if not manifest.is_file():
            ctx.fout(naam_manifest, "ontbreekt, dus geen enkele syllabuspagina komt in de PDF")
            return
        tekst = ctx.tekst(manifest)
        blokken = list(_moduleblokken(tekst))
        if not blokken:
            if LEEG_MANIFEST_RE.search(tekst):
                ctx.waarschuw(manifest, "window.LAB_REFERENCE is leeg; er staat nog geen "
                                        "hoofdstuk in deze repo, dus deze regel kijkt naar niets")
            else:
                ctx.fout(manifest, "geen enkele module gevonden")
            return

        doc = document_re(ctx)
        for naam, blok in blokken:
            if not re.findall(r"name:\s*'([^']*)',\s*topics:", blok):
                ctx.fout(manifest, f"module '{naam}' heeft geen enkele categorie")

        for naam, blok in blokken:
            topics = [dict(re.findall(r"(\w+):\s*'((?:[^'\\]|\\.)*)'", t.group(0)))
                      for t in re.finditer(r"\{\s*id:.*?\}", blok, re.S)]
            theorie = _theoriemap(ctx, naam)
            if not theorie.is_dir():
                ctx.fout(manifest, f"module '{naam}' heeft geen Theorie-map")
                continue
            ids, vermeld = set(), set()
            for topic in topics:
                for veld in ("id", "name", "href"):
                    if not topic.get(veld):
                        ctx.fout(manifest, f"{naam}: veld '{veld}' ontbreekt of is leeg")
                href = topic.get("href", "")
                tid = topic.get("id")
                if href.startswith("http"):
                    ctx.fout(manifest, f"{naam}/{tid}: absolute URL, gebruik een relatief pad")
                if tid in ids:
                    ctx.fout(manifest, f"{naam}: id '{tid}' komt twee keer voor")
                ids.add(tid)
                doel = Path(os.path.normpath(theorie / href))
                if not doel.exists():
                    ctx.fout(manifest, f"{naam}/{tid}: href bestaat niet ({href})")
                elif not ctx.exacte_hoofdletters(doel):
                    ctx.fout(manifest, f"{naam}/{tid}: hoofdletters kloppen niet, dit geeft "
                                       f"404 op de server ({href})")
                elif not doc.search(href):
                    vermeld.add(str(doel))
            for pagina in sorted(theorie.rglob("*.html")):
                if str(pagina) not in vermeld and not ctx.overgeslagen(pagina):
                    ctx.fout(pagina, f"staat niet in {naam_manifest}, dus niet in de syllabus-PDF")


class SyllabusVerouderd(Regel):
    """De syllabus-PDF is niet ouder dan de pagina's waaruit ze gegenereerd is.

    Dezelfde regel als verslag-stale, en om een scherpere reden: van de hele
    syllabus is de PDF het enige dat de student te zien krijgt. Een pagina
    onder paths.syllabus_src aanpassen zonder export-syllabus opnieuw te
    draaien, verandert dus niets aan wat hij leest. Op het scherm klopt alles,
    en niets anders zou het merken.

    syllabus.css (in paths.syllabus_dir) telt mee als bron. Het is de enige
    plaats waar staat wat het gedrukte blad met een pagina doet, en de exporteur
    linkt het; een marge daar verzetten verandert de PDF net zo goed als een zin
    op een pagina. Op het scherm zie je er niets van, want daar laden
    diezelfde pagina's OrionCSS.

    De afbeeldingen tellen bewust niet mee, anders dan bij handout-stale. De
    grens ligt bij de prijs en niet bij het principe: een handout drukt in
    seconden af, de syllabus doet er een minuut over. Wie een syllabusfiguur
    bijsnijdt, draait de export zelf.

    Welke PDF het is, zegt syllabus.pdf (een bestandsnaam onder
    paths.downloads). De regel vergelijkt mtimes en draait dus alleen lokaal:
    met --ci slaat ze over (zie Context.tijd).
    """

    id = "syllabus-stale"
    legacy = ("DeN:13", "ICEES:13")
    alleen_lokaal = True

    def van_toepassing(self, ctx):
        return heeft_syllabus(ctx)

    def controleer(self, ctx):
        naam = ctx.config["syllabus"]["pdf"]
        if not naam:
            ctx.fout("oriontools.json", "syllabus.pdf is niet ingesteld, terwijl er "
                                        "syllabuspagina's zijn")
            return
        pdf = ctx.vak.pad("downloads") / naam
        if not pdf.exists():
            ctx.fout(pdf, "bestaat niet; draai python ../OrionTools/orion.py export-syllabus")
            return
        stijl = ctx.vak.pad("syllabus_dir") / "syllabus.css"
        bronnen = syllabus_paginas(ctx) + ([stijl] if stijl.exists() else [])
        stempel = ctx.tijd(pdf)
        for bron in sorted(bronnen):
            if ctx.tijd(bron) > stempel:
                ctx.fout(pdf, f"is ouder dan {ctx._rel(bron)}; draai "
                              "python ../OrionTools/orion.py export-syllabus opnieuw")
                return


class VragenBeantwoord(Regel):
    """Elke vraag in de syllabus draagt haar antwoord.

    Een vragenlijst is een <ol class="vragen">. Een meerkeuzevraag duidt precies
    een mogelijkheid aan met class="juist"; een open vraag draagt
    <div class="oplossing">. Uit die markering drukt de syllabusexport de sectie
    Oplossingen achteraan het hoofdstuk en maakt OrionCSS main.js op de site een
    uitklap. De letter (a, b, c) wordt daarbij geteld in plaats van
    overgeschreven, zodat een verwisselde mogelijkheid geen fout antwoord kan
    opleveren. Een vraag met meer juiste antwoorden wordt herschreven, niet de
    regel versoepeld.

    Het gaat over elke pagina en niet alleen over TestJezelf.html: een oefening
    halverwege een hoofdstuk stelt dezelfde soort vraag, en toen de regel op de
    bestandsnaam keek, keek ze daar langs.

    De export is alles of niets: ontbreekt er een antwoord, dan drukt ze voor dat
    hoofdstuk helemaal geen oplossingen, want een lijst waar vraag 3 uit
    weggevallen is laat de student denken dat hij vraag 3 goed heeft. Dat is de
    juiste keuze en tegelijk een stille: op het scherm is er niets aan te zien,
    en in de uitvoer van de export is het een regel "let op" tussen de andere.
    Vandaar deze regel, die het meldt voor er gedrukt wordt.
    """

    id = "vragen-answered"
    legacy = ("DeN:14", "ICEES:14")

    def van_toepassing(self, ctx):
        return heeft_syllabus(ctx)

    def controleer(self, ctx):
        for pagina in syllabus_paginas(ctx):
            for nummer, _, inhoud in vragen(ctx.tekst(pagina)):
                keuzes = lijstitems(inhoud, "ul")
                if keuzes:
                    juist = [tag for tag, _ in keuzes if re.search(r'class="[^"]*\bjuist\b', tag)]
                    if len(juist) != 1:
                        ctx.fout(pagina, f"vraag {nummer} heeft {len(juist)} mogelijkheden met "
                                         'class="juist"; het moeten er precies een zijn, anders '
                                         "drukt de export voor dit hoofdstuk geen oplossingen")
                elif not re.search(r'<div class="oplossing">\s*\S', inhoud):
                    ctx.fout(pagina, f"vraag {nummer} is een open vraag zonder "
                                     '<div class="oplossing">; zonder dat antwoord drukt de '
                                     "export voor dit hoofdstuk geen oplossingen")


class VragenNummering(Regel):
    """De nummering van een vragenlijst loopt door over de <ol>'s heen.

    Een vragenlijst valt in HTML uiteen zodra er een tussenzin, een tabel of een
    figuur tussen twee vragen staat, en alleen het start-attribuut houdt de
    telling dan aan. Vergeet je het, dan begint de lijst op het scherm en op
    papier opnieuw bij 1, terwijl de sectie Oplossingen achteraan het hoofdstuk
    gewoon doortelt: antwoord 1 hoort dan bij vraag 3, en niets behalve het
    nummer zelf verraadt het. Dat is gebeurd: een Test jezelf drukte 1 tot 5 en
    daarna 1 tot 3, terwijl de oplossingen ernaast 6, 7 en 8 zeiden.

    Er wordt gekeken of het attribuut gedeclareerd is, niet naar het
    samengeregen nummer: dat valt bij gebrek aan een attribuut terug op de
    verwachte waarde en is dan altijd gelijk. Een melding per pagina.
    """

    id = "vragen-numbering"
    legacy = ("DeN:14", "ICEES:14")

    def van_toepassing(self, ctx):
        return heeft_syllabus(ctx)

    def controleer(self, ctx):
        for pagina in syllabus_paginas(ctx):
            for begin, items, gedeclareerd, verwacht in top_lijsten(ctx.tekst(pagina)):
                if not items:
                    continue
                if gedeclareerd:
                    if begin == verwacht:
                        continue
                    ctx.fout(pagina, f'een <ol class="vragen"> begint op start="{begin}" terwijl '
                                     f"de vraag ervoor op {verwacht - 1} eindigde; de nummering "
                                     "springt")
                else:
                    if verwacht == 1:
                        continue
                    ctx.fout(pagina, f'een <ol class="vragen"> mist start="{verwacht}", dus de '
                                     "nummering begint opnieuw bij 1 terwijl de oplossingen "
                                     f"doortellen vanaf {verwacht}")
                break


class VragenKlasse(Regel):
    """Een <ol> met invulruimte eronder draagt class="vragen".

    Dit is het gat dat de klasse openlaat. Wat een vragenlijst is, staat nergens
    anders meer dan in die klasse, dus vergeet je ze bij een nieuw ingevoerd
    hoofdstuk, dan drukt de export stilzwijgend geen oplossingen en faalt er
    niets.

    Het signaal is de invulruimte: een lege tabel onder een genummerd item is
    waar de student op papier antwoordt, en op een theoriepagina komt zoiets
    niet voor. Het is een verklikker en geen bewijs: een oefening die met
    onderstreepte lijnen werkt in plaats van met een tabel, glipt erdoor. Alleen
    op een pagina zonder enige vragenlijst.
    """

    id = "vragen-class"
    legacy = ("DeN:14", "ICEES:14")

    def van_toepassing(self, ctx):
        return heeft_syllabus(ctx)

    def controleer(self, ctx):
        for pagina in syllabus_paginas(ctx):
            tekst = ctx.tekst(pagina)
            if vragen(tekst):
                continue
            for m in re.finditer(r"<ol\b([^>]*)>", tekst):
                if re.search(r'class="[^"]*\bvragen\b', m.group(1)):
                    continue
                if any("invulruimte" in inhoud for _, inhoud in lijstitems(tekst[m.start():], "ol")):
                    ctx.fout(pagina, 'een <ol> met invulruimte eronder maar zonder class="vragen"; '
                                     "zonder die klasse ziet de export er geen vragen in en drukt "
                                     "ze er geen oplossingen bij")
                    break


class ImporterGok(Regel):
    """Geen onopgeloste gok van de importer (data-geraden) in een syllabuspagina.

    Waar de Word niets zegt, moet de syllabusimporter kiezen, en zo'n keuze mag
    niet alleen in IMPORT.md belanden. Die log wordt per hoofdstuk geschreven en
    daarna nooit meer aangeraakt, dus over de hoofdstukken die niet in de run
    zaten vertelt hij wat er ooit gebeurde in plaats van wat er nu staat. Na een
    correctie aan de kopregelregel beweerde hij over drie tabellen een kopregel
    die er niet meer stond, met een reden die de code niet meer kende, en niets
    merkte dat op.

    Daarom staat de twijfel als data-geraden op het element zelf. Zolang ze er
    staat is de check rood, dus ze staat in de weg in plaats van in een logboek,
    en ze veroudert niet, want ze staat bij de markup die ze beschrijft. Je lost
    ze op door het attribuut te schrappen (de gok klopt) of door de markup te
    veranderen, en dat schrappen is meteen het bewijs dat er iemand gekeken heeft.
    """

    id = "importer-guess"
    legacy = ("DeN:15", "ICEES:15")

    def van_toepassing(self, ctx):
        return heeft_syllabus(ctx)

    def controleer(self, ctx):
        for pagina in syllabus_paginas(ctx):
            tekst = ctx.tekst(pagina)
            for m in re.finditer(r'data-geraden="([^"]*)"', tekst):
                ctx.fout(pagina, f"onopgeloste gok van de import: {m.group(1)}. Kijk na wat de "
                                 "Word doet, pas de markup aan of laat ze staan, en schrap dan "
                                 "het attribuut", regelnr=tekst.count("\n", 0, m.start()) + 1)


class WeesAfbeelding(Regel):
    """Elke syllabusafbeelding (img/syllabus-*) wordt ergens gebruikt.

    De importer schrijft de afbeeldingen uit de Word naar img/ en zet ze in de
    pagina waar ze horen. Mist die tweede stap, dan staat het bestand er wel en
    verwijst niets ernaar: de vraag "welke topologie is dit?" verschijnt zonder
    tekening, en er is niets aan stuk. Precies dat gebeurde met drie
    topologietekeningen die in een lijstitem stonden, en het is gevonden doordat
    iemand de pagina las.

    Een bestand in img/ waar niets naar wijst, is dus geen rommel maar een
    aanwijzing dat er inhoud verloren is. De regel blijft ook van pas als de
    importer allang niet meer draait: ze vangt even goed een figuur die uit een
    pagina geknipt wordt terwijl het bestand blijft staan.

    Als gebruik telt elke html, css en js van de repo, en het omslaglogo uit
    syllabus.logo in oriontools.json: dat laadt de export en geen pagina.
    """

    id = "orphan-image"
    legacy = ("DeN:16", "ICEES:16")

    def van_toepassing(self, ctx):
        img = ctx.vak.pad("img")
        if img.is_dir() and any(p.name.startswith("syllabus-") for p in img.iterdir()):
            return True
        return "geen img/syllabus-*"

    def controleer(self, ctx):
        img = ctx.vak.pad("img")
        bestanden = sorted(p for p in img.iterdir()
                           if p.name.startswith("syllabus-") and p.is_file())
        overslaan = ctx.staging | {".git", "node_modules"}
        delen = []
        for map_, submappen, namen in os.walk(ctx.root):
            submappen[:] = [d for d in submappen if d not in overslaan]
            for n in namen:
                if n.endswith((".html", ".css", ".js")):
                    p = Path(map_) / n
                    delen.append(ctx.tekst(p) if n.endswith(".html")
                                 else p.read_text(encoding="utf-8", errors="ignore"))
        gebruikt = "\n".join(delen)
        logo = Path(ctx.config["syllabus"]["logo"]).name
        for bestand in bestanden:
            if bestand.name != logo and bestand.name not in gebruikt:
                ctx.fout(bestand, "staat in img/ maar geen enkele pagina gebruikt hem; de import "
                                  "heeft hem geschreven en nergens gezet, dus er ontbreekt een "
                                  "afbeelding op een pagina")
