"""Druk het spiekblad van een labo af als de PDF die de student naast zich legt.

    python ../OrionTools/orion.py export-spiekblad Labo/LinuxBasis
    python ../OrionTools/orion.py export-spiekblad Labo/LinuxBasis --html-only

De bron is <labo>/Theorie/Spiekblad.html, de pagina die ook in de cursus staat.
De uitvoer is <downloads>/<labopad met streepjes>-spiekblad.pdf, bij ICEES dus
downloads/Labo-LinuxBasis-spiekblad.pdf: dezelfde naamregel als het
verslagsjabloon ernaast. Ze wordt GECOMMIT, want OrionSync spiegelt alleen wat
in git zit.

HET IS DEZELFDE PAGINA, ANDERS OPGEMAAKT. De bundel neemt de inhoud van de
pagina over en legt er spiekblad.css op in plaats van OrionCSS. Er wordt hier
dus geen tekst geschreven: staat er iets fout op papier, dan staat het fout op
de pagina, en daar wordt het rechtgezet. Drie dingen gaan eruit, en ze gaan er
alle drie uit omdat ze over het scherm gaan:

- de <h1> en de eerste alinea eronder. Die zegt bij elk spiekblad dat je de
  pagina in een tweede venster openhoudt. De kop wordt opnieuw gezet, met de
  naam van het labo erbij, want op papier ligt het blad los van de cursus.
- de download-container, die naar deze PDF zelf wijst.
- elke <a>, die tot haar tekst herleid wordt. Een link op papier is blauwe
  tekst waar niemand op klikt.

De naam van het labo komt uit de <h1> van <labo>/overview.html, zonder het
woord Labo ervoor. Een spiekblad zonder Inleiding ernaast drukt zonder naam.

Of de PDF bij haar pagina blijft, bewaakt de regel spiekblad-stale: die grijpt
op de link die de pagina zelf naar haar PDF legt.
"""

import argparse
import html
import re
import shutil
import sys
import tempfile
from pathlib import Path

from .. import huisstijl, repo
from ..chrome import zoek_chrome
from . import pdfhulp
from .handout import absolute_paden, stempel

try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("pypdf ontbreekt:  pip install pypdf")


def pagina_van(wortel, doel):
    """Labo/LinuxBasis of het pad naar de pagina zelf; geeft (labomap, pagina)."""
    pad = (wortel / doel).resolve()
    if pad.suffix == ".html":
        labo = pad.parent.parent if pad.parent.name == "Theorie" else pad.parent
        return labo, pad
    return pad, pad / "Theorie" / "Spiekblad.html"


def pdf_naam(wortel, labo):
    """Labo/LinuxBasis wordt Labo-LinuxBasis-spiekblad.pdf."""
    return "-".join(labo.relative_to(wortel).parts) + "-spiekblad.pdf"


def labonaam(labo):
    """"Linux Basis" uit de <h1> van overview.html, of None."""
    inleiding = labo / "overview.html"
    if not inleiding.exists():
        return None
    m = re.search(r"<h1[^>]*>(.*?)</h1>", inleiding.read_text(encoding="utf-8"), re.S)
    if not m:
        return None
    naam = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
    return re.sub(r"^Labo\s+", "", naam)


def inhoud_van(tekst):
    """Wat er van de pagina op papier komt, als HTML-fragment."""
    m = re.search(r"<body[^>]*>(.*)</body>", tekst, re.S)
    if not m:
        sys.exit("de pagina heeft geen <body>")
    romp = m.group(1)
    romp = re.sub(r"<script\b.*?</script>", "", romp, flags=re.S)
    # De kop en de alinea eronder: ze gaan over het scherm (zie de docstring).
    romp, n = re.subn(r"<h1[^>]*>.*?</h1>\s*(<p\b[^>]*>.*?</p>)?", "", romp,
                      count=1, flags=re.S)
    if not n:
        sys.exit("de pagina heeft geen <h1>; is dit wel een spiekblad?")
    romp = re.sub(r'<div class="download-container">.*?</ul>\s*</div>', "", romp,
                  flags=re.S)
    romp = re.sub(r"<a\b[^>]*>(.*?)</a>", r"\1", romp, flags=re.S)
    return romp


def bouw_bundel(inhoud, titel, labo):
    kop = f'<span class="labo">Labo {html.escape(labo)}</span>' if labo else ""
    return ("<!DOCTYPE html>\n"
            '<html lang="nl">\n<head>\n<meta charset="utf-8">\n'
            f"<title>{html.escape(titel)}</title>\n"
            f'<link rel="stylesheet" href="{huisstijl.spiekblad_css().as_uri()}">\n'
            "</head>\n<body>\n"
            f"<header><h1>Spiekblad</h1>{kop}</header>\n"
            f"{inhoud}\n</body>\n</html>\n")


def main(argv):
    p = argparse.ArgumentParser(prog="orion.py export-spiekblad")
    p.add_argument("labo", help="de labomap (Labo/LinuxBasis) of het pad naar het spiekblad")
    p.add_argument("--chrome")
    p.add_argument("--html-only", action="store_true")
    repo.voeg_repo_toe(p)
    args = p.parse_args(argv)
    vak = repo.vind(args)
    wortel = vak.root
    if not vak.titel:
        sys.exit("oriontools: course.title ontbreekt in oriontools.json")

    labo, pagina = pagina_van(wortel, args.labo)
    if not pagina.exists():
        sys.exit(f"geen spiekblad gevonden: {pagina}")
    if not huisstijl.spiekblad_css().exists():
        # Zonder stijlblad drukt Chrome in de standaardopmaak af en klaagt niet.
        sys.exit(f"{huisstijl.spiekblad_css()} ontbreekt")

    naam = labonaam(labo)
    titel = f"{vak.titel}, spiekblad" + (f" labo {naam}" if naam else "")
    inhoud = absolute_paden(inhoud_van(pagina.read_text(encoding="utf-8")), pagina.parent)

    werkmap = Path(tempfile.mkdtemp(prefix="spiekblad-"))
    bundel_pad = werkmap / "spiekblad.html"
    bundel_pad.write_text(bouw_bundel(inhoud, titel, naam), encoding="utf-8")
    if args.html_only:
        print(bundel_pad)
        return 0

    rauw = werkmap / "rauw.pdf"
    pdfhulp.druk_af(zoek_chrome(args.chrome), bundel_pad, rauw)
    uit = vak.pad("downloads")
    uit.mkdir(parents=True, exist_ok=True)
    doel = uit / pdf_naam(wortel, labo)
    schrijver = stempel(rauw, titel, pdfhulp.stempelletters())
    with open(doel, "wb") as f:
        schrijver.write(f)
    shutil.rmtree(werkmap, ignore_errors=True)

    bladen = len(PdfReader(str(doel)).pages)
    print(f"{doel.relative_to(wortel).as_posix()}: {bladen} bladen")
    if doel.name not in pagina.read_text(encoding="utf-8"):
        print(f"let op: {pagina.relative_to(wortel).as_posix()} linkt nog niet naar "
              f"{doel.name}, dus de student vindt ze niet en spiekblad-stale bewaakt ze niet")
    return 0
