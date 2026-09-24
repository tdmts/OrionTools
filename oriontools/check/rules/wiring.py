"""Wat een pagina laadt: de gehoste OrionCSS, en de scripts van de repo die ze gebruikt."""

import re

from ..context import ORION_CSS, ORION_JS
from ..regel import Regel


class OrionCssWiring(Regel):
    """Elke sitepagina linkt de gehoste OrionCSS: style.css en main.js, op hun absolute URL.

    De huisstijl leeft in tdmts/OrionCSS en niet in de vakrepo. OrionSync
    herschrijft die URL's onderweg naar zijn eigen spiegel in de cursus; de repo
    houdt ze absoluut, zodat een lokale preview gewoon opgemaakt is. Een pagina
    zonder die twee staat in Orion kaal, en zonder main.js werkt geen enkele
    component die gedrag heeft (uitklappers, spoilers, tabs).

    Een pagina uit exempt_pages valt erbuiten, en zo ook de html in een map uit
    non_site_dirs. Een deck onder Hoorcollege/ is een document, geen pagina: het
    staat in geen Orion-menu, de student ziet er alleen de handout-PDF van, en
    het laadt zijn eigen stylesheet in plaats van OrionCSS, want twee
    stylesheets over elkaar is bij elk verschil gokken wie wint.
    """

    id = "orioncss-wiring"
    legacy = ("DeN:3", "ICEES:3", "MC:3", "IR:3")

    def controleer(self, ctx):
        gecontroleerd = set(ctx.paginas)
        for pad in ctx.sitepaginas:
            if pad not in gecontroleerd:
                continue
            tekst = ctx.tekst(pad)
            if ORION_CSS not in tekst:
                ctx.fout(pad, "linkt de gehoste OrionCSS style.css niet")
            if ORION_JS not in tekst:
                ctx.fout(pad, "linkt de gehoste OrionCSS main.js niet")


CHECKLIST_RE = re.compile(r'class="checklist"')
SYNC_RE = re.compile(r"checklist-sync\.js")
INIT_RE = re.compile(r"""initChecklistSync\(\{\s*labId:\s*["'](labo[0-9]+)["']""")
LABMAP_RE = re.compile(r"^Labo([0-9]+)/")


class ChecklistWiring(Regel):
    """Een pagina met een checklist laadt checklist-sync.js en noemt haar eigen labo.

    De vinkjes van de student staan in localStorage onder een sleutel waarvan
    de labId de helft is. Een pagina die uit een ander labo gekopieerd werd,
    zou haar voortgang dus stil onder dat andere labo opbergen. Daarom roept
    elke checklist initChecklistSync({ labId: 'laboN', exerciseId: '...' })
    aan, en klopt N met de map LaboN/ waar de pagina in staat. Zonder
    checklist-sync.js blijft de checklist een lijst die niets onthoudt.

    Van toepassing zodra een pagina een class="checklist" draagt; de vorm
    laboN is het contract van checklist-sync.js zelf.
    """

    id = "checklist-wiring"
    legacy = ("MC:3",)

    def van_toepassing(self, ctx):
        if any(CHECKLIST_RE.search(ctx.tekst(p)) for p in ctx.paginas):
            return True
        return "geen pagina met een checklist"

    def controleer(self, ctx):
        for pad in ctx.paginas:
            tekst = ctx.tekst(pad)
            if not CHECKLIST_RE.search(tekst):
                continue
            m = LABMAP_RE.match(pad.relative_to(ctx.root).as_posix())
            lab = f"labo{m.group(1)}" if m else ""
            if not SYNC_RE.search(tekst):
                ctx.fout(pad, "heeft een checklist maar laadt checklist-sync.js niet")
            init = INIT_RE.search(tekst)
            if not init:
                ctx.fout(pad, "heeft een checklist maar roept nooit initChecklistSync({ labId: "
                              f"'{lab or 'laboN'}', exerciseId: '...' }}) aan")
            elif lab and init.group(1) != lab:
                ctx.fout(pad, f"staat in {lab} maar roept initChecklistSync aan met labId "
                              f"'{init.group(1)}'")


# Op het class-attribuut en niet op het losse woord: het woord staat ook in
# proza die de component uitlegt (template.html, een kopcommentaar).
SOLUTION_RE = re.compile(r'class="[^"]*solution-container')
REVEAL_RE = re.compile(r"solution-reveal\.js")


def heeft_solution_reveal(ctx):
    """Is solution-reveal.js hier het contract van de oplossing?

    Twee families: Microcontrollers en IR tonen een oplossing met de
    eenrichtingsknop van solution-reveal.js, DeN en ICEES met de
    spoiler-container van OrionCSS die oplossingen.js neerzet. De regels van de
    eerste familie verbieden precies wat de tweede gebruikt, dus ze gelden
    alleen waar het script in de root van de repo staat.
    """
    if (ctx.root / "solution-reveal.js").is_file():
        return True
    return "geen solution-reveal.js in de root"


class SolutionRevealWiring(Regel):
    """Een solution-container en solution-reveal.js gaan samen, in beide richtingen.

    Zonder het script opent de knop niets en ziet de student nooit de
    oplossing. Omgekeerd: een pagina waarvan de laatste solution-container naar
    een accordeon verhuisde (solution-placement), laadt het script nog en bindt
    dan niets. Onschuldig in de browser, en precies het restant dat de volgende
    auteur doet denken dat hier nog een oplossing te tonen valt. --fix haalt die
    ene <script>-regel weg.
    """

    id = "solution-reveal-wiring"
    legacy = ("MC:3", "IR:3")

    def van_toepassing(self, ctx):
        return heeft_solution_reveal(ctx)

    def controleer(self, ctx):
        for pad in ctx.paginas:
            tekst = ctx.tekst(pad)
            container, script = SOLUTION_RE.search(tekst), REVEAL_RE.search(tekst)
            if container and not script:
                ctx.fout(pad, "heeft een solution-container maar laadt solution-reveal.js niet")
            elif script and not container:
                ctx.fout(pad, "laadt solution-reveal.js maar heeft geen solution-container meer "
                              "(haal de include weg)")
