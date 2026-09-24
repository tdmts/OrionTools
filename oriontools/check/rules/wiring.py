"""Elke sitepagina hangt aan de gehoste OrionCSS."""

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
    legacy = ("DeN:3", "ICEES:3")

    def controleer(self, ctx):
        for pad in ctx.sitepaginas:
            tekst = ctx.tekst(pad)
            if ORION_CSS not in tekst:
                ctx.fout(pad, "linkt de gehoste OrionCSS style.css niet")
            if ORION_JS not in tekst:
                ctx.fout(pad, "linkt de gehoste OrionCSS main.js niet")
