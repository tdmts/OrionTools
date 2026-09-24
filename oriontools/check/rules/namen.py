"""Namen die de student leest: de titel van een oefening."""

import re

from ..regel import Regel
from ._gedeeld import heeft_orion


def naam_re(ctx):
    woorden = "|".join(re.escape(w) for w in ctx.config["check"]["exercise_title_words"])
    return r"(gevorderde|basis|extra|bonus|laatste)?\s*(" + woorden + r")\s*[0-9]"


class OefeningNaam(Regel):
    """Een oefening heet naar wat de student bouwt, niet "Gevorderde oefening 2".

    Een nummer zegt de student niets over wat hij gaat maken, leest als een
    plaatshouder, en betekent niets meer zodra de volgorde verandert. Een label
    zonder nummer ("Begeleide oefening") mag: dat beschrijft de vorm, geen
    plaats in een rij. "deel 1" mag ook, dat noemt een stuk van een taak die al
    een naam heeft.

    Nagekeken: de titels in orion.json (het menu dat de student leest) en de
    <h1> en <title> van elke pagina. Welke woorden een nummer niet mogen
    dragen, zegt check.exercise_title_words (IR voegde "opdracht" toe).
    """

    id = "exercise-name"
    legacy = ("MC:6", "IR:6")

    def van_toepassing(self, ctx):
        if not ctx.config["check"]["exercise_title_words"]:
            return "geen exercise_title_words"
        return True

    def controleer(self, ctx):
        naam = naam_re(ctx)
        titel_re = re.compile(r'"title":\s*"[^"]*' + naam, re.I)
        kop_re = re.compile(r"<(h1|title)>[^<]*" + naam, re.I)
        if heeft_orion(ctx) is True:
            tekst = (ctx.root / "orion.json").read_text(encoding="utf-8")
            for nr, regel in enumerate(tekst.split("\n"), 1):
                if titel_re.search(regel):
                    ctx.fout("orion.json", "generieke titel, noem de oefening naar wat de "
                                           f"student bouwt: {regel.strip()}", regelnr=nr)
        for pad in ctx.paginas:
            for nr, regel in enumerate(ctx.tekst(pad).split("\n"), 1):
                if kop_re.search(regel):
                    ctx.fout(pad, "generieke titel in <h1> of <title>, zeg wat de oefening "
                                  f"bouwt: {regel.strip()}", regelnr=nr)
