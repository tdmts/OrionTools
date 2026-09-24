"""Zet een hoofdstuk van de syllabus-Word om naar HTML-pagina's.

    python ../OrionTools/orion.py import-syllabus --hoofdstuk 1 --voorwoord
    python ../OrionTools/orion.py import-syllabus --hoofdstuk 2 --docx "pad/naar/syllabus.docx"

De Word is de HERKOMST van de tekst, niet de bron ervan: na de import is de HTML
de bron en wordt de Word gearchiveerd. Dit commando draait dus eenmalig per
hoofdstuk, zoals import-brightspace, en nooit in CI of in de Stop-hook. Het is
destructief: een tweede run over een hoofdstuk gooit elke correctie met de hand
in die pagina's en elke hertekende figuur weg.

Waar de Word staat, zegt syllabus.docx in oriontools.json, relatief aan je
thuismap; --docx gaat daarboven.

WAT ERUIT KOMT (de mappen uit paths in oriontools.json)

    <syllabus_src>/<Hoofdstuk>/Overzicht.html   kernpunten en studievragen
    <syllabus_src>/<Hoofdstuk>/<Sectie>.html    een pagina per Heading 2
    <img>/syllabus-<nn>-<slug>-<kk>.png         de afbeeldingen
    <syllabus_dir>/IMPORT.md                    wat de import niet zeker wist

Een Heading 1 is een hoofdstuk en wordt een map. Alles tussen die kop en de
eerste Heading 2 is de opening van het hoofdstuk en komt op Overzicht.html; in
de Word zijn dat de kaders Kernpunten en Studievragen. Elke Heading 2 wordt een
eigen pagina, en Heading 3 en 4 worden daarbinnen h2 en h3: de h1 van de pagina
is immers al de Heading 2 zelf.

DE TEKST GAAT ER LETTERLIJK IN. Dit script vertaalt opmaak, geen woorden. Het
verbetert geen typfouten en herschrijft geen zin. Wat het onderweg opmerkt (een
tabel waarvan het de kopregel moest raden, een lege tabel, een em-dash) schrijft
het in IMPORT.md, zodat de auteur beslist in plaats van het script.

WAAR HET MOET GOKKEN, ZET HET DAT IN DE PAGINA. IMPORT.md is een verslag van een
run en geen werklijst: hij wordt per hoofdstuk bevroren op het moment van
importeren, dus zodra je hier een regel verandert of de HTML met de hand
bijwerkt, staat er iets in dat niet meer waar is. Dat is ook echt gebeurd: na de
correctie aan heeft_kopregel beweerde IMPORT.md over drie tabellen een kopregel
die er niet meer stond, met een reden die de code niet meer kent.

Een gok krijgt daarom een data-geraden op het element zelf, en de regel
importer-guess van de check (orion.py check) laat de check daarop vallen. Zo staat de twijfel in de
weg in plaats van in een logboek, en veroudert ze niet, want ze staat bij de
markup die ze beschrijft. Je lost ze op door het attribuut te schrappen, en dat
schrappen is de bevestiging.

WAT HET WEL INTERPRETEERT, en waarom dat geen woorden raakt:

  - Een tabel van twee rijen waarvan de tweede rij over de volle breedte loopt,
    is in deze Word een kader met een titel (Kernpunten, Studievragen). Dat
    wordt een OrionCSS info-box. Het icoontje in de eerste cel valt weg: de
    info-box tekent zijn eigen.
  - Een tabel waarin geen enkele cel tekst bevat, is invulruimte voor de student
    en blijft een lege tabel: op papier is dat waar hij schrijft. Een tabel met
    een kolom die overal leeg staat, is dat ook: links de definitie, rechts wat
    de student invult. Staat zo'n tabel vlak na een genummerde vraag, dan hoort
    ze bij die vraag en gaat ze erin. Zo'n tabel krijgt de kolombreedtes van
    de Word mee, want Chrome geeft een lege cel anders niet meer dan haar
    opvulling en dan is er niets om in te schrijven.
  - Samengevoegde cellen (vMerge, gridSpan) worden rowspan en colspan. Zonder
    dat verschuift de hele tabel een kolom en klopt er niets meer van.
  - Een kopregel wordt alleen gezet als de Word er een aanduidt (tblHeader),
    als de hele eerste rij vet staat, of als de tabelstijl de eerste rij
    voorwaardelijk opmaakt en die stijl dat ook werkelijk definieert. Anders
    krijgt de tabel geen thead en een data-geraden, want dan is er geen enkel
    signaal en is het een gok.
  - Een alinea in de stijl List Paragraph zonder nummering is de uitleg ONDER
    het opsommingsteken erboven, en gaat dus in dat lijstitem. Zonder dat valt
    een lijst van zes uiteen in zes lijstjes van een.
  - Een genummerde lijst die door een tussenzin onderbroken wordt, telt door.
    De Word houdt daar dezelfde numId aan; hier wordt dat het start-attribuut,
    zodat vraag 6 vraag 6 blijft heten in plaats van opnieuw vraag 1.
"""

import argparse
import html
import re
import unicodedata
import sys
from io import BytesIO
import zipfile
from pathlib import Path

from .. import repo

try:
    import docx
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph
except ImportError:
    sys.exit("python-docx ontbreekt:  pip install python-docx")

# Gezet door main() uit het vak; de functies hieronder lezen ze zoals ze de
# constanten lazen toen dit script nog in de vakrepo stond.
REPO = None
UIT = None
IMG = None
IMPORT_LOG = None

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"

notities = []


def noteer(waar, tekst):
    """Leg vast wat de importer moest raden, voor IMPORT.md.

    EEN REDEN DIE DE IMPORTER AFDRUKT, MOET EEN REDEN ZIJN DIE HIJ GELEZEN HEEFT.
    Achter elke "want ..." in een notitie hoort een predicaat dat precies die
    reden test, en geen stand-in ervoor. data-geraden en importer-guess vangen
    alleen de gok die weet dat hij gokt; de importer die zelfverzekerd fout zit,
    vangt geen regel. Zo liep het met de kopregel: de log zei "want tblLook
    firstRow", terwijl heeft_kopregel alleen de vlag las en niet of de
    tabelstijl de eerste rij ook opmaakt. De reden klopte vaak genoeg om vier
    hoofdstukken lang niet op te vallen, en een en twintig tabellen kregen een
    kopregel die de Word niet tekent (zie heeft_kopregel).
    """
    notities.append((waar, tekst))


