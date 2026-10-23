"""Maak de ingediende verslagen van een dropbox anoniem, zodat Claude ze kan lezen.

    python ../OrionTools/orion.py feedback-voorbereiden _feedback/Labo-RS485

De map houdt wat OrionSync uit de dropbox ophaalde:

    npm run dropbox -- export <orgUnitId> <folderId> --out <map>/inzendingen.json --files <map>/bestanden

Dit commando schrijft ernaast:

    <map>/sleutel.json              welke code (S01, S02 ...) bij welke student hoort
    <map>/anoniem/OVERZICHT.md      per code wat er gevonden en weggelaten is
    <map>/anoniem/S01/verslag.md    het verslag zonder voorblad, als tekst
    <map>/anoniem/S01/img/          de afbeeldingen, in de volgorde van het verslag; een
                                    figuur die ook in het sjabloon staat, wordt alleen genoemd
    <map>/anoniem/S01/code/         de code die de student indiende

Claude stelt feedback voor op wat in anoniem/ staat en leest de rest van de map
niet. Wat een student aanwijst, blijft daarbuiten:

- Het voorblad. Het sjabloon van export-verslag begint met een bladzijde met de
  regel Naam/Groep/Datum; alles tot en met het eerste paginaeinde na "Naam:"
  valt weg. Bij een pdf valt de eerste bladzijde weg als daar "Naam" op staat,
  en komen alleen de tekst en de ingesloten afbeeldingen mee, geen beeld van
  de bladzijde: daarop staat de kop- en voettekst.
- De eigenschappen van het docx (de auteur), de kop- en voettekst en de
  opmerkingen in de kantlijn: alleen de body wordt tekst, de rest wordt niet
  gelezen.
- De metadata van een afbeelding (een foto van een gsm draagt soms een
  gps-positie): elke afbeelding wordt opnieuw opgeslagen, zonder.
- Elke naam van een student van het vak, ook die van een labopartner: die
  wordt [naam], in de tekst, in de code en in een bestandsnaam.
  inzendingen.json somt alle studenten op, ook wie niets indiende.

Wat het niet tegenhoudt: een naam op een schermafdruk, zoals C:\\Users\\<naam>
of een prompt. De skill zegt dat Claude die nooit overneemt.

Per student telt per soort de laatste inzending, want een latere vult de
vorige meestal aan: eerst het verslag, dan de code, of omgekeerd (RS485,
oktober 2026). Het verslag komt uit de laatste inzending met een docx of pdf;
staan er meer in, dan komt dat met een voorblad eerst. De code komt uit de
laatste inzending met code. Een zip wordt uitgepakt.

Een tweede run houdt de codes: sleutel.json wordt aangevuld, niet herschreven.
Zo kan een dropbox in golven vollopen, groep na groep.

Een tweede run zegt ook wat er sinds de vorige veranderd is. Per code staat in
<map>/vingerafdrukken.json een hash van wat er gelezen werd (de inhoud van de
gekozen bestanden en de opmerking, niet hun naam), en OVERZICHT.md zet in de
kolom Sinds vorige run "nieuw" bij een code die er de vorige keer niet was en
"gewijzigd" bij een student die opnieuw indiende. Een gewijzigde code heeft in
voorstellen.md een sectie over een verslag dat niet meer bestaat: die schrijf
je opnieuw. De eerste run met dit bestand laat de kolom leeg, want er is niets
om mee te vergelijken.

Git moet de map negeren, want OrionSync spiegelt wat getrackt is naar de
cursus. Zonder die regel weigert het commando.
"""

import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

from .. import repo

