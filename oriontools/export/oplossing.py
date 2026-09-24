"""Genereer het ingevulde oplossingendocument (.pdf) van een opdracht.

    python ../OrionTools/orion.py export-oplossing Labo/RS485

Het antwoordbestand is standaard <oplossingen>/RS485.md (paths.oplossingen,
standaard _oplossingen/): het pad van de opdracht zonder de labomap ervoor,
met streepjes. De PDF komt ernaast als Labo-RS485-oplossing.pdf.

Het document is de opdracht met de antwoorden erin, met "OPLOSSING" diagonaal
over elke bladzijde gestempeld.

WIE HET LEEST
-------------
De student, meteen nadat hij zijn opdracht ingediend heeft, om zijn eigen werk
mee na te kijken. Er is maar EEN uitvoering: geen tweede met correctienoten
erbij, want dan is er een versie die per ongeluk de verkeerde kant op gaat.

EEN ANTWOORD IS EEN BLOK, EN ER HANGT NIETS ONDER
-------------------------------------------------
Waar het verslag een leeg kader of een lege tabelkolom heeft, staat hier
hetzelfde kader of dezelfde tabel met het antwoord erin. Daarmee is het af:
onder een kader komt geen uitleg, geen nuance en geen noot. Wie er toch een
schrijft, krijgt de regel te zien in plaats van stil een document met
commentaar eronder; zie ONDER_HET_KADER.

Wat je kwijt wil, hoort dus in het antwoord zelf, of het hoort er niet.

WAT ER NIET IN GIT MAG
----------------------
Geen van de twee, en de antwoorden evenmin. Een inleverfolder op Orion geeft de
oplossing pas vrij NA het indienen, en dat is precies het punt; alles wat hier
getrackt staat, spiegelt OrionSync naar de cursusbestanden, waar elke
ingeschreven student erbij kan, ook wie nog moet indienen. Daarom staat alles in
`_oplossingen/`, dat in .gitignore staat, en schrijft dit script standaard
nergens anders naartoe. Dit script zelf draagt geen enkel antwoord en mag dus
wel mee.

Opladen naar Orion doe je met de hand. Dat is met opzet geen stap die hier
geautomatiseerd staat.

HOE HET NIET KAN VEROUDEREN
---------------------------
Zelfde afspraak als bij export-verslag: de vragen komen uit het
`<!-- verslag -->` blok van Opdracht.html en worden hier niet overgetypt. Het
antwoordbestand draagt alleen de ANTWOORDEN, per vraagnummer. Verdwijnt er een
vraag of komt er een bij, dan klopt de nummering niet meer en slaat dit script
af met de vraag welke sleutel er ontbreekt of te veel is. Dat is de enige
bewaking die er is, en ze is er precies omdat een oplossing die stil
achterloopt erger is dan geen oplossing.

De nummering is dezelfde als in het verslagsjabloon: EEN teller over het hele
blok, alleen voor `<ol class="vragen">`, dus vraag 11 volgt op vraag 10 ook al
staan er twee koppen tussen.

HET ANTWOORDBESTAND
-------------------
Platte tekst, per opdracht een bestand in `_oplossingen/`:

    # Een regel die met # begint is een noot voor jezelf en komt nergens.

    [kader] Foto van je goedgekeurde schema
    Wat er op de foto te zien hoort te zijn.

    2.
    Het antwoord op vraag 2. Een lege regel begint een nieuwe alinea.

    3.
    Lengte: 305 mm
    Breedte: 244 mm

    [sectie] Schakeling deel 4
    De uitwerking van een schakeling die geen genummerde vraag draagt.

    ```
    void loop()
    {
    }
    ```

* `N.` op een eigen regel opent het antwoord op vraag N.
* `[kader]` opent het antwoord op het volgende invulkader, in de volgorde
  waarin de kaders in de opdracht staan. Wat erachter staat is een geheugensteun
  en wordt niet vergeleken.
* `[sectie] <kop>` opent een uitwerking die onderaan die `<h2>` komt. De reden
  staat onder EEN SECTIE ZONDER VRAAG hieronder.
* Draagt de vraag een `<table class="verslag-tabel">`, dan vullen de regels,
  in de vorm `Rijlabel: waarde`, die rijen in. Een label dat niet in de tabel
  staat slaat af, een rij zonder antwoord ook, en tekst NA de rijen ook: dat
  zou onder de tabel belanden. Draagt de vraag geen tabel, dan is een regel met
  een dubbelpunt gewoon een zin.
* Heeft die tabel meer dan twee kolommen, dan scheidt `|` de waarden van de
  kolommen na het rijlabel: `Rijlabel: kolom 2 | kolom 3`. Spaties rond de
  streep tellen niet mee, en een waarde MAG leeg zijn: `R:  |  | x |` zet een
  kruisje in de derde kolom van vier en laat de rest blanco. In de ICEES-kopie
  van dit script was ` | ` de scheiding en kon een lege kolom niet, want daar
  vult elke rij elke kolom. De pintabel van RS485 in DeN vraagt precies het
  omgekeerde: een kruisje in een van de vier. Wat met ` | ` geschreven was,
  leest hier hetzelfde. Een rij met te veel of te weinig waarden slaat af.
* Het label eindigt op de eerste dubbelpunt MET een spatie erachter, zodat een
  label als een Windows-pad met `c:` erin heel blijft.
* Een blok tussen ``` wordt een codeblok. Alleen daar blijft de inspringing
  staan; elders wordt een regel gestript, want daar is ze opmaak van het
  antwoordbestand en niet van het antwoord.
* `[figuur] <pad>` sluit een afbeelding in, op de plaats waar de regel staat.
  Zie DE FIGUUR BIJ EEN ANTWOORD hieronder.

DE FIGUUR BIJ EEN ANTWOORD
--------------------------
Een vraag die om een screenshot uit de datasheet vraagt, wordt met woorden
alleen niet beantwoord: "de bladzijde Pin Configuration and Functions" is een
verwijzing, en de student legt dit document naast zijn verslag om te zien of
hij het juiste beeld genomen heeft. Daarom mag een antwoord een figuur dragen:

    [figuur] datasheets/sn75176a.pdf blz 3 vak 0.07,0.09,0.93,0.44
    [figuur] img/rs485-schakeling-deel2-arduino-zender.png breedte 10cm

Het pad is het eerste woord en draagt dus zelf geen spaties; het wordt gezocht
vanaf de root van de vakrepo en anders naast het antwoordbestand. Daarachter
mag staan:

* `blz N`  welke bladzijde van een PDF. Alleen voor een PDF, en verplicht.
* `vak l,b,r,o`  welk stuk van die bladzijde, als breuken van haar breedte en
  hoogte, van linksboven. Laat je het weg, dan komt de hele bladzijde mee.
* `breedte Ncm`  hoe breed de figuur afgedrukt wordt. Standaard is dat haar
  eigen maat, afgetopt op de tekstbreedte.

DE FIGUUR KOMT UIT DE PDF ZELF, NIET UIT EEN SCREENSHOT
-------------------------------------------------------
De datasheet staat in `datasheets/` omdat een link naar een fabrikant
halverwege het semester sterft. Precies daarom wordt de figuur hier uit dat
bestand geknipt en niet apart bewaard: de bron staat in git, het knipsel niet,
en zo kan het knipsel niet achterlopen op een datasheet die vervangen wordt.
Een screenshot ernaast zou dat wel kunnen, en niets zou het merken.

Het knippen gebeurt met pypdfium2, dat alleen ingeladen wordt als er echt een
PDF in een antwoord staat. Een labo dat geen datasheetfiguur nodig heeft, heeft
het pakket dus niet nodig, dezelfde afspraak die export-verslag met Chrome
maakt.

EEN SECTIE ZONDER VRAAG
-----------------------
Een DeN-labo vraagt niet alleen om geschreven antwoorden. Schakeling 3 draagt
twee opzettelijke compileerfouten, en schakeling 4, 6 en 7 vragen om code en om
een schakeling zonder er ook maar een genummerde vraag bij te stellen. Zonder
`[sectie]` zou de oplossing die halve opdracht stilzwijgend overslaan: de kop
staat er dan wel, en er staat niets onder.

De sleutel hangt aan de TEKST van de `<h2>`, en het antwoord komt onderaan die
sectie, na de code en na "Laat je oefening controleren". Vandaar dat het niet
aan een nummer hangt: een sectie heeft er geen, en de kop is wat de lezer ziet.
Hernoem je de kop in Opdracht.html, dan vindt de sleutel niets meer en slaat dit
script af, dezelfde bewaking als bij een vraagnummer. Een sectie zonder
`[sectie]` is daarentegen gewoon een sectie zonder uitwerking: veel van hen
vragen nergens om, en elke kop verplicht van een antwoord voorzien zou het
document vullen met zinnen die niets zeggen.

WAT ER UIT DE OPDRACHT MEEKOMT
------------------------------
Alles wat in het verslagsjabloon staat: de koppen, de alinea's, de lijsten, de
codeblokken, de figuren, de tips uit een accordeon en de info-boxen. De twee
documenten liggen bij het nakijken naast elkaar, dus wat in het ene staat en in
het andere niet, is een verschil dat de student zelf moet uitzoeken. De
ICEES-kopie van dit script liet de figuren, de accordeons en de info-boxen nog
weg; die zijn er met de samenvoeging in OrionTools bij gekomen.

De kolommen van een ingevulde tabel krijgen geen breedte: de browser verdeelt
ze naar hun inhoud, wat de smalle kruisjeskolommen van de pintabel van RS485
nodig hebben. Gelijke kolommen (width: 50% per cel) gaven daar een brede kolom
voor een kruisje.

Een figuur wordt ingesloten met een absolute file-URL en op de maat die ook
export-verslag rekent: de eigen maat op 96 dpi, afgetopt op de
tekstbreedte. Een svg gaat ongemoeid het document in, want hier drukt Chrome af
en die kent svg wel; alleen Word kan er niet mee overweg.

DE PARSER IS EEN KOPIE
----------------------
`Node`, `TreeBuilder`, `parse_fragment`, `png_afmeting` en `svg_maat` hieronder
komen woord voor woord uit oriontools/export/verslag.py. Ze zijn gekopieerd en
niet geimporteerd, want dat bestand stopt bij het inlezen al met een
foutmelding als python-docx ontbreekt, en dit commando maakt geen docx. Wijzig
je de een, kijk dan de ander na.

Nodig: pypdf en reportlab (pip install pypdf reportlab), plus Chrome of Edge
voor het afdrukken. Dezelfde drie als export-syllabus. Waar die browser staat
weet oriontools/chrome.py, en het afdrukken zelf doet pdfhulp.druk_af. Draagt
een antwoord een figuur uit een PDF, dan komt daar pypdfium2 bij
(pip install pypdfium2).
"""