# ------------------------------------------------------------------ namen

# De afkortingen die in de koppen van de Word staan, met de schrijfwijze die
# ze in een bestandsnaam krijgen: syllabus.afkortingen in oriontools.json, want
# elke Word heeft de hare. Elke waarde is dezelfde PascalCase die de regel
# eronder ook zelf zou maken, en dat is de bedoeling: de tabel LEGT DIE
# SCHRIJFWIJZE VAST in plaats van ze te veranderen. Een repo schrijft een
# afkorting in een bestandsnaam als een gewoon woord (BiosUefi.html,
# MbrPartities.html, GptPartities.html), niet in kapitalen, en zonder deze
# tabel is dat nergens opgeschreven. Zet je er "bios": "BIOS" in, dan heet de
# syllabuspagina BIOS... en het labo Bios..., en dat verschil valt pas op als
# je de twee naast elkaar legt.
AFKORTINGEN = {}


def ontdiakritiseer(tekst):
    """Vervang elke letter met een teken erop door de kale letter: ue -> u, e -> e.

    Een bestandsnaam in deze repo is ASCII, en de regel eronder gooide alles weg
    wat dat niet is. Een trema brak zo het WOORD in twee: "vacuumbuizen" met
    trema werd Generatie1VacuMbuizen, en "Industriele" met trema wordt
    IndustriLe, wat hoofdstuk 4 raakt zonder dat iemand er iets aan gedaan
    heeft. NFKD hangt het teken los van zijn letter, waarna de combinerende
    tekens (categorie Mn) weg kunnen en de letter blijft staan.
    """
    ontbonden = unicodedata.normalize("NFKD", tekst)
    return "".join(k for k in ontbonden if not unicodedata.combining(k))


def pascal(tekst):
    """PascalCase Nederlands zelfstandig naamwoord, zoals elke naam in deze repo."""
    t = ontdiakritiseer(tekst).lower().replace("/", " ")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    delen = [d for d in t.split() if d]
    naam = "".join(AFKORTINGEN.get(d, d[:1].upper() + d[1:]) for d in delen)
    return naam or "Pagina"


def slug(tekst):
    """Kleine letters met koppeltekens, voor de bestandsnaam van een afbeelding.

    Dezelfde reden als bij pascal(): zonder ontdiakritiseer() breekt een teken
    op een letter het woord in twee, en werd hoofdstuk 4
    "industri-le-computer-vs-embedded-system".
    """
    return re.sub(r"[^a-z0-9]+", "-", ontdiakritiseer(tekst).lower()).strip("-") or "sectie"


def strip_tags(tekst):
    return re.sub(r"<[^>]+>", "", tekst or "")


# ------------------------------------------------------------- docx lezen

def blokken(parent, doc):
    """Alinea's en tabellen in documentvolgorde; python-docx geeft ze apart."""
    for kind in parent.iterchildren():
        if kind.tag == qn("w:p"):
            yield Paragraph(kind, doc)
        elif kind.tag == qn("w:tbl"):
            yield Table(kind, doc)


def kopniveau(par):
    m = re.match(r"(?:Heading|Kop) (\d)", par.style.name)
    return int(m.group(1)) if m else None


def lees_nummering(pad):
    """numId -> ilvl -> numFmt. Alleen dat zegt of het bullets of cijfers zijn."""
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(str(pad)) as z:
        if "word/numbering.xml" not in z.namelist():
            return {}
        xml = z.read("word/numbering.xml")
    ns = {"w": W}
    root = ET.fromstring(xml)
    abstract = {}
    for a in root.findall("w:abstractNum", ns):
        niveaus = {}
        for lvl in a.findall("w:lvl", ns):
            fmt = lvl.find("w:numFmt", ns)
            niveaus[lvl.get(f"{{{W}}}ilvl")] = (
                fmt.get(f"{{{W}}}val") if fmt is not None else "bullet")
        abstract[a.get(f"{{{W}}}abstractNumId")] = niveaus
    formaten = {}
    for n in root.findall("w:num", ns):
        aid = n.find("w:abstractNumId", ns)
        formaten[n.get(f"{{{W}}}numId")] = (
            abstract.get(aid.get(f"{{{W}}}val"), {}) if aid is not None else {})
    return formaten


def lijstinfo(par, formaten):
    pr = par._p.pPr
    if pr is None or pr.numPr is None:
        return None
    num = pr.numPr
    num_id = str(num.numId.val) if num.numId is not None else None
    ilvl = str(num.ilvl.val) if num.ilvl is not None else "0"
    fmt = formaten.get(num_id, {}).get(ilvl, "bullet")
    return (int(ilvl), "ul" if fmt == "bullet" else "ol", num_id)


def lijstalinea(par):
    """Staat deze alinea in de lijststijl zonder zelf genummerd te zijn?

    Word geeft de uitleg ONDER een opsommingsteken de stijl List Paragraph mee
    en laat de nummering weg. Dat is het enige verschil met een gewone alinea,
    en het is precies wat zegt dat die uitleg bij het vorige item hoort in
    plaats van ernaast. Neem je dat niet over, dan valt de lijst uiteen in
    evenveel lijstjes van een item als er items zijn.
    """
    return par.style.name in ("List Paragraph", "Lijstalinea")


# ---------------------------------------------------------------- inline

# Of vet uit de Word meekomt in de lopende tekst, zegt syllabus.vet_uit_de_word
# in oriontools.json. Standaard wel; bij de Word van ICEES niet, en waarom volgt
# hieronder, want het is een oordeel over een Word en niet over de code.
#
# Vet uit die Word komt niet mee. Beslist 10 september 2026, nadat de zestien
# hoofdstukken naast elkaar lagen: het vet in die Word is geen
# systeem. Tien van de 128 bladzijden droegen het, tien van de zestien
# hoofdstukken hadden er nul (RAM, Besturingssystemen en Chipset onder meer), en
# van de veertig stuks stonden er zestien op een enkele bladzijde, waar zowat elk
# inhoudswoord vet stond. Waar het dicht staat werkt het dus niet, en waar het
# ontbreekt suggereert het dat daar niets te onthouden valt. Patroon 10 van
# SCHRIJFSTIJL.md laat vet alleen toe om een term, een pinnaam of een getal te
# markeren en nooit om een zinsdeel; drie van die tien bladzijden zetten hele
# zinnen vet. Het scanwerk doen de Kernpunten, de sectiekoppen en Test jezelf,
# en de syllabus is bovendien papier.
#
# Dit staat in de config en niet als handmatige correctie in de HTML, want zo
# overleeft de beslissing een herimport en hoeft ze in geen enkele NOTITIES.md
# te staan. Zet hem op true en het vet komt weer mee, hoofdstuk per hoofdstuk.
VET_UIT_DE_WORD = True