CODE = {".ino", ".c", ".cpp", ".h", ".hpp", ".py", ".js", ".cs", ".java", ".sh", ".txt"}
BEELD = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
VERSLAG = {".docx", ".pdf"}
MIN_BEELD = 40              # px; kleiner is een icoon of een lijn, geen schermafdruk
MAX_BREEDTE = 1600          # px; een schermafdruk blijft leesbaar, een foto van 4000 px niet nodig
MAX_CODE = 200_000          # tekens per codebestand
PARTIKELS = {"van", "de", "der", "den", "het", "ten", "ter", "le", "la", "du", "da", "di", "von",
             "vanden", "vander", "el", "al", "bin", "ben", "op", "in", "t"}

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
V = "{urn:schemas-microsoft-com:vml}"
WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
PAGINA = "\x0c"             # paginaeinde in de tekst van een alinea
VINKJES = {"F0FD": "☒", "F0FE": "☒", "F078": "☒", "F0A8": "☐", "F06F": "☐"}


# ---- namen ---------------------------------------------------------------

class Namen:
    """Vervangt elke naam van een student van het vak door [naam].

    Een deel van vijf letters of meer wordt ook in kleine letters herkend
    (een gebruikersnaam in een pad); een korter deel alleen zoals het
    geschreven is, anders wordt "jan" in "januari"-achtige code ook [naam].
    """

    def __init__(self, studenten):
        lang, kort = set(), set()
        for s in studenten:
            naam = s.get("name") or ""
            mail = (s.get("email") or "").split("@")[0]
            for geheel in (naam, mail):
                if len(geheel) >= 3:
                    lang.add(geheel)
            for deel in re.split(r"[\s.\-_]+", naam + " " + mail):
                if len(deel) < 3 or deel.lower() in PARTIKELS:
                    continue
                (lang if len(deel) >= 5 else kort).add(deel)
        def patroon(woorden, vlag):
            if not woorden:
                return None
            alt = "|".join(re.escape(w) for w in sorted(woorden, key=len, reverse=True))
            return re.compile(rf"(?<![^\W_])(?:{alt})(?![^\W_])", vlag)
        self.lang = patroon(lang, re.IGNORECASE)
        self.kort = patroon(kort, 0)
        self.aantal = 0

    def __call__(self, tekst):
        for p in (self.lang, self.kort):
            if p:
                tekst, n = p.subn("[naam]", tekst)
                self.aantal += n
        return tekst


# ---- bestanden van een inzending -----------------------------------------

def bestanden(inzending):
    """(naam, bytes) van elk bestand van een inzending, met een zip uitgepakt."""
    for f in inzending["files"]:
        pad = Path(f.get("saved") or "")
        if not pad.is_file():
            yield f["name"], None
            continue
        if f["name"].lower().endswith(".zip"):
            try:
                z = zipfile.ZipFile(pad)
            except zipfile.BadZipFile:
                yield f["name"], None
                continue
            for lid in z.infolist():
                naam = PurePosixPath(lid.filename)
                if lid.is_dir() or "__MACOSX" in naam.parts or naam.name.startswith(("._", "~$")):
                    continue
                yield naam.name, z.read(lid)
        else:
            yield f["name"], pad.read_bytes()


def soort(naam):
    ext = PurePosixPath(naam.lower()).suffix
    if naam.startswith("~$"):
        return None
    if ext in VERSLAG:
        return "verslag"
    if ext in CODE:
        return "code"
    if ext in BEELD:
        return "beeld"
    return None


def kies(student):
    """Per soort de bestanden van de laatste inzending die er een van die soort heeft."""
    gekozen, onleesbaar = {}, []
    for inz in sorted(student["submissions"], key=lambda s: s["date"]):
        per = {}
        for naam, data in bestanden(inz):
            if data is None:
                onleesbaar.append(naam)
                continue
            s = soort(naam)
            if s:
                per.setdefault(s, []).append((naam, data))
        gekozen.update(per)
    return {s: ontdubbel(lijst) for s, lijst in gekozen.items()}, onleesbaar