import argparse
import html as html_mod
import re
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote

from .. import repo
from ..chrome import zoek_chrome
from .pdfhulp import druk_af

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    sys.exit("pypdf ontbreekt:  pip install pypdf")

try:
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas
except ImportError:
    sys.exit("reportlab ontbreekt:  pip install reportlab")


VERSLAG_MARKER = "verslag"
SKIP_CONTENT = {"script", "style", "head"}
VOID = {"img", "br", "hr", "input", "meta", "link"}

WATERMERK = "OPLOSSING"

# De tekstbreedte van het blad: 8,5 duim min tweemaal 1,25 duim marge. Dezelfde
# maat die export-verslag in de docx aanhoudt, zodat een figuur in
# de twee documenten even groot staat.
MAX_BREEDTE_CM = 15.0


# --------------------------------------------------------------- HTML -> boom

class Node:
    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = []
        self.text = ""

    @property
    def classes(self):
        return set((self.attrs.get("class") or "").split())

    def find_all(self, tag):
        for child in self.children:
            if child.tag == tag:
                yield child
            yield from child.find_all(tag)

    def _flat_text(self):
        parts = [self.text] if self.text else []
        for child in self.children:
            if child.tag in SKIP_CONTENT:
                continue
            parts.append(child._flat_text())
        return "".join(parts)

    def inner_text(self):
        return re.sub(r"\s+", " ", self._flat_text()).strip()

    def raw_text(self):
        parts = [self.text] if self.text else []
        for child in self.children:
            parts.append(child.raw_text())
        return "".join(parts)


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        node = Node("#text")
        node.text = data
        self.stack[-1].children.append(node)

    def handle_comment(self, data):
        node = Node("#comment")
        node.text = data
        self.stack[-1].children.append(node)


def parse_fragment(markup):
    builder = TreeBuilder()
    builder.feed(markup)
    return builder.root


# ------------------------------------------------------- het antwoordbestand