def run_delen(run):
    """(tekst, vet, cursief) van een run, of None als er geen tekst in staat."""
    tekst = "".join(t.text or "" for t in run.findall(qn("w:t")))
    if not tekst:
        return None
    pr = run.find(qn("w:rPr"))
    vet = pr is not None and pr.find(qn("w:b")) is not None
    cursief = pr is not None and pr.find(qn("w:i")) is not None
    return (tekst, vet, cursief)


def delen_html(delen, ontvet=False):
    """Plak aangrenzende delen met dezelfde opmaak samen.

    Word hakt een zin in stukken zodra je er ooit in gecorrigeerd hebt, dus een
    vetgedrukte zin komt eruit als acht runs. Zonder dit samenplakken staat er
    acht keer <strong> in een zin die er een verdient.
    """
    gebundeld = []
    for tekst, vet, cursief in delen:
        if ontvet or not VET_UIT_DE_WORD:
            vet = False
        if gebundeld and gebundeld[-1][1] == vet and gebundeld[-1][2] == cursief:
            gebundeld[-1][0] += tekst
        else:
            gebundeld.append([tekst, vet, cursief])
    uit = []
    for tekst, vet, cursief in gebundeld:
        stuk = html.escape(tekst)
        if cursief:
            stuk = f"<em>{stuk}</em>"
        if vet:
            stuk = f"<strong>{stuk}</strong>"
        uit.append(stuk)
    return "".join(uit)


def alinea_html(par, rels, ontvet=False):
    """Een alinea naar HTML. Alleen vet, cursief en links overleven.

    ontvet=True laat het vet vallen. Dat is voor een kader waarvan de hele
    inhoud vet staat: daar is het vet de opmaak van het kader zelf, en de
    info-box tekent die opmaak al. Zie tabel_html.

    Zolang VET_UIT_DE_WORD False staat valt het vet overal, en doet deze
    schakelaar er niet toe.
    """
    stukken = []
    for kind in par._p.iterchildren():
        if kind.tag == qn("w:hyperlink"):
            doel = rels.get(kind.get(f"{{{R}}}id"))
            delen = [d for d in (run_delen(r) for r in kind.findall(qn("w:r"))) if d]
            binnen = delen_html(delen, ontvet)
            if doel and binnen.strip():
                extern = doel.startswith("http")
                attr = ' target="_blank" rel="noopener"' if extern else ""
                stukken.append(f'<a href="{html.escape(doel)}"{attr}>{binnen}</a>')
            else:
                stukken.append(binnen)
        elif kind.tag == qn("w:r"):
            deel = run_delen(kind)
            if deel:
                stukken.append(delen_html([deel], ontvet))
    return "".join(stukken)


def volledig_vet(blokkenlijst):
    """Staat elke letter tekst in deze blokken vet? Dan is het opmaak, geen nadruk."""
    gezien = False
    for blok in blokkenlijst:
        if not isinstance(blok, Paragraph):
            continue
        for run in blok._p.findall(".//" + qn("w:r")):
            deel = run_delen(run)
            if deel is None or not deel[0].strip():
                continue
            gezien = True
            if not deel[1]:
                return False
    return gezien


def tekening_van(blip):
    """De w:drawing waar deze blip in zit; daar hangen maat en uitsnede aan."""
    ouder = blip
    while ouder is not None and ouder.tag != qn("w:drawing"):
        ouder = ouder.getparent()
    return ouder


def breedte_van(blip):
    """De breedte in mm die de Word aan deze afbeelding geeft, of None.

    Zonder haar valt een plaatje terug op zijn eigen pixelmaat bij 96 dpi,
    en die zegt niets: ze hangt af van hoe de schermafdruk genomen is. Een
    foto van een ethernetkabel van 550 pixels breed wordt zo 145mm, bijna
    de hele bladspiegel, terwijl de Word haar op 50.4mm zet. wp:extent is
    de maat die de auteur gekozen heeft, in dezelfde eenheid als de
    bladspiegel: 914400 EMU is een inch, dus 36000 een millimeter.
    """
    tekening = tekening_van(blip)
    if tekening is None:
        return None
    extent = tekening.find(f".//{{{WP}}}extent")
    if extent is None or not extent.get("cx"):
        return None
    return int(extent.get("cx")) / 36000


def zwevend_van(blip):
    """Zweeft deze afbeelding naast de tekst (wp:anchor) of staat ze erin (wp:inline)?

    Word kent twee manieren om een afbeelding te plaatsen. Een INLINE afbeelding
    staat in de tekstregel zelf: de alinea eromheen is dan haar bijschrift, en zo
    zijn de meeste figuren in deze Word gemaakt. Een ZWEVENDE afbeelding is aan
    een alinea verankerd en de tekst loopt eromheen (wrapSquare); die alinea is
    gewone lopende tekst die toevallig naast het plaatje staat.

    Het verschil is niet cosmetisch. Wie het overslaat, verandert vier alinea's
    van hoofdstuk 1 van lopende tekst in een klein gecentreerd bijschrift, en de
    tekst die de student hoort te lezen staat dan in de opmaak van een onderschrift.
    In de Word van ICEES zijn 21 van de 132 afbeeldingen zo verankerd, in die
    van DeN 9 van de 92.
    """
    tekening = tekening_van(blip)
    if tekening is None:
        return False
    return tekening.find(f"{{{WP}}}anchor") is not None