def ontdubbel(lijst):
    """Laat een identiek bestand en de pdf-export van een docx weg.

    Een zip draagt soms hetzelfde verslag vier keer, en naast een docx staat
    vaak de pdf die Word ervan maakte (RS485, oktober 2026). Twee keer
    hetzelfde lezen levert geen betere feedback op.
    """
    gezien, uit = set(), []
    for naam, data in lijst:
        if data not in gezien:
            gezien.add(data)
            uit.append((naam, data))
    docx = {PurePosixPath(n.lower()).stem for n, _ in uit if n.lower().endswith(".docx")}
    return [(n, d) for n, d in uit if not (n.lower().endswith(".pdf") and PurePosixPath(n.lower()).stem in docx)]


# ---- afbeeldingen ----------------------------------------------------------

class Beelden:
    def __init__(self, map_, sjabloon=frozenset()):
        self.map = map_
        self.sjabloon = sjabloon
        self.n = 0
        self.niet = 0

    def bewaar(self, data, ext):
        """Schrijf een afbeelding zonder metadata, zo nodig kleiner; geef de markdown terug."""
        from PIL import Image
        if hashlib.sha256(data).hexdigest() in self.sjabloon:
            return "[figuur uit het sjabloon]"
        ext = ext.lower()
        if ext not in BEELD:
            self.niet += 1
            return f"[afbeelding als {ext or 'onbekend'}, niet omgezet]"
        try:
            beeld = Image.open(io.BytesIO(data))
            beeld.load()
        except Exception:
            self.niet += 1
            return "[afbeelding die niet te openen is]"
        if beeld.width > MAX_BREEDTE:
            beeld = beeld.resize((MAX_BREEDTE, round(beeld.height * MAX_BREEDTE / beeld.width)))
        self.n += 1
        self.map.mkdir(parents=True, exist_ok=True)
        if ext in (".jpg", ".jpeg"):
            naam = f"{self.n:02d}.jpg"
            beeld.convert("RGB").save(self.map / naam, quality=85)
        else:
            naam = f"{self.n:02d}.png"
            if beeld.mode not in ("RGB", "RGBA", "L", "LA", "P"):
                beeld = beeld.convert("RGBA")
            beeld.save(self.map / naam)
        return f"![afbeelding {self.n}](img/{naam})"


# ---- docx ------------------------------------------------------------------

def blokken(el):
    """De alinea's en tabellen van een body of cel, door inhoudsbesturingselementen heen."""
    for kind in el:
        if kind.tag in (W + "p", W + "tbl"):
            yield kind
        elif kind.tag == W + "sdt":
            inhoud = kind.find(W + "sdtContent")
            if inhoud is not None:
                yield from blokken(inhoud)