class Antwoord:
    """De regels die bij een sleutel horen, nog niet uit elkaar gehaald.

    Of een regel `Label: waarde` een tabelrij is of gewone tekst, hangt af van
    de VRAAG en niet van de regel: "Ja, dat gebeurt vaak: dezelfde kabel ..." is
    een zin. Die beslissing valt dus pas bij het renderen, wanneer bekend is of
    de vraag een invultabel draagt. Ze hier al nemen kostte een valse fout, en
    ze omgekeerd nemen zou een tabelrij stil als alinea afdrukken.
    """

    def __init__(self, sleutel, naam=""):
        self.sleutel = sleutel
        self.naam = naam        # de kop of het opschrift, voor een foutmelding
        self.regels = []        # ruwe regels, lege regels inbegrepen

    def alineas(self):
        tekst = "\n".join(self.regels).strip("\n")
        return [s.strip() for s in re.split(r"\n\s*\n", tekst) if s.strip()]

    def velden_en_rest(self):
        """De kopregels `Label: waarde`, en wat er daarna nog aan tekst staat.

        De reeks stopt bij de eerste regel die geen label draagt, dus een zin
        met een dubbelpunt halverwege het antwoord blijft een zin.
        """
        velden = []
        i = 0
        for i, regel in enumerate(self.regels):
            m = VELD.match(regel.strip())
            if regel.strip() and m:
                velden.append((m.group(1).strip(), (m.group(2) or "").strip()))
                continue
            break
        else:
            i = len(self.regels)
        rest = Antwoord(self.sleutel, self.naam)
        rest.regels = self.regels[i:]
        return velden, rest


# DE REGEL. Een antwoord is precies EEN blok: het ingevulde kader, of de
# ingevulde tabel. Er hangt niets onder. Uitleg onder een kader leest als een
# aanhangsel bij het antwoord, en de student hoort te zien wat het antwoord is
# en verder niets. Hier afgedwongen in plaats van onthouden, want zulke staarten
# sluipen er per vraag een terug in.
ONDER_HET_KADER = (
    "onder een kader hoort niets te staan: een antwoord is het kader of de "
    "tabel, en daarmee is het af. Zet wat je kwijt wil in het antwoord zelf, "
    "of laat het weg. Gevonden:"
)

VRAAGSLEUTEL = re.compile(r"^\s*(\d+)\s*\.\s*$")
KADERSLEUTEL = re.compile(r"^\s*\[kader\]", re.I)
SECTIESLEUTEL = re.compile(r"^\s*\[sectie\]\s*(.+?)\s*$", re.I)
VELD = re.compile(r"^(.{1,120}?):(?:\s+(.*))?$")
HEK = "```"


def normaliseer(tekst):
    return re.sub(r"\s+", " ", html_mod.unescape(tekst or "")).strip().lower()


def lees_antwoorden(pad):
    """Het antwoordbestand als {sleutel: Antwoord}, in leesvolgorde.

    Een vraag heet '3', een invulkader 'kader1', 'kader2', ... op volgorde, en
    een uitwerking onder een kop 'sectie:<kop>'.
    """
    antwoorden = {}
    huidig = None
    kaderteller = 0
    in_code = False

    for regel in pad.read_text(encoding="utf-8").splitlines():
        # Binnen een codeblok is geen enkele regel een sleutel: een Arduino-
        # programma mag gerust met een # beginnen, en "3." hoort ook niet
        # ineens een nieuwe vraag te openen omdat het toevallig op een regel
        # alleen staat.
        if regel.strip().startswith(HEK):
            in_code = not in_code
            if huidig is not None:
                huidig.regels.append(regel.rstrip())
            continue
        if in_code:
            if huidig is None:
                sys.exit(f"{pad.name}: een codeblok voor de eerste sleutel")
            huidig.regels.append(regel.rstrip())
            continue

        if regel.lstrip().startswith("#"):
            continue

        m = VRAAGSLEUTEL.match(regel)
        if m:
            huidig = Antwoord(m.group(1))
            if huidig.sleutel in antwoorden:
                sys.exit(f"{pad.name}: vraag {huidig.sleutel} staat er twee keer in")
            antwoorden[huidig.sleutel] = huidig
            continue

        if KADERSLEUTEL.match(regel):
            kaderteller += 1
            huidig = Antwoord(f"kader{kaderteller}", regel.strip())
            antwoorden[huidig.sleutel] = huidig
            continue

        m = SECTIESLEUTEL.match(regel)
        if m:
            kop = m.group(1)
            huidig = Antwoord(f"sectie:{normaliseer(kop)}", kop)
            if huidig.sleutel in antwoorden:
                sys.exit(f"{pad.name}: sectie '{kop}' staat er twee keer in")
            antwoorden[huidig.sleutel] = huidig
            continue

        if huidig is None:
            if regel.strip():
                sys.exit(f"{pad.name}: tekst voor de eerste sleutel:\n  {regel.strip()}")
            continue

        # Er heeft in ICEES een notensyntaxis gestaan, met > en >>, die tekst
        # ONDER het kader zette. Die is eruit, en de regel hieronder is wat
        # ervoor in de plaats komt: wie zo'n regel toch nog typt, krijgt de
        # regel te zien in plaats van stil een document met een staart eronder.
        if regel.lstrip().startswith(">"):
            sys.exit(f"{pad.name}, {ONDER_HET_KADER}\n  {regel.strip()[:70]}")

        huidig.regels.append(regel.rstrip())

    if in_code:
        sys.exit(f"{pad.name}: een codeblok is niet afgesloten met {HEK}")

    return antwoorden


# ----------------------------------------------------------- de opdracht lezen

def opdrachtblok(pad):
    """(<h1>, lead, het verslagblok als boom) uit een Opdracht.html."""
    root = parse_fragment(pad.read_text(encoding="utf-8"))
    containers = [n for n in root.find_all("div") if "container" in n.classes]
    if not containers:
        sys.exit(f'Geen <div class="container"> in {pad}')
    container = containers[0]

    titels = list(container.find_all("h1"))
    titel = titels[0].inner_text() if titels else pad.parent.name

    leads = [n for n in container.find_all("p") if "lead" in n.classes]
    lead = leads[0].inner_text() if leads else ""

    blokken = [c for c in container.children
               if c.tag == "#comment" and c.text.strip().startswith(VERSLAG_MARKER)]
    if not blokken:
        sys.exit(f"{pad}: geen <!-- verslag --> blok")

    body = Node("div")
    for blok in blokken:
        inhoud = blok.text.strip()
        body.children.extend(parse_fragment(inhoud[len(VERSLAG_MARKER):]).children)
    return titel, lead, body


# ------------------------------------------------------------------- figuren

PNG_SIGNATUUR = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])

