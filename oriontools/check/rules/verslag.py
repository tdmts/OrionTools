"""De labo-opdracht: een landingspagina, en een docx die eruit gegenereerd wordt."""

import re
from urllib.parse import unquote

from ..regel import Regel
from ._gedeeld import (COMMENTAAR_RE, GEEN_VERSLAG_RE, LEAD_RE, heeft_opdracht,
                       onafgesloten_commentaren, opdracht_paginas)


class VerslagVerouderd(Regel):
    """Het verslagsjabloon bestaat voor elke Opdracht.html, en is niet ouder dan die pagina.

    Het sjabloon wordt uit Opdracht.html gegenereerd (export-verslag), zodat het
    niet kan afdrijven van de opdracht waar het bij hoort. Een oudere docx
    betekent dat de export opnieuw moet lopen; OrionSync spiegelt alleen wat
    gecommit is, dus het sjabloon hoort in dezelfde commit als de pagina.

    Het pad dat de pagina zelf aanbiedt, is leidend. Een opdracht die bewust
    geen sjabloon heeft, zegt dat met <!-- geen-verslag: reden --> en wordt
    overgeslagen: een deel dat een .pka oplevert en geen document, heeft aan een
    sjabloon zonder iets om in te vullen minder dan aan geen sjabloon.

    De regel vergelijkt mtimes en draait dus alleen lokaal: met --ci slaat ze
    over (zie Context.tijd).
    """

    id = "verslag-stale"
    legacy = ("DeN:6", "ICEES:6")
    alleen_lokaal = True

    def van_toepassing(self, ctx):
        return heeft_opdracht(ctx)

    def controleer(self, ctx):
        for opdracht in opdracht_paginas(ctx):
            module = ctx._rel(opdracht.parent)
            tekst = ctx.tekst(opdracht)
            if GEEN_VERSLAG_RE.search(tekst):
                continue
            m = re.search(r'href="([^"]*downloads/[^"]+\.docx)"', tekst)
            if not m:
                ctx.waarschuw(opdracht, "biedt geen verslagsjabloon aan")
                continue
            docx = (opdracht.parent / unquote(m.group(1))).resolve()
            if not docx.exists():
                ctx.fout(opdracht, "verslagsjabloon ontbreekt, draai: "
                                   f"python ../OrionTools/orion.py export-verslag {module}")
                continue
            if ctx.tijd(docx) < ctx.tijd(opdracht):
                ctx.fout(docx, "is ouder dan Opdracht.html, draai: "
                               f"python ../OrionTools/orion.py export-verslag {module}")


class OnafgeslotenCommentaar(Regel):
    """Elk <!-- is afgesloten met --> voor het volgende commentaar begint.

    Een commentaar dat niet afgesloten is, slikt alles tot het volgende
    commentaar stil op: in de browser verdwijnt een stuk pagina, en in een
    Opdracht.html verdwijnt een deel van de opdracht uit de docx. Een geneste
    --> in het verslagblok breekt het net zo vroeg af, en daarom horen
    auteursnotities in een apart commentaar erboven.
    """

    id = "unclosed-comment"
    legacy = ("DeN:7", "ICEES:7")

    def controleer(self, ctx):
        for pad in ctx.html:
            for regel in onafgesloten_commentaren(ctx.tekst(pad)):
                ctx.fout(pad, f"het commentaar op regel {regel} is niet afgesloten met -->; "
                              "alles tot het volgende commentaar verdwijnt stil uit de pagina",
                         regelnr=regel)


TABEL_RE = re.compile('<table class="[^"]*verslag-tabel[^"]*">(.*?)</table>', re.S)
RIJ_RE = re.compile("<tr[^>]*>(.*?)</tr>", re.S)
# Met de sluitende punthaak of een spatie erachter, anders telt <thead> mee
# als kolomkop en klopt elke tabel per definitie niet.
TH_RE = re.compile("<th[ >]")
TD_RE = re.compile("<td[ >]")
VERSLAG_MARKUP_RE = re.compile(r'class="[^"]*\b(vragen|verslag-kader)\b', re.I)