def uitsnede_van(blip):
    """Wat de Word van deze afbeelding wegsnijdt, als (l, t, r, b), of None.

    Word bewaart een bijgesneden afbeelding heel: het bestand in de docx is
    het origineel en a:srcRect zegt welk stuk ervan te zien is, in honderd-
    duizendsten. Wie dat overslaat drukt de rest mee af, en dat is precies
    wat de auteur weggehaald had. In hoofdstuk 2 tonen twee schermafdrukken
    zo hun onderste helft, die in de syllabus nooit gestaan heeft.

    Een onbijgesneden afbeelding krijgt van Word een leeg a:srcRect, dus de
    vier nullen tellen als geen uitsnede.
    """
    tekening = tekening_van(blip)
    if tekening is None:
        return None
    rect = tekening.find(".//" + qn("a:srcRect"))
    if rect is None:
        return None
    kanten = tuple(int(rect.get(kant, 0)) / 100000
                   for kant in ("l", "t", "r", "b"))
    return kanten if any(kanten) else None


def snijden(blob, kanten):
    """Snijd de bytes van een afbeelding bij zoals de Word haar toont."""
    try:
        from PIL import Image, JpegImagePlugin
    except ImportError:
        sys.exit("De Word snijdt een afbeelding bij en dat vraagt Pillow:  "
                 "pip install pillow")
    links, boven, rechts, onder = kanten
    beeld = Image.open(BytesIO(blob))
    breed, hoog = beeld.size
    vak = (round(links * breed), round(boven * hoog),
           round((1 - rechts) * breed), round((1 - onder) * hoog))
    extra = {}
    if beeld.format == "JPEG":
        # Met de tabellen van het origineel erbij is bijsnijden geen
        # tweede compressie. crop() laat het formaat en die tabellen
        # vallen, dus quality="keep" ziet geen JPEG meer en ze moeten
        # er met de hand bij.
        extra = {"qtables": beeld.quantization,
                 "subsampling": JpegImagePlugin.get_sampling(beeld)}
    uit = BytesIO()
    beeld.crop(vak).save(uit, format=beeld.format, **extra)
    return uit.getvalue()


def afbeeldingen_van(element, doc, stam, teller):
    """Schrijf elke afbeelding naar img/ en geef (naam, breedte, zwevend) terug."""
    namen = []
    for blip in element.findall(".//" + qn("a:blip")):
        rid = blip.get(f"{{{R}}}embed")
        deel = doc.part.related_parts.get(rid) if rid else None
        if deel is None:
            continue
        teller[0] += 1
        ext = Path(str(deel.partname)).suffix.lower() or ".png"
        naam = f"{stam}-{teller[0]:02d}{ext}"
        kanten = uitsnede_van(blip)
        (IMG / naam).write_bytes(
            snijden(deel.blob, kanten) if kanten else deel.blob)
        namen.append((naam, breedte_van(blip), zwevend_van(blip)))
    return namen


def figuur(naam, bijschrift, diepte, breedte=None):
    onder = ""
    if bijschrift:
        onder = f'\n    <figcaption class="figure-caption">{bijschrift}</figcaption>'
    alt = html.escape(strip_tags(bijschrift)) or "Afbeelding uit de syllabus"
    # De breedte is een maat uit de Word en geen opmaak; wat de gedrukte
    # pagina ermee doet staat in syllabus.css. Op de site leest niets
    # --figuur-breedte, dus daar blijft de afbeelding wat img-fluid ervan
    # maakt.
    maat = f' style="--figuur-breedte: {breedte:.1f}mm"' if breedte else ''
    return (f'<figure class="figure w-100 text-center figure-zoom"{maat}>\n'
            f'    <img src="{"../" * diepte}img/{naam}" class="img-fluid" alt="{alt}">'
            f'{onder}\n</figure>')


# ----------------------------------------------------------------- tabel

class Cel:
    """Een w:tc met net genoeg interface om er blokken() op te draaien."""

    def __init__(self, tc):
        self._tc = tc

    def iterchildren(self):
        return self._tc.iterchildren()


def rooster(tabel):
    """Rijen als [tc, rowspan, colspan, kolom]; vervolgcellen van een merge vallen weg.

    Die laatste is de kolom waar de cel in het rooster begint, en dus niet haar
    plaats in de rij: door een verticale merge staat de derde cel van een rij
    even goed in kolom vier. Ze is nodig om te weten welke cel in een lege
    kolom staat.
    """
    rijen = []
    start_van_kolom = {}
    for ri, rij in enumerate(tabel.rows):
        uit = []
        kolom = 0
        for tc in rij._tr.findall(qn("w:tc")):
            pr = tc.find(qn("w:tcPr"))
            span, merge = 1, None
            if pr is not None:
                gs = pr.find(qn("w:gridSpan"))
                if gs is not None:
                    span = int(gs.get(f"{{{W}}}val") or 1)
                vm = pr.find(qn("w:vMerge"))
                if vm is not None:
                    merge = vm.get(f"{{{W}}}val") or "continue"
            if merge == "continue":
                bron = start_van_kolom.get(kolom)
                if bron is not None:
                    rijen[bron[0]][bron[1]][1] += 1
                kolom += span
                continue
            if merge == "restart":
                start_van_kolom[kolom] = (ri, len(uit))
            uit.append([tc, 1, span, kolom])
            kolom += span
        rijen.append(uit)
    return rijen


def lege_kolommen(tabel):
    """Welke kolommen staan volledig leeg?

    Zo'n kolom is invulruimte: de definitie staat links, de student schrijft
    rechts. Een tabel met zo'n kolom vlak na een genummerde vraag hoort bij die
    vraag, net als de volledig lege tabel waar de student vrij onder schrijft.
    """
    try:
        kolommen = list(zip(*[[c.text.strip() for c in r.cells] for r in tabel.rows]))
    except TypeError:
        return set()
    if len(kolommen) < 2:
        return set()
    return {i for i, kolom in enumerate(kolommen) if not any(kolom)}


def lege_kolom(tabel):
    return bool(lege_kolommen(tabel))