SVG_TAG_RE = re.compile(r"<svg\b[^>]*>", re.I | re.S)
# Niet \b voor de naam: in stroke-width staat ook een woordgrens, en dan
# wordt de lijndikte de breedte van de figuur.
MAAT_RE = re.compile(r'(?<![-\w])(width|height)\s*=\s*["\']([0-9.]+)', re.I)
VIEWBOX_RE = re.compile(r'viewBox\s*=\s*["\']\s*[-0-9.]+\s+[-0-9.]+\s+'
                        r'([0-9.]+)\s+([0-9.]+)', re.I)


def png_afmeting(pad):
    """Breedte en hoogte in pixels uit de PNG-header, zonder Pillow erbij te halen."""
    with open(pad, "rb") as f:
        kop = f.read(24)
    if len(kop) < 24 or kop[:8] != PNG_SIGNATUUR:
        return None
    return (int.from_bytes(kop[16:20], "big"), int.from_bytes(kop[20:24], "big"))


def svg_maat(pad):
    """Breedte en hoogte van een svg in CSS-pixels."""
    tag = SVG_TAG_RE.search(pad.read_text(encoding="utf-8", errors="replace"))
    if not tag:
        return None
    # Alleen binnen de openingstag zoeken. Elke <rect> eronder draagt ook een
    # width, en die van de eerste zou anders de maat bepalen.
    tag = tag.group(0)
    maten = {}
    for m in MAAT_RE.finditer(tag):
        maten.setdefault(m.group(1).lower(), float(m.group(2)))
    if "width" in maten and "height" in maten:
        return maten["width"], maten["height"]
    vak = VIEWBOX_RE.search(tag)
    if vak:
        return float(vak.group(1)), float(vak.group(2))
    return None


# Op hoeveel pixels breed een uitsnede uit een PDF getrokken wordt. De figuur
# is in het document ongeveer 15 cm breed en wordt afgedrukt, dus dit komt neer
# op zo'n 270 dpi. Chrome schaalt hem daarna terug; te grof trekken zie je pas
# op papier, en dat is te laat.
FIGUUR_PIXELS = 1600


def pdf_naar_png(pad, blz, vak, doel):
    """Knip een (stuk van een) PDF-bladzijde tot een png. Geeft de breedte in cm.

    pypdfium2 wordt hier pas ingeladen: een labo zonder datasheetfiguur hoeft
    het pakket niet te hebben.
    """
    try:
        import pypdfium2 as pdfium
    except ImportError:
        sys.exit("pypdfium2 ontbreekt, en een antwoord draagt een figuur uit een "
                 "PDF:  pip install pypdfium2")

    doc = pdfium.PdfDocument(str(pad))
    if not 1 <= blz <= len(doc):
        sys.exit(f"{pad.name} heeft {len(doc)} bladzijden, geen {blz}")
    bladzijde = doc[blz - 1]
    breedte_pt, hoogte_pt = bladzijde.get_size()

    links, boven, rechts, onder = vak
    deel = rechts - links
    if deel <= 0 or onder - boven <= 0:
        sys.exit(f"{pad.name}, blz {blz}: het vak {vak} heeft geen oppervlak")

    schaal = FIGUUR_PIXELS / (breedte_pt * deel)
    beeld = bladzijde.render(scale=schaal).to_pil()
    b, h = beeld.size
    beeld.crop((round(links * b), round(boven * h),
                round(rechts * b), round(onder * h))).save(doel)

    # Zelf sluiten: pypdfium2 ruimt zijn documenten anders pas bij het afsluiten
    # op en zegt dat met een waarschuwing, midden tussen de meldingen van dit
    # script door.
    bladzijde.close()
    doc.close()
    # De maat van het knipsel zelf, in punten van 1/72 duim, niet de pixels: die
    # dragen de schaal waarop het getrokken is.
    return breedte_pt * deel / 72 * 2.54


def breedte_cm(pad):
    """De maat waarop de figuur afgedrukt wordt, of None als ze onbekend is.

    Dezelfde rekensom als in export-verslag: de eigen maat op 96 dpi,
    afgetopt op de tekstbreedte. Een klein plaatje wordt dus niet opgeblazen, en
    de figuur staat in de oplossing even groot als in het verslag.
    """
    afmeting = svg_maat(pad) if pad.suffix.lower() == ".svg" else png_afmeting(pad)
    if not afmeting:
        return None
    return min(afmeting[0] / 96 * 2.54, MAX_BREEDTE_CM)


# --------------------------------------------------------------- HTML bouwen

def esc(tekst):
    return html_mod.escape(tekst, quote=False)


def esc_attr(tekst):
    return html_mod.escape(tekst or "", quote=True)


FIGUURREGEL = re.compile(r"^\s*\[figuur\]\s*(\S+)\s*(.*)$", re.I)
BLZ = re.compile(r"\bblz\s+(\d+)\b", re.I)
VAK = re.compile(r"\bvak\s+([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)", re.I)
OPGEGEVEN_BREEDTE = re.compile(r"\bbreedte\s+([0-9.]+)\s*cm\b", re.I)


def antwoord_figuur(regel, staat, waar):
    """De figuur van een `[figuur]`-regel, ingesloten in het antwoord."""
    m = FIGUURREGEL.match(regel)
    pad_tekst, rest = m.group(1), m.group(2)

    # Eerst vanaf de repo, dan naast het antwoordbestand: zo staat een figuur
    # die uit de repo komt op haar eigen plaats, en kan een screenshot die
    # alleen bij de oplossing hoort naast de antwoorden blijven, buiten git.
    pad = staat["wortel"] / pad_tekst
    if not pad.exists():
        pad = staat["antwoordmap"] / pad_tekst
    if not pad.exists():
        sys.exit(f"{waar}: [figuur] {pad_tekst} bestaat niet, niet vanaf de repo "
                 f"en niet naast het antwoordbestand")

    over = rest
    blz = BLZ.search(rest)
    vak = VAK.search(rest)
    opgegeven = OPGEGEVEN_BREEDTE.search(rest)
    for gevonden in (blz, vak, opgegeven):
        if gevonden:
            over = over.replace(gevonden.group(0), "", 1)
    if over.strip():
        sys.exit(f"{waar}: [figuur] {pad_tekst}: dit begrijp ik niet: {over.strip()}")

    if pad.suffix.lower() == ".pdf":
        if not blz:
            sys.exit(f"{waar}: [figuur] {pad_tekst} is een PDF, dus zeg er "
                     f"'blz N' bij")
        vlak = (0.0, 0.0, 1.0, 1.0)
        if vak:
            vlak = tuple(float(g) for g in vak.groups())
        staat["figuur"] += 1
        doel = staat["figuurmap"] / f"antwoord-figuur{staat['figuur']}.png"
        natuurlijk = pdf_naar_png(pad, int(blz.group(1)), vlak, doel)
        pad = doel
    else:
        if blz or vak:
            sys.exit(f"{waar}: [figuur] {pad_tekst} is geen PDF, dus 'blz' en "
                     f"'vak' zeggen hier niets")
        natuurlijk = breedte_cm(pad)

    maat = float(opgegeven.group(1)) if opgegeven else natuurlijk
    stijl = f' style="width: {min(maat, MAX_BREEDTE_CM):.2f}cm"' if maat else ""
    return f'<figure><img src="{esc_attr(pad.as_uri())}" alt=""{stijl}></figure>'


