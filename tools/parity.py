#!/usr/bin/env python3
"""De oude check tegen de nieuwe, op dezelfde boom.

    python tools/parity.py ../DeN --config tools/vakken/DeN.json
    python tools/parity.py ../DeN --config tools/vakken/DeN.json --mutaties WERKMAP
    python tools/parity.py ../IR --config tools/vakken/IR.json --bash [--audit]
    python tools/parity.py ../IR --config tools/vakken/IR.json --bash [--audit] --mutaties WERKMAP
    python tools/parity.py ../IR --config tools/vakken/IR.json --bash --fix WERKMAP

Met --bash is de oude check scripts/check-content.sh (Microcontrollers, IR);
zie de sectie over de bash-check verderop.

De oude check is scripts/check-content.py in de vakrepo, gedraaid met die repo
als werkmap. De nieuwe is orion.py check. Beide uitvoeren worden herleid tot een
multiset van (ernst, regel-id, pad): de nieuwe noemt haar regel-id zelf, de
oude krijgt er een via ORUD hieronder, op de kern van haar boodschap. Zo mag de
nieuwe haar boodschappen herformuleren zonder dat de vergelijking breekt, en
telt toch elke melding apart.

Met --mutaties maakt het een wegwerpkloon (git clone --local) in WERKMAP, zet
alle mtimes op een vast tijdstip (een kloon zet ze in checkoutvolgorde, en dan
is een afgeleid bestand soms toevallig een microseconde ouder dan zijn bron),
spuit in elke regel minstens een overtreding in, en eist dan twee dingen: dat
beide checks precies hetzelfde melden, en dat elke bedoelde regel-id er
tussen zit. Het raakt de echte repo niet aan; de kloon blijft staan om na te
kijken.

Stdlib alleen, zoals de check.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
ORION = HIER / "orion.py"

# Oude boodschap -> regel-id. De eerste die past, wint; volgorde telt.
ORUD = [
    (r"git niet beschikbaar", None),
    (r"^orion\.json$", None, "orion-targets"),      # (pad-regex, -, id)
    (r"window\.LAB_REFERENCE is leeg", "syllabus-manifest"),
    (r"staat niet in reference\.js", "syllabus-manifest"),
    (r"nog te maken asset|link wijst nergens heen|dit geeft 404 op Pages: |nog niet in git",
     "links"),
    (r"staat niet als page in orion\.json", "orion-orphan"),
    (r"linkt de gehoste OrionCSS", "orioncss-wiring"),
    (r"hotlinkt naar Brightspace", "brightspace-hotlink"),
    (r"externe afbeelding", "remote-image"),
    (r"externe documentlink", "remote-document"),
    (r"YouTube-embed", "youtube-referrer"),
    (r"em-dash", "em-dash"),
    (r"^codeblok regel", "code-style"),
    (r"biedt geen verslagsjabloon|verslagsjabloon ontbreekt|is ouder dan Opdracht\.html",
     "verslag-stale"),
    (r"is niet afgesloten met -->", "unclosed-comment"),
    (r"staat buiten een <!-- verslag|blok bevat geen vragenlijst|verslag-tabel",
     "verslag-markup"),
    (r'geen <p class="lead">', "opdracht-lead"),
    (r"kop Verloop|steps-container", "no-verloop"),
    (r"sessietelling", "no-session-count"),
    (r"gewicht in procent", "no-weight"),
    (r"linkt in de iframe", "topic-frame"),
    (r"de downloadknop heet", "download-button"),
    (r"de lead deelt", "duplicate-lead"),
    (r"export-syllabus\.py", "syllabus-stale"),
    (r"export-handout\.py", "handout-stale"),
    (r"mogelijkheden met|open vraag zonder", "vragen-answered"),
    (r'begint op start=|mist start=', "vragen-numbering"),
    (r"met invulruimte eronder", "vragen-class"),
    (r"laadt oplossingen\.js niet", "oplossingen-script"),
    (r"onopgeloste gok", "importer-guess"),
    (r"staat in img/ maar", "orphan-image"),
]

OUD_RE = re.compile(r"^\s*(FOUT|waarschuwing)\s+(.*?): (.*)$")
NIEUW_RE = re.compile(r"^\s*(FOUT|waarschuwing)\s+\[([^\]]+)\] (.*?)(?::\d+)?: (.*)$")


def _omgeving():
    return dict(os.environ, PYTHONIOENCODING="utf-8")


def oud_id(pad, boodschap):
    for regel in ORUD:
        if len(regel) == 3:
            if re.search(regel[0], pad):
                return regel[2]
            continue
        patroon, rid = regel
        if re.search(patroon, boodschap):
            return rid or "-"
    if pad == "reference.js":
        return "syllabus-manifest"
    return "?onbekend"


def draai_oud(repo):
    uit = subprocess.run([sys.executable, "scripts/check-content.py"], cwd=repo,
                         capture_output=True, text=True, encoding="utf-8", env=_omgeving())
    telling, onbekend = Counter(), []
    for regel in uit.stdout.splitlines():
        m = OUD_RE.match(regel)
        if not m:
            continue
        ernst, pad, boodschap = m.group(1), m.group(2).replace("\\", "/"), m.group(3)
        rid = oud_id(pad, boodschap)
        if rid == "-":
            continue
        if rid == "?onbekend":
            onbekend.append(regel.strip())
        telling[(ernst, rid, pad)] += 1
    return telling, onbekend, uit.stdout


def draai_nieuw(repo, config):
    cmd = [sys.executable, str(ORION), "check", "--repo", str(repo)]
    if config:
        cmd += ["--config", str(config)]
    uit = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=_omgeving())
    telling = Counter()
    for regel in uit.stdout.splitlines():
        m = NIEUW_RE.match(regel)
        if m and m.group(3) != ".":
            telling[(m.group(1), m.group(2), m.group(3))] += 1
    return telling, uit.stdout


def vergelijk(repo, config):
    oud, onbekend, _ = draai_oud(repo)
    nieuw, _ = draai_nieuw(repo, config)
    alleen_oud = oud - nieuw
    alleen_nieuw = nieuw - oud
    for regel in onbekend:
        print(f"  oude melding zonder id: {regel}")
    for sleutel, n in sorted(alleen_oud.items()):
        print(f"  alleen oud   {n}x {sleutel}")
    for sleutel, n in sorted(alleen_nieuw.items()):
        print(f"  alleen nieuw {n}x {sleutel}")
    gelijk = not (alleen_oud or alleen_nieuw or onbekend)
    print(f"{repo}: {sum(oud.values())} oud, {sum(nieuw.values())} nieuw, "
          f"{'gelijk' if gelijk else 'VERSCHIL'}")
    return gelijk, oud, nieuw


# ------------------------------------------------------------- mutaties

LEAD_OPEN_RE = re.compile(r'(<p class="[^"]*\blead\b[^"]*"[^>]*>)')
KOPIE = "alfa bravo charlie delta echo foxtrot golf hotel india. "


def _lees(p):
    return p.read_text(encoding="utf-8")


def _schrijf(p, tekst):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(tekst, encoding="utf-8", newline="")


def _voor_body(p, extra):
    t = _lees(p)
    i = t.rfind("</body>")
    _schrijf(p, t[:i] + extra + "\n" + t[i:] if i >= 0 else t + extra)


KALE_PAGINA = ('<!DOCTYPE html>\n<html lang="nl"><head><meta charset="utf-8">\n{css}'
               '<title>x</title></head>\n<body>\n{body}\n</body></html>\n')
CSS = ('<link rel="stylesheet" href="https://tdmts.github.io/OrionCSS/style.css">\n'
       '<script src="https://tdmts.github.io/OrionCSS/main.js"></script>\n')


def muteer(kloon, cfg, leeg_manifest=False):
    """Spuit de overtredingen in; geeft de regel-ids die gemeld moeten worden."""
    verwacht = set()
    paths = cfg.get("paths", {})
    labo = kloon / paths.get("labo", "Labo")
    syl_src = kloon / paths.get("syllabus_src", "Theorie/Syllabus/Theorie")
    downloads = kloon / paths.get("downloads", "downloads")
    img = kloon / paths.get("img", "img")
    decks = kloon / paths.get("decks", "Hoorcollege")

    # Een labo met een hub en een opdracht ernaast.
    overview = next(p for p in sorted(labo.glob("*/overview.html"))
                    if (p.parent / "Opdracht.html").is_file())
    module = overview.parent
    opdracht = module / "Opdracht.html"
    andere_opdracht = next(p for p in sorted(labo.glob("*/Opdracht.html"))
                           + sorted(labo.glob("*/*/Opdracht.html")) if p != opdracht)

    # Hub: em-dash, hoofdletters, dode link, untracked asset, hygiene, codestijl,
    # verloop, sessietelling, gewicht, topicgrens.
    bestaand = sorted(img.glob("*.png"))[0]
    shutil.copy(bestaand, img / "parity-untracked.png")
    rel_img = os.path.relpath(img, module).replace("\\", "/")
    _voor_body(overview, "\n".join([
        "<p>een zin — met een em-dash</p>",
        '<a href="OVERVIEW.html" target="_blank">hoofdletters</a>',
        '<img src="bestaat-niet.png" alt="">',
        f'<img src="{rel_img}/parity-untracked.png" alt="">',
        "<p>zie /content/enforced/12345/</p>",
        '<img src="https://example.com/a.png" alt="">',
        '<a href="https://example.com/datasheet.pdf" target="_blank">ds</a>',
        '<iframe src="https://www.youtube.com/embed/abc"></iframe>',
        '<pre class="code-wrapper language-arduino"><code>void setup() {\n  int a=1;\n}\n</code></pre>',
        "<h2>Verloop</h2>",
        '<div class="steps-container"></div>',
        "<p>Voor dit labo zijn twee sessies voorzien.</p>",
        "<p>Verslag [40%]</p>",
        '<a href="Opdracht.html">naar de opdracht</a>',
    ]))
    verwacht |= {"em-dash", "links", "brightspace-hotlink", "remote-image", "remote-document",
                 "youtube-referrer", "code-style", "no-verloop", "no-session-count",
                 "no-weight", "topic-frame"}

    # Dubbele lead: dezelfde negen woorden vooraan in hub en opdracht.
    for p in (overview, opdracht):
        _schrijf(p, LEAD_OPEN_RE.sub(lambda m: m.group(1) + KOPIE, _lees(p), count=1))
    verwacht.add("duplicate-lead")

    # Opdracht: knoptekst, markup buiten commentaar, scheve tabel, leeg blok.
    t = _lees(opdracht).replace(">Opdracht downloaden<", ">Opdracht en verslag downloaden<", 1)
    t = t.replace("<!-- verslag", "<!-- verslag\n<ol class=\"vragen\"><li>x"
                  '<table class="verslag-tabel"><thead><tr><th>a</th><th>b</th></tr></thead>'
                  "<tbody><tr><td>1</td></tr></tbody></table></li></ol>", 1)
    t = t.replace("</body>", '<ol class="vragen"><li>zichtbaar</li></ol>\n'
                             "<!-- verslag zonder inhoud -->\n</body>", 1)
    _schrijf(opdracht, t)
    verwacht |= {"download-button", "verslag-markup"}

    # Andere opdracht: geen lead meer.
    _schrijf(andere_opdracht, LEAD_OPEN_RE.sub('<p class="intro">', _lees(andere_opdracht)))
    verwacht.add("opdracht-lead")

    # Nieuwe pagina's onder Labo: een zonder OrionCSS en met een open commentaar
    # (wiring, orphan, unclosed), een gewone die in orion.json ontbreekt.
    _schrijf(module / "Kaal.html", KALE_PAGINA.format(
        css="", body="<!-- open\n<p>x</p>\n<!-- dicht -->"))
    _schrijf(module / "Wees.html", KALE_PAGINA.format(css=CSS, body="<p>x</p>"))
    verwacht |= {"orioncss-wiring", "orion-orphan", "unclosed-comment"}

    # orion.json: een page die niet bestaat.
    oj = kloon / "orion.json"
    doc = json.loads(_lees(oj))
    doc["modules"][0].setdefault("items", []).append(
        {"title": "weg", "page": f"{paths.get('labo', 'Labo')}/BestaatNiet.html"})
    _schrijf(oj, json.dumps(doc, ensure_ascii=False, indent=2))
    verwacht.add("orion-targets")

    # Syllabus.
    paginas = sorted(syl_src.rglob("*.html"))
    met_vragen = [p for p in paginas if 'class="vragen"' in _lees(p)]
    juist = next(p for p in met_vragen if 'class="juist"' in _lees(p))
    _schrijf(juist, _lees(juist).replace(' class="juist"', "", 1))
    verwacht.add("vragen-answered")
    start = [p for p in met_vragen if re.search(r'<ol class="vragen" start="\d+"', _lees(p))]
    if start:
        _schrijf(start[0], re.sub(r'(<ol class="vragen") start="\d+"', r"\1", _lees(start[0]),
                                  count=1))
        verwacht.add("vragen-numbering")
    script = next(p for p in met_vragen if p not in (juist,) and "oplossingen.js" in _lees(p))
    _schrijf(script, re.sub(r"<script[^>]*oplossingen\.js[^>]*>\s*</script>", "", _lees(script)))
    verwacht.add("oplossingen-script")
    zonder = next(p for p in paginas if 'class="vragen"' not in _lees(p))
    _voor_body(zonder, '<ol><li>vraag<table class="invulruimte"><tr><td></td></tr></table>'
                       '</li></ol>\n<p data-geraden="parity">x</p>')
    verwacht |= {"vragen-class", "importer-guess"}
    _schrijf(zonder.parent / "NietInManifest.html", KALE_PAGINA.format(css=CSS, body="<p>x</p>"))
    verwacht.add("syllabus-manifest")
    shutil.copy(bestaand, img / "syllabus-parity-wees.png")
    verwacht.add("orphan-image")

    if leeg_manifest:
        mf = kloon / cfg.get("syllabus", {}).get("manifest", "reference.js")
        t = _lees(mf)
        begin = t.index("window.LAB_REFERENCE")
        _schrijf(mf, t[:begin] + "window.LAB_REFERENCE = {};\n")

    # Tijden: alles op T0, dan de verouderingen expliciet.
    t0 = 1_700_000_000
    for map_, submappen, namen in os.walk(kloon):
        submappen[:] = [d for d in submappen if d != ".git"]
        for n in namen:
            os.utime(Path(map_) / n, (t0, t0))
    # Opdracht nieuwer dan haar docx.
    m = re.search(r'href="([^"]*downloads/[^"]+\.docx)"', _lees(opdracht))
    if m:
        os.utime(opdracht, (t0 + 100, t0 + 100))
        verwacht.add("verslag-stale")
    # Een syllabuspagina nieuwer dan de PDF.
    pdf = downloads / cfg.get("syllabus", {}).get("pdf", "")
    if pdf.is_file():
        os.utime(paginas[0], (t0 + 100, t0 + 100))
        verwacht.add("syllabus-stale")
    # Een deck nieuwer dan zijn handout.
    prefix = cfg.get("handout", {}).get("prefix", "")
    for deck in sorted(decks.glob("*.html")) if prefix else []:
        naam = re.sub(r"(?<!^)(?=[A-Z0-9])", "-", deck.stem).lower()
        if (downloads / f"{prefix}{naam}.pdf").is_file():
            os.utime(deck, (t0 + 100, t0 + 100))
            verwacht.add("handout-stale")
            break
    return verwacht


def kloon_maken(repo, werkmap, naam):
    doel = werkmap / naam
    if doel.exists():
        shutil.rmtree(doel, onerror=lambda f, p, e: (os.chmod(p, 0o700), f(p)))
    subprocess.run(["git", "clone", "--local", "--quiet", str(repo), str(doel)], check=True)
    # Het oude script van de werkboom, niet van HEAD: dat is wat vergeleken wordt.
    shutil.copy(repo / "scripts" / "check-content.py", doel / "scripts" / "check-content.py")
    subprocess.run(["git", "update-index", "--assume-unchanged", "scripts/check-content.py"],
                   cwd=doel, check=True)
    return doel


def mutatieronde(repo, config, werkmap, leeg_manifest):
    cfg = json.loads(Path(config).read_text(encoding="utf-8")) if config else {}
    naam = repo.name + ("-leeg" if leeg_manifest else "-mutaties")
    kloon = kloon_maken(repo, werkmap, naam)
    verwacht = muteer(kloon, cfg, leeg_manifest)
    gelijk, oud, nieuw = vergelijk(kloon, config)
    gemeld_oud = {rid for _, rid, _ in oud}
    gemeld_nieuw = {rid for _, rid, _ in nieuw}
    if leeg_manifest:
        # Een leeg manifest legt syllabus-manifest stil op een waarschuwing na.
        verwacht.discard("syllabus-manifest")
        if ("waarschuwing", "syllabus-manifest", "reference.js") not in nieuw:
            print("  de waarschuwing over het lege manifest ontbreekt")
            gelijk = False
    for rid in sorted(verwacht):
        if rid not in gemeld_oud or rid not in gemeld_nieuw:
            print(f"  NIET GEMELD: {rid} (oud {'ja' if rid in gemeld_oud else 'nee'}, "
                  f"nieuw {'ja' if rid in gemeld_nieuw else 'nee'})")
            gelijk = False
    print(f"  {len(verwacht)} geinjecteerde regels, "
          f"{len(verwacht & gemeld_oud & gemeld_nieuw)} door beide gemeld")
    return gelijk


# ------------------------------------------- de bash-check (MC en IR)
#
# Microcontrollers en IR hadden scripts/check-content.sh. Die noemt geen
# regel-id: ze groepeert haar meldingen onder een kop, en een melding is
# "pad -> doel (...)", "pad:regel:inhoud  <- uitleg" of "pad: boodschap". De kop
# en de boodschap bepalen samen de id (BASH_ORUD), het pad is het eerste woord.
# Vergeleken wordt als verzameling van (ernst, id, pad): de bash-check meldt
# een em-dash per regel en de nieuwe per pagina, en dat is geen verschil.

BASH_KOPPEN = [
    (r"^Broken links or assets", "links"),
    (r"^orion\.json does not match", "orion"),
    (r"^Page wiring", "wiring"),
    (r"^Asset hygiene", "asset"),
    (r"^K&R brace", "code-style"),
    (r"^Em-dash", "em-dash"),
    (r"^Operator\(s\) without", "code-style"),
    (r"^Generic exercise title in orion\.json", "exercise-name-orion"),
    (r"^Generic page title", "exercise-name"),
    (r"^solution-container outside", "solution-placement"),
    (r"^spoiler-container is retired", "spoiler-retired"),
    (r"^A link loads another page", "topic-frame"),
    (r"^Pending placeholders", "placeholder"),
    (r"^Style audit", "audit"),
    (r"^(Deviations recorded|Fixed automatically|Still needs a human|Sketch compilation"
     r"|check-content:|Many of these|Some of these)", None),
]

BASH_ORUD = {
    "orion": [(r"is not a page in orion\.json", "orion-orphan"),
              (r"^orion\.json: id ", "orion-ids"), (r"^orion\.json: ", "orion-targets")],
    "wiring": [(r"does not link the hosted", "orioncss-wiring"),
               (r"checklist|initChecklistSync", "checklist-wiring"),
               (r"solution-container|solution-reveal", "solution-reveal-wiring"),
               (r"^[^ ]+:\d+:<(link|script)", "foreign-assets")],
    "asset": [(r"Brightspace hotlink", "brightspace-hotlink"), (r"remote image", "remote-image"),
              (r"remote document", "remote-document"), (r"YouTube", "youtube-referrer"),
              (r"Chamilo", "chamilo-link")],
    "audit": [(r"unknown audit-skip", "audit-skip"),
              (r": code block|plaintext block", "audit-code-class"),
              (r"stock formula", "audit-lead-opener"), (r"diminutive", "audit-verkleinwoord"),
              (r"Netherlandic", "audit-noord-nederlands"), (r"is padding", "audit-vulwoord"),
              (r"'LED' in the prose", "audit-led-spelling"),
              (r"Engelse identifier", "audit-identifier-taal"), (r"u-vorm", "audit-u-vorm"),
              (r'no <p class="lead">', "audit-lead"), (r"<img> outside", "audit-figure"),
              (r'id="indienen"|Indienen section', "audit-indienen"),
              (r'id="oplossing"', "audit-oplossing")],
}


def _bash():
    return shutil.which("bash") or "bash"


def draai_bash(repo, *vlaggen):
    uit = subprocess.run([_bash(), "scripts/check-content.sh", *vlaggen], cwd=repo,
                         capture_output=True, text=True, encoding="utf-8", errors="replace",
                         env=_omgeving())
    return uit.stdout + "\n" + uit.stderr


def lees_bash(tekst):
    """(standaard, audit, onbekend): Counters van (ernst, id, pad) uit de bash-uitvoer."""
    standaard, audit, onbekend = Counter(), Counter(), []
    kop = None
    for regel in tekst.splitlines():
        if not regel.strip():
            continue
        if not regel.startswith(" "):
            kop = "?"
            for patroon, naam in BASH_KOPPEN:
                if re.search(patroon, regel):
                    kop = naam
                    break
            continue
        if kop is None or kop == "?":
            if kop == "?":
                onbekend.append(regel.strip())
            continue
        item = regel.strip()
        pad = re.match(r"[^\s:]+", item).group(0)
        if kop in BASH_ORUD:
            rid = next((r for p, r in BASH_ORUD[kop] if re.search(p, item)), None)
            if rid is None:
                onbekend.append(f"[{kop}] {item}")
                continue
            if rid.startswith("orion-") and rid != "orion-orphan":
                pad = "orion.json"
        elif kop == "placeholder":
            rid = "links"
        elif kop == "exercise-name-orion":
            rid, pad = "exercise-name", "orion.json"
        else:
            rid = kop
        if kop == "audit":
            audit[("waarschuwing", rid, pad)] += 1
        else:
            ernst = "waarschuwing" if kop == "placeholder" else "FOUT"
            standaard[(ernst, rid, pad)] += 1
    return standaard, audit, onbekend


def lees_nieuw(tekst):
    standaard, audit = Counter(), Counter()
    for regel in tekst.splitlines():
        m = NIEUW_RE.match(regel)
        if m and m.group(3) != ".":
            doel = audit if m.group(2).startswith("audit-") else standaard
            doel[(m.group(1), m.group(2), m.group(3))] += 1
    return standaard, audit


def vergelijk_bash(repo, config, audit=False):
    t0 = time.perf_counter()
    oud_tekst = draai_bash(repo, *(["--audit"] if audit else []))
    t_oud = time.perf_counter() - t0
    cmd = [sys.executable, str(ORION), "check", "--repo", str(repo)]
    if config:
        cmd += ["--config", str(config)]
    if audit:
        cmd.append("--audit")
    t0 = time.perf_counter()
    nieuw_tekst = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                 env=_omgeving()).stdout
    t_nieuw = time.perf_counter() - t0
    oud, oud_audit, onbekend = lees_bash(oud_tekst)
    nieuw, nieuw_audit = lees_nieuw(nieuw_tekst)
    gelijk = not onbekend
    for regel in onbekend:
        print(f"  oude melding zonder id: {regel}")
    paren = [("", set(oud), set(nieuw))]
    if audit:
        paren.append(("audit ", set(oud_audit), set(nieuw_audit)))
    for label, a, b in paren:
        for sleutel in sorted(a - b):
            print(f"  alleen oud   {label}{sleutel}")
        for sleutel in sorted(b - a):
            print(f"  alleen nieuw {label}{sleutel}")
        gelijk &= a == b
    print(f"{repo}: {len(set(oud))} oud, {len(set(nieuw))} nieuw"
          + (f", audit {sum(oud_audit.values())} oud / {sum(nieuw_audit.values())} nieuw"
             if audit else "")
          + f", {'gelijk' if gelijk else 'VERSCHIL'}  (bash {t_oud:.1f}s, nieuw {t_nieuw:.1f}s)")
    return gelijk, set(oud) | set(oud_audit), set(nieuw) | set(nieuw_audit)


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _orion_paginas(kloon):
    doc = json.loads(_lees(kloon / "orion.json"))
    uit = []

    def loop(item):
        if isinstance(item.get("page"), str):
            uit.append(item["page"])
        for kind in item.get("items", []):
            loop(kind)

    for m in doc["modules"]:
        loop(m)
    return uit


def muteer_bash(kloon):
    """Een overtreding per regel van de bash-check; geeft de verwachte regel-ids.

    Elke nieuwe pagina wordt gestaged: de bash-check kijkt alleen naar
    getrackte html. De ongetrackte afbeelding blijft ongetrackt, die is de
    overtreding.
    """
    verwacht = set()
    arduino = (kloon / "checklist-sync.js").is_file()
    paginas = _orion_paginas(kloon)
    gastheer = next(kloon / p for p in paginas
                    if p.count("/") >= 1 and "</body>" in _lees(kloon / p)
                    and "code-wrapper" not in _lees(kloon / p)
                    and "solution-reveal.js" not in _lees(kloon / p))
    buur = next(kloon / p for p in paginas
                if (kloon / p).parent == gastheer.parent and kloon / p != gastheer)
    img = kloon / "img"
    bestaand = sorted(img.glob("*.png"))[0]
    shutil.copy(bestaand, img / "parity-untracked.png")
    rel_img = os.path.relpath(img, gastheer.parent).replace("\\", "/")
    regels = [
        "<p>een zin — met een em-dash</p>",
        f'<img src="{rel_img}/{bestaand.name.upper()}" alt="">',
        '<img src="bestaat-niet.png" alt="">',
        f'<img src="{rel_img}/parity-untracked.png" alt="">',
        "<p>zie /content/enforced/12345/</p>",
        '<img src="https://example.com/a.png" alt="">',
        '<a href="https://example.com/datasheet.pdf" target="_blank">ds</a>',
        '<iframe src="https://www.youtube.com/embed/abc" allowfullscreen></iframe>',
        "<h1>Gevorderde oefening 2</h1>",
        f'<a href="{buur.name}">naar de buur</a>',
        '<h2 id="parity">Parity</h2>',
        '<div class="solution-container">x</div>',
        '<div class="spoiler-container">x</div>',
    ]
    verwacht |= {"em-dash", "links", "brightspace-hotlink", "remote-image", "remote-document",
                 "youtube-referrer", "exercise-name", "topic-frame", "solution-placement",
                 "spoiler-retired", "solution-reveal-wiring"}
    if not arduino:
        regels += ['<a href="https://chamilo.hogent.be/doc?id=1" target="_blank">c</a>',
                   '<a href="https://example.com/p.rspag" target="_blank">r</a>',
                   '<link rel="stylesheet" href="https://cdn.example.com/bootstrap.css">',
                   '<script src="https://code.jquery.com/jquery.js"></script>',
                   '<a href="/d2l/common/x.d2l" target="_blank">d2l</a>',
                   "<h1>Opdracht 3</h1>"]
        verwacht |= {"chamilo-link", "foreign-assets"}
    _voor_body(gastheer, "\n".join(regels))

    module = gastheer.parent
    rel_root = os.path.relpath(kloon, module).replace("\\", "/")
    nieuw = [module / "ParityKaal.html", module / "ParityWees.html"]
    _schrijf(nieuw[0], KALE_PAGINA.format(css="", body="<p>x</p>"))
    _schrijf(nieuw[1], KALE_PAGINA.format(
        css=CSS, body=f'<p>x</p>\n<script src="{rel_root}/solution-reveal.js"></script>'))
    verwacht |= {"orioncss-wiring", "orion-orphan"}
    if arduino:
        lab = next(p for p in paginas if re.match(r"Labo1/", p))
        pc = kloon / Path(lab).parent / "ParityChecklist.html"
        _schrijf(pc, KALE_PAGINA.format(css=CSS, body=(
            '<ul class="checklist"><li>x</li></ul>\n'
            "<script>initChecklistSync({ labId: 'labo2', exerciseId: 'x' });</script>")))
        nieuw.append(pc)
        verwacht.add("checklist-wiring")
        # code-style: een K&R-accolade en krappe operatoren in een bestaand blok.
        code = next(kloon / p for p in paginas
                    if '<pre class="code-wrapper language-cpp' in _lees(kloon / p))
        t = _lees(code)
        i = t.index("\n", t.index('<pre class="code-wrapper language-cpp')) + 1
        _schrijf(code, t[:i] + "void parity() {\nint a=1;\nfor(int i=0;i&lt;3;i++)\n" + t[i:])
        verwacht.add("code-style")

    oj = kloon / "orion.json"
    doc = json.loads(_lees(oj))
    items = doc["modules"][0].setdefault("items", [])
    pdf = next((p for p in sorted(kloon.rglob("*.pdf")) if ".git" not in p.parts), None)
    # De hoofdletter- en ./-varianten wijzen naar een file en niet naar een page:
    # de bash-check leest een page onder elke alias als een apart bestand
    # (Windows vindt ze allemaal) en meldt topic-frame dan dubbel.
    rel_pdf = pdf.relative_to(kloon).as_posix()
    items += [
        {"id": "Parity_Fout", "title": "Oefening 4", "page": paginas[0]},
        {"id": doc["modules"][0]["id"], "title": "dubbel", "page": paginas[0]},
        {"id": "parity-kaal", "title": "niet kaal", "file": "./" + rel_pdf},
        {"id": "parity-weg", "title": "weg", "page": "BestaatNiet.html"},
        {"id": "parity-case", "title": "case", "file": rel_pdf.upper()},
        {"id": "parity-untracked", "title": "u", "file": "img/parity-untracked.png"},
        {"id": "parity-pdf", "title": "pdf", "page": rel_pdf},
    ]
    _schrijf(oj, json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    verwacht |= {"orion-ids", "orion-targets"}

    for p in nieuw:
        _git(kloon, "add", "--", p.relative_to(kloon).as_posix())
    return verwacht


def bash_kloon(repo, werkmap, naam):
    doel = werkmap / naam
    if doel.exists():
        shutil.rmtree(doel, onerror=lambda f, p, e: (os.chmod(p, 0o700), f(p)))
    subprocess.run(["git", "clone", "--local", "--quiet", str(repo), str(doel)], check=True)
    return doel


def mutatieronde_bash(repo, config, werkmap):
    kloon = bash_kloon(repo, werkmap, repo.name + "-bash-mutaties")
    verwacht = muteer_bash(kloon)
    gelijk, oud, nieuw = vergelijk_bash(kloon, config)
    gemeld_oud = {rid for _, rid, _ in oud}
    gemeld_nieuw = {rid for _, rid, _ in nieuw}
    for rid in sorted(verwacht):
        if rid not in gemeld_oud or rid not in gemeld_nieuw:
            print(f"  NIET GEMELD: {rid} (oud {'ja' if rid in gemeld_oud else 'nee'}, "
                  f"nieuw {'ja' if rid in gemeld_nieuw else 'nee'})")
            gelijk = False
    print(f"  {len(verwacht)} geinjecteerde regels, "
          f"{len(verwacht & gemeld_oud & gemeld_nieuw)} door beide gemeld")
    return gelijk


def muteer_audit(kloon, cfg):
    """Een afwijking per auditregel, op een pagina die onder page_patterns valt."""
    audit = cfg.get("check", {}).get("audit", {})
    patronen = audit.get("page_patterns", ["*"])
    oefening = audit.get("exercise_patterns", [])
    paginas = _orion_paginas(kloon)
    from fnmatch import fnmatch
    doel = next(kloon / p for p in paginas if any(fnmatch(p, x) for x in oefening or patronen)
                and "</body>" in _lees(kloon / p))
    t = _lees(doel)
    t = re.sub(r'<p class="lead">', '<p class="lead">Hier lees je alles. ', t, count=1)
    t = t.replace("</body>", "\n".join([
        "<p>een blokje en een lusje, prima, uiteraard</p>",
        "<p>de LED brandt</p>",
        "<p>Als u kunt, doe het.</p>",
        '<pre class="code-wrapper language-arduino"><code>int pinLed = 3;',
        "</code></pre>",
        '<pre class="code-wrapper language-plaintext linenumbers show-language"><code>x',
        "</code></pre>",
        '<img src="data:," alt="">',
        "<!-- audit-skip: bestaatniet -->",
    ]) + "\n</body>", 1)
    t = re.sub(r'<h2([^>]*)id="(indienen|oplossing)"', r'<h2\1id="parity-\2"', t)
    _schrijf(doel, t)
    zonder_lead = next(kloon / p for p in paginas if any(fnmatch(p, x) for x in patronen)
                       and kloon / p != doel and 'class="lead"' in _lees(kloon / p))
    _schrijf(zonder_lead, _lees(zonder_lead).replace('class="lead"', 'class="intro"'))


def auditronde(repo, config, werkmap):
    cfg = json.loads(Path(config).read_text(encoding="utf-8")) if config else {}
    kloon = bash_kloon(repo, werkmap, repo.name + "-bash-audit")
    muteer_audit(kloon, cfg)
    gelijk, oud, nieuw = vergelijk_bash(kloon, config, audit=True)
    print("  auditregels gemeld: "
          + " ".join(sorted({r for _, r, _ in oud if r.startswith("audit-")})))
    return gelijk


def muteer_fix(kloon):
    """Dezelfde mechanische overtredingen, voor --fix."""
    arduino = (kloon / "checklist-sync.js").is_file()
    paginas = _orion_paginas(kloon)
    gastheer = next(kloon / p for p in paginas
                    if p.count("/") >= 1 and "</body>" in _lees(kloon / p)
                    and "solution-container" not in _lees(kloon / p))
    img = kloon / "img"
    shutil.copy(sorted(img.glob("*.png"))[0], img / "parity-untracked.png")
    shutil.copy(sorted(img.glob("*.png"))[1], img / "parity-orion.png")
    rel_img = os.path.relpath(img, gastheer.parent).replace("\\", "/")
    rel_root = os.path.relpath(kloon, gastheer.parent).replace("\\", "/")
    _voor_body(gastheer, "\n".join([
        "<p>een zin — met een em-dash &mdash; en nog een</p>",
        "<p>eindigt op een em-dash —",
        "en loopt door</p>",
        f'<img src="{rel_img}/parity-untracked.png" alt="">',
        '<iframe src="https://www.youtube.com/embed/abc" allowfullscreen></iframe>',
        '<iframe src="https://www.youtube-nocookie.com/embed/def"></iframe>',
        f'<script src="{rel_root}/solution-reveal.js"></script>',
    ]))
    if arduino:
        code = next(kloon / p for p in paginas
                    if '<pre class="code-wrapper language-cpp' in _lees(kloon / p))
        t = _lees(code)
        i = t.index("\n", t.index('<pre class="code-wrapper language-cpp')) + 1
        _schrijf(code, t[:i] + "void parity() {\n  int a=1;\n  for(int i=0;i&lt;3;i++) {\n"
                 "    if(a==b&amp;&amp;c!=d) x=f(a,b); // a,b,c\n  } else {\n"
                 '    Serial.print("a,b=c");\n  }\n}\n' + t[i:])
        # CRLF, zoals een Windows-werkkopie: een herstelling mag geen regeleinde
        # verliezen of verdubbelen.
        _schrijf(code, _lees(code).replace("\n", "\r\n"))
    oj = kloon / "orion.json"
    doc = json.loads(_lees(oj))
    doc["modules"][0].setdefault("items", []).append(
        {"id": "parity-orion", "title": "o", "file": "img/parity-orion.png"})
    _schrijf(oj, json.dumps(doc, ensure_ascii=False, indent=2) + "\n")


def fixronde(repo, config, werkmap):
    oud = bash_kloon(repo, werkmap, repo.name + "-fix-oud")
    nieuw = bash_kloon(repo, werkmap, repo.name + "-fix-nieuw")
    for k in (oud, nieuw):
        muteer_fix(k)
    t = time.perf_counter()
    subprocess.run([_bash(), "scripts/check-content.sh", "--fix", "--force"], cwd=oud,
                   capture_output=True, env=_omgeving())
    t_oud = time.perf_counter() - t
    cmd = [sys.executable, str(ORION), "check", "--repo", str(nieuw), "--fix", "--force"]
    if config:
        cmd += ["--config", str(config)]
    t = time.perf_counter()
    subprocess.run(cmd, capture_output=True, env=_omgeving())
    t_nieuw = time.perf_counter() - t
    verschil = subprocess.run(["git", "diff", "--no-index", "--stat", "--", str(oud), str(nieuw)],
                              capture_output=True, text=True, encoding="utf-8")
    regels = [r for r in verschil.stdout.splitlines() if "/.git/" not in r]
    staged = [subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=k,
                             capture_output=True, text=True).stdout.split() for k in (oud, nieuw)]
    wijz = [subprocess.run(["git", "diff", "--stat"], cwd=k, capture_output=True,
                           text=True).stdout.strip().splitlines()[-1:] for k in (oud, nieuw)]
    # git diff --no-index vergelijkt ook .git; alleen de werkboom telt.
    werkboom = subprocess.run(
        ["git", "diff", "--no-index", "--name-only", "--", str(oud), str(nieuw)],
        capture_output=True, text=True, encoding="utf-8").stdout.splitlines()
    werkboom = [r for r in werkboom if "/.git/" not in r.replace("\\", "/")]
    gelijk = not werkboom and staged[0] == staged[1]
    for r in werkboom:
        print(f"  verschilt: {r}")
    print(f"  gestaged oud {staged[0]} / nieuw {staged[1]}")
    print(f"  gewijzigd oud {wijz[0]} / nieuw {wijz[1]}")
    print(f"{repo}: --fix {'gelijk' if gelijk else 'VERSCHIL'} "
          f"(bash {t_oud:.1f}s, nieuw {t_nieuw:.1f}s)")
    del regels
    return gelijk


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("repo", type=Path)
    p.add_argument("--config", type=Path)
    p.add_argument("--mutaties", type=Path, metavar="WERKMAP",
                   help="kloon de repo hierin en spuit in elke regel een overtreding in")
    p.add_argument("--leeg-manifest", action="store_true",
                   help="met --mutaties: maak ook het manifest leeg")
    p.add_argument("--bash", action="store_true",
                   help="de oude check is scripts/check-content.sh (MC, IR)")
    p.add_argument("--audit", action="store_true", help="met --bash: vergelijk ook --audit")
    p.add_argument("--fix", type=Path, metavar="WERKMAP",
                   help="met --bash: vergelijk --fix op twee klonen in WERKMAP")
    args = p.parse_args(argv)
    repo = args.repo.resolve()
    config = args.config.resolve() if args.config else None
    if args.bash and args.fix:
        ok = fixronde(repo, config, args.fix.resolve())
    elif args.bash and args.mutaties and args.audit:
        ok = auditronde(repo, config, args.mutaties.resolve())
    elif args.bash and args.mutaties:
        ok = mutatieronde_bash(repo, config, args.mutaties.resolve())
    elif args.bash:
        ok, _, _ = vergelijk_bash(repo, config, args.audit)
    elif args.mutaties:
        ok = mutatieronde(repo, config, args.mutaties.resolve(), args.leeg_manifest)
    else:
        ok, _, _ = vergelijk(repo, config)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
