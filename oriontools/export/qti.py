"""Maak van een vragenpagina een QTI 3.0-pakket (zip) voor de toetsomgeving ANS.

    python ../OrionTools/orion.py export-qti _toets/Netwerklaag.html
    python ../OrionTools/orion.py export-qti Labo/RS485/Theorie/TestJezelf.html --feedback

De zip komt in paths.toets (standaard _toets/), genoemd naar het pad van de
pagina met streepjes, zoals export-verslag: Labo-RS485-Theorie-TestJezelf-qti.zip.
Importeren in ANS: School, Question banks, Settings, Import, QTI 3.0.

DE BRON IS DE VRAGENLIJST, NIET EEN TWEEDE FORMAAT
--------------------------------------------------
Een vraag is hier wat ze overal is: een <li> in een <ol class="vragen">, de
juiste mogelijkheid gemerkt met class="juist", de uitleg in een
<div class="oplossing">. De check, export-syllabus en OrionCSS main.js lezen
diezelfde markup al. Een eigen quiz-formaat ernaast was een tweede bron, en
dan kan dezelfde vraag op twee plaatsen een ander juist antwoord hebben. Een
toets die Claude schrijft, is dus een gewone vragenpagina in _toets/: je leest
ze na in de browser, met de uitklap van main.js, en exporteert pas daarna.

Een vraag zonder <ul> is een open vraag en heeft in ANS geen meerkeuze-item;
ze wordt overgeslagen en gemeld. Een meerkeuzevraag zonder of met twee juiste
mogelijkheden stopt de export helemaal, zoals vragen-answered: een toets met
een stil fout antwoordsleutel is erger dan geen toets.

WAT NIET IN GIT MAG
-------------------
Een summatieve toets. Alles wat getrackt staat, spiegelt OrionSync naar de
cursusbestanden, waar elke student erbij kan. Daarom schrijft dit commando in
paths.toets, en weigert het wanneer git die map niet negeert: een vergeten
regel in .gitignore mag een toets niet stil publiek maken. Een zelftest onder
Labo/ is al publiek en mag gewoon als bron dienen, voor een oefentoets.

--feedback zet de <div class="oplossing"> als feedback bij het item, die de
student na het antwoorden ziet. Zonder de vlag gaat ze niet mee, wat voor een
summatieve toets het enige veilige is: de uitleg noemt het juiste antwoord.

HET PAKKET
----------
De vorm is die van het script waarmee een collega al in de praktijk naar ANS
importeert: imsmanifest.xml en een item-XML per vraag in de root van de zip,
geen submap, en response processing met de standaardsjabloon match_correct.
Wat daarvan veranderd is, staat bij de code: de attributen in kebab-case zoals
QTI 3 ze schrijft (base-type, niet baseType), identifiers die per vak en per
toets uniek zijn zodat twee toetsen in een vragenbank elkaar niet raken, en de
zip rechtstreeks geschreven, zodat een item van een vorige run er niet in
achterblijft.

Een figuur (<img src> relatief) gaat mee in de zip, onder zijn pad in het vak,
en staat in het manifest bij het item dat hem gebruikt. Een codeblok blijft
een <pre>. Een link wordt zijn tekst: in ANS bestaat de pagina niet waar hij
naartoe wees.

IN ANS NAGEKEKEN
---------------
Wat het script van de collega niet deed en hier bijkwam, is op 25 september
2026 in ANS geimporteerd met de Test jezelf van labo RS485: de feedback
(qti-modal-feedback met een uitgeschreven response processing) verschijnt bij
het item, en een svg-figuur uit de zip wordt getoond. Een png of jpeg volgt
hetzelfde pad in de zip en het manifest, maar is daar niet apart geprobeerd.
"""

import argparse
import html
import re
import subprocess
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

from .. import repo
from ..check.rules._gedeeld import COMMENTAAR_RE, lijstitems, vragen

OPLOSSING_RE = re.compile(r'<div class="oplossing">(.*?)</div>', re.S)
JUIST_RE = re.compile(r'class="[^"]*\bjuist\b')

# Met geschudde mogelijkheden wijst "alle bovenstaande" naar niets vast meer.
VERWIJZEND_RE = re.compile(r"\b(alle|geen van (de )?)\s*(bovenstaande|vorige|voorgaande)\b", re.I)


# ------------------------------------------------------ HTML naar QTI-XHTML

# Wat QTI 3 in een itembody toelaat en wij gebruiken. Een andere tag wordt
# uitgepakt: zijn inhoud blijft, de tag zelf niet.
BLOK = {"p", "div", "pre", "ul", "ol", "li", "table", "thead", "tbody", "tfoot", "tr",
        "th", "td", "caption", "figure", "figcaption", "blockquote", "h3", "h4", "h5", "h6"}
