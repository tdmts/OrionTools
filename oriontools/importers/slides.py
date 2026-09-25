"""Zet een PowerPoint om in een HTML-deck onder Hoorcollege/.

    python ../OrionTools/orion.py import-slides "<pad>/DeN - Physical.pptx" --naam Sessie1

De decks komen in paths.decks van het vak (standaard Hoorcollege/), de
afbeeldingen in paths.img, en het deck verwijst er relatief naar.

Vanaf dan is die HTML de bron en wordt de pptx gearchiveerd, niet meer
bewerkt. Twee bronnen die allebei bewerkt worden lopen uit elkaar, en dat was
bij de syllabus al gebeurd: de Word stond op 29 november en de PDF die de
student las op 12 september.

Net als import-syllabus vertaalt dit commando OPMAAK, GEEN WOORDEN.
Geen tikfout wordt verbeterd en geen zin herschreven. Wat het moest raden,
komt in Hoorcollege/IMPORT.md te staan, en dat is de lijst die je naleest.

Het schrijft het deck ELKE KEER OPNIEUW, dus draai het een keer per deck en
werk daarna in de HTML. Een tweede import gooit weg wat je met de hand hebt
rechtgezet, en dat is precies het werk dat IMPORT.md je heeft aangewezen.

DE VOLGORDE KOMT UIT presentation.xml, niet uit de bestandsnamen. slide12.xml
hoeft de twaalfde slide niet te zijn: PowerPoint hernoemt niets wanneer je een
slide versleept. p:sldIdLst zegt de echte volgorde. Om dezelfde reden hangen de
notities aan de relaties van de slide en niet aan notesSlide<zelfde nummer>:
die twee lopen uit elkaar zodra er ergens een slide bijkomt.

WAT HET INTERPRETEERT

- De layoutnaam zegt wat voor slide het is. Het HOGENT-sjabloon noemt ze
  "Titel wit" (de titelslide), "Titel oranje" (een tussentitel), "Start wit"
  en "Start zwart" (een slide die uit een beeld bestaat) en "titel en
  opsomming wit" (de gewone). Dat is het enige signaal dat er is: aan de vormen
  zelf zie je het verschil niet, want een tussentitel is ook maar een tekstvak.
  Een layoutnaam die hier niet in staat, wordt gemeld in plaats van geraden.
- Een tijdelijke aanduiding met een titel wordt <h1> of <h2>, een met een
  opsomming wordt <ul>, en het niveau van een alinea wordt de nesting. Lege
  alinea's vallen weg: PowerPoint zet ze tussen de punten als witruimte, en die
  witruimte staat hier in het stylesheet.
- Een leeg tekstkader wordt overgeslagen. Het sjabloon legt er op elke slide
  een als versiering, en die is nooit ingevuld.
- De breedte van een afbeelding komt uit de PowerPoint, als a:ext, en gaat mee
  als --figuur-breedte in mm. Zonder dat valt een afbeelding terug op haar
  eigen pixelmaat, en die zegt alleen hoe de schermafdruk genomen is.
- Een bijgesneden afbeelding wordt bijgesneden. PowerPoint bewaart het bestand
  heel en zegt met a:srcRect welk stuk te zien is; wie dat overslaat drukt af
  wat de auteur net had weggehaald.
- Een afbeelding wordt teruggebracht tot wat haar plaats op de slide vraagt, en
  nooit vergroot. Wat de PowerPoint aan pixels bewaart, zegt niets over hoe
  groot ze getoond wordt: de titelfoto is 2506 punten breed voor een plaats van
  123mm. Dat is niet zichtbaar op het scherm en wel in de handout, die er van
  4.8 naar 1 MB gaat.
- Staan er meerdere afbeeldingen op een slide, dan zeggen hun plaatsen in
  welke volgorde en in welke richting ze horen. De volgorde in het bestand is
  de stapelvolgorde en niet de leesvolgorde, en twee schema's onder elkaar in
  een rij persen maakt ze allebei onleesbaar. Zie rangschik().
- Een afbeelding die linksboven op de slide begint, is een achtergrond en geen
  figuur. Ze krijgt haar plaats en haar maat mee en gaat achter de tekst staan;
  in de gewone stroom duwt ze anders de titel van de slide af.
- Een afbeelding met een hyperlink eraan wordt een link, en opent in een nieuw
  tabblad. Bij een ingebedde video gebeurt hetzelfde: de poster blijft, de mp4
  niet, want daar staat op deze slides al een YouTube-link naast. Een deck van
  100 MB hoort niet in git.

WAT HET NIET INTERPRETEERT, EN DUS MELDT

Een los tekstvak (een vorm die geen tijdelijke aanduiding is) staat op een
plaats die iets betekent: het is een bijschrift bij een tekening, of een label
in een schema. Die plaats is hier niet te bewaren zonder alles absoluut te
positioneren, en dan krijg je een HTML-bestand dat even lastig te bewerken is
als de PowerPoint zelf. Zo'n tekstvak komt er dus als <p class="los"> in en
staat in IMPORT.md, zodat je die slide met de hand afwerkt.

Hetzelfde geldt voor verbindingslijnen en vormen zonder tekst (waar samen een
tekening van gemaakt is) en voor een invoegtoepassing als Wooclap, die alleen
in PowerPoint bestaat.
"""