def kolombreedtes(tabel):
    """De kolombreedtes in mm, zoals de Word ze zet (tblGrid, in twips).

    Chrome verdeelt een tabel zelf over haar inhoud, en een lege cel krijgt
    dan niet meer dan haar opvulling: precies de kolom waarin geschreven moet
    worden valt weg. De Word weet wel hoe breed die is, dus die maat wordt
    overgenomen, zoals de breedte van een figuur.
    """
    grid = tabel._tbl.find(qn("w:tblGrid"))
    if grid is None:
        return []
    uit = []
    for kolom in grid.findall(qn("w:gridCol")):
        breedte = kolom.get(f"{{{W}}}w")
        if not breedte or not breedte.isdigit():
            return []
        uit.append(round(int(breedte) / 1440 * 25.4, 1))
    return uit


def maakt_stijl_eerste_rij_op(doc, stijl_id):
    """Definieert deze tabelstijl voorwaardelijke opmaak voor de eerste rij?

    Zonder die definitie tekent Word niets, hoe de vlag ook staat.
    """
    if not stijl_id:
        return False
    for st in doc.styles.element.findall(qn("w:style")):
        if st.get(f"{{{W}}}styleId") != stijl_id:
            continue
        return any(c.get(f"{{{W}}}type") == "firstRow"
                   for c in st.findall(qn("w:tblStylePr")))
    return False


def heeft_kopregel(tabel, rijen, doc):
    """Is de eerste rij een kopregel?

    Deze Word geeft daar geen enkel zichtbaar teken van: de kopregels van
    "OSI / TCP/IP" staan niet vet en hebben geen arcering, want de tabelstijl
    (Plain Table 1) maakt ze op via de voorwaardelijke opmaak van de eerste
    rij. Wat dat aan- en uitzet is tblLook firstRow, en dat is dus het enige
    signaal dat de tabel met een kopregel onderscheidt van de tabel zonder.
    Eenkolomstabellen vallen af: die stapelen lagen op elkaar en hun eerste
    rij is gewoon de bovenste laag.

    Die vlag telt alleen bij een stijl die de eerste rij ook werkelijk
    opmaakt. Tabelraster en TableGrid doen dat niet: ze definieren geen
    enkele voorwaardelijke opmaak, dus daar staat de vlag aan zonder dat
    Word iets tekent. Een en twintig tabellen in deze Word kregen zo een
    kopregel die er in het document niet staat, waaronder de AND berekening
    van 4.7, waarvan de bovenste rij gewoon het IP adres is. Zonder signaal
    is het geen kopregel maar iets om na te kijken, en dat zegt de log dan
    ook.
    """
    pr = tabel.rows[0]._tr.find(qn("w:trPr"))
    if pr is not None and pr.find(qn("w:tblHeader")) is not None:
        return True, "de Word duidt de kopregel zelf aan (tblHeader)"

    vet = []
    for tc, _, _, _ in rijen[0]:
        runs = [r for r in tc.findall(".//" + qn("w:r"))
                if "".join(t.text or "" for t in r.findall(qn("w:t"))).strip()]
        if not runs:
            continue
        vet.append(all(r.find(qn("w:rPr")) is not None
                       and r.find(qn("w:rPr")).find(qn("w:b")) is not None
                       for r in runs))
    if vet and all(vet):
        return True, "de hele eerste rij staat vet"

    tblpr = tabel._tbl.find(qn("w:tblPr"))
    look = tblpr.find(qn("w:tblLook")) if tblpr is not None else None
    stijl = tblpr.find(qn("w:tblStyle")) if tblpr is not None else None
    stijl_id = stijl.get(f"{{{W}}}val") if stijl is not None else None
    eerste_rij = (look is not None and look.get(f"{{{W}}}firstRow") == "1"
                  and maakt_stijl_eerste_rij_op(doc, stijl_id))
    if eerste_rij and len(rijen[0]) > 1 and len(rijen) > 2:
        return True, "de tabelstijl maakt de eerste rij op (tblLook firstRow)"
    return False, ("eenkolomstabel" if len(rijen[0]) < 2 else "geen enkel signaal")


def cel_html(tc, ctx, ontvet=False):
    inhoud = renderen(list(blokken(Cel(tc), ctx["doc"])), ctx,
                      kop_offset=3, ontvet=ontvet)
    if len(inhoud) == 1 and inhoud[0].startswith("<p>") and inhoud[0].endswith("</p>"):
        return inhoud[0][3:-4]
    return "\n".join(inhoud)