INLINE = {"strong", "em", "b", "i", "u", "sub", "sup", "code", "kbd", "span", "br", "img",
          "small", "q", "abbr"}
LEEG = {"br", "img", "hr", "wbr"}
WEG = {"script", "style", "hr"}
ATTRIBUTEN = {"img": {"src", "alt", "width", "height"}, "td": {"colspan", "rowspan"},
              "th": {"colspan", "rowspan"}, "ol": {"start"}}


class Knoop:
    def __init__(self, tag, attrs=()):
        self.tag, self.attrs, self.kinderen = tag, dict(attrs), []


class _Lezer(HTMLParser):
    """Een HTML-fragment als boom, met de tags uit BLOK en INLINE en niets anders."""

    def __init__(self, uitgepakt):
        super().__init__(convert_charrefs=True)
        self.wortel = Knoop(None)
        self.stapel = [self.wortel]
        self.weg = 0
        self.uitgepakt = uitgepakt

    def handle_starttag(self, tag, attrs):
        if tag in WEG:
            self.weg += tag not in LEEG
            return
        if self.weg:
            return
        if tag not in BLOK | INLINE:
            if tag != "a":
                self.uitgepakt.add(tag)
            return
        knoop = Knoop(tag, attrs)
        self.stapel[-1].kinderen.append(knoop)
        if tag not in LEEG:
            self.stapel.append(knoop)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in LEEG and tag in BLOK | INLINE and not self.weg:
            self.stapel.pop()

    def handle_endtag(self, tag):
        if tag in WEG:
            self.weg = max(0, self.weg - (tag not in LEEG))
            return
        if self.weg:
            return
        for i in range(len(self.stapel) - 1, 0, -1):
            if self.stapel[i].tag == tag:
                del self.stapel[i:]
                return

    def handle_data(self, data):
        if not self.weg:
            self.stapel[-1].kinderen.append(data)


def _tekst(s):
    return html.escape(s, quote=False)


def _schrijf(knoop, in_pre=False):
    if isinstance(knoop, str):
        return _tekst(knoop if in_pre else re.sub(r"\s+", " ", knoop))
    toegelaten = ATTRIBUTEN.get(knoop.tag, set())
    attrs = "".join(f' {k}="{html.escape(v or "")}"'
                    for k, v in knoop.attrs.items() if k in toegelaten)
    if knoop.tag in LEEG:
        return f"<{knoop.tag}{attrs}/>"
    pre = in_pre or knoop.tag == "pre"
    binnen = "".join(_schrijf(k, pre) for k in knoop.kinderen)
    if not pre and knoop.tag in BLOK:
        binnen = binnen.strip()
    return f"<{knoop.tag}{attrs}>{binnen}</{knoop.tag}>"


def lees(fragment, uitgepakt):
    lezer = _Lezer(uitgepakt)
    lezer.feed(fragment)
    lezer.close()
    return lezer.wortel.kinderen


def als_blokken(fragment, uitgepakt):
    """Het fragment als XHTML-blokken: losse tekst en inline tags komen in een <p>.

    Een itembody en een feedback bevatten blokken; de vraagtekst in een <li>
    is losse tekst tot de <ul> met mogelijkheden begint.
    """
    uit, loop = [], []

    def sluit():
        tekst = "".join(_schrijf(k) for k in loop).strip()
        if tekst:
            uit.append(f"<p>{tekst}</p>")
        loop.clear()

    for knoop in lees(fragment, uitgepakt):
        if isinstance(knoop, Knoop) and knoop.tag in BLOK:
            sluit()
            uit.append(_schrijf(knoop))
        else:
            loop.append(knoop)
    sluit()
    return "\n".join(uit)


def als_inline(fragment, uitgepakt):
    return "".join(_schrijf(k) for k in lees(fragment, uitgepakt)).strip()


# ------------------------------------------------------------ de vragen

class Fout(Exception):
    pass


def eerste_lijst(inhoud, tag):
    """(begin, einde) van de eerste <tag>...</tag> in inhoud, met de geneste meegeteld."""
    open_ = re.search(rf"<{tag}\b[^>]*>", inhoud)
    if not open_:
        return None
    diepte = 0
    for m in re.finditer(rf"<(/?){tag}\b[^>]*>", inhoud[open_.start():]):
        diepte += -1 if m.group(1) else 1
        if diepte == 0:
            return open_.start(), open_.start() + m.end()
    return open_.start(), len(inhoud)