class VerslagMarkup(Regel):
    """De opdracht staat in <!-- verslag ... --> en niet op het scherm.

    Opdracht.html is een landingspagina; het werk gebeurt in de docx die eruit
    gegenereerd wordt. Een student die een vraag op de pagina leest, heeft daar
    geen plaats om te antwoorden, en gaat zich afvragen of hij ze twee keer moet
    beantwoorden. Daarom staan ze in commentaar: het bestand houdt ze, de pagina
    toont ze niet, en de export haalt ze eruit.

    Drie dingen worden nagekeken:

    - een vragenlijst of kader (class vragen, verslag-kader) buiten commentaar,
      alleen onder paths.labo: een verslag bestaat alleen waar een
      Opdracht.html staat. In de syllabus betekent class="vragen" iets anders,
      een vragenlijst die juist wel op het scherm hoort, met haar antwoord
      eronder. Twee mechanismen, hetzelfde woord, en dit is de plaats waar dat
      verschil uitgesproken wordt;
    - een verslagblok waar geen vragenlijst of kader in staat, want dat levert
      niets op in het sjabloon;
    - een invultabel (verslag-tabel) met een scheve rij: evenveel cellen per rij
      als kolomkoppen, want een scheve rij geeft een scheve tabel in Word zonder
      dat iets faalt, en in de browser zie je het niet omdat de tabel in
      commentaar staat.

    Een pagina met een onafgesloten commentaar slaat ze over; unclosed-comment
    meldt die al, en wat erna komt is dan niet te vertrouwen.
    """

    id = "verslag-markup"
    legacy = ("DeN:7", "ICEES:7")

    def van_toepassing(self, ctx):
        return heeft_opdracht(ctx)

    def controleer(self, ctx):
        labo = ctx.config["paths"]["labo"]
        for pad in ctx.html:
            tekst = ctx.tekst(pad)
            if onafgesloten_commentaren(tekst):
                continue
            if labo in pad.relative_to(ctx.root).parts:
                m = VERSLAG_MARKUP_RE.search(COMMENTAAR_RE.sub("", tekst))
                if m:
                    ctx.fout(pad, f"'{m.group(1)}' staat buiten een <!-- verslag --> blok, "
                                  "dus de student ziet de vragen zonder plaats om te antwoorden")
            for blok in COMMENTAAR_RE.finditer(tekst):
                inhoud = blok.group(1).strip()
                if inhoud.startswith("verslag") and not VERSLAG_MARKUP_RE.search(inhoud):
                    ctx.fout(pad, "een <!-- verslag --> blok bevat geen vragenlijst of kader, "
                                  "dus het levert niets op in het sjabloon")
            for tabel in TABEL_RE.finditer(tekst):
                body = tabel.group(1)
                kolommen = len(TH_RE.findall(body))
                if not kolommen:
                    ctx.fout(pad, "een verslag-tabel heeft geen <th>, dus geen kolomkoppen")
                    continue
                for n, rij in enumerate(RIJ_RE.finditer(body), start=1):
                    cellen = len(TD_RE.findall(rij.group(1)))
                    if cellen and cellen != kolommen:
                        ctx.fout(pad, f"verslag-tabel rij {n}: {cellen} cellen tegenover "
                                      f"{kolommen} kolomkoppen")


class OpdrachtLead(Regel):
    """Elke Opdracht.html heeft een <p class="lead"> buiten het commentaar.

    Die lead is de introductie van het labo, en de verslagexport zet ze op de
    eerste bladzijde van de docx. Zonder lead begint het document dat de student
    offline invult met een invulregel en verder niets, en weet wie het opent
    zonder de site gezien te hebben niet waar het labo over gaat. De export
    stopt er zelf ook op, maar pas bij het genereren; hier merk je het bij de
    gewone controle.
    """

    id = "opdracht-lead"
    legacy = ("DeN:8", "ICEES:8")

    def van_toepassing(self, ctx):
        return heeft_opdracht(ctx)

    def controleer(self, ctx):
        for opdracht in opdracht_paginas(ctx):
            if not LEAD_RE.search(COMMENTAAR_RE.sub("", ctx.tekst(opdracht))):
                ctx.fout(opdracht, 'geen <p class="lead"> buiten het commentaar, dus het '
                                   "verslag begint zonder te zeggen waar het labo over gaat")


# Niet vast aan <a href=...>: een knop met een class ervoor zou er stil
# tussenuit glippen, en dan keurt deze regel niets meer af zonder te falen.
VERSLAGKNOP_RE = re.compile(
    r'<a\b[^>]*href="[^"]*downloads/[^"]+\.docx"[^>]*>(.*?)</a>', re.S | re.I)
KNOPTEKST = "Opdracht downloaden"


class DownloadKnop(Regel):
    """De downloadknop op een Opdracht.html heet "Opdracht downloaden", en niets anders.

    Op een Opdracht.html staat precies een download: de docx die uit die pagina
    gegenereerd is. Ze heette ooit "Opdracht en verslag downloaden", en dat leest
    als twee bestanden waarvan de student er dan een mist. Het is er een: de
    opdracht staat erin, hij vult ze in dat document in en dient het zo in. Dat
    het daarna een verslag is, merkt hij bij het indienen, niet bij het
    downloaden.

    Het opschrift wordt letterlijk vergeleken, omdat een knoptekst precies het
    soort ding is dat op een pagina herschreven wordt en op de andere niet.
    """

    id = "download-button"
    legacy = ("DeN:11", "ICEES:11")

    def van_toepassing(self, ctx):
        return heeft_opdracht(ctx)

    def controleer(self, ctx):
        for opdracht in opdracht_paginas(ctx):
            tekst = ctx.tekst(opdracht)
            if GEEN_VERSLAG_RE.search(tekst):
                continue
            m = VERSLAGKNOP_RE.search(tekst)
            if not m:
                continue  # verslag-stale meldt al dat er geen sjabloon aangeboden wordt
            opschrift = " ".join(re.sub("<[^>]+>", " ", m.group(1)).split())
            if opschrift != KNOPTEKST:
                ctx.fout(opdracht, f'de downloadknop heet "{opschrift}"; de docx is het enige '
                                   f'bestand dat deze pagina aanbiedt, dus dat is "{KNOPTEKST}"')
