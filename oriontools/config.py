"""oriontools.json: wat een vak anders doet dan de andere, en niets meer.

Het bestand staat in de root van de vakrepo. OrionSync spiegelt het niet
(courses.json sluit het uit bij elk vak), want het stuurt de scripts aan en is
geen cursusinhoud.

Wat hier niet staat, is een standaard die voor elk vak geldt. Die standaarden
staan in STANDAARD hieronder, en een sleutel die daar niet in staat is een
fout: een tikfout in een sleutel mag niet stil de standaard laten gelden.

Een lege dict in STANDAARD is een vrije tabel (check.disable, de
afkortingen): daar zijn de sleutels van het vak zelf en wordt niets
nagekeken. De inhoud van check.disable kijkt de check zelf na, tegen de
regels die ze kent.
"""

import copy
import json

BESTAND = "oriontools.json"

STANDAARD = {
    "course": {
        "code": "",            # korte naam: DeN, ICEES, MC, IR; zit in bestandsnamen
        "title": "",           # voluit, zoals op de kaft
    },
    "paths": {
        "labo": "Labo",
        "syllabus_src": "Theorie/Syllabus/Theorie",
        "syllabus_dir": "Theorie/Syllabus",
        "decks": "Hoorcollege",
        "downloads": "downloads",
        "img": "img",
        "datasheets": "datasheets",
        "oplossingen": "_oplossingen",
        "incoming": "_incoming",
        "export": "_export",
        "startbestanden": "startbestanden",
    },
    # Mappen die de check overslaat: ruwe import, eigen uitvoer, oplossingen.
    # Waarom: zie Context.overgeslagen in check/context.py.
    "staging": ["_incoming", "_export", "_oplossingen"],
    # Pagina's in de repo die geen pagina van de site zijn.
    "exempt_pages": ["pasteInOrion.html", "template.html"],
    # Mappen met html die geen sitepagina is (een deck laadt geen OrionCSS).
    "non_site_dirs": ["Hoorcollege"],
    "check": {
        "disable": {},          # {regel-id: reden}
        "orphan_roots": ["Labo"],
        "remote_document_exts_extra": [],
        "code_style_languages": ["arduino", "cpp", "c", "csharp", "python"],
        # Pagina's die buiten elke regel vallen behalve em-dash en code-style:
        # een stijlgids die elke component demonstreert, ook met kapotte demo-links.
        "skip_pages": [],
        # Een titel "<woord> N" zegt niet wat de student bouwt (exercise-name).
        "exercise_title_words": ["oefening", "opdracht"],
        # --audit. De woordenlijsten staan in rules/audit.py; *_extra vult ze aan.
        "audit": {
            "stock_lead_extra": [],
            "diminutives_extra": [],
            "noord_nl_extra": [],
            "fillers_extra": [],
            # Engelse identifiers die in een codeblok Nederlands horen (leeg: n.v.t.).
            "identifier_words": [],
            # Toegelaten language-* van een codeblok; leeg: elke language-*.
            "code_languages": [],
            # Talen die geen show-language dragen (de badge zou "plaintext" zeggen).
            "code_no_badge": ["plaintext"],
            # fnmatch op het relatieve pad. Waar audit-lead kijkt: alleen waar het
            # vak een lead zet, want een theoriepagina zonder lead is geen fout.
            "lead_patterns": ["*"],
            # Waar audit-figure kijkt. Een kale afbeelding is overal een
            # afwijking, dus een vak laat dit meestal op elke pagina staan.
            "figure_patterns": ["*"],
            # Waar audit-indienen en audit-oplossing kijken (leeg: n.v.t.).
            "exercise_patterns": [],
        },
    },
    "syllabus": {
        "manifest": "reference.js",
        "manifest_key": "",
        "pdf": "",
        "logo": "",
        "docx": "",
        "afkortingen": {},
        "vet_uit_de_word": True,
        # dpi 0: niet krimpen. onaangeroerd: bestandsnamen in img/ die met hun
        # tekst gelezen moeten worden en dus op volle resolutie blijven.
        "krimp": {"dpi": 0, "onaangeroerd": []},
        # De cover, zoals nagemeten van de bestaande syllabus: een regel per
        # element van een lijst. De titel is course.title.
        "cover": {
            "opleiding": "",
            "auteur": "",
            "departement": [],
            "voet": [],
        },
    },
    "handout": {
        "prefix": "",
    },
    "import_brightspace": {
        # Een document boven deze grens wordt overgeslagen. GitHub waarschuwt
        # vanaf 50 MB en weigert 100 MB.
        "max_mb": 50,
        # Hoe diep een geconverteerde pagina staat: zoveel keer ../ voor img/,
        # datasheets/ en startbestanden/ in een herschreven link. 2 voor
        # LaboN/Exercises/, 3 voor Labo/<Naam>/Theorie/.
        "page_depth": 2,
        # Wat een pagina linkt en wij dus zelf hosten. Slides en office-bestanden
        # ontbreken met opzet: ze zijn intern, niet iets wat een pagina linkt, en
        # groot (de grootste .pptx in een echte export is 200 MB).
        "doc_exts": [".pdf", ".zip"],
        # Welke van doc_exts een startbestand is (paths.startbestanden) in plaats
        # van een datasheet: wat een student in een tool opent.
        "start_exts": [],
    },
    "export_pdf": {
        "group": "module",     # lab of module
        # De bestandsnaam zonder .pdf. Velden: {code} van het vak, {id} van de
        # module in orion.json, {n} het labo- of modulenummer. Nooit de titel:
        # een titel die in Orion verandert, mag de naam van een gepubliceerde
        # PDF niet meenemen.
        "naam": "{code}-{id}",
        # Wat bovenop .pdf .zip .docx .pptx .xlsx een los document is, geen pagina.
        "doc_exts_extra": [],
        # Bij group=lab: een pagina in deze map is een oefening, een andere naslag.
        "oefeningen_map": "Exercises",
    },
}


class ConfigFout(Exception):
    pass


def _meng(standaard, eigen, pad):
    if not isinstance(eigen, dict):
        raise ConfigFout(f"{pad or 'de root'} moet een object zijn")
    uit = copy.deepcopy(standaard)
    for sleutel, waarde in eigen.items():
        volledig = f"{pad}.{sleutel}" if pad else sleutel
        if sleutel.startswith("_"):
            continue  # "_uitleg" en dergelijke: commentaar in JSON
        if sleutel not in standaard:
            raise ConfigFout(f"onbekende sleutel {volledig}")
        basis = standaard[sleutel]
        if isinstance(basis, dict) and basis:
            uit[sleutel] = _meng(basis, waarde, volledig)
        elif isinstance(basis, dict):
            if not isinstance(waarde, dict):
                raise ConfigFout(f"{volledig} moet een object zijn")
            uit[sleutel] = waarde
        else:
            if basis is not None and not isinstance(waarde, type(basis)):
                raise ConfigFout(f"{volledig} moet een {type(basis).__name__} zijn")
            uit[sleutel] = waarde
    return uit


def laad(root, pad=None):
    """De config van de vakrepo in root, gemengd met STANDAARD."""
    pad = pad or root / BESTAND
    try:
        eigen = json.loads(pad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigFout(f"{pad} ontbreekt; dit is geen vakrepo voor OrionTools")
    except json.JSONDecodeError as e:
        raise ConfigFout(f"{pad}: geen geldige JSON ({e})")
    return _meng(STANDAARD, eigen, "")