def tabel_html(tabel, ctx):
    rijen = rooster(tabel)
    waar = ctx["waar"]
    alle_tekst = "".join(c.text for r in tabel.rows for c in r.cells).strip()

    # Kader met titel: twee rijen, de tweede over de volle breedte.
    if (len(rijen) == 2 and len(rijen[0]) == 2 and len(rijen[1]) == 1
            and rijen[1][0][2] > 1):
        titel = tabel.rows[0].cells[-1].text.strip()
        inhoud_cel = rijen[1][0][0]
        ontvet = volledig_vet(list(blokken(Cel(inhoud_cel), ctx["doc"])))
        binnen = cel_html(inhoud_cel, ctx, ontvet=ontvet)
        klasse = "tip" if "vragen" in titel.lower() else "remark"
        # data-kader zegt WELK kader dit is. Op de site tekent OrionCSS het via
        # de info-title-klasse; in de PDF hangt Theorie/Syllabus/syllabus.css er
        # de kleur en het icoon van HOGENT aan, en die horen bij het soort kader
        # en niet bij de OrionCSS-klasse.
        soort = slug(titel)
        gevolg = " en het vet, want de hele inhoud stond vet" if ontvet else ""
        noteer(waar, f'kader "{titel}" werd een info-box met data-kader="{soort}"; '
                     f'het icoontje uit de Word valt weg{gevolg}')
        return (f'<div class="info-box" data-kader="{soort}">\n'
                f'    <div class="info-title {klasse}">{html.escape(titel)}</div>\n'
                + inspringen(binnen, 4) + "\n</div>")

    # Lege tabel: invulruimte voor de student, die op papier moet blijven.
    if not alle_tekst:
        noteer(waar, f"lege tabel van {len(tabel.rows)} rijen overgenomen als invulruimte")
        body = "\n".join("            <tr><td>&nbsp;</td></tr>" for _ in tabel.rows)
        return ('<div class="table-responsive table-spacer">\n'
                '    <table class="table table-bordered invulruimte">\n'
                '        <tbody>\n' + body + '\n        </tbody>\n'
                '    </table>\n</div>')

    kop, reden = heeft_kopregel(tabel, rijen, ctx["doc"])
    eerste_cel = tabel.rows[0].cells[0].text.strip()[:30]
    if kop:
        noteer(waar, f'tabel "{eerste_cel}" kreeg een kopregel, want {reden}')
    else:
        noteer(waar, f'tabel "{eerste_cel}" kreeg GEEN kopregel ({reden}), nakijken')

    # Waar de Word niets zegt, gokt de importer, en die gok hoort in de pagina
    # te staan en niet alleen in IMPORT.md. Een logregel wordt niet gelezen en
    # veroudert bovendien stil: verander je hier een regel of pas je de HTML met
    # de hand aan, dan blijft er in IMPORT.md staan wat er ooit gebeurde. Het
    # attribuut staat bij de markup die het beschrijft, en de regel
    # importer-guess van de check (orion.py check) laat de check erop vallen tot een mens beslist
    # heeft. Je lost het op door het attribuut te schrappen (gok bevestigd) of
    # door de markup te veranderen.
    #
    # Alleen wanneer er geen enkel signaal is. Een eenkolomstabel is een
    # afgesproken uitzondering en geen gok, en een kopregel die de Word wel
    # aanduidt evenmin.
    geraden = ""
    if not kop and reden == "geen enkel signaal":
        # Het label van de tabel gaat mee, anders staan er op een pagina met drie
        # zulke tabellen drie meldingen die niet uit elkaar te houden zijn.
        label = html.escape(" ".join(eerste_cel.split())[:24], quote=True)
        geraden = (' data-geraden="kopregel: de Word geeft geen enkel signaal'
                   f'{(", tabel " + label) if label else ""}"')

    # Een kolom die overal leeg staat, is invulruimte binnen een tabel die
    # verder tekst draagt. Ze wordt als zodanig gemerkt en de tabel krijgt de
    # kolombreedtes van de Word mee, want anders houdt Chrome niets over om in
    # te schrijven. Wat de bladzijde daarmee doet, beslist syllabus.css.
    leeg = lege_kolommen(tabel)
    breedtes = kolombreedtes(tabel) if leeg else []
    if leeg and len(breedtes) != len(tabel.columns):
        noteer(waar, f'tabel "{eerste_cel}" heeft een lege kolom, maar de Word '
                     f"geeft er geen breedtes bij; de invulkolom blijft smal")
        leeg, breedtes = set(), []
    elif leeg:
        kolommen = ", ".join(str(i + 1) for i in sorted(leeg))
        noteer(waar, f'tabel "{eerste_cel}": kolom {kolommen} staat overal leeg '
                     f"en werd invulruimte, op de breedte van de Word")

    def rij_html(cellen, tag):
        uit = []
        for tc, rs, cs, kolom in cellen:
            attrs = f' rowspan="{rs}"' if rs > 1 else ""
            attrs += f' colspan="{cs}"' if cs > 1 else ""
            if kolom in leeg:
                attrs += ' class="invulruimte"'
            uit.append(f"<{tag}{attrs}>{cel_html(tc, ctx)}</{tag}>")
        return "<tr>" + "".join(uit) + "</tr>"

    klassen = "table table-bordered" + (" invulkolom" if leeg else "")
    stukken = ['<div class="table-responsive table-spacer">',
               f'    <table class="{klassen}"{geraden}>']
    if breedtes:
        stukken.append("        <colgroup>")
        for mm in breedtes:
            stukken.append(f'            <col style="--kolom-breedte: {mm}mm">')
        stukken.append("        </colgroup>")
    eerste = 0
    if kop:
        stukken += ['        <thead class="table-header-custom">',
                    "            " + rij_html(rijen[0], "th"),
                    "        </thead>"]
        eerste = 1
    stukken.append("        <tbody>")
    for rij in rijen[eerste:]:
        stukken.append("            " + rij_html(rij, "td"))
    stukken += ["        </tbody>", "    </table>", "</div>"]
    return "\n".join(stukken)


# ---------------------------------------------------------------- render

def lijst_html(tag, items, start=1):
    """<ul>/<ol> met een <li> per item; wat bij een item hoort, zit in dat <li>."""
    attr = f' start="{start}"' if tag == "ol" and start > 1 else ""
    regels = [f"<{tag}{attr}>"]
    for tekst, onder in items:
        if onder:
            regels.append(f"    <li>{tekst}")
            for stuk in onder:
                regels.append(inspringen(stuk, 8))
            regels.append("    </li>")
        else:
            regels.append(f"    <li>{tekst}</li>")
    regels.append(f"</{tag}>")
    return "\n".join(regels)


def vast_bijschrift(plaatjes):
    """Neemt een van deze afbeeldingen de tekst van de alinea als bijschrift over?

    Alleen een INLINE afbeelding doet dat (zie zwevend_van). Staan er enkel
    zwevende plaatjes in de alinea, dan is haar tekst gewone lopende tekst en
    moet ze als <p> blijven staan; zonder deze vraag valt ze weg omdat er
    "wel een afbeelding" in de alinea zat.
    """
    return any(not zwevend for _, _, zwevend in plaatjes)