def lees_vragen(tekst, meldingen):
    """(nummer, stam, [(inhoud, juist)], oplossing) per meerkeuzevraag van de pagina."""
    uit, fouten = [], []
    for nummer, _, inhoud in vragen(COMMENTAAR_RE.sub("", tekst)):
        oplossing = OPLOSSING_RE.search(inhoud)
        oplossing = oplossing.group(1) if oplossing else ""
        zonder = OPLOSSING_RE.sub("", inhoud)
        lijst = eerste_lijst(zonder, "ul")
        if not lijst:
            meldingen.append(f"vraag {nummer} is een open vraag en is overgeslagen")
            continue
        keuzes = lijstitems(zonder[lijst[0]:], "ul")
        juist = [i for i, (tag, _) in enumerate(keuzes) if JUIST_RE.search(tag)]
        if len(juist) != 1:
            fouten.append(f'vraag {nummer} heeft {len(juist)} mogelijkheden met class="juist" '
                          "in plaats van een")
            continue
        if len(keuzes) > 26:
            fouten.append(f"vraag {nummer} heeft meer dan 26 mogelijkheden")
            continue
        na = html.unescape(re.sub(r"<[^>]+>", "", zonder[lijst[1]:])).strip()
        if na:
            meldingen.append(f"vraag {nummer}: tekst na de mogelijkheden valt weg ({na[:40]})")
        uit.append((nummer, zonder[:lijst[0]], [(k, i == juist[0]) for i, (_, k) in enumerate(keuzes)],
                    oplossing))
    if fouten:
        raise Fout("\n".join(fouten))
    return uit


# ------------------------------------------------------------ figuren

IMG_RE = re.compile(r'(<img\b[^>]*?\bsrc=")([^"]+)(")')


def figuren(fragment, pagina, root):
    """Herschrijf elke <img src> naar zijn pad in de zip; geeft (fragment, {zippad: bestand})."""
    gevonden, fouten = {}, []

    def een(m):
        src = m.group(2)
        if urlparse(src).scheme or src.startswith("/"):
            fouten.append(f"{src}: alleen een figuur uit het vak gaat mee in de zip")
            return m.group(0)
        bestand = (pagina.parent / unquote(src)).resolve()
        try:
            zippad = bestand.relative_to(root).as_posix()
        except ValueError:
            fouten.append(f"{src}: ligt buiten het vak")
            return m.group(0)
        if not bestand.is_file():
            fouten.append(f"{src}: bestaat niet")
            return m.group(0)
        gevonden[zippad] = bestand
        return m.group(1) + html.escape(zippad) + m.group(3)

    fragment = IMG_RE.sub(een, fragment)
    if fouten:
        raise Fout("\n".join(fouten))
    return fragment, gevonden


# ------------------------------------------------------------ het pakket

def identifier(s):
    """Een QTI-identifier: begint met een letter, dan letters, cijfers, - en _."""
    s = re.sub(r"[^A-Za-z0-9_-]+", "-", s).strip("-")
    return s if s[:1].isalpha() else f"q-{s}"


ITEM = """<?xml version="1.0" encoding="UTF-8"?>
<qti-assessment-item
  xmlns="http://www.imsglobal.org/xsd/imsqtiasi_v3p0"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqtiasi_v3p0 https://purl.imsglobal.org/spec/qti/v3p0/schema/xsd/imsqti_asiv3p0p1_v1p0.xsd"
  identifier="{id}"
  title="{titel}"
  adaptive="false"
  time-dependent="false"
  xml:lang="nl">

  <qti-response-declaration identifier="RESPONSE" cardinality="single" base-type="identifier">
    <qti-correct-response>
      <qti-value>{juist}</qti-value>
    </qti-correct-response>
  </qti-response-declaration>

  <qti-outcome-declaration identifier="SCORE" cardinality="single" base-type="float" normal-maximum="1">
    <qti-default-value>
      <qti-value>0</qti-value>
    </qti-default-value>
  </qti-outcome-declaration>
{feedbackdeclaratie}
  <qti-item-body>
{stam}
    <qti-choice-interaction response-identifier="RESPONSE" shuffle="{schudden}" max-choices="1">
{keuzes}
    </qti-choice-interaction>
  </qti-item-body>

{verwerking}
{feedback}
</qti-assessment-item>
"""

VERWERKING = ('  <qti-response-processing '
              'template="https://purl.imsglobal.org/spec/qti/v3p0/rptemplates/match_correct"/>')

# Met feedback kan de sjabloon niet: die zet alleen SCORE. Dit is match_correct
# uitgeschreven, plus een FEEDBACK die altijd de uitleg toont.
FEEDBACKDECLARATIE = """
  <qti-outcome-declaration identifier="FEEDBACK" cardinality="single" base-type="identifier"/>
"""

