"""Wat elke PDF-export deelt: Chrome laten afdrukken en de letters van de stempel.

De syllabus en de handouts drukken allebei een HTML-bundel af met een headless
Chrome en stempelen er achteraf met reportlab een kop- of voettekst op. In de
vakrepo's laadde export-handout.py daarvoor export-syllabus.py als module in;
hier staat het gedeelde apart, zodat een handout niet de hele syllabusexport
meesleept om twee functies te lenen.

Het zoeken van Chrome zelf staat in oriontools/chrome.py, want export-verslag
heeft het ook nodig en mag geen pypdf of reportlab laden.
"""

import subprocess
import sys
from pathlib import Path

from ..chrome import zoek_chrome  # noqa: F401  (hier ook te halen, voor het gemak)

ARIAL_KANDIDATEN = [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf",
     "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
]


def stempelletters():
    """(gewoon, vet) voor de kop- en voettekst, in Arial als dat te vinden is.

    Helvetica zit in elke PDF-lezer ingebakken en lijkt er sterk op, maar het is
    het lettertype van de rest van dit document niet. Staat Arial nergens, dan is
    Helvetica de terugval en scheelt het alleen een haartje.
    """
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        sys.exit("reportlab ontbreekt:  pip install reportlab")
    for gewoon, vet in ARIAL_KANDIDATEN:
        if Path(gewoon).exists() and Path(vet).exists():
            try:
                pdfmetrics.registerFont(TTFont("SyllabusArial", gewoon))
                pdfmetrics.registerFont(TTFont("SyllabusArial-Bold", vet))
                return "SyllabusArial", "SyllabusArial-Bold"
            except Exception:
                pass
    return "Helvetica", "Helvetica-Bold"


def druk_af(chrome, html_pad, pdf_pad):
    """Laat Chrome html_pad afdrukken naar pdf_pad, zonder zijn eigen kop en voet."""
    opdracht = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                "--no-pdf-header-footer", "--virtual-time-budget=20000",
                f"--print-to-pdf={pdf_pad}", Path(html_pad).as_uri()]
    klaar = subprocess.run(opdracht, capture_output=True, text=True)
    if not Path(pdf_pad).exists():
        sys.exit(f"Chrome maakte geen PDF:\n{klaar.stderr[-2000:]}")