def renderen(blokkenlijst, ctx, kop_offset=2, ontvet=False):
    """Blokken naar HTML-fragmenten.

    Twee dingen die een lijst NIET afsluiten, want in deze Word horen ze bij het
    vorige lijstitem en niet ernaast. Allebei komen ze uit Test jezelf:

      - een lege tabel vlak na een genummerde vraag is de schrijfruimte voor het
        antwoord op die vraag;
      - een bulletlijst vlak na een genummerde vraag zijn de keuzemogelijkheden
        bij die vraag. Word geeft die een eigen numId in plaats van een tweede
        niveau, dus het inspringen zegt het niet en de nummering wel.

    Een lege alinea sluit ook niets af. Word zet er een tussen elke vraag, en
    wie daarop afsluit, laat elke vraag opnieuw bij 1 beginnen.

    Wat een lijst WEL afsluit, is een gewone alinea ertussen ("Ook in industriele
    netwerken ..."), en dan telt de volgende lijst door met een start-attribuut.
    Die zin hoort niet bij de vraag erboven en niet bij die eronder, dus hij komt
    ertussen te staan zoals in de Word, maar de nummering mag er niet aan
    kapotgaan.
    """
    uit = []
    stapel = []          # open lijsten: [tag, items, sleutel] van buiten naar binnen
    geteld = {}          # sleutel -> hoeveel items die nummering al gehad heeft

    def sluit_tot(niveau):
        while len(stapel) > niveau:
            tag, items, sleutel = stapel.pop()
            start = geteld.get(sleutel, 0) + 1
            geteld[sleutel] = start - 1 + len(items)
            klaar = lijst_html(tag, items, start)
            if stapel:
                stapel[-1][1][-1][1].append(klaar)
            else:
                uit.append(klaar)

    def onder_laatste(fragment):
        """Hang een blok onder het lopende lijstitem in plaats van ernaast."""
        stapel[-1][1][-1][1].append(fragment)

    for blok in blokkenlijst:
        if isinstance(blok, Table):
            leeg = not "".join(c.text for r in blok.rows for c in r.cells).strip()
            if (leeg or lege_kolom(blok)) and stapel and stapel[-1][1]:
                if not leeg:
                    noteer(ctx["waar"], "tabel met een lege kolom onder de vraag "
                                        "erboven gezet als invulruimte")
                onder_laatste(tabel_html(blok, ctx))
                continue
            sluit_tot(0)
            uit.append(tabel_html(blok, ctx))
            continue

        niveau = kopniveau(blok)
        inhoud = alinea_html(blok, ctx["rels"], ontvet).strip()
        plaatjes = afbeeldingen_van(blok._p, ctx["doc"], ctx["stam"], ctx["teller"])

        if niveau:
            sluit_tot(0)
            tag = f"h{min(max(niveau - kop_offset + 1, 2), 6)}"
            uit.append(f"<{tag}>{inhoud}</{tag}>")
            continue

        info = lijstinfo(blok, ctx["formaten"])
        if info and inhoud:
            ilvl, tag, num_id = info
            if (ilvl == 0 and tag == "ul" and stapel and stapel[0][0] == "ol"
                    and stapel[0][1]):
                ilvl = len(stapel) if stapel[-1][0] == "ol" else len(stapel) - 1
            sluit_tot(ilvl + 1)
            if len(stapel) == ilvl + 1 and stapel[ilvl][0] != tag:
                sluit_tot(ilvl)
            while len(stapel) < ilvl + 1:
                stapel.append([tag, [], (num_id, len(stapel))])
            stapel[-1][1].append([inhoud, []])
            # Een afbeelding in de alinea van een lijstitem hoort bij dat item.
            # De drie topologievragen van hoofdstuk 2 dragen elk hun tekening zo,
            # en zonder haar is de vraag niet te beantwoorden. Ze krijgt geen
            # bijschrift: de tekst van de alinea is de vraag zelf.
            for naam, breedte, _ in plaatjes:
                noteer(ctx["waar"], f"afbeelding {naam} stond in een lijstitem "
                                    "en is erin gezet, zonder bijschrift")
                onder_laatste(figuur(naam, "", ctx["diepte"], breedte))
            continue

        if (info is None and lijstalinea(blok) and stapel and stapel[-1][1]
                and (inhoud or plaatjes)):
            for naam, breedte, zwevend in plaatjes:
                onder_laatste(figuur(naam, "" if zwevend else inhoud,
                                     ctx["diepte"], breedte))
            if inhoud and not vast_bijschrift(plaatjes):
                onder_laatste(f"<p>{inhoud}</p>")
            continue

        # Een alinea zonder tekst die alleen een tekening draagt, sluit een
        # genummerde lijst niet af: in deze Word staat die tekening bij de vraag
        # erboven en volgen de keuzemogelijkheden eronder. Vraag 13 en 19 van
        # Test jezelf van de datalink laag zijn zo gebouwd. Zonder deze regel
        # valt zo'n vraag uiteen in een lijstitem, een losse figuur en een losse
        # bulletlijst, en dan staan de keuzes buiten de vraag: de export vindt
        # er geen enkele in en kan de letter van het juiste antwoord niet meer
        # tellen. Alleen bij een open <ol>, zoals de keuzelijst-regel hierboven,
        # want na een gewone opsomming is een figuur wel degelijk een figuur.
        if (not inhoud and plaatjes and stapel and stapel[0][0] == "ol"
                and stapel[-1][1]):
            for naam, breedte, _ in plaatjes:
                noteer(ctx["waar"], f"afbeelding {naam} stond tussen een vraag "
                                    "en haar keuzes en is in de vraag gezet")
                onder_laatste(figuur(naam, "", ctx["diepte"], breedte))
            continue

        if not inhoud and not plaatjes:
            continue

        sluit_tot(0)
        if "—" in inhoud or "–" in inhoud:
            noteer(ctx["waar"], f"em-dash of en-dash in: {strip_tags(inhoud)[:70]}")
        for naam, breedte, zwevend in plaatjes:
            if zwevend:
                noteer(ctx["waar"], f"afbeelding {naam} zweeft naast haar alinea "
                                    "(wrapSquare); die alinea blijft lopende tekst "
                                    "en de figuur krijgt geen bijschrift uit de Word")
            uit.append(figuur(naam, "" if zwevend else inhoud,
                              ctx["diepte"], breedte))
        if inhoud and not vast_bijschrift(plaatjes):
            uit.append(f"<p>{inhoud}</p>")

    sluit_tot(0)
    return uit


# ---------------------------------------------------------------- pagina

SJABLOON = """<!DOCTYPE html>
<html lang="nl">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titel}</title>
    <link rel="stylesheet" href="https://tdmts.github.io/OrionCSS/style.css">
    <script type="text/javascript" src="https://tdmts.github.io/OrionCSS/main.js"></script>
</head>

<body>
    <div class="container">
        <h1>{kop}</h1>

{inhoud}
    </div>

</body>

</html>
"""


def inspringen(tekst, spaties):
    pre = " " * spaties
    return "\n".join(pre + r if r.strip() else r for r in tekst.split("\n"))


def schrijf_pagina(pad, titel, blokkenlijst):
    body = "\n\n".join(inspringen(b, 8) for b in blokkenlijst)
    pad.parent.mkdir(parents=True, exist_ok=True)
    pad.write_text(SJABLOON.format(titel=html.escape(strip_tags(titel)),
                                   kop=html.escape(titel), inhoud=body),
                   encoding="utf-8")
    print(f"    {pad.relative_to(REPO)}")


