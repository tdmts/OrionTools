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
        "audit": {},
    },
    "syllabus": {
        "manifest": "reference.js",
        "manifest_key": "",
        "pdf": "",
        "logo": "",
        "docx": "",
        "afkortingen": {},
        "vet_uit_de_word": True,
        "krimp": {"dpi": 0, "onaangeroerd": []},
    },
    "handout": {
        "prefix": "",
    },
    "import_brightspace": {
        "max_mb": 50,
        "start_dir": "",
        "start_prefix": "",
    },
    "export_pdf": {
        "group": "module",     # lab of module
        "naam": "",
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