VERWERKING_MET_FEEDBACK = """  <qti-response-processing>
    <qti-response-condition>
      <qti-response-if>
        <qti-match>
          <qti-variable identifier="RESPONSE"/>
          <qti-correct identifier="RESPONSE"/>
        </qti-match>
        <qti-set-outcome-value identifier="SCORE">
          <qti-base-value base-type="float">1</qti-base-value>
        </qti-set-outcome-value>
      </qti-response-if>
      <qti-response-else>
        <qti-set-outcome-value identifier="SCORE">
          <qti-base-value base-type="float">0</qti-base-value>
        </qti-set-outcome-value>
      </qti-response-else>
    </qti-response-condition>
    <qti-set-outcome-value identifier="FEEDBACK">
      <qti-base-value base-type="identifier">UITLEG</qti-base-value>
    </qti-set-outcome-value>
  </qti-response-processing>"""

FEEDBACK = """
  <qti-modal-feedback outcome-identifier="FEEDBACK" identifier="UITLEG" show-hide="show">
    <qti-content-body>
{uitleg}
    </qti-content-body>
  </qti-modal-feedback>"""

MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<manifest xmlns="http://www.imsglobal.org/xsd/qti/qtiv3p0/imscp_v1p1"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  identifier="{id}"
  xsi:schemaLocation="http://www.imsglobal.org/xsd/qti/qtiv3p0/imscp_v1p1 https://purl.imsglobal.org/spec/qti/v3p0/schema/xsd/imsqtiv3p0_imscpv1p2_v1p0.xsd">

  <metadata>
    <schema>QTI Package</schema>
    <schemaversion>3.0.0</schemaversion>
    <lom xmlns="http://ltsc.ieee.org/xsd/LOM">
      <general>
        <title><string language="nl">{titel}</string></title>
      </general>
    </lom>
  </metadata>

  <organizations/>

  <resources>
{resources}
  </resources>