import argparse
import html
import os
import re
import sys
import zipfile

try:
    from PIL import Image                                      # noqa: F401
except ImportError:
    sys.exit("Pillow ontbreekt:  pip install pillow")

from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

from .. import huisstijl, repo

# Gezet door main(), uit de config van het vak: waar de decks en de
# afbeeldingen staan, en hoe het deck naar die afbeeldingen verwijst.
DECKS = None
BEELDEN = None
BEELD_URL = "../img"

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
EMU_PER_MM = 914400 / 25.4

# Wat als "niets" telt in een tekstvak. str.strip() haalt de gewone witruimte
# weg maar laat een zero-width space staan, en PowerPoint zet die neer in een
# vak waar ooit in getypt is en dat daarna leeggemaakt werd. Zo'n vak tekent
# niets en kwam er toch in, als <p class="los"> zonder woorden erin; slide 34
# van Sessie2 droeg er een. De feff is de BOM, die om dezelfde reden meekomt.
ONZICHTBAAR = "\u200b\u200c\u200d\u2060\ufeff"


def leeg(tekst):
    return not tekst.strip(ONZICHTBAAR + " \t\r\n\u00a0")


# De layoutnamen van het HOGENT-sjabloon, en welke klasse(n) de slide krijgt.
# Zie de kop: dit is het enige signaal, aan de vormen is het niet te zien.
#
# "Start zwart" en "Start wit" zijn allebei een beeldslide, maar de eerste zet
# tx1 als achtergrond en dat is zwart in dit thema. Die twee op een hoop gooien
# zette de zwarte Edison-foto op een wit vlak, met een band boven en onder die
# op de beamer als een fout leest. Alleen de laatste klasse verschilt, dus de
# vergelijkingen verderop op "titel", "sectie" en "gewoon" blijven kloppen.
SOORTEN = {
    "titel wit": "titel",
    "titel oranje": "sectie",
    "start wit": "beeld",
    "start zwart": "beeld zwart",
    "titel en opsomming wit": "gewoon",
}

meldingen = []


def meld(nr, boodschap):
    meldingen.append((nr, boodschap))


# ------------------------------------------------------------- het pakket

def onderdelen(pptx):
    """De slides in de volgorde van presentation.xml, elk met zijn relaties."""
    z = zipfile.ZipFile(pptx)
    prels = relaties(z, "ppt/_rels/presentation.xml.rels")
    pres = ET.fromstring(z.read("ppt/presentation.xml"))
    maat = pres.find(f"{P}sldSz")
    grootte = (int(maat.get("cx")) / EMU_PER_MM, int(maat.get("cy")) / EMU_PER_MM)
    namen = []
    for sld in pres.find(f"{P}sldIdLst"):
        doel = prels[sld.get(f"{R}id")]["target"]
        namen.append("ppt/" + doel.replace("../", ""))
    return z, grootte, namen


