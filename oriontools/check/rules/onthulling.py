"""Een onthulcomponent betekent een ding.

OrionCSS main.js verbergt een antwoord op twee manieren, en ze zijn niet
uitwisselbaar; het verschil is didactisch en niet visueel. Een vraag uit een
<ol class="vragen"> krijgt een spoiler die open en weer dicht kan, gebouwd uit
li.juist en div.oplossing. DE oplossing van een oefening zit in een
.solution-container, een knop die maar een kant op gaat. Alles wat de lezer
verder wil open- en dichtklappen, is een accordion-item.

Tot fase 2 van OrionTools laadde elk vak daarvoor een eigen script:
oplossingen.js in DeN en ICEES, solution-reveal.js in Microcontrollers en IR.
"""

import re

from ..regel import Regel

H2_RE = re.compile(r"<h2")
H2_ID_RE = re.compile(r'.*<h2[^>]*id="([^"]*)"')
SOLUTION_DIV_RE = re.compile(r'<div[^>]*class="[^"]*solution-container')
SPOILER_DIV_RE = re.compile(r'<div[^>]*class="[^"]*spoiler-container')
SCRIPT_RE = re.compile(r'<script[^>]*src="(?:[^"]*/)?(oplossingen|solution-reveal)\.js"')
SCRIPTS = ("oplossingen.js", "solution-reveal.js")


class SolutionPlaatsing(Regel):
    """Een solution-container staat alleen onder een <h2 id="oplossing...">.

    .solution-container is de eenrichtingsknop van main.js: een knop, en eens
    weg is er geen terug. Dat klopt voor DE oplossing, waar een student die
    kijkt de oefening toch al afgesloten heeft, en is fout erboven, waar een
    verborgen antwoord er is om na te denken, te controleren en verder te
    lezen. Een denkvraag die niet meer dicht kan, is opgebruikt bij de eerste
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
    """Geen .spoiler-container in de HTML: main.js zet hem zelf neer waar hij hoort.

    De spoiler van OrionCSS was een derde manier om een alinea te verbergen,
    naast het accordion-item en de solution-container, en wat erin stond is
    precies wat een van die twee bevat. Drie componenten voor twee taken is hoe
    een pagina per ongeluk kiest. Wat een oplossing is, gaat in een
    solution-container onder <h2 id="oplossing">, de rest in een accordion-item.

    Het antwoord op een vraag is wel een spoiler, maar main.js bouwt hem uit
    <ol class="vragen"> met li.juist en div.oplossing. Met de hand geschreven
    staat de letter er als tekst ("Antwoord b.") en loopt ze stil uit de pas
    zodra twee mogelijkheden van plaats wisselen.
    """

    id = "spoiler-retired"
    legacy = ("MC:7", "IR:7")

    def controleer(self, ctx):
        for pad in ctx.paginas:
            for nr, regel in enumerate(ctx.tekst(pad).split("\n"), 1):
                if SPOILER_DIV_RE.search(regel):
                    ctx.fout(pad, "spoiler-container is met pensioen: een vraag in "
                                  '<ol class="vragen"> met li.juist of div.oplossing, een '
                                  'solution-container onder <h2 id="oplossing">, of anders een '
                                  "accordion-item", regelnr=nr)


class RevealScriptRetired(Regel):
    """Geen oplossingen.js of solution-reveal.js meer: main.js doet het werk.

    Beide scripts waren een kopie per vak, en oplossingen.js werkte alleen als
    het voor de DOMContentLoaded van main.js draaide. main.js bouwt nu zelf de
    vragenlijst en de eenrichtingsknop, met dezelfde markup. Een pagina die een
    van de twee nog laadt, doet het werk dubbel (main.js slaat een vraag die al
    een antwoord heeft over, dus het ziet er niet verkeerd uit), en een script
    in de root gaat met elke sync mee naar de cursus. --fix haalt de
    <script>-regel weg; het bestand verwijder je zelf.
    """

    id = "reveal-script-retired"
    legacy = ("DeN:14", "ICEES:14", "MC:3", "IR:3")

    def controleer(self, ctx):
        for naam in SCRIPTS:
            if (ctx.root / naam).is_file():
                ctx.fout(naam, "is met pensioen: OrionCSS main.js toont de antwoorden en de "
                               "oplossing nu zelf; verwijder het bestand")
        for pad in ctx.paginas:
            for nr, regel in enumerate(ctx.tekst(pad).split("\n"), 1):
                m = SCRIPT_RE.search(regel)
                if m:
                    ctx.fout(pad, f"laadt {m.group(1)}.js, dat met pensioen is: main.js doet het "
                                  "werk (check --fix haalt de include weg)", regelnr=nr)