def inhoud(antwoord, staat, waar):
    """De alinea's, de codeblokken en de figuren van een antwoord, als HTML."""
    uit = []
    alinea = []
    code = None

    def spoel():
        if alinea:
            uit.append(f"<p>{esc(chr(10).join(alinea)).strip()}</p>")
            alinea.clear()

    for regel in antwoord.regels:
        if code is None and FIGUURREGEL.match(regel):
            spoel()
            uit.append(antwoord_figuur(regel, staat, waar))
            continue
        if regel.strip().startswith(HEK):
            if code is None:
                spoel()
                code = []
            else:
                uit.append(f'<pre>{esc(chr(10).join(code).strip(chr(10)))}</pre>')
                code = None
            continue
        if code is not None:
            code.append(regel)
        elif regel.strip():
            alinea.append(regel.strip())
        else:
            spoel()
    if code is not None:
        sys.exit(f"{waar}: een codeblok is niet afgesloten met {HEK}")
    spoel()
    return "".join(uit)


def antwoordblok(antwoord, staat, waar):
    """Het ingevulde kader onder een vraag. Er komt niets achter."""
    romp = inhoud(antwoord, staat, waar)
    return f'<div class="antwoord">{romp}</div>' if romp else ""


def ingevulde_tabel(node, velden, waar):
    """De invultabel met de antwoorden in de kolommen na het rijlabel.

    De rijlabels van de opdracht zijn leidend: staat er een label in het
    antwoordbestand dat de tabel niet heeft, dan is de opdracht gewijzigd en
    slaat dit af in plaats van de waarde stil te laten vallen.
    """
    koppen = [c.inner_text() for c in node.find_all("th")]
    rijen = [r for r in node.find_all("tr") if any(c.tag == "td" for c in r.children)]
    if not koppen or not rijen:
        return ""

    per_label = {normaliseer(label): waarde for label, waarde in velden}
    gebruikt = set()

    uit = ['<table class="invul">', "<thead><tr>"]
    for kop in koppen:
        uit.append(f"<th>{esc(kop)}</th>")
    uit.append("</tr></thead><tbody>")

    for rij in rijen:
        cellen = [c for c in rij.children if c.tag == "td"]
        label = cellen[0].inner_text() if cellen else ""
        sleutel = normaliseer(label)
        uit.append("<tr>")
        uit.append(f"<td>{esc(label)}</td>")
        if sleutel in per_label:
            gebruikt.add(sleutel)
            waarden = [per_label[sleutel]]
            if len(koppen) > 2:
                # Op de streep zelf splitsen en pas daarna strippen, want een
                # kolom mag leeg zijn en een lege kolom vooraan of achteraan
                # overleeft een scheiding met spaties erin niet.
                waarden = [w.strip() for w in per_label[sleutel].split("|")]
                if len(waarden) != len(koppen) - 1:
                    sys.exit(f"{waar}: rij '{label}' draagt {len(waarden)} waarden, "
                             f"de tabel heeft er {len(koppen) - 1} nodig, "
                             f"gescheiden door '|'")
            for waarde in waarden:
                uit.append(f'<td class="gevuld">{esc(waarde)}</td>')
        else:
            for _ in range(len(koppen) - 1):
                uit.append('<td class="ontbreekt"></td>')
        uit.append("</tr>")
    uit.append("</tbody></table>")

    over = set(per_label) - gebruikt
    if over:
        namen = ", ".join(sorted(over))
        sys.exit(f"{waar}: deze labels staan niet in de tabel van de opdracht: {namen}")
    ontbreekt = [normaliseer([c for c in r.children if c.tag == "td"][0].inner_text())
                 for r in rijen]
    leeg = [n for n in ontbreekt if n not in per_label]
    if leeg:
        namen = ", ".join(leeg)
        sys.exit(f"{waar}: geen antwoord voor deze rijen: {namen}")
    return "".join(uit)


def figuur(node, basis):
    """Sluit de afbeelding in, met een absolute file-URL.

    Het document wordt in een tijdelijke map gedrukt, dus een relatief pad uit
    Opdracht.html wijst daar naar niets. Een svg gaat ongewijzigd mee: hier
    drukt Chrome af, en die kent svg.
    """
    imgs = list(node.find_all("img"))
    if not imgs:
        return ""
    src = imgs[0].attrs.get("src", "")
    alt = imgs[0].attrs.get("alt", "")
    pad = (basis / unquote(urlparse(src).path)).resolve()
    if not pad.exists():
        return f'<p class="ontbreekt">[Afbeelding ontbreekt: {esc(src)}]</p>'

    maat = breedte_cm(pad)
    stijl = f' style="width: {maat:.2f}cm"' if maat else ""
    uit = [f'<figure><img src="{esc_attr(pad.as_uri())}" alt="{esc_attr(alt)}"{stijl}>']

    onderschriften = [c for c in node.children if c.tag == "figcaption"]
    tekst = onderschriften[0].inner_text() if onderschriften else alt
    if tekst:
        uit.append(f"<figcaption>{esc(tekst)}</figcaption>")
    uit.append("</figure>")
    return "".join(uit)


def accordion(node):
    """Een hint of een tip. Op het scherm klapt die open; hier staat hij open.

    Zoals in het verslagsjabloon: wat daar staat en hier niet, is een verschil
    dat de student bij het nakijken zelf moet uitzoeken.
    """
    uit = []
    for item in node.children:
        if "accordion-item" not in item.classes:
            continue
        titels = [c for c in item.children if "title" in c.classes]
        rest = Node("div")
        rest.children = [c for c in item.children if "title" not in c.classes]
        kop = f"<strong>{esc(titels[0].inner_text())}</strong> " if titels else ""
        uit.append(f'<p class="tip">{kop}{esc(rest.inner_text())}</p>')
    return "".join(uit)


