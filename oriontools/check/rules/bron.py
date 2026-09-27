"""data-bron: over welke theorie een vraag of een doelstelling gaat."""

import html
import posixpath

from ..regel import Regel
from ._gedeeld import BRON_RE, COMMENTAAR_RE


def zonder_commentaar(tekst):
    """De tekst met elk commentaar weg, maar met zijn regeleinden, zodat een regelnummer klopt."""
    return COMMENTAAR_RE.sub(lambda m: "\n" * m.group(0).count("\n"), tekst)


def met_bron(ctx):
    """(pad, regelnr, [pad in data-bron]) voor elke data-bron op een pagina die de check ziet."""
    if "_bronnen" not in ctx.__dict__:
        uit = []
        for pad in ctx.paginas:
            tekst = zonder_commentaar(ctx.tekst(pad))
            for m in BRON_RE.finditer(tekst):
                uit.append((pad, tekst.count("\n", 0, m.start()) + 1,
                            [html.unescape(p) for p in m.group(1).split()]))
        ctx._bronnen = uit
    return ctx._bronnen


class DataBron(Regel):
    """Elk pad in een data-bron bestaat, vanaf de root en met exact die hoofdletters.

    data-bron zegt over welke theorie iets gaat: op de <li> van een vraag, en
    op de <li> van een doelstelling onder <h2 id="doelstellingen">. ans-dekking
    leest het, en vergelijkt die paden als tekst met de paden waarnaar een
    vraag in ANS wijst. Een tikfout, een verkeerde hoofdletter of een pad met
    ../ geeft daar dus geen fout, maar een doelstelling die voor altijd "geen
    vraag in ANS" blijft terwijl de vraag er staat. ans-dekking praat met ANS
    en draait niet in CI; deze regel wel.

    Een toets in paths.toets ziet de check niet. Daar doet export-qti dezelfde
    controle, voor het pakket gebouwd wordt.
    """

    id = "data-bron"
    legacy = ()

    def van_toepassing(self, ctx):
        return True if met_bron(ctx) else "geen data-bron"

    def controleer(self, ctx):
        for pad, regelnr, paden in met_bron(ctx):
            if not paden:
                ctx.fout(pad, "lege data-bron: laat het attribuut weg", regelnr=regelnr)
            for p in paden:
                if p.startswith(("/", "../")) or posixpath.normpath(p) != p:
                    ctx.fout(pad, f"data-bron {p} is geen pad vanaf de root van het vak",
                             regelnr=regelnr)
                elif not (ctx.root / p).is_file():
                    ctx.fout(pad, f"data-bron {p} bestaat niet", regelnr=regelnr)
                elif not ctx.exacte_hoofdletters(ctx.root / p):
                    ctx.fout(pad, f"data-bron {p}: de hoofdletters kloppen niet, dus "
                                  "ans-dekking vindt de pagina niet terug", regelnr=regelnr)