def relaties(z, pad):
    uit = {}
    for r in ET.fromstring(z.read(pad)):
        uit[r.get("Id")] = {"type": r.get("Type").rsplit("/", 1)[-1],
                            "target": r.get("Target"),
                            "extern": r.get("TargetMode") == "External"}
    return uit


def rels_van(z, deel):
    pad = str(Path(deel).parent / "_rels" / (Path(deel).name + ".rels"))
    return relaties(z, pad.replace("\\", "/"))


def opgelost(rels, soort):
    for gegevens in rels.values():
        if gegevens["type"] == soort:
            return gegevens["target"]
    return None


def soort_van(z, rels, nr):
    """Wat voor slide dit is, afgeleid van de naam van haar layout."""
    doel = opgelost(rels, "slideLayout")
    if doel is None:
        return "gewoon", ""
    pad = "ppt/" + doel.replace("../", "")
    naam = ET.fromstring(z.read(pad)).find(f"{P}cSld").get("name") or ""
    sleutel = naam.strip().lower()
    if sleutel not in SOORTEN:
        meld(nr, f'onbekende layout "{naam}", als gewone slide behandeld')
        return "gewoon", naam
    return SOORTEN[sleutel], naam


# ------------------------------------------------------------------ tekst

# Een regeleinde tussen de runs. Een eigen object en geen string, want elke
# string zou hier ook uit de PowerPoint kunnen komen.
BREUK = object()


def geweven(alinea, rels):
    """De runs van een alinea als HTML, met aangrenzende runs samengevoegd.

    PowerPoint hakt een zin in stukken zodra er ooit iets in verbeterd is, dus
    zonder dit staat er <strong>n</strong><strong>etwerk</strong>.

    EEN a:br IS EEN REGELEINDE BINNEN DE ALINEA en wordt <br>. Wie alleen de
    runs leest, plakt de twee regels aan elkaar zonder er iets tussen te zetten,
    en dat blijft een geldige zin: op de titelslide werden twee regels, twee
    namen boven twee adressen, een regel waarin elke naam naast het adres van
    de ander kwam te staan.
    """
    stukken = []
    for kind in alinea:
        if kind.tag == f"{A}br":
            stukken.append([BREUK, None, None, None])
            continue
        if kind.tag != f"{A}r":
            continue
        run = kind
        tekst = "".join(run.itertext())
        rpr = run.find(f"{A}rPr")
        vet = rpr is not None and rpr.get("b") == "1"
        schuin = rpr is not None and rpr.get("i") == "1"
        link = None
        if rpr is not None:
            klik = rpr.find(f"{A}hlinkClick")
            if klik is not None and klik.get(f"{R}id"):
                gegevens = rels.get(klik.get(f"{R}id"))
                link = gegevens["target"] if gegevens else None
        if stukken and tuple(stukken[-1][1:]) == (vet, schuin, link):
            stukken[-1][0] += tekst
        else:
            stukken.append([tekst, vet, schuin, link])

    while stukken and stukken[0][0] is BREUK:
        stukken.pop(0)
    while stukken and stukken[-1][0] is BREUK:
        stukken.pop()

    uit = []
    for tekst, vet, schuin, link in stukken:
        if tekst is BREUK:
            uit.append("<br>")
            continue
        stuk = html.escape(schoon(tekst))
        if not stuk.strip():
            continue
        if vet:
            stuk = f"<strong>{stuk}</strong>"
        if schuin:
            stuk = f"<em>{stuk}</em>"
        if link:
            stuk = f'<a href="{html.escape(link)}" target="_blank">{stuk}</a>'
        uit.append(stuk)
    return "".join(uit)


def schoon(tekst):
    """Weg met de tekens die alleen in een symboollettertype bestaan.

    Wingdings zet zijn vinkjes en smileys in het gebied voor eigen gebruik, en
    daar staat in elk ander lettertype een blokje. De tekst zelf blijft.
    """
    return re.sub(r"[-]", "", tekst).replace(" ", " ")


def alineas(vorm, rels):
    for alinea in vorm.findall(f".//{A}p"):
        tekst = geweven(alinea, rels)
        if not tekst.strip():
            continue
        ppr = alinea.find(f"{A}pPr")
        niveau = int(ppr.get("lvl", 0)) if ppr is not None else 0
        yield niveau, tekst


