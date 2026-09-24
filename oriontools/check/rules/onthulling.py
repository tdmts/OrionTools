"""Een onthulcomponent betekent een ding (Microcontrollers en IR, solution-reveal.js).

Twee componenten verbergen iets achter een klik, en ze zijn niet uitwisselbaar;
het verschil is didactisch en niet visueel. Beide regels gelden alleen waar
solution-reveal.js het contract van de oplossing is (heeft_solution_reveal):
DeN en ICEES tonen hun antwoorden juist in de spoiler-container van OrionCSS,
via oplossingen.js, en daar zou spoiler-retired elke vraag afkeuren.
"""

import re

from ..regel import Regel
from .wiring import heeft_solution_reveal

H2_RE = re.compile(r"<h2")
H2_ID_RE = re.compile(r'.*<h2[^>]*id="([^"]*)"')
SOLUTION_DIV_RE = re.compile(r'<div[^>]*class="[^"]*solution-container')
SPOILER_DIV_RE = re.compile(r'<div[^>]*class="[^"]*spoiler-container')


class SolutionPlaatsing(Regel):
    """Een solution-container staat alleen onder een <h2 id="oplossing...">.

    .solution-container is de eenrichtingsknop van solution-reveal.js: een
    knop, en eens weg is er geen terug. Dat klopt voor DE oplossing, waar een
    student die kijkt de oefening toch al afgesloten heeft, en is fout erboven,
    waar een verborgen antwoord er is om na te denken, te controleren en verder
    te lezen. Een denkvraag die niet meer dicht kan, is opgebruikt bij de eerste
    blik. Een hint, een denkvraag of een uitgewerkte berekening is dus een
    .accordion-item met een <div class="title">, dat zo vaak open en dicht gaat
    als de lezer wil.

    "De oplossing" is geen oordeel maar de sectie onder een <h2> waarvan de id
    met "oplossing" begint: id="oplossing" op een labo-oefening en het paar
    oplossing-schema / oplossing-code op de voorbeeldtesten. Dezelfde anker
    waarop audit-oplossing en --no-solutions van export-pdf sleutelen.

    Blokkerend en zonder audit-skip, want de fout is stil: een hint in een
    eenrichtingsknop ziet er in de browser niet verkeerd uit. De sectie wordt
    per regel bijgehouden, zoals de awk van de bash-check deed: elke <h2>
    draagt een id, dus dat is exact en geen gok.
    """

    id = "solution-placement"
    legacy = ("MC:7", "IR:7")

    def van_toepassing(self, ctx):
        return heeft_solution_reveal(ctx)

    def controleer(self, ctx):
        for pad in ctx.paginas:
            sectie = ""
            for nr, regel in enumerate(ctx.tekst(pad).split("\n"), 1):
                if H2_RE.search(regel):
                    m = H2_ID_RE.match(regel)
                    sectie = m.group(1) if m else "(no id)"
                if SOLUTION_DIV_RE.search(regel) and not sectie.startswith("oplossing"):
                    waar = f'<h2 id="{sectie}">' if sectie else "geen enkele <h2>"
                    ctx.fout(pad, f"solution-container onder {waar}: de eenrichtingsknop is "
                                  'voor DE oplossing, onder <h2 id="oplossing...">; een hint of '
                                  "denkvraag is een accordion-item", regelnr=nr)


class SpoilerRetired(Regel):
    """Geen .spoiler-container: waar solution-reveal.js de oplossing toont, is die met pensioen.

    De spoiler van OrionCSS was een derde manier om een alinea te verbergen, ze
    lijkt op geen van de andere twee, en wat erin stond is precies wat een
    accordion-item bevat. Drie componenten voor twee taken is hoe een pagina
    per ongeluk kiest. Wat een oplossing is, gaat in een solution-container
    onder <h2 id="oplossing">, de rest in een accordion-item.

    Alleen in een vak met solution-reveal.js: in DeN en ICEES is de
    spoiler-container net de onthulling van een antwoord (oplossingen.js).
    """

    id = "spoiler-retired"
    legacy = ("MC:7", "IR:7")

    def van_toepassing(self, ctx):
        return heeft_solution_reveal(ctx)

    def controleer(self, ctx):
        for pad in ctx.paginas:
            for nr, regel in enumerate(ctx.tekst(pad).split("\n"), 1):
                if SPOILER_DIV_RE.search(regel):
                    ctx.fout(pad, "spoiler-container is met pensioen: een accordion-item met "
                                  '<div class="title">, of een solution-container onder '
                                  '<h2 id="oplossing"> als het echt de oplossing is', regelnr=nr)