def infobox(node):
    """Een info-box als een ingesprongen alinea met een vet opschrift."""
    titels = [c for c in node.children if "info-title" in c.classes]
    opschrift = titels[0].inner_text() if titels else ""
    rest = Node("div")
    rest.children = [c for c in node.children if "info-title" not in c.classes]
    if opschrift and opschrift[-1] not in ".:?!":
        # Het opschrift is vet, maar het loopt in dezelfde alinea door in de
        # tekst erna, en twee zinnen zonder scheiding lezen als een.
        opschrift += "."
    kop = f"<strong>{esc(opschrift)}</strong> " if opschrift else ""
    return f'<p class="tip">{kop}{esc(rest.inner_text())}</p>'


# Een blok binnen een <li> krijgt zijn eigen alinea's onder die stap, in plaats
# van dat de afbeelding wegvalt en haar onderschrift in de zin van de stap
# belandt. Zelfde lijst als in export-verslag.
BLOKKEN_IN_LI = ("ol", "ul", "figure", "pre")


def blok_in_li(sub, basis):
    if sub.tag == "figure":
        return figuur(sub, basis)
    if sub.tag == "pre":
        return f"<pre>{esc(html_mod.unescape(sub.raw_text()).strip())}</pre>"
    return lijst(sub, basis)


def lijst(node, basis):
    uit = [f"<{node.tag}>"]
    for li in node.children:
        if li.tag != "li":
            continue
        blokken = [c for c in li.children if c.tag in BLOKKEN_IN_LI]
        hints = [c for c in li.children if "accordion-container" in c.classes]
        eigen = Node("li")
        eigen.children = [c for c in li.children
                          if c.tag not in BLOKKEN_IN_LI
                          and "accordion-container" not in c.classes]
        uit.append(f"<li>{esc(eigen.inner_text())}")
        for blok in blokken:
            uit.append(blok_in_li(blok, basis))
        for hint in hints:
            uit.append(accordion(hint))
        uit.append("</li>")
    uit.append(f"</{node.tag}>")
    return "".join(uit)


def vragenlijst(node, uit, antwoorden, staat, basis, waar):
    """Elke vraag als een alinea met een vet nummer, niet als een <li>.

    export-verslag doet het in de docx net zo: een gewone alinea met
    een vette run "N. " ervoor. Een echte <ol> springt in, en dan lopen het
    verslag en de oplossing niet meer gelijk.
    """
    for li in node.children:
        if li.tag != "li":
            continue
        staat["vraag"] += 1
        nummer = str(staat["vraag"])
        antwoord = antwoorden.get(nummer)
        if antwoord is None:
            sys.exit(f"{waar}: geen antwoord voor vraag {nummer}")
        staat["gezien"].add(nummer)

        tabellen = [c for c in li.children if c.tag == "table"]
        blokken = [c for c in li.children if c.tag in BLOKKEN_IN_LI]
        hints = [c for c in li.children if "accordion-container" in c.classes]
        eigen = Node("li")
        eigen.children = [c for c in li.children
                          if c.tag != "table" and c.tag not in BLOKKEN_IN_LI
                          and "accordion-container" not in c.classes]

        uit.append(f'<div class="vraag"><p class="vraagtekst">'
                   f'<span class="nr">{nummer}.</span> {esc(eigen.inner_text())}</p>')
        for blok in blokken:
            uit.append(blok_in_li(blok, basis))
        for hint in hints:
            uit.append(accordion(hint))

        if tabellen:
            # Alleen HIER worden `Label: waarde` regels als tabelrijen gelezen.
            velden, rest = antwoord.velden_en_rest()
            if rest.alineas():
                sys.exit(f"{waar}, vraag {nummer}: {ONDER_HET_KADER}\n"
                         f"  {rest.alineas()[0][:70]}")
            for tabel in tabellen:
                uit.append(ingevulde_tabel(tabel, velden, f"{waar}, vraag {nummer}"))
        else:
            uit.append(antwoordblok(antwoord, staat, f"{waar}, vraag {nummer}"))
        uit.append("</div>")


def sluit_sectie(uit, antwoorden, staat, waar):
    """De uitwerking onderaan de sectie die nu afgesloten wordt, als die er is.

    Onderaan en niet bovenaan: de code van schakeling 4 hoort na de opdracht te
    staan die erom vraagt, niet ervoor.
    """
    kop = staat["sectie"]
    staat["sectie"] = None
    if not kop:
        return
    sleutel = f"sectie:{normaliseer(kop)}"
    antwoord = antwoorden.get(sleutel)
    if antwoord is None:
        return
    staat["gezien"].add(sleutel)
    uit.append('<div class="uitwerking">')
    uit.append('<p class="uitwerkingkop">Uitwerking</p>')
    uit.append(inhoud(antwoord, staat, f"{waar}, sectie '{kop}'"))
    uit.append("</div>")


def render(container, uit, antwoorden, staat, basis, waar):
    for node in container.children:
        klassen = node.classes
        if node.tag in SKIP_CONTENT:
            continue

        if "accordion-container" in klassen:
            uit.append(accordion(node))
            continue

        if "verslag-kader" in klassen:
            staat["kader"] += 1
            sleutel = f"kader{staat['kader']}"
            opschrift = node.attrs.get("data-verslag") or "Foto"
            antwoord = antwoorden.get(sleutel)
            if antwoord is None:
                sys.exit(f"{waar}: geen [kader]-antwoord nummer {staat['kader']} "
                         f"({opschrift})")
            staat["gezien"].add(sleutel)
            uit.append('<div class="kader">')
            uit.append(f'<p class="kaderkop">{esc(opschrift)}</p>')
            uit.append(antwoordblok(antwoord, staat, f"{waar}, kader {staat['kader']}"))
            uit.append("</div>")
            continue

        if node.tag in ("h1", "h2"):
            # De vorige sectie eerst afsluiten: haar uitwerking hoort boven deze
            # kop en niet eronder.
            sluit_sectie(uit, antwoorden, staat, waar)
            staat["sectie"] = node.inner_text()
            uit.append(f"<h2>{esc(node.inner_text())}</h2>")
        elif node.tag == "h3":
            uit.append(f"<h3>{esc(node.inner_text())}</h3>")
        elif node.tag == "p":
            tekst = node.inner_text()
            if tekst:
                uit.append(f"<p>{esc(tekst)}</p>")
        elif node.tag == "pre":
            uit.append(f"<pre>{esc(html_mod.unescape(node.raw_text()).strip())}</pre>")
        elif node.tag == "figure":
            uit.append(figuur(node, basis))
        elif node.tag == "ol" and "vragen" in klassen:
            vragenlijst(node, uit, antwoorden, staat, basis, waar)
        elif node.tag in ("ol", "ul"):
            uit.append(lijst(node, basis))
        elif node.tag in ("div", "section"):
            if "download-container" in klassen:
                continue
            if "info-box" in klassen:
                uit.append(infobox(node))
                continue
            render(node, uit, antwoorden, staat, basis, waar)


