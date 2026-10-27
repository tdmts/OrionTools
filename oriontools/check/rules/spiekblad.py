"""Het spiekblad van een labo: een pagina, en een PDF die eruit gedrukt wordt."""

import re

from ... import huisstijl
from ..regel import Regel
from ._gedeeld import lokaal_doel

PDF_RE = re.compile(r'href="([^"]*-spiekblad\.pdf)"')


def spiekbladen(ctx):
    return [p for p in ctx.html if p.name == "Spiekblad.html"]


def labo_van(pagina):
    """Labo/LinuxBasis bij Labo/LinuxBasis/Theorie/Spiekblad.html."""
    return pagina.parent.parent if pagina.parent.name == "Theorie" else pagina.parent


class SpiekbladVerouderd(Regel):
    """Een spiekblad-PDF bestaat waar de pagina ernaar linkt, en is niet ouder dan die pagina.

    Dezelfde regel als verslag-stale en handout-stale, voor het spiekblad. De
    PDF komt uit Spiekblad.html (export-spiekblad), en wie een commando op de
    pagina rechtzet zonder opnieuw te exporteren, ziet het goed op het scherm
    terwijl de student een blad afdrukt met de oude regel. Dat blad ligt het
    hele labo naast zijn toetsenbord.

    De pagina zelf is leidend: de regel grijpt op de link die ze naar haar PDF
    legt, en een spiekblad zonder zo'n link doet niet mee. Niet elk labo wil
    een afdruk, en een PDF waar niets naar linkt, vindt de student niet.
    spiekblad.css telt mee voor elk spiekblad, want een wijziging daar
    verandert elk gedrukt blad zonder dat er een pagina aan te pas komt.

    De regel vergelijkt mtimes en draait dus alleen lokaal: met --ci slaat de
    vergelijking over (zie Context.tijd).
    """

    id = "spiekblad-stale"
    alleen_lokaal = True

    def van_toepassing(self, ctx):
        return True if spiekbladen(ctx) else "geen Spiekblad.html"

    def controleer(self, ctx):
        stijl = huisstijl.spiekblad_css()
        for pagina in spiekbladen(ctx):
            m = PDF_RE.search(ctx.tekst(pagina))
            if not m:
                continue
            opdracht = ("python ../OrionTools/orion.py export-spiekblad "
                        f"{ctx._rel(labo_van(pagina))}")
            pdf = lokaal_doel(pagina, m.group(1))
            if not pdf.exists():
                ctx.fout(pagina, f"linkt naar {m.group(1)}, en die bestaat niet; draai {opdracht}")
                continue
            stempel = ctx.tijd(pdf)
            for bron in [pagina] + ([stijl] if stijl.exists() else []):
                if ctx.tijd(bron) > stempel:
                    ctx.fout(pdf, f"is ouder dan {ctx._rel(bron)}; draai {opdracht}")
                    break