def opsomming(vorm, rels):
    """De alinea's van een tekstkader als een geneste <ul>.

    Een diepere lijst hoort IN het punt erboven en niet ernaast, dus daarvoor
    gaat de laatste </li> er weer af. Anders staat er <ul><ul>, wat een browser
    wel tekent maar geen geldige HTML is.
    """
    regels = list(alineas(vorm, rels))
    if not regels:
        return ""
    uit = ["<ul>"]
    diep = 0
    for niveau, tekst in regels:
        while diep < niveau:
            if uit[-1] == "</li>":
                uit.pop()
            uit.append("<ul>")
            diep += 1
        while diep > niveau:
            uit.append("</ul></li>")
            diep -= 1
        uit.append(f"<li>{tekst}")
        uit.append("</li>")
    while diep > 0:
        uit.append("</ul></li>")
        diep -= 1
    uit.append("</ul>")
    return "".join(uit)


# ------------------------------------------------------------ afbeeldingen

def uitsnede(pic):
    rect = pic.find(f".//{A}srcRect")
    if rect is None:
        return None
    kanten = tuple(int(rect.get(k, 0)) / 100000 for k in ("l", "t", "r", "b"))
    return kanten if any(kanten) else None


def snijden(blob, kanten):
    from PIL import Image, JpegImagePlugin
    links, boven, rechts, onder = kanten
    beeld = Image.open(BytesIO(blob))
    breed, hoog = beeld.size
    vak = (round(links * breed), round(boven * hoog),
           round((1 - rechts) * breed), round((1 - onder) * hoog))
    extra = {}
    if beeld.format == "JPEG":
        extra = {"qtables": beeld.quantization,
                 "subsampling": JpegImagePlugin.get_sampling(beeld)}
    uit = BytesIO()
    beeld.crop(vak).save(uit, format=beeld.format, **extra)
    return uit.getvalue()


# Hoeveel beeldpunten een millimeter van de slide waard is. Een beamer trekt
# 1920 punten over 254mm, dus 7.6 volstaat om te projecteren; 10 laat marge en
# is voor de handout ruim voldoende, want daar wordt de slide op 39% gedrukt.
# Hoger is alleen een grotere PDF: de titelfoto kwam als 2506 punten breed uit
# de PowerPoint voor een plaats van 123mm, en dat is vier keer te veel.
PUNTEN_PER_MM = 10


def verkleind(blob, breedte_mm):
    """Breng een afbeelding terug tot wat haar plaats op de slide vraagt.

    Nooit vergroten: een schema dat klein aangeleverd is, wordt door uitrekken
    niet scherper.
    """
    if not breedte_mm:
        return blob
    from PIL import Image
    beeld = Image.open(BytesIO(blob))
    doel = round(breedte_mm * PUNTEN_PER_MM)
    if beeld.width <= doel:
        return blob
    hoogte = round(beeld.height * doel / beeld.width)
    kleiner = beeld.resize((doel, hoogte), Image.LANCZOS)
    uit = BytesIO()
    if beeld.format == "JPEG":
        kleiner.save(uit, format="JPEG", quality=85, optimize=True)
    else:
        kleiner.save(uit, format=beeld.format, optimize=True)
    return uit.getvalue()


def maat(vorm):
    xfrm = vorm.find(f".//{A}xfrm")
    if xfrm is None:
        return None
    ext = xfrm.find(f"{A}ext")
    if ext is None or not ext.get("cx"):
        return None
    return int(ext.get("cx")) / EMU_PER_MM


def hoogte_van(vorm):
    xfrm = vorm.find(f".//{A}xfrm")
    if xfrm is None:
        return None
    ext = xfrm.find(f"{A}ext")
    if ext is None or not ext.get("cy"):
        return None
    return int(ext.get("cy")) / EMU_PER_MM


def plaats(vorm):
    """De linkerbovenhoek en de hoogte van een vorm, in mm."""
    xfrm = vorm.find(f".//{A}xfrm")
    if xfrm is None:
        return None
    off, ext = xfrm.find(f"{A}off"), xfrm.find(f"{A}ext")
    if off is None or ext is None or not ext.get("cy"):
        return None
    return (int(off.get("x", 0)) / EMU_PER_MM,
            int(off.get("y", 0)) / EMU_PER_MM,
            int(ext.get("cy")) / EMU_PER_MM)