STIJL = """
/* De maten hieronder zijn NIET gekozen: ze komen uit downloads/Labo-...-verslag.docx
   zelf, uit word/styles.xml en de sectPr, zodat de oplossing en het verslag die de
   student ingevuld heeft naast elkaar dezelfde bladspiegel hebben. Wijzig je
   oriontools/export/verslag.py of het sjabloon van python-docx, lees ze dan opnieuw af
   in plaats van hier iets bij te schatten.
   Letter 8,5 x 11 duim, marges 1 duim boven en onder en 1,25 duim links en rechts;
   Normal is Calibri 11pt met 10pt eronder en regelafstand 1,15; Title 26pt #17365D
   met een onderrand van 1pt in #4F81BD; Heading 1 vet 14pt #365F91 met 24pt erboven;
   Heading 2 vet 13pt #4F81BD met 10pt erboven; Table Grid heeft randen van 0,5pt in
   zwart en celmarges van 0,19cm links en rechts. */

@page { size: 8.5in 11in; margin: 1in 1.25in; }
body { font-family: Calibri, Carlito, "Segoe UI", sans-serif; font-size: 11pt;
       line-height: 1.15; color: #000; margin: 0; }
p { margin: 0 0 10pt 0; }

h1 { font-family: Calibri, Carlito, sans-serif; font-size: 26pt; font-weight: normal;
     color: #17365D; letter-spacing: 0.25pt; line-height: 1.0;
     border-bottom: 1pt solid #4F81BD; padding-bottom: 4pt; margin: 0 0 15pt 0; }
h2 { font-size: 14pt; font-weight: bold; color: #365F91; margin: 24pt 0 0 0;
     page-break-after: avoid; }
h3 { font-size: 13pt; font-weight: bold; color: #4F81BD; margin: 10pt 0 0 0;
     page-break-after: avoid; }

/* De voorbladen lopen gelijk: titel, de inleiding van het labo, de cursieve regel
   die zegt wat je met dit document doet, en dan een bladovergang. */
div.voorblad { page-break-after: always; }
p.mededeling { font-size: 9pt; font-style: italic; color: #5A5A5A; }

/* Een vraag is in het verslag geen lijstitem maar een alinea met een vet nummer
   ervoor, dus hier ook. Een <ol> zou inspringen en dan lopen de twee documenten
   niet meer gelijk. */
div.vraag { page-break-inside: avoid; margin: 0 0 14pt 0; }
p.vraagtekst { margin: 0 0 10pt 0; }
p.vraagtekst span.nr { font-weight: bold; }

/* Waar het verslag een leeg kader zet, staat hier hetzelfde kader met het antwoord
   erin: dezelfde rand van 0,5pt en dezelfde celmarge van 0,19cm. */
div.antwoord { border: 0.5pt solid #000; padding: 0 0.19cm; margin: 0 0 6pt 0;
               page-break-inside: avoid; }
div.kader { margin: 0 0 14pt 0; page-break-inside: avoid; }
p.kaderkop { font-size: 9pt; font-style: italic; color: #5A5A5A; margin: 0 0 2pt 0; }

/* De uitwerking van een schakeling die geen genummerde vraag draagt. Ze staat in
   hetzelfde kader als een antwoord, want dat is ze ook; alleen mag ze wel over een
   bladovergang lopen, want een programma van veertig regels past nergens op. */
div.uitwerking { border: 0.5pt solid #000; padding: 0 0.19cm; margin: 0 0 14pt 0; }
p.uitwerkingkop { font-size: 9pt; font-style: italic; color: #5A5A5A;
                  margin: 6pt 0 2pt 0; }

table.invul { border-collapse: collapse; width: 100%; margin: 0 0 6pt 0;
              page-break-inside: avoid; }
table.invul th, table.invul td { border: 0.5pt solid #000; padding: 0 0.19cm;
                                 vertical-align: top; }
table.invul th { text-align: left; font-weight: bold; }
table.invul td { height: 0.8cm; }
table.invul td p, table.invul th p { margin: 0; }

pre { font-family: Consolas, monospace; font-size: 9pt; margin: 0 0 10pt 0.6cm;
      white-space: pre-wrap; }
ol, ul { padding-left: 0.63cm; margin: 0 0 10pt 0; }
li { margin: 0; }

/* Een tip uit een accordeon en een info-box: ingesprongen, zoals in het
   verslagsjabloon, met het opschrift vet in dezelfde alinea. */
p.tip { margin: 0 0 10pt 0.5cm; }

figure { margin: 0 0 10pt 0; text-align: center; page-break-inside: avoid; }
figure img { max-width: 100%; }
figcaption { font-size: 9pt; font-style: italic; color: #5A5A5A; margin-top: 2pt; }
p.ontbreekt { font-style: italic; color: #5A5A5A; }
"""


HOOFDING = ("Dit is de modeloplossing bij je opdracht. Leg ze naast je eigen verslag "
            "en kijk na waar je antwoord verschilt.")


def bouw_html(titel, lead, body, antwoorden, basis, figuurmap, antwoordmap, waar,
              wortel):
    staat = {"vraag": 0, "kader": 0, "figuur": 0, "sectie": None, "gezien": set(),
             "figuurmap": figuurmap, "antwoordmap": antwoordmap, "wortel": wortel}
    uit = []
    render(body, uit, antwoorden, staat, basis, waar)
    sluit_sectie(uit, antwoorden, staat, waar)

    over = set(antwoorden) - staat["gezien"]
    if over:
        namen = ", ".join(sorted(over, key=lambda s: (not s.isdigit(), s)))
        sys.exit(f"{waar}: deze sleutels horen bij geen enkele vraag, geen kader "
                 f"en geen kop van de opdracht: {namen}. Is de opdracht gewijzigd?")

    stijl = STIJL
    return f"""<!DOCTYPE html>
<html lang="nl"><head><meta charset="utf-8"><title>{esc(titel)}</title>
<style>{stijl}</style></head><body>
<div class="voorblad">
<h1>Oplossing {esc(titel)}</h1>
<p>{esc(lead)}</p>
<p class="mededeling">{esc(HOOFDING)}</p>
</div>
{''.join(uit)}
</body></html>
"""


# ------------------------------------------------------- afdrukken en stempelen