class Docx:
    def __init__(self, data, beelden, namen):
        from docx import Document
        self.doc = Document(io.BytesIO(data))
        self.beelden = beelden
        self.namen = namen
        self.gezien = {}

    def beeld(self, rid):
        if not rid:
            return ""
        if rid not in self.gezien:
            deel = self.doc.part.related_parts.get(rid)
            if deel is None:
                return ""
            self.gezien[rid] = self.beelden.bewaar(deel.blob, PurePosixPath(str(deel.partname)).suffix)
        return self.gezien[rid]

    def tekst(self, el, uit):
        """De tekst van een alinea in volgorde, met afbeeldingen op hun plaats."""
        for kind in el:
            t = kind.tag
            if t == MC_FALLBACK or t == W + "delText" or t == W + "instrText":
                continue
            if t == W + "t":
                uit.append(kind.text or "")
            elif t == W + "tab":
                uit.append("\t")
            elif t == W + "br":
                uit.append(PAGINA if kind.get(W + "type") == "page" else "\n")
            elif t == W + "cr":
                uit.append("\n")
            elif t == W + "sym":
                uit.append(VINKJES.get((kind.get(W + "char") or "").upper(), ""))
            elif t == A + "blip":
                uit.append(" " + self.beeld(kind.get(R + "embed")) + " ")
            elif t == V + "imagedata":
                uit.append(" " + self.beeld(kind.get(R + "id")) + " ")
            elif t in (WP + "anchor", WP + "inline") and not self.inhoud(kind):
                # Een vorm die de student tekende, zonder tekst of afbeelding erin:
                # een kruisje of een cirkel in een vak van de pintabel (RS485,
                # oktober 2026). Weglaten zou een ingevulde tabel leeg tonen.
                uit.append(" [vorm] ")
            else:
                self.tekst(kind, uit)
        return uit

    @staticmethod
    def inhoud(tekening):
        """Draagt een tekening een afbeelding of tekst die tekst() zelf vindt?"""
        return (next(tekening.iter(A + "blip"), None) is not None
                or next(tekening.iter(W + "t"), None) is not None)

    def alinea(self, p):
        stijl = p.find(f"{W}pPr/{W}pStyle")
        stijl = (stijl.get(W + "val") if stijl is not None else "") or ""
        tekst = "".join(self.tekst(p, []))
        kop = ""
        if stijl.lower() in ("title", "titel"):
            kop = "# "
        else:
            m = re.fullmatch(r"(?:heading|kop)(\d)", stijl.lower())
            if m:
                kop = "#" * (int(m.group(1)) + 1) + " "
        if not kop and p.find(f"{W}pPr/{W}numPr") is not None and tekst.strip():
            kop = "- "
        return kop, tekst

    def cel(self, tc):
        return "\n".join(self.blok(b) for b in blokken(tc)).strip()

    def tabel(self, tbl):
        rijen = [[self.cel(tc) for tc in tr.findall(W + "tc")] for tr in tbl.findall(W + "tr")]
        rijen = [r for r in rijen if r]
        if len(rijen) == 1 and len(rijen[0]) == 1:
            # Een vak met één cel is in het sjabloon de invulruimte: het antwoord.
            inhoud = rijen[0][0]
            return "\n".join("> " + r for r in inhoud.splitlines()) if inhoud else "> (leeg)"
        breedte = max(len(r) for r in rijen)
        def rij(r):
            r = r + [""] * (breedte - len(r))
            return "| " + " | ".join(c.replace("\n", "<br>").replace("|", "\\|") for c in r) + " |"
        regels = [rij(rijen[0]), "|" + " --- |" * breedte] + [rij(r) for r in rijen[1:]]
        return "\n".join(regels)

    def blok(self, b):
        if b.tag == W + "tbl":
            return self.tabel(b)
        kop, tekst = self.alinea(b)
        return kop + tekst.replace(PAGINA, "\n").strip()

    def markdown(self):
        """(markdown zonder voorblad, wat er met het voorblad gebeurde)."""
        alle = list(blokken(self.doc.element.body))
        tekst = lambda b: "".join(self.tekst(b, [])) if b.tag == W + "p" else ""
        # Lees de tekst zonder de afbeeldingen al te bewaren: die horen er pas
        # bij als het blok blijft.
        def ruw(b):
            return "".join(t.text or "" for t in b.iter(W + "t"))
        naam = next((i for i, b in enumerate(alle[:20]) if b.tag == W + "p" and "Naam:" in ruw(b)), None)
        start, voorblad, rest = 0, "geen voorblad gevonden", None
        if naam is not None:
            for i in range(naam, min(naam + 20, len(alle))):
                b = alle[i]
                if b.tag != W + "p":
                    continue
                breuk = any(br.get(W + "type") == "page" for br in b.iter(W + "br"))
                sectie = b.find(f"{W}pPr/{W}sectPr") is not None
                volgende = alle[i + 1] if i + 1 < len(alle) else None
                ervoor = volgende is not None and volgende.find(f"{W}pPr/{W}pageBreakBefore") is not None
                if breuk:
                    start, voorblad = i + 1, "weggelaten"
                    rest = tekst(b).split(PAGINA)[-1].strip()
                    break
                if sectie or ervoor:
                    start, voorblad = i + 1, "weggelaten"
                    break
            else:
                start, voorblad = naam + 1, "deels: tot en met de regel Naam, geen paginaeinde gevonden"
        delen = [rest] if rest else []
        delen += [self.blok(b) for b in alle[start:]]
        md = "\n\n".join(d for d in delen if d.strip())
        return self.namen(md), voorblad