def rangschik(beelden):
    """De volgorde en de richting van meerdere figuren, uit hun plaats.

    DE VOLGORDE IN HET XML IS DE STAPELVOLGORDE, niet de leesvolgorde: wie in
    PowerPoint een figuur naar voren haalt, zet ze achteraan in het bestand.
    Slide 8 van Sessie1 heeft de rechtse schets vooraan staan, en die kwam hier
    dus links terecht. Sorteren op de plaats zet dat recht.

    OVERLAPPEN DE VERTICALE BEREIKEN NIET, dan stonden ze ONDER elkaar. Er een
    rij van maken perst de twee schema's van slide 22 (221 en 177mm breed) in
    de 210mm die een slide binnen haar marge overhoudt, en dan is geen van
    beide nog te lezen. Overlappen ze wel, dan is het een rij, ook als de een
    wat hoger begint dan de ander.
    """
    plaatsen = [p for p, _ in beelden]
    if any(p is None for p in plaatsen):
        return "beelden", [h for _, h in beelden]
    stapel = all(not (a[1] < b[1] + b[2] and b[1] < a[1] + a[2])
                 for i, a in enumerate(plaatsen) for b in plaatsen[i + 1:])
    as_ = 1 if stapel else 0
    op_volgorde = sorted(beelden, key=lambda bp: bp[0][as_])
    return ("beelden onder-elkaar" if stapel else "beelden",
            [h for _, h in op_volgorde])


def bij_de_oorsprong(pic):
    """Staat deze afbeelding linksboven op de slide?

    Dan is het een achtergrond en geen figuur: het sjabloon legt er op een
    titelslide twee van tegen de rand, achter de tekst. In de gewone stroom
    zetten duwt die tekst van de slide af, en met overflow: hidden erop zie je
    dat niet gebeuren.
    """
    xfrm = pic.find(f".//{A}xfrm")
    if xfrm is None:
        return False
    off = xfrm.find(f"{A}off")
    if off is None or not off.get("x"):
        return False
    # Een halve millimeter speling, want PowerPoint schrijft voor de linkerrand
    # van de foto op deze titelslide x="-1" en niet x="0".
    speling = 0.5 * EMU_PER_MM
    return (abs(int(off.get("x"))) <= speling
            and abs(int(off.get("y", 0))) <= speling)


def afbeelding(z, pic, rels, stam, teller, nr):
    blip = pic.find(f".//{A}blip")
    if blip is None or not blip.get(f"{R}embed"):
        return ""
    gegevens = rels.get(blip.get(f"{R}embed"))
    if gegevens is None:
        return ""
    pad = "ppt/" + gegevens["target"].replace("../", "")
    blob = z.read(pad)
    kanten = uitsnede(pic)
    if kanten:
        blob = snijden(blob, kanten)
    blob = verkleind(blob, maat(pic))
    teller[0] += 1
    ext = Path(pad).suffix.lower()
    naam = f"{stam}-{teller[0]:02d}{ext}"
    (BEELDEN / naam).write_bytes(blob)

    breedte = maat(pic)
    stijl = f' style="--figuur-breedte: {breedte:.0f}mm"' if breedte else ""
    klasse = ""
    if bij_de_oorsprong(pic):
        klasse = ' class="achtergrond"'
        hoogte = hoogte_van(pic)
        if hoogte:
            stijl = (f' style="--figuur-breedte: {breedte:.0f}mm; '
                     f'--figuur-hoogte: {hoogte:.0f}mm"')
    beeld = f'<img src="{BEELD_URL}/{naam}" alt="">'

    klik = pic.find(f".//{A}hlinkClick")
    doel = None
    if klik is not None and klik.get(f"{R}id"):
        verwijzing = rels.get(klik.get(f"{R}id"))
        doel = verwijzing["target"] if verwijzing else None
    if doel is None and opgelost(rels, "video"):
        links = [g["target"] for g in rels.values() if g["type"] == "hyperlink"]
        doel = links[0] if links else None
        meld(nr, "ingebedde video vervangen door de link ernaast; "
                 "de mp4 gaat niet mee")
    if doel:
        beeld = f'<a href="{html.escape(doel)}" target="_blank">{beeld}</a>'
    return f"<figure{klasse}{stijl}>{beeld}</figure>"


