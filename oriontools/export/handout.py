"""Druk een deck uit Hoorcollege/ af als de handout die de student meebrengt.

    python ../OrionTools/orion.py export-handout Sessie1
    python ../OrionTools/orion.py export-handout Sessie1 --html-only   # zonder Chrome

De decks staan in paths.decks van het vak (standaard Hoorcollege/). De uitvoer
is <downloads>/<handout.prefix><naam>.pdf, bij DeN dus
downloads/DeN-handout-sessie-1.pdf, en die is GECOMMIT, net als de syllabus:
OrionSync spiegelt alleen wat in git zit naar Brightspace, en van een
deck is de PDF het enige dat hij ooit te zien krijgt. De titel onderaan elk
blad begint met course.title.

HET IS DEZELFDE SLIDE, ALLEEN KLEINER. De bundel laadt hoorcollege.css (wat een
slide van binnen is) en legt daar handout.css bovenop (wat het blad ermee doet).
Er wordt hier dus niets hertekend en er staat hier geen opmaak; staat er iets
niet goed op papier, dan hoort dat in handout.css opgelost te worden. Waar die
twee staan, en waarom hoorcollege.css uit de checkout van OrionCSS komt, zegt
oriontools/huisstijl.py.

Een gang door Chrome volstaat. De syllabus heeft er drie nodig omdat haar
inhoudstafel paginanummers draagt die pas na het drukken bekend zijn; een
handout heeft geen inhoudstafel. De kop- en voettekst worden er wel op dezelfde
manier achteraf op gestempeld met reportlab, want via de commandoregel zet
Chrome alleen zijn eigen voettekst, met de datum en de bestands-URL erin.

Chrome zoeken staat in oriontools/chrome.py, en afdrukken en de letters van de
stempel in oriontools/export/pdfhulp.py, gedeeld met de syllabus in plaats van
overgeschreven: twee kopieen van dezelfde lijst zoekpaden lopen uit elkaar
zodra er ergens een browser bijkomt. In de vakrepo's laadde dit script daarvoor
export-syllabus.py in; dat hoeft niet meer.
"""

import argparse
import html
import io
import re
import shutil
import sys
import tempfile
from pathlib import Path

from .. import huisstijl, repo
from ..chrome import zoek_chrome
from . import pdfhulp

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    sys.exit("pypdf ontbreekt:  pip install pypdf")

try:
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas
except ImportError:
    sys.exit("reportlab ontbreekt:  pip install reportlab")


# ------------------------------------------------------------- de bundel

def slides_uit(deck):
    """De <section class="slide">-blokken van een deck, in volgorde."""
    tekst = deck.read_text(encoding="utf-8")
    return re.findall(r'<section class="slide.*?</section>', tekst, re.S)


def absolute_paden(fragment, map_van_deck):
    """../img/x.png wordt een file-URI, want de bundel staat elders.

    Chrome leest de bundel uit een tijdelijke map, dus een relatief pad wijst
    daar naar niets. Een ontbrekende afbeelding drukt af als een leeg vlak en
    zegt verder niets, dus dit mag niet stilletjes misgaan.
    """
    def vervang(match):
        attribuut, waarde = match.group(1), match.group(2)
        if waarde.startswith(("http:", "https:", "mailto:", "data:", "file:",
                              "#")):
            return match.group(0)
        doel = (map_van_deck / waarde).resolve()
        if not doel.exists():
            sys.exit(f"de bundel verwijst naar {waarde}, en dat bestaat niet")
        return f'{attribuut}="{doel.as_uri()}"'

    return re.sub(r'(src|href)="([^"]+)"', vervang, fragment)


def bouw_bundel(slides, titel):
    # Vijf vakken van 9mm, elk met een lijn eronder, zodat de onderste gelijk
    # valt met de onderkant van de slide. Met zes wordt het 7.5mm en dat is krap
    # om met de hand in te schrijven. Als elementen, want een verloop wordt bij
    # het drukken een patroon, en niet elke PDF-lezer tekent
    # dat: de eerste proefdruk gaf roze vlakken waar de schrijfruimte hoorde.
    ruimte = '<div class="ruimte">' + "<i></i>" * 5 + "</div>"
    # Het nummer in de marge komt uit data-slide en niet uit de plaats in het
    # deck. Die twee lopen uiteen, want een deck begint bij slide 2, en het is
    # data-slide dat op de beamer staat en dat in de les genoemd wordt. Stond
    # hier de plaats, dan zou een student die "slide 45" hoort op zijn blad bij
    # 44 uitkomen.
    rijen = []
    for plaats, slide in enumerate(slides, 1):
        gevonden = re.search(r'data-slide="(\d+)"', slide)
        nr = gevonden.group(1) if gevonden else plaats
        rijen.append(f'<div class="rij"><div class="nr">{nr}</div>'
                     f'<div class="kader">{slide}</div>{ruimte}</div>')
    css = "\n".join(
        f'<link rel="stylesheet" href="{stijl.as_uri()}">'
        for stijl in (huisstijl.hoorcollege_css(), huisstijl.handout_css()))
    return ("<!DOCTYPE html>\n"
            '<html lang="nl">\n<head>\n<meta charset="utf-8">\n'
            f"<title>{html.escape(titel)}</title>\n{css}\n</head>\n"
            '<body style="--slide-breedte: 254mm; --slide-hoogte: 143mm">\n'
            + "\n".join(rijen)
            + "\n</body>\n</html>\n")