CALIBRI_KANDIDATEN = [
    ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf"),
    ("/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
     "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf"),
]


def stempelletters():
    """(gewoon, vet) in Calibri, want dat is het lettertype van het document zelf.

    Zelfde aanpak als stempelletters() in oriontools/export/pdfhulp.py, dat Arial
    zoekt omdat de syllabus in Arial staat. Vindt hij niets, dan is Helvetica de
    terugval en scheelt het alleen een haartje in de voettekst.
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for gewoon, vet in CALIBRI_KANDIDATEN:
        if Path(gewoon).exists() and Path(vet).exists():
            try:
                pdfmetrics.registerFont(TTFont("OplossingCalibri", gewoon))
                pdfmetrics.registerFont(TTFont("OplossingCalibri-Bold", vet))
                return "OplossingCalibri", "OplossingCalibri-Bold"
            except Exception:
                pass
    return "Helvetica", "Helvetica-Bold"


def stempel(bron_pdf, tekst):
    """Het watermerk diagonaal over elke bladzijde, plus het bladnummer.

    Bovenop de inhoud en niet eronder, met een alfa van 0,12: een stempel
    onder de tekst verdwijnt zodra Chrome ergens wel een achtergrond schildert,
    en dat merk je pas in de gedrukte PDF. Doorschijnend bovenop kan dat niet
    overkomen.

    EEN canvas voor alle bladzijden, zoals in export-syllabus: dat
    is daar de zwaarste post van het document gebleken.
    """
    import io

    lezer = PdfReader(str(bron_pdf))
    schrijver = PdfWriter()
    gewoon, vet = stempelletters()

    buffer = io.BytesIO()
    eerste = lezer.pages[0]
    c = rl_canvas.Canvas(buffer, pagesize=(float(eerste.mediabox.width),
                                           float(eerste.mediabox.height)))
    for i, bladzijde in enumerate(lezer.pages):
        breedte = float(bladzijde.mediabox.width)
        hoogte = float(bladzijde.mediabox.height)
        c.setPageSize((breedte, hoogte))

        c.saveState()
        c.setFillAlpha(0.12)
        # #4F81BD, de accentkleur waar Word de titelrand en de koppen mee zet.
        c.setFillColorRGB(0.310, 0.506, 0.741)
        c.translate(breedte / 2, hoogte / 2)
        # De hoek van de bladdiagonaal, zodat het woord de bladzijde volgt en
        # niet toevallig scheef staat.
        c.rotate(54.7)
        c.setFont(vet, 88)
        c.drawCentredString(0, -30, tekst)
        c.restoreState()

        c.setFont(gewoon, 8)
        c.setFillGray(0.45)
        c.drawCentredString(breedte / 2, 11 * mm, f"{tekst}   |   {i + 1}")
        c.showPage()
    c.save()
    buffer.seek(0)

    stempels = PdfReader(buffer).pages
    for i, bladzijde in enumerate(lezer.pages):
        bladzijde.merge_page(stempels[i])
        schrijver.add_page(bladzijde)
    return schrijver


# -------------------------------------------------------------------- main

def main(argv):
    p = argparse.ArgumentParser(
        prog="orion.py export-oplossing",
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("module", help="pad naar de opdracht, bv. Labo/RS485")
    p.add_argument("--antwoorden", help="pad naar het antwoordbestand "
                                        "(standaard <oplossingen>/<Module>.md)")
    p.add_argument("--uitmap", help="map waarin de PDF komt (standaard <oplossingen>/)")
    p.add_argument("--watermerk", default=WATERMERK)
    p.add_argument("--chrome")
    p.add_argument("--html-only", action="store_true",
                   help="schrijf alleen de tussen-HTML, voor het nakijken van de opmaak")
    repo.voeg_repo_toe(p)
    args = p.parse_args(argv)
    vak = repo.vind(args)
    wortel = vak.root
    oplossingen = vak.pad("oplossingen")

    module = (wortel / args.module).resolve()
    opdracht = module / "Opdracht.html"
    if not opdracht.exists():
        sys.exit(f"Niet gevonden: {opdracht}")

    # Het antwoordbestand zonder de labomap, de PDF met: Labo/RS485 geeft
    # RS485.md en Labo-RS485-oplossing.pdf, dezelfde naam als het verslag.
    delen = module.relative_to(wortel).parts
    stam = "-".join(delen[1:])
    antwoordpad = Path(args.antwoorden) if args.antwoorden else oplossingen / f"{stam}.md"
    if not antwoordpad.exists():
        sys.exit(f"Geen antwoordbestand: {antwoordpad}")

    titel, lead, body = opdrachtblok(opdracht)
    antwoorden = lees_antwoorden(antwoordpad)

    uitmap = Path(args.uitmap) if args.uitmap else oplossingen
    uitmap.mkdir(parents=True, exist_ok=True)
    vragen = sum(1 for s in antwoorden if s.isdigit())

    uit = uitmap / f"{'-'.join(delen)}-oplossing.pdf"

    if args.html_only:
        # De knipsels komen hier naast de HTML te staan in plaats van in een
        # tijdelijke map: die map is weg zodra dit script klaar is, en dan wijst
        # de HTML die je wil nakijken naar afbeeldingen die niet meer bestaan.
        document = bouw_html(titel, lead, body, antwoorden, module,
                             uitmap, antwoordpad.parent, antwoordpad.name,
                             wortel)
        doel = uit.with_suffix(".html")
        doel.write_text(document, encoding="utf-8")
        print(f"Geschreven: {doel}")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        document = bouw_html(titel, lead, body, antwoorden, module,
                             Path(tmp), antwoordpad.parent, antwoordpad.name,
                             wortel)
        html_pad = Path(tmp) / "oplossing.html"
        html_pad.write_text(document, encoding="utf-8")
        ruw = Path(tmp) / "ruw.pdf"
        druk_af(zoek_chrome(args.chrome), html_pad, ruw)
        schrijver = stempel(ruw, args.watermerk)
        try:
            with open(uit, "wb") as f:
                schrijver.write(f)
        except PermissionError:
            # Een PDF-lezer houdt het bestand vergrendeld. Dat is geen fout in
            # dit script, en een traceback zegt niet wat je eraan doet. Zelfde
            # afhandeling als in export-verslag voor een open Word.
            sys.exit(f"Kan {uit.name} niet overschrijven. Staat het open in een "
                     f"PDF-lezer? Sluit het en draai dit opnieuw.")

    bladen = len(PdfReader(str(uit)).pages)
    print(f"Geschreven: {uit.name}  ({bladen} bladzijden, {vragen} vragen)")
    return 0