# ------------------------------------------------------------------ tabel

def tabel(frame, rels):
    """Een tabel, met de kolombreedtes en alleen de koprij die er echt is.

    De koprij komt van firstRow op a:tblPr en wordt niet geraden aan vet of
    arcering: de tabel van slide 16 is een oefening waarvan de student de
    onderste rijen invult, en een koprij die er niet staat maakt van zijn
    eerste antwoord een kolomtitel.

    De breedtes gaan mee omdat een lege cel anders krimpt tot haar opvulling.
    In deze tabel is elke cel op een na leeg, en daar hoort de student net in
    te schrijven.
    """
    tbl = frame.find(f".//{A}tbl")
    if tbl is None:
        return ""
    eigenschappen = tbl.find(f"{A}tblPr")
    koprij = eigenschappen is not None and eigenschappen.get("firstRow") == "1"
    kolommen = [int(g.get("w")) / EMU_PER_MM
                for g in tbl.findall(f"{A}tblGrid/{A}gridCol") if g.get("w")]

    rijen = []
    for i, tr in enumerate(tbl.findall(f"{A}tr")):
        tag = "th" if (koprij and i == 0) else "td"
        cellen = []
        for tc in tr.findall(f"{A}tc"):
            inhoud = " ".join(t for _, t in alineas(tc, rels))
            leeg = "" if inhoud else ' class="invulruimte"'
            cellen.append(f"<{tag}{leeg}>{inhoud}</{tag}>")
        rijen.append("<tr>" + "".join(cellen) + "</tr>")

    groep = ""
    if kolommen:
        groep = "<colgroup>" + "".join(
            f'<col style="--kolom-breedte: {b:.0f}mm">' for b in kolommen
        ) + "</colgroup>"
    kop = f"<thead>{rijen[0]}</thead>" if koprij and rijen else ""
    lijf = "<tbody>" + "".join(rijen[1:] if koprij else rijen) + "</tbody>"
    return f"<table>{groep}{kop}{lijf}</table>"


# -------------------------------------------------------------- een slide

def is_titelkader(vorm):
    ph = vorm.find(f".//{P}ph")
    return ph is not None and ph.get("type") in ("ctrTitle", "title")


def is_aanduiding(vorm):
    return vorm.find(f".//{P}ph") is not None


def ontlijst(fragment):
    """Een <ul> met een of meer punten terug naar platte tekst.

    De punten worden regels en geen zin met schuine strepen ertussen. In het
    tekstvak stonden het regels, en een schuine streep is een leesteken dat in
    het document niet staat: dit script vertaalt opmaak en geen woorden. Op
    slide 31 van Sessie2 leverde dat etiketten als "Modes? / b, g, n, ac, ax"
    op, waar het label en zijn inhoud twee regels waren.
    """
    fragment = re.sub(r"</li>\s*<li>", "<br>", fragment)
    return re.sub(r"</?[uo]l>|</?li>", "", fragment).strip()


def notitietekst(z, rels):
    doel = opgelost(rels, "notesSlide")
    if doel is None:
        return ""
    pad = "ppt/" + doel.replace("../", "")
    root = ET.fromstring(z.read(pad))
    nrels = rels_van(z, pad)
    regels = []
    for vorm in root.iter(f"{P}sp"):
        ph = vorm.find(f".//{P}ph")
        if ph is None or ph.get("type") != "body":
            continue
        for _, tekst in alineas(vorm, nrels):
            if tekst.strip().isdigit():
                continue        # de tijdelijke aanduiding van het slidenummer
            regels.append(f"<p>{tekst}</p>")
    return "".join(regels)


