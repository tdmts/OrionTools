"""De hub van een labo (overview.html) en de introducties van dat labo."""

import re
from difflib import SequenceMatcher

from ..regel import Regel
from ._gedeeld import COMMENTAAR_RE, TAGS_RE, overview_paginas

VERLOOP_KOP_RE = re.compile(r'<h[1-6][^>]*\bid="verloop"|<h[1-6][^>]*>\s*verloop\b', re.I)
STAPPEN_RE = re.compile(r'class="[^"]*\bsteps-container\b', re.I)
SESSIETELLING_RE = re.compile(
    r"\b(een|één|twee|drie|vier|vijf|zes|zeven|acht|negen|tien|\d+)\s+"
    r"sessies?\b[^.]{0,80}?\bvoorzien\b", re.I)
PERCENTAGE_RE = re.compile(r"\[\s*\d{1,3}\s*%\s*\]")


def heeft_hub(ctx):
    return True if overview_paginas(ctx) else "geen overview.html"


def _zichtbaar(ctx, pad):
    return COMMENTAAR_RE.sub("", ctx.tekst(pad))


class GeenVerloop(Regel):
    """Geen verloop op overview.html: geen kop Verloop en geen steps-container.

    De hub zegt wat het labo is, wat je nodig hebt en hoe het meetelt; hij
    vertelt niet in welke volgorde je te werk gaat. Zo'n stappenplan herhaalt
    wat het Orion-menu en Opdracht.html zelf al tonen, en het telt op wat elders
    staat ("zes theoriepagina's", "tien vragen", "zeven schakelingen"). Die
    getallen staan in orion.json en in het verslagcommentaar, niet hier. Ze
    lopen dus stil uit de pas zodra daar iets bijkomt, en niets faalt. De
    volgorde hoort bij het menu en de pagina's die haar dragen.
    """

    id = "no-verloop"
    legacy = ("DeN:9", "ICEES:9")

    def van_toepassing(self, ctx):
        return heeft_hub(ctx)

    def controleer(self, ctx):
        for pad in overview_paginas(ctx):
            zichtbaar = _zichtbaar(ctx, pad)
            if VERLOOP_KOP_RE.search(zichtbaar):
                ctx.fout(pad, "een kop Verloop hoort niet op de hub: de volgorde staat in het "
                              "Orion-menu en in de opdracht, en loopt hier stil uit de pas")
            if STAPPEN_RE.search(zichtbaar):
                ctx.fout(pad, "een steps-container hoort niet op de hub: dat is een stappenplan "
                              "dat herhaalt wat het Orion-menu en de opdracht zelf al tonen")


class GeenSessietelling(Regel):
    """Geen sessietelling op overview.html ("voor dit labo zijn twee sessies voorzien").

    Hoeveel sessies een labo krijgt en wanneer het doorgaat, staat in de
    planning (Algemeen/Planning.html), en het verschilt per groep: de ene groep
    volgt een andere volgorde dan de andere. Een getal op de hub is dus een
    kopie die voor een deel van de studenten sowieso niet klopt. Dat was geen
    theorie: een hub zei een sessie waar de planning er twee toonde.

    Dit is een struikeldraad en geen bewijs. Ze grijpt op "N sessies ...
    voorzien", dus een telling die anders geformuleerd is, glipt erdoor. De
    werkafspraak "zorg dat je klaar bent voor het einde van een sessie" blijft
    toegelaten: dat is een regel en geen getal.
    """

    id = "no-session-count"
    legacy = ("DeN:9", "ICEES:9")

    def van_toepassing(self, ctx):
        return heeft_hub(ctx)

    def controleer(self, ctx):
        for pad in overview_paginas(ctx):
            plat = " ".join(TAGS_RE.sub(" ", _zichtbaar(ctx, pad)).split())
            if SESSIETELLING_RE.search(plat):
                ctx.fout(pad, "een sessietelling hoort niet op de hub: hoeveel sessies dit labo "
                              "krijgt staat in Algemeen/Planning.html en verschilt per groep")