# ---- pdf -------------------------------------------------------------------

def pdf_markdown(data, beelden, namen):
    import logging
    from pypdf import PdfReader
    # pypdf meldt elk scheef object van een export uit Word; dat zegt niets over het verslag.
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    lezer = PdfReader(io.BytesIO(data))
    teksten = [(p.extract_text() or "") for p in lezer.pages]
    start, voorblad = 0, "geen voorblad gevonden"
    if teksten and "Naam" in teksten[0]:
        start, voorblad = 1, "weggelaten (eerste bladzijde)"
    # De afbeeldingen die in de pdf zitten, niet een afbeelding van de hele
    # bladzijde: die toont ook de kop- en voettekst, en daar staat vaak de
    # naam van de student (RS485, oktober 2026).
    delen = []
    for i in range(start, len(teksten)):
        stukken = [f"## Bladzijde {i + 1}", teksten[i].strip()]
        try:
            ingesloten = list(lezer.pages[i].images)
        except Exception:
            ingesloten = []
            stukken.append("[afbeeldingen op deze bladzijde niet te lezen]")
        for img in ingesloten:
            try:
                pil = img.image
            except Exception:
                continue
            if pil is None or min(pil.size) < MIN_BEELD:
                continue
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            stukken.append(beelden.bewaar(buf.getvalue(), ".png"))
        delen.append("\n\n".join(s for s in stukken if s))
    return namen("\n\n".join(delen)), voorblad


# ---- per student -------------------------------------------------------------

def veilig(naam):
    return re.sub(r"[^\w.\-\[\]]+", "_", naam).strip("_") or "bestand"


def sjabloonbeelden(pad):
    """De afbeeldingen van het verslagsjabloon, als sha256.

    Het sjabloon draagt de figuren van de opdracht zelf (de schakeling van
    deel 2, die van deel 3). In een ingediend verslag zijn dat geen
    schermafdrukken van de student, en wie ze toch leest als werk van de
    student, beoordeelt de opdracht in plaats van het antwoord.
    """
    if not pad.is_file():
        return frozenset()
    with zipfile.ZipFile(pad) as z:
        return frozenset(hashlib.sha256(z.read(n)).hexdigest()
                         for n in z.namelist() if n.startswith("word/media/"))


def verwerk(student, map_, namen, sjabloon=frozenset()):
    """Schrijf de anonieme versie van één student; geef de regel voor het overzicht terug."""
    if map_.exists():
        shutil.rmtree(map_)
    map_.mkdir(parents=True)
    voor = namen.aantal
    gekozen, onleesbaar = kies(student)
    beelden = Beelden(map_ / "img", sjabloon)
    delen, soorten, voorbladen = [], [], []

    verslagen = gekozen.get("verslag", [])
    gelezen = []
    for naam, data in verslagen:
        ext = PurePosixPath(naam.lower()).suffix
        try:
            if ext == ".docx":
                md, vb = Docx(data, beelden, namen).markdown()
            else:
                md, vb = pdf_markdown(data, beelden, namen)
        except Exception as e:
            onleesbaar.append(f"{ext} ({type(e).__name__})")
            continue
        gelezen.append((not vb.startswith("weggelaten"), ext, md, vb))
    gelezen.sort(key=lambda g: g[0])         # dat met een voorblad eerst
    for i, (_, ext, md, vb) in enumerate(gelezen):
        kop = "# Verslag" if i == 0 else f"# Bijlage {i} ({ext[1:]})"
        delen.append(f"{kop}\n\n{md}")
        soorten.append(ext[1:])
        voorbladen.append(vb)
    if not gelezen:
        delen.append("# Verslag\n\nGeen verslag ingediend.")

    for naam, data in gekozen.get("beeld", []):
        delen.append(f"# Bijgevoegde afbeelding\n\n{beelden.bewaar(data, PurePosixPath(naam.lower()).suffix)}")

    code = gekozen.get("code", [])
    if code:
        (map_ / "code").mkdir()
        lijst, gebruikt = [], set()
        for naam, data in code:
            doel = veilig(namen(PurePosixPath(naam).name))
            while doel.lower() in gebruikt:
                doel = "_" + doel
            gebruikt.add(doel.lower())
            tekst = data.decode("utf-8", errors="replace")[:MAX_CODE]
            (map_ / "code" / doel).write_text(namen(tekst), encoding="utf-8")
            lijst.append(f"- [code/{doel}](code/{doel})")
        delen.append("# Code\n\n" + "\n".join(lijst))

    teksten = [s["text"] for s in sorted(student["submissions"], key=lambda s: s["date"]) if s["text"]]
    opmerkingen = [namen(t) for t in teksten]
    if opmerkingen:
        delen.append("# Opmerking bij de inzending\n\n" + "\n\n".join(opmerkingen))

    (map_ / "verslag.md").write_text("\n\n".join(delen) + "\n", encoding="utf-8")
    return {
        "verslag": "+".join(soorten) or "geen",
        "voorblad": "; ".join(voorbladen) or "-",
        "afbeeldingen": beelden.n,
        "niet_omgezet": beelden.niet,
        "code": len(code),
        "namen": namen.aantal - voor,
        "onleesbaar": onleesbaar,
        "feedback": bool(student.get("feedback")),
        "vingerafdruk": vingerafdruk(gekozen, teksten),
    }