# ------------------------------------------------------- kop- en voettekst

def stempel(bron_pdf, titel, letters):
    """De titel linksonder, het bladnummer rechtsonder.

    Onderaan en niet bovenaan zoals in de syllabus: daar staat het nummer boven
    omdat de Word dat doet, hier is de bovenrand de eerste slide en zou een
    nummer ertegenaan lezen als een onderschrift bij de verkeerde slide.
    """
    gewoon, vet = letters
    lezer = PdfReader(str(bron_pdf))
    schrijver = PdfWriter()
    for i, bladzijde in enumerate(lezer.pages):
        breedte = float(bladzijde.mediabox.width)
        hoogte = float(bladzijde.mediabox.height)
        laag = io.BytesIO()
        c = rl_canvas.Canvas(laag, pagesize=(breedte, hoogte))
        c.setFont(gewoon, 8)
        c.setFillGray(0.45)
        c.drawString(14 * mm, 9 * mm, titel)
        c.setFont(vet, 8)
        c.drawRightString(breedte - 14 * mm, 9 * mm,
                          f"{i + 1} / {len(lezer.pages)}")
        c.save()
        laag.seek(0)
        bladzijde.merge_page(PdfReader(laag).pages[0])
        schrijver.add_page(bladzijde)
    return schrijver


# -------------------------------------------------------------------- main

def leesbaar(naam):
    """Sessie1 wordt "Sessie 1"; het cijfer hoort niet tegen het woord."""
    return re.sub(r"(?<=[a-z])(?=\d)", " ", naam)


def kebab(naam):
    return re.sub(r"(?<!^)(?=[A-Z0-9])", "-", naam).lower()


def main(argv):
    p = argparse.ArgumentParser(prog="orion.py export-handout")
    p.add_argument("naam", help="de bestandsnaam van het deck, zonder .html")
    p.add_argument("--titel", help="wat er onderaan elk blad staat")
    p.add_argument("--chrome")
    p.add_argument("--html-only", action="store_true")
    repo.voeg_repo_toe(p)
    args = p.parse_args(argv)
    vak = repo.vind(args)
    wortel = vak.root
    decks = vak.pad("decks")
    uit = vak.pad("downloads")

    # Zonder prefix zou de handout van elk vak op dezelfde naam uitkomen, en
    # zonder titel stond er onderaan elk blad alleen ", sessie 1".
    prefix = vak.config["handout"]["prefix"]
    if not prefix:
        sys.exit("oriontools: handout.prefix ontbreekt in oriontools.json")
    if not vak.titel and not args.titel:
        sys.exit("oriontools: course.title ontbreekt in oriontools.json")

    deck = decks / f"{args.naam}.html"
    if not deck.exists():
        sys.exit(f"geen deck gevonden: {deck.relative_to(wortel)}")

    titel = args.titel or f"{vak.titel}, {leesbaar(args.naam).lower()}"
    slides = slides_uit(deck)
    if not slides:
        sys.exit(f"{deck.relative_to(wortel)} bevat geen enkele slide")

    for stijl in (huisstijl.hoorcollege_css(), huisstijl.handout_css()):
        if not stijl.exists():
            # Zonder stijlblad drukt Chrome gewoon af, in de standaardopmaak
            # van de browser, en klaagt nergens over.
            sys.exit(f"{stijl} ontbreekt; zonder dat bestand heeft de handout "
                     "geen opmaak (zie oriontools/huisstijl.py)")

    bundel = absolute_paden(bouw_bundel(slides, titel), decks)
    werkmap = Path(tempfile.mkdtemp(prefix="handout-"))
    bundel_pad = werkmap / "handout.html"
    bundel_pad.write_text(bundel, encoding="utf-8")

    if args.html_only:
        print(f"{bundel_pad}: {len(slides)} slides")
        return 0

    chrome = zoek_chrome(args.chrome)
    rauw = werkmap / "rauw.pdf"
    pdfhulp.druk_af(chrome, bundel_pad, rauw)

    uit.mkdir(parents=True, exist_ok=True)
    doel = uit / f"{prefix}{kebab(args.naam)}.pdf"
    schrijver = stempel(rauw, titel, pdfhulp.stempelletters())
    with open(doel, "wb") as f:
        schrijver.write(f)
    shutil.rmtree(werkmap, ignore_errors=True)

    bladen = len(PdfReader(str(doel)).pages)
    print(f"{doel.relative_to(wortel)}: {len(slides)} slides op {bladen} bladen")
    return 0