class GeenGewicht(Regel):
    """Geen gewicht in procent op overview.html ("[40%]").

    Wat een onderdeel bijdraagt, staat op de evaluatiepagina
    (Algemeen/Evaluatie.html), waar de labo's naast elkaar staan en samen met de
    theorie optellen tot een eindcijfer. Los op een hub is een percentage een
    breuk zonder noemer: waar binnen dat labo, en stil over wat het labo voor
    het vak betekent. Wat wel op de hub blijft, is de vorm van de evaluatie (een
    test gesloten boek, een verslag dat zelf geen punt krijgt) en de
    werkafspraken die eruit volgen.
    """

    id = "no-weight"
    legacy = ("DeN:9", "ICEES:9")

    def van_toepassing(self, ctx):
        return heeft_hub(ctx)

    def controleer(self, ctx):
        for pad in overview_paginas(ctx):
            if PERCENTAGE_RE.search(_zichtbaar(ctx, pad)):
                ctx.fout(pad, "een gewicht in procent hoort niet op de hub: wat een onderdeel "
                              "bijdraagt staat in Algemeen/Evaluatie.html, naast de andere labo's")


LEAD_BLOK_RE = re.compile(r'<p class="[^"]*\blead\b[^"]*"[^>]*>(.*?)</p>', re.S | re.I)
ENTITEIT_RE = re.compile(r"&[a-z]+;|&#\d+;", re.I)
WOORD_RE = re.compile(r"[\w/-]+", re.UNICODE)

# Vanaf zoveel woorden op een rij is het geen toeval meer maar een kopie. Acht
# liet "een HP ProCurve via de seriele console" nog door, zes greep op wendingen
# die toevallig samenvielen ("verkeer van je eigen computer").
GEDEELDE_WOORDEN = 7


class DubbeleLead(Regel):
    """Twee introducties van hetzelfde labo vertellen niet hetzelfde.

    Een labo heeft een lead per menu-item in Orion dat er een heeft, en elk
    heeft een eigen taak: overview.html zegt waar het labo over gaat en waarom,
    Opdracht.html zegt wat je doet en indient. Die van de opdracht komt
    bovendien op de eerste bladzijde van het verslag terecht (opdracht-lead),
    dus ze moet op zichzelf leesbaar zijn.

    Samenvoegen tot een enkele tekst kan niet: het zijn aparte items in het
    Orion-menu en er linkt niets zijwaarts (topic-frame), dus elke ingang moet
    alleen staan. Wat wel kan, is dat er geen twee dezelfde zin in staat. Die
    ontstaat vanzelf: je herschrijft er een, en de andere blijft de oude versie
    navertellen.

    De regel grijpt op een letterlijk gedeelde woordenreeks van zeven woorden of
    meer tussen twee leads van hetzelfde labo. Ze kijkt niet naar betekenis, dus
    een herhaling die herschreven is glipt erdoor, en een feit dat in twee leads
    thuishoort mag gerust, zolang het er niet twee keer hetzelfde staat.
    """

    id = "duplicate-lead"
    legacy = ("DeN:12", "ICEES:12")

    def van_toepassing(self, ctx):
        return heeft_hub(ctx)

    def _woorden(self, ctx, pagina):
        m = LEAD_BLOK_RE.search(_zichtbaar(ctx, pagina))
        if not m:
            return []
        plat = ENTITEIT_RE.sub(" ", TAGS_RE.sub(" ", m.group(1))).lower()
        return WOORD_RE.findall(plat)

    def controleer(self, ctx):
        for overview in overview_paginas(ctx):
            module = overview.parent
            paginas = [overview] + sorted(module.glob("Opdracht.html"))
            paginas += sorted(module.glob("*/Opdracht.html"))
            paginas = [p for p in paginas if p.is_file()]
            woorden = {p: self._woorden(ctx, p) for p in paginas}
            for i, eerste in enumerate(paginas):
                for tweede in paginas[i + 1:]:
                    a, b = woorden[eerste], woorden[tweede]
                    if not a or not b:
                        continue
                    m = SequenceMatcher(None, a, b, autojunk=False).find_longest_match(
                        0, len(a), 0, len(b))
                    if m.size >= GEDEELDE_WOORDEN:
                        zin = " ".join(a[m.a:m.a + m.size])
                        ctx.fout(eerste, f'de lead deelt "{zin}" met {ctx._rel(tweede)}; die '
                                         "twee introducties horen elk iets anders te zeggen")