</manifest>
"""


def item(item_id, titel, vraag, schudden, feedback, uitgepakt):
    _, stam, keuzes, oplossing = vraag
    letters = [chr(ord("A") + i) for i in range(len(keuzes))]
    juist = next(l for l, (_, j) in zip(letters, keuzes) if j)
    regels = [f'      <qti-simple-choice identifier="{l}">{als_inline(k, uitgepakt)}</qti-simple-choice>'
              for l, (k, _) in zip(letters, keuzes)]
    met = feedback and als_blokken(oplossing, uitgepakt)
    return ITEM.format(
        id=item_id, titel=html.escape(titel), juist=juist,
        schudden="true" if schudden else "false",
        stam=als_blokken(stam, uitgepakt),
        keuzes="\n".join(regels),
        feedbackdeclaratie=FEEDBACKDECLARATIE if met else "",
        verwerking=VERWERKING_MET_FEEDBACK if met else VERWERKING,
        feedback=FEEDBACK.format(uitleg=met) if met else "")


def resource(item_id, bestand, figuren_):
    files = "\n".join(f'      <file href="{html.escape(p)}"/>' for p in [bestand, *figuren_])
    return (f'    <resource identifier="{item_id}" type="imsqti_item_xmlv3p0" href="{bestand}">\n'
            f"{files}\n    </resource>")


def paginatitel(tekst, standaard):
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", tekst, re.S) or re.search(r"<title>(.*?)</title>", tekst, re.S)
    return html.unescape(re.sub(r"<[^>]+>|\s+", " ", m.group(1))).strip() if m else standaard


def naam_van(pagina, root, toetsmap):
    """Het pad met streepjes, zonder .html en zonder de toetsmap ervoor."""
    try:
        rel = pagina.relative_to(toetsmap)
    except ValueError:
        rel = pagina.relative_to(root)
    return "-".join(rel.with_suffix("").parts)


def genegeerd(root, map_):
    """Negeert git map_? None als root geen git-repo is."""
    try:
        r = subprocess.run(["git", "check-ignore", "-q", str(map_ / "x.zip")], cwd=root,
                           capture_output=True)
    except OSError:
        return None
    return {0: True, 1: False}.get(r.returncode)


def welgevormd(xml, wat):
    """Een zip met een kapot item weigert ANS in zijn geheel; beter hier stoppen."""
    try:
        ElementTree.fromstring(xml.encode("utf-8"))
    except ElementTree.ParseError as e:
        raise Fout(f"{wat}: geen welgevormde XML ({e})")


def bouw(pagina, root, naam, schudden, feedback):
    """{zippad: bytes} van het pakket, de meldingen en het aantal vragen.

    naam wordt de identifier van het pakket, en met het vraagnummer erachter
    die van elk item: per vak en per toets uniek, en stabiel tussen twee runs.
    """
    tekst = pagina.read_text(encoding="utf-8")
    meldingen, uitgepakt = [], set()
    tekst, figuurbestanden = figuren(tekst, pagina, root)
    lijst = lees_vragen(tekst, meldingen)
    if not lijst:
        raise Fout(f'{pagina.name}: geen meerkeuzevraag in een <ol class="vragen">')

    titel = paginatitel(tekst, pagina.stem)
    pakket = identifier(naam)
    uit, resources = {}, []
    for vraag in lijst:
        nummer, stam, keuzes, oplossing = vraag
        item_id = f"{pakket}-{nummer:02d}"
        for inhoud, _ in keuzes:
            if schudden and VERWIJZEND_RE.search(inhoud):
                meldingen.append(f"vraag {nummer}: een mogelijkheid verwijst naar de andere, "
                                 "en de volgorde wordt geschud")
        xml = item(item_id, f"{titel} - vraag {nummer}", vraag, schudden, feedback, uitgepakt)
        welgevormd(xml, f"vraag {nummer}")
        gebruikt = sorted({html.unescape(s) for s in re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', xml)})
        uit[f"{item_id}.xml"] = xml.encode("utf-8")
        resources.append(resource(item_id, f"{item_id}.xml", gebruikt))
        # Alleen wat een item toont: een figuur elders op de pagina hoort niet in de vragenbank.
        for zippad in gebruikt:
            uit[zippad] = figuurbestanden[zippad].read_bytes()

    manifest = MANIFEST.format(id=f"{pakket}-package", titel=html.escape(titel),
                               resources="\n".join(resources))
    welgevormd(manifest, "imsmanifest.xml")
    uit["imsmanifest.xml"] = manifest.encode("utf-8")
    for tag in sorted(uitgepakt):
        meldingen.append(f"<{tag}> is uitgepakt: QTI kent die tag niet, de inhoud blijft")
    return uit, meldingen, len(lijst)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="orion.py export-qti", description=__doc__.split("\n")[0])
    repo.voeg_repo_toe(parser)
    parser.add_argument("pagina", type=Path, help='een pagina met een <ol class="vragen">')
    parser.add_argument("--feedback", action="store_true",
                        help="de uitleg (div.oplossing) als feedback meegeven; niet voor een summatieve toets")
    parser.add_argument("--niet-schudden", action="store_true",
                        help="de mogelijkheden in de volgorde van de pagina laten")
    parser.add_argument("--uit", type=Path, default=None,
                        help="de zip (standaard: paths.toets/<pad-met-streepjes>-qti.zip)")
    args = parser.parse_args(argv)
    vak = repo.vind(args)

    pagina = args.pagina if args.pagina.is_absolute() else (Path.cwd() / args.pagina)
    if not pagina.is_file():
        pagina = vak.root / args.pagina
    pagina = pagina.resolve()
    if not pagina.is_file():
        sys.exit(f"export-qti: {args.pagina} bestaat niet")

    toetsmap = vak.pad("toets")
    uit = (args.uit or toetsmap / f"{naam_van(pagina, vak.root, toetsmap)}-qti.zip").resolve()
    for map_ in {toetsmap, uit.parent}:
        if (map_ == toetsmap or toetsmap in map_.parents) and genegeerd(vak.root, map_) is False:
            sys.exit(f"export-qti: git negeert {map_.relative_to(vak.root).as_posix()}/ niet. "
                     "Zet de map in .gitignore: wat getrackt is, spiegelt OrionSync naar de "
                     "cursus, en daar leest elke student een toets.")

    try:
        naam = naam_van(pagina, vak.root, toetsmap)
        bestanden, meldingen, aantal = bouw(pagina, vak.root, f"{vak.code}-{naam}",
                                            not args.niet_schudden, args.feedback)
    except Fout as e:
        sys.exit(f"export-qti: {pagina.relative_to(vak.root).as_posix()}: geen zip gemaakt\n{e}")

    uit.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(uit, "w", zipfile.ZIP_DEFLATED) as z:
        for naam, inhoud in bestanden.items():
            z.writestr(naam, inhoud)

    print(f"{aantal} vragen -> {uit.relative_to(vak.root).as_posix() if vak.root in uit.parents else uit}")
    print("feedback: " + ("de uitleg gaat mee" if args.feedback else "geen"))
    for m in meldingen:
        print(f"  let op: {m}")
    print("Importeer in ANS: School > Question banks > Settings > Import > QTI 3.0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
