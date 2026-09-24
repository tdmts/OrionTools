"""Het hoorcollege: een deck waar een handout-PDF uit gedrukt wordt."""

import re

from ..regel import Regel
from ._gedeeld import lokaal_doel

FIGUUR_RE = re.compile(r'<img\b[^>]*?\bsrc\s*=\s*"([^"]+)"', re.I | re.S)


def handout_van(ctx, deck):
    """downloads/<prefix>sessie-1.pdf bij Hoorcollege/Sessie1.html.

    Dezelfde naamregel als kebab() in de handoutexport, en daarom doet een
    nieuw deck vanzelf mee: er wordt hier geen lijst bijgehouden. Ze staat
    overgeschreven en niet geimporteerd, want de export haalt pypdf en
    reportlab binnen, en de check draait op een kale Python.

    Dat overschrijven is de prijs ervoor. Verandert de naamregel daar, dan moet
    ze hier mee, en niets merkt het verschil: deze regel zoekt dan een PDF die
    niet bestaat en zwijgt, net zoals ze bij een nieuw deck hoort te zwijgen.
    """
    naam = re.sub(r"(?<!^)(?=[A-Z0-9])", "-", deck.stem).lower()
    return ctx.vak.pad("downloads") / f"{ctx.config['handout']['prefix']}{naam}.pdf"


def figuren_van(ctx, deck):
    """De afbeeldingen die dit deck insluit, als bestaande paden.

    Alleen de src van een <img> in dit deck: een tekening die alleen in een
    ander deck staat, hoort niet bij deze handout, ook al ligt ze in dezelfde
    map. Een src die niet bestaat, wordt overgeslagen; dat meldt links al.
    """
    for url in FIGUUR_RE.findall(ctx.tekst(deck)):
        if url.startswith(("http://", "https://", "data:")):
            continue
        doel = lokaal_doel(deck, url)
        if doel is not None and doel.is_file():
            yield doel


class HandoutVerouderd(Regel):
    """Een handout-PDF is niet ouder dan het deck waar ze uit komt.

    Dezelfde regel als verslag-stale en syllabus-stale, voor het derde spoor.
    Een deck staat in geen enkel Orion-menu en er linkt niets naartoe: het
    Orion-topic wijst rechtstreeks naar de handout in paths.downloads, en die
    PDF is dus alles wat de student van dat hoorcollege in handen krijgt. Een
    slide aanpassen zonder export-handout opnieuw te draaien, verandert niets
    aan het blad dat hij meebrengt, terwijl op het scherm alles klopt.

    Ook hoorcollege.css en handout.css tellen mee, voor elke handout. De bundel
    laadt de eerste (wat een slide is) en legt de tweede erover (wat het blad
    ermee doet), dus een wijziging daar verandert elk gedrukt blad zonder dat er
    een slide aan te pas komt.

    En de afbeeldingen die het deck insluit tellen mee, want een handout drukt
    die af en niet de slide waar ze in staat. Dat was geen theorie: vier
    tekeningen zijn bijgesneden, de handouts liepen daardoor achter, en de check
    bleef groen omdat ze alleen naar de slides en de opmaak keek. syllabus-stale
    krijgt die uitbreiding bewust niet: een handout drukt in seconden af, de
    syllabus doet er een minuut over.

    Een deck zonder handout is geen fout: het kan nieuw zijn of nog in aanbouw,
    en dan is er niets om mee te vergelijken. De regel meldt alleen een PDF die
    er wel is en achterloopt, een keer per handout. De naam is
    handout.prefix plus de kebabvorm van het deck (Sessie1 wordt sessie-1).
    Lokaal telt de mtime, in CI de laatste commit.
    """

    id = "handout-stale"
    legacy = ("DeN:17",)
    alleen_lokaal = True

    def van_toepassing(self, ctx):
        decks = ctx.vak.pad("decks")
        if not (decks.is_dir() and any(decks.glob("*.html"))):
            return f"geen deck onder {ctx.config['paths']['decks']}"
        if not ctx.config["handout"]["prefix"]:
            return "handout.prefix is niet ingesteld"
        return True

    def controleer(self, ctx):
        decks = ctx.vak.pad("decks")
        stijlen = [s for s in (decks / "hoorcollege.css", decks / "handout.css") if s.exists()]
        for deck in sorted(decks.glob("*.html")):
            pdf = handout_van(ctx, deck)
            if not pdf.exists():
                continue
            stempel = ctx.tijd(pdf)
            for bron in [deck] + stijlen + sorted(set(figuren_van(ctx, deck))):
                if ctx.tijd(bron) > stempel:
                    ctx.fout(pdf, f"is ouder dan {ctx._rel(bron)}; draai "
                                  f"python ../OrionTools/orion.py export-handout {deck.stem}")
                    break