# ------------------------------------------------------------------ main

def verwerk(titel, inhoud, doc, rels, formaten, nummer):
    mapnaam = pascal(titel)
    doelmap = UIT / mapnaam if nummer else UIT
    stam = (f"syllabus-{nummer:02d}-{slug(titel)}" if nummer
            else f"syllabus-00-{slug(titel)}")
    ctx = {"doc": doc, "rels": rels, "formaten": formaten, "stam": stam,
           "teller": [0], "waar": titel,
           "diepte": len(doelmap.relative_to(REPO).parts)}

    secties = [i for i, b in enumerate(inhoud)
               if isinstance(b, Paragraph) and kopniveau(b) == 2]
    opening = inhoud[:secties[0]] if secties else inhoud

    if any(isinstance(b, Table) or b.text.strip() for b in opening):
        ctx["waar"] = f"{titel} (opening)"
        naam = "Overzicht.html" if nummer else f"{mapnaam}.html"
        schrijf_pagina(doelmap / naam, titel, renderen(opening, ctx))

    for n, i in enumerate(secties):
        eind = secties[n + 1] if n + 1 < len(secties) else len(inhoud)
        kop = inhoud[i].text.strip()
        ctx["waar"] = f"{titel} > {kop}"
        schrijf_pagina(doelmap / f"{pascal(kop)}.html", kop,
                       renderen(inhoud[i + 1:eind], ctx))


KOP = """# Wat de import gemeld heeft

Dit bestand wordt door orion.py import-syllabus geschreven en bij elke run
overschreven voor de hoofdstukken die hij net gedaan heeft. De andere blijven
staan. Schrijf er dus niets met de hand in; inhoudelijke bevindingen horen in
NOTITIES.md ernaast.

Per kop staat wat de omzetting moest raden of liet vallen. De tekst zelf is
letterlijk overgenomen.
"""


def schrijf_notities(verwerkte_titels):
    """Vervang de secties van de hoofdstukken die net gedaan zijn, laat de rest.

    Aanvullen zou bij elke tweede run alles verdubbelen, en helemaal overschrijven
    zou de meldingen van de vijf andere hoofdstukken wissen zodra je er een
    opnieuw importeert.
    """
    IMPORT_LOG.parent.mkdir(parents=True, exist_ok=True)
    bewaard = []
    if IMPORT_LOG.exists():
        houden = True
        for regel in IMPORT_LOG.read_text(encoding="utf-8").splitlines():
            if regel.startswith("## "):
                kop = regel[3:].strip()
                houden = not any(kop == t or kop.startswith(t + " ")
                                 for t in verwerkte_titels)
            elif regel.startswith("# "):
                houden = False
            if houden:
                bewaard.append(regel)

    regels = []
    huidig = None
    for waar, tekst in notities:
        if waar != huidig:
            regels += ["", f"## {waar}", ""]
            huidig = waar
        regels.append(f"- {tekst}")

    tekst = KOP + "\n".join(bewaard).strip() + "\n" + "\n".join(regels) + "\n"
    IMPORT_LOG.write_text(re.sub(r"\n{3,}", "\n\n", tekst), encoding="utf-8")
    print(f"    {IMPORT_LOG.relative_to(REPO)}")


def main(argv=None):
    global REPO, UIT, IMG, IMPORT_LOG, AFKORTINGEN, VET_UIT_DE_WORD
    p = argparse.ArgumentParser(
        prog="orion.py import-syllabus",
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--hoofdstuk", type=int,
                   help="het hoeveelste genummerde hoofdstuk (Voorwoord telt niet mee)")
    p.add_argument("--voorwoord", action="store_true", help="ook het Voorwoord omzetten")
    p.add_argument("--docx", help="de Word (standaard: syllabus.docx uit oriontools.json, "
                                  "relatief aan je thuismap)")
    repo.voeg_repo_toe(p)
    args = p.parse_args(argv)

    vak = repo.vind(args)
    instelling = vak.config["syllabus"]
    REPO = vak.root
    UIT = vak.pad("syllabus_src")
    IMG = vak.pad("img")
    IMPORT_LOG = vak.pad("syllabus_dir") / "IMPORT.md"
    AFKORTINGEN = dict(instelling["afkortingen"])
    VET_UIT_DE_WORD = instelling["vet_uit_de_word"]

    if args.docx:
        bron = Path(args.docx)
    elif instelling["docx"]:
        bron = Path.home() / instelling["docx"]
    else:
        sys.exit("geen Word: geef --docx PAD of zet syllabus.docx in oriontools.json")
    if not bron.exists():
        sys.exit(f"niet gevonden: {bron}")
    if not args.hoofdstuk and not args.voorwoord:
        sys.exit("geef --hoofdstuk N, --voorwoord, of allebei")

    doc = docx.Document(str(bron))
    formaten = lees_nummering(bron)
    rels = {rid: rel.target_ref for rid, rel in doc.part.rels.items()}

    alles = list(blokken(doc.element.body, doc))
    grenzen = [i for i, b in enumerate(alles)
               if isinstance(b, Paragraph) and kopniveau(b) == 1]
    titels = [alles[i].text.strip() for i in grenzen]
    genummerd = [(i, t) for i, t in zip(grenzen, titels) if t.lower() != "voorwoord"]

    doelen = []
    if args.voorwoord:
        if not titels or titels[0].lower() != "voorwoord":
            sys.exit("de eerste Heading 1 van de Word is geen Voorwoord")
        eind = grenzen[1] if len(grenzen) > 1 else len(alles)
        doelen.append(("Voorwoord", grenzen[0], eind, None))
    if args.hoofdstuk:
        if args.hoofdstuk > len(genummerd):
            sys.exit(f"de Word heeft {len(genummerd)} genummerde hoofdstukken")
        start, titel = genummerd[args.hoofdstuk - 1]
        verder = [g for g in grenzen if g > start]
        doelen.append((titel, start, verder[0] if verder else len(alles), args.hoofdstuk))

    IMG.mkdir(exist_ok=True)
    for titel, start, eind, nummer in doelen:
        verwerk(titel, alles[start + 1:eind], doc, rels, formaten, nummer)

    schrijf_notities([t for t, _, _, _ in doelen])

    return 0
