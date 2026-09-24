#!/usr/bin/env python3
"""De oude check tegen de nieuwe, op dezelfde boom.

    python tools/parity.py ../DeN --config tools/vakken/DeN.json
    python tools/parity.py ../DeN --config tools/vakken/DeN.json --mutaties WERKMAP

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


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("repo", type=Path)
    p.add_argument("--config", type=Path)
    p.add_argument("--mutaties", type=Path, metavar="WERKMAP",
                   help="kloon de repo hierin en spuit in elke regel een overtreding in")
    p.add_argument("--leeg-manifest", action="store_true",
                   help="met --mutaties: maak ook het manifest leeg")
    args = p.parse_args(argv)
    repo = args.repo.resolve()
    config = args.config.resolve() if args.config else None
    if args.mutaties:
        ok = mutatieronde(repo, config, args.mutaties.resolve(), args.leeg_manifest)
    else:
        ok, _, _ = vergelijk(repo, config)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