def bouw_slide(z, deel, nr, stam, teller):
    root = ET.fromstring(z.read(deel))
    rels = rels_van(z, deel)
    soort, _ = soort_van(z, rels, nr)
    boom = root.find(f"{P}cSld/{P}spTree")

    koppen, tekst, beelden, los = [], [], [], []
    tekening = 0

    def loop(el):
        nonlocal tekening
        for kind in el:
            tag = kind.tag
            if tag == f"{P}sp":
                if leeg("".join(kind.itertext())):
                    if not is_aanduiding(kind):
                        tekening += 1
                    continue
                if is_titelkader(kind):
                    koppen.append(" ".join(t for _, t in alineas(kind, rels)))
                elif is_aanduiding(kind):
                    tekst.append(opsomming(kind, rels))
                else:
                    los.append(opsomming(kind, rels))
            elif tag == f"{P}pic":
                gemaakt = afbeelding(z, kind, rels, stam, teller, nr)
                if gemaakt:
                    beelden.append((plaats(kind), gemaakt))
            elif tag == f"{P}cxnSp":
                tekening += 1
            elif tag == f"{P}graphicFrame":
                gemaakt = tabel(kind, rels)
                if gemaakt:
                    tekst.append(gemaakt)
                else:
                    meld(nr, "invoegtoepassing (Wooclap of dergelijke) "
                             "overgeslagen: die bestaat alleen in PowerPoint")
            elif tag == f"{MC}AlternateContent":
                meld(nr, "invoegtoepassing (Wooclap of dergelijke) "
                         "overgeslagen: die bestaat alleen in PowerPoint")
            elif tag == f"{P}grpSp":
                loop(kind)

    loop(boom)

    # Een afbeelding linksboven is alleen een ACHTERGROND als er tekst van het
    # sjabloon is om achter te staan. Zonder die tekst is er niets om de
    # achtergrond van te zijn en is ze gewoon de inhoud van de slide. De
    # videoslide zet haar affiche ook op 0,0, en die absoluut plaatsen legde
    # het blauwe beeld over de QR-code ernaast: binnen een stapelcontext wint
    # een geplaatst element van een gewoon element, wat niemand ziet gebeuren.
    if not (koppen or tekst):
        beelden = [(p, h.replace(' class="achtergrond"', "")) for p, h in beelden]

    if tekening:
        meld(nr, f"{tekening} lijnen of vormen zonder tekst overgeslagen; "
                 "de tekening moet je met de hand terugzetten")

    if not (koppen or tekst or beelden or los):
        meld(nr, "lege slide, niet overgenomen")
        return None

    kop = koppen[0] if koppen else ""
    if soort == "sectie" and not kop and los:
        kop, los = ontlijst(los[0]), los[1:]
    if los:
        meld(nr, f"{len(los)} los tekstvak/tekstvakken staan nu onder de "
                 "slide, hun plaats op het scherm ging verloren")

    delen = []
    if kop:
        delen.append(f"<h1>{kop}</h1>" if soort == "titel" else f"<h2>{kop}</h2>")
    if soort == "titel":
        for stuk in tekst + los:
            delen.append(f'<p class="ondertitel">{ontlijst(stuk)}</p>')
        delen.extend(h for _, h in beelden)
    else:
        delen.extend(tekst)
        if len(beelden) > 1:
            # Naast of onder elkaar, zoals ze op de slide stonden; zie
            # rangschik() hierboven en hoorcollege.css.
            klasse_beelden, op_volgorde = rangschik(beelden)
            delen.append(f'<div class="{klasse_beelden}">'
                         + "".join(op_volgorde) + "</div>")
        else:
            delen.extend(h for _, h in beelden)
        for stuk in los:
            delen.append(f'<p class="los">{ontlijst(stuk)}</p>')

    notities = notitietekst(z, rels)
    if notities:
        delen.append(f'<aside class="notities">{notities}</aside>')

    klasse = "slide" if soort == "gewoon" else f"slide {soort}"
    inhoud = "\n        ".join(d for d in delen if d)
    return (f'    <section class="{klasse}" data-slide="{nr}">\n'
            f'        {inhoud}\n'
            f'    </section>')


# -------------------------------------------------------------------- main

def kebab(naam):
    return re.sub(r"(?<!^)(?=[A-Z0-9])", "-", naam).lower()