def vingerafdruk(gekozen, teksten):
    """Een hash van wat er gelezen werd: de inhoud per soort, niet de bestandsnaam."""
    h = hashlib.sha256()
    for s in sorted(gekozen):
        for d in sorted(hashlib.sha256(data).hexdigest() for _, data in gekozen[s]):
            h.update(f"{s}:{d}\n".encode())
    for t in teksten:
        h.update(f"tekst:{t}\n".encode("utf-8"))
    return h.hexdigest()


# ---- sleutel en overzicht ------------------------------------------------------

def codes(sleutel, studenten):
    """Een vaste code per student: wie al een code had, houdt ze; een nieuwe komt achteraan."""
    per_id = {str(v["id"]): k for k, v in sleutel["codes"].items()}
    nummer = max((int(k[1:]) for k in sleutel["codes"]), default=0)
    breedte = 3 if len(studenten) + nummer >= 100 else 2
    for s in sorted(studenten, key=lambda s: int(s["id"])):
        if str(s["id"]) not in per_id:
            nummer += 1
            code = f"S{nummer:0{max(breedte, len(str(nummer)))}d}"
            sleutel["codes"][code] = {"id": s["id"], "name": s["name"]}
            per_id[str(s["id"])] = code
    return per_id


def overzicht(map_, regels, folder):
    kop = ("| Code | Verslag | Voorblad | Afb. | Niet omgezet | Code | Namen vervangen | Al feedback | Onleesbaar "
           "| Sinds vorige run |\n"
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    rijen = [f"| {c} | {r['verslag']} | {r['voorblad']} | {r['afbeeldingen']} | {r['niet_omgezet']} | {r['code']} "
             f"| {r['namen']} | {'ja' if r['feedback'] else ''} | {', '.join(r['onleesbaar'])} | {r.get('sinds', '')} |"
             for c, r in regels]
    tekst = (f"# {folder}\n\nWat feedback-voorbereiden per code vond. Wie niets indiende, staat er niet in.\n\n"
             + kop + "\n" + "\n".join(rijen) + "\n")
    (map_ / "OVERZICHT.md").write_text(tekst, encoding="utf-8")


def genegeerd(root, map_):
    try:
        r = subprocess.run(["git", "check-ignore", "-q", str(map_ / "x")], cwd=root, capture_output=True)
    except OSError:
        return None
    return {0: True, 1: False}.get(r.returncode)


def main(argv):
    ap = argparse.ArgumentParser(prog="orion.py feedback-voorbereiden", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("map", help="de map met inzendingen.json, bv. _feedback/Labo-RS485")
    repo.voeg_repo_toe(ap)
    args = ap.parse_args(argv)
    vak = repo.vind(args)
    map_ = (vak.root / args.map).resolve()

    bron = map_ / "inzendingen.json"
    if not bron.is_file():
        sys.exit(f"Niet gevonden: {bron}. Haal de dropbox eerst op met npm run dropbox -- export in OrionSync.")
    if genegeerd(vak.root, map_) is not True:
        sys.exit(f"Git negeert {map_} niet. Zet {vak.config['paths']['feedback']}/ in .gitignore: "
                 f"wat getrackt is, spiegelt OrionSync naar de cursus, en dit zijn verslagen met namen.")

    data = json.loads(bron.read_text(encoding="utf-8"))
    studenten = data["students"]
    namen = Namen(studenten)

    sleutelpad = map_ / "sleutel.json"
    sleutel = (json.loads(sleutelpad.read_text(encoding="utf-8")) if sleutelpad.exists()
               else {"orgUnitId": data["orgUnitId"], "folderId": data["folderId"], "codes": {}})
    if (sleutel["orgUnitId"], sleutel["folderId"]) != (data["orgUnitId"], data["folderId"]):
        sys.exit(f"{sleutelpad.name} hoort bij een andere dropbox dan {bron.name}.")
    ingediend = [s for s in studenten if s["submissions"]]
    per_id = codes(sleutel, ingediend)
    sleutelpad.write_text(json.dumps(sleutel, indent=1, ensure_ascii=False), encoding="utf-8")

    anoniem = map_ / "anoniem"
    anoniem.mkdir(exist_ok=True)
    sjabloon = sjabloonbeelden(vak.pad("downloads") / f"{map_.name}-verslag.docx")
    regels = []
    for s in sorted(ingediend, key=lambda s: per_id[str(s["id"])]):
        code = per_id[str(s["id"])]
        regels.append((code, verwerk(s, anoniem / code, namen, sjabloon)))

    afdrukpad = map_ / "vingerafdrukken.json"
    vorige = json.loads(afdrukpad.read_text(encoding="utf-8")) if afdrukpad.exists() else None
    for code, r in regels:
        if vorige is not None:
            r["sinds"] = ("nieuw" if code not in vorige
                          else "gewijzigd" if vorige[code] != r["vingerafdruk"] else "")
    afdrukken = dict(vorige or {})
    afdrukken.update({code: r["vingerafdruk"] for code, r in regels})
    afdrukpad.write_text(json.dumps(afdrukken, indent=1, sort_keys=True), encoding="utf-8")
    overzicht(anoniem, regels, data["folder"]["name"])

    zonder = [c for c, r in regels if r["verslag"] == "geen"]
    deels = [c for c, r in regels if r["voorblad"] != "-" and not r["voorblad"].startswith("weggelaten")]
    print(f"{len(regels)} inzendingen anoniem in {anoniem.relative_to(vak.root)}")
    if vorige is None:
        print("  eerste vingerafdruk: vanaf de volgende run zegt OVERZICHT.md wat nieuw en gewijzigd is")
    else:
        nieuw = [c for c, r in regels if r["sinds"] == "nieuw"]
        gewijzigd = [c for c, r in regels if r["sinds"] == "gewijzigd"]
        print(f"  sinds de vorige run: {len(nieuw)} nieuw{': ' + ', '.join(nieuw) if nieuw else ''}, "
              f"{len(gewijzigd)} gewijzigd{': ' + ', '.join(gewijzigd) if gewijzigd else ''}")
        if gewijzigd:
            print("  een gewijzigde code: schrijf haar sectie in voorstellen.md opnieuw")
    if zonder:
        print(f"  zonder verslag: {', '.join(zonder)}")
    if deels:
        print(f"  voorblad niet (volledig) herkend: {', '.join(deels)}; kijk die na voor Claude ze leest")
    onl = [c for c, r in regels if r["onleesbaar"]]
    if onl:
        print(f"  met een bestand dat niet te lezen was: {', '.join(onl)}")
    return 0