def schrijf_import_md(naam, pptx, gemaakt, totaal):
    pad = DECKS / "IMPORT.md"
    regels = [f"## {naam}", "",
              f"Uit `{pptx.name}`, {gemaakt} van de {totaal} slides overgenomen.",
              ""]
    if meldingen:
        regels.append("| Slide | Wat het script niet kon vertalen |")
        regels.append("|---|---|")
        for nr, boodschap in meldingen:
            regels.append(f"| {nr} | {boodschap} |")
    else:
        regels.append("Niets te melden.")
    regels.append("")

    bestaand = pad.read_text(encoding="utf-8") if pad.exists() else ""
    if not bestaand:
        bestaand = ("# Wat de slide-import moest raden\n\n"
                    "Geschreven door `orion.py import-slides`. Een sectie per "
                    "deck, herschreven bij elke import van dat deck en verder "
                    "met rust gelaten.\n\n")
    blokken = re.split(r"(?m)^## ", bestaand)
    hoofd = blokken[0]
    rest = [b for b in blokken[1:] if not b.startswith(naam + "\n")]
    pad.write_text(hoofd + "".join("## " + b for b in rest)
                   + "\n".join(regels) + "\n", encoding="utf-8")


def main(argv):
    global DECKS, BEELDEN, BEELD_URL
    p = argparse.ArgumentParser(prog="orion.py import-slides")
    p.add_argument("pptx")
    p.add_argument("--naam", required=True,
                   help="de bestandsnaam van het deck, zonder .html")
    p.add_argument("--stam", help="het voorvoegsel van de afbeeldingen; "
                                  "standaard hoorcollege-<naam>")
    repo.voeg_repo_toe(p)
    args = p.parse_args(argv)
    vak = repo.vind(args)
    DECKS = vak.pad("decks")
    BEELDEN = vak.pad("img")
    BEELD_URL = Path(os.path.relpath(BEELDEN, DECKS)).as_posix()

    pptx = Path(args.pptx)
    if not pptx.exists():
        sys.exit(f"niet gevonden: {pptx}")
    stam = args.stam or f"hoorcollege-{kebab(args.naam)}"
    DECKS.mkdir(parents=True, exist_ok=True)

    z, (breed, hoog), namen = onderdelen(pptx)
    teller = [0]
    secties = []
    for nr, deel in enumerate(namen, 1):
        gemaakt = bouw_slide(z, deel, nr, stam, teller)
        if gemaakt:
            secties.append(gemaakt)

    # --sessie is wat er op elke slide onder komt te staan, naast het nummer
    # uit data-slide. Het staat hier een keer per deck en niet per slide;
    # hoorcollege.css legt uit waarom het daar hoort en niet in de secties.
    # Sessie2 wordt "Sessie 2": het cijfer hoort niet tegen het woord, dezelfde
    # regel als in export-handout. Buiten de f-string, met opzet: daarbinnen
    # stond de regex met een dubbele backslash in een r-string, en die zoekt
    # een letterlijke backslash gevolgd door een d. De spatie kwam er dus nooit;
    # de decks van DeN zijn met de hand rechtgezet zonder dat het script het
    # leerde.
    sessie = re.sub(r"(?<=[a-z])(?=\d)", " ", args.naam)
    uit = DECKS / f"{args.naam}.html"
    uit.write_text(
        "<!DOCTYPE html>\n"
        '<html lang="nl">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(args.naam)}</title>\n"
        f'<link rel="stylesheet" href="{huisstijl.ORIONCSS_URL}hoorcollege.css">\n'
        f'</head>\n<body style="--slide-breedte: {breed:.0f}mm; '
        f'--slide-hoogte: {hoog:.0f}mm; '
        f"--sessie: '{sessie}'\">\n\n"
        + "\n\n".join(secties)
        + f'\n\n<script src="{huisstijl.ORIONCSS_URL}hoorcollege.js"></script>\n'
        "</body>\n</html>\n",
        encoding="utf-8")

    schrijf_import_md(args.naam, pptx, len(secties), len(namen))
    print(f"{uit.relative_to(vak.root)}: {len(secties)} van {len(namen)} slides, "
          f"{teller[0]} afbeeldingen")
    for nr, boodschap in meldingen:
        print(f"  slide {nr}: {boodschap}")
    return 0
