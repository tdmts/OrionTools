"""De publiceerbaarheidscontrole van een vakrepo.

    python ../OrionTools/orion.py check            fouten en samenvatting, exit 1 bij fouten
    python ../OrionTools/orion.py check --hook     stil als alles klopt; anders fouten op
                                                   stderr en exit 2, wat de Stop-hook laat
                                                   blokkeren (exit 1 blokkeert niet)
    python ../OrionTools/orion.py check --ci       zonder de verouderingsregels, die een
                                                   werkkopie nodig hebben
    python ../OrionTools/orion.py check --audit    ook de huisstijl; adviserend, zonder
                                                   invloed op de exitcode
    python ../OrionTools/orion.py check --fix      eerst de mechanische fouten herstellen
    python ../OrionTools/orion.py check --rules    welke regels er zijn en welke hier gelden
    python ../OrionTools/orion.py check --explain ID
    python ../OrionTools/orion.py check --json     dezelfde controle als een JSON-object op
                                                   stdout, voor het paneel; samen met --ci
                                                   en --audit, niet met de rest

Een regel geldt voor elk vak waar het ding bestaat dat ze nakijkt. Een vak
zet er een uit in oriontools.json, met de reden erbij:

    "check": {"disable": {"code-style": "RAPID kent geen accolades"}}

Een lege reden of een onbekende id is een fout: een uitzondering zonder reden
wordt nooit meer herbekeken.
"""

import argparse
import importlib
import json
import pkgutil
import sys

from .. import repo
from . import rules
from .context import Context
from .regel import REGISTER


def laad_regels():
    for mod in pkgutil.iter_modules(rules.__path__):
        importlib.import_module(f"{rules.__name__}.{mod.name}")
    return REGISTER


def _uitgezet(ctx):
    uit = ctx.config["check"]["disable"]
    for rid, reden in uit.items():
        if rid not in REGISTER:
            ctx.fout("oriontools.json", f"check.disable noemt een onbekende regel: {rid}")
        elif not isinstance(reden, str) or not reden.strip():
            ctx.fout("oriontools.json", f"check.disable.{rid} heeft geen reden")
    return uit


def toestand(ctx, regel, uit):
    """('actief'|'uit'|'n.v.t.', reden) voor een regel in dit vak."""
    if regel.id in uit:
        return "uit", uit[regel.id]
    if regel.alleen_lokaal and ctx.ci:
        return "n.v.t.", "alleen lokaal, niet met --ci"
    ok = regel().van_toepassing(ctx)
    if ok is True:
        return "actief", ""
    return "n.v.t.", ok or "niet van toepassing"


def draai(ctx, modi):
    uit = _uitgezet(ctx)
    for rid, cls in REGISTER.items():
        if cls.modus not in modi:
            continue
        stand, _ = toestand(ctx, cls, uit)
        if stand != "actief":
            continue
        ctx._huidige_regel = rid
        cls().controleer(ctx)
    ctx._huidige_regel = None


def main(argv):
    p = argparse.ArgumentParser(prog="orion.py check", description=__doc__.split("\n")[0])
    repo.voeg_repo_toe(p)
    p.add_argument("--hook", action="store_true")
    p.add_argument("--ci", action="store_true")
    p.add_argument("--audit", action="store_true")
    p.add_argument("--fix", action="store_true")
    p.add_argument("--force", action="store_true", help="--fix ook op een vuile tree")
    p.add_argument("--rules", action="store_true")
    p.add_argument("--explain", metavar="ID")
    p.add_argument("--json", action="store_true", help="het resultaat als JSON op stdout")
    args = p.parse_args(argv)

    if args.hook and (args.audit or args.fix):
        p.error("--hook gaat niet samen met --audit of --fix")
    if args.json:
        andere = [v for v, aan in (("--hook", args.hook), ("--fix", args.fix),
                                   ("--rules", args.rules), ("--explain", args.explain)) if aan]
        if andere:
            p.error(f"--json gaat niet samen met {' of '.join(andere)}: "
                    "die hebben elk hun eigen uitvoer")

    vak = repo.vind(args)
    laad_regels()
    ctx = Context(vak, ci=args.ci)

    if args.explain:
        cls = REGISTER.get(args.explain)
        if not cls:
            print(f"geen regel {args.explain}", file=sys.stderr)
            return 2
        print(f"{cls.id}  (vroeger {', '.join(cls.legacy) or '-'})\n")
        print((cls.__doc__ or "").strip())
        return 0

    if args.rules:
        uit = _uitgezet(ctx)
        breed = max(map(len, REGISTER), default=0)
        for rid, cls in sorted(REGISTER.items()):
            stand, reden = toestand(ctx, cls, uit)
            extra = f"  ({reden})" if reden else ""
            modus = "" if cls.modus == "standaard" else f" [{cls.modus}]"
            print(f"  {rid.ljust(breed)}  {stand:7}{modus}  {', '.join(cls.legacy)}{extra}")
        return 0

    if args.fix:
        from . import fix
        code = fix.herstel(ctx, force=args.force)
        if code:
            return code
        ctx = Context(vak, ci=args.ci)

    modi = {"standaard"} | ({"audit"} if args.audit else set())
    draai(ctx, modi)
    if args.json:
        return rapporteer_json(ctx, args)
    return rapporteer(ctx, args.hook)


def rapporteer(ctx, hook):
    fouten = [b for b in ctx.bevindingen if b.ernst == "fout"]
    waarschuwingen = [b for b in ctx.bevindingen if b.ernst == "waarschuwing"]
    afwijkingen = [b for b in ctx.bevindingen if b.ernst == "afwijking"]
    if hook:
        if not fouten:
            return 0
        for b in fouten:
            print(f"  FOUT [{b.regel}] {b.plaats()}: {b.boodschap}", file=sys.stderr)
        print(f"\n{len(fouten)} fout(en). Los ze op voor je afrondt.", file=sys.stderr)
        return 2
    if afwijkingen:
        print("Afwijkingen die de pagina zelf vastlegt:")
        for b in afwijkingen:
            print(f"  {b.plaats()}: {b.boodschap}")
        print()
    for b in waarschuwingen:
        print(f"  waarschuwing  [{b.regel}] {b.plaats()}: {b.boodschap}")
    for b in fouten:
        print(f"  FOUT          [{b.regel}] {b.plaats()}: {b.boodschap}")
    if fouten:
        print(f"\n{len(fouten)} fout(en), {len(waarschuwingen)} waarschuwing(en).")
        return 1
    print(f"\nAlles in orde. {len(waarschuwingen)} waarschuwing(en).")
    return 0


JSON_VERSIE = 1


def rapporteer_json(ctx, args):
    """Het resultaat als een JSON-object op stdout, en verder niets.

    Het control center van de lector draait de check in elk vak en toont per
    repo de fouten en waarschuwingen. Een paneel dat de tekstuitvoer leest,
    breekt op de eerste herformulering van een regel, en kan een pad met een
    dubbelpunt niet van het regelnummer scheiden. Daarom leest het dit:

        {"versie": 1, "repo": "DeN", "ci": false, "audit": false,
         "fouten": 0, "waarschuwingen": 1, "adviezen": 0, "afwijkingen": 0,
         "bevindingen": [{"regel": "links", "ernst": "waarschuwing",
                          "pad": "Labo/A/x.html", "regelnr": 12,
                          "boodschap": "..."}]}

    Plat met opzet: een lijst bevindingen met elk dezelfde vijf sleutels, en
    de tellingen ernaast, zodat het paneel niet zelf hoeft te tellen. versie
    gaat omhoog als een sleutel van betekenis verandert; een sleutel erbij
    laat ze staan. repo is de naam van de map, want zo kent het paneel het vak.
    pad is relatief aan de root van het vak, met /; regelnr is null als de
    regel geen regel aanwijst, en regel is null voor een fout in
    oriontools.json zelf (check.disable), die geen regel meldt.

    ernst is een van vier. fout en waarschuwing betekenen wat ze in de tekst
    betekenen. advies is een waarschuwing van een auditregel (alleen met
    --audit): de tekst noemt die ook waarschuwing, maar een paneel dat de
    huisstijl op een hoop gooit met een kapotte link, leert je de
    waarschuwingen niet meer lezen. afwijking is een geldige audit-skip, die
    de tekst apart opsomt. Alleen fout bepaalt de exitcode, zoals zonder
    --json: 1 bij fouten, anders 0.

    ensure_ascii, omdat stdout onder Windows naar een pijp cp1252 schrijft en
    een boodschap met een pijl dan de hele uitvoer doet crashen; een JSON-lezer
    leest de escape terug als hetzelfde teken. Met --hook, --fix, --rules of
    --explain weigert main(): die schrijven elk hun eigen tekst, en een
    stdout die half tekst en half JSON is, leest geen paneel.
    """
    bevindingen = []
    for b in ctx.bevindingen:
        ernst = b.ernst
        cls = REGISTER.get(b.regel)
        if ernst == "waarschuwing" and cls is not None and cls.modus == "audit":
            ernst = "advies"
        bevindingen.append({"regel": b.regel, "ernst": ernst,
                            "pad": str(b.pad).replace("\\", "/"),
                            "regelnr": b.regelnr or None, "boodschap": b.boodschap})

    def tel(ernst):
        return sum(1 for b in bevindingen if b["ernst"] == ernst)

    uit = {"versie": JSON_VERSIE, "repo": ctx.root.name, "ci": bool(args.ci),
           "audit": bool(args.audit), "fouten": tel("fout"),
           "waarschuwingen": tel("waarschuwing"), "adviezen": tel("advies"),
           "afwijkingen": tel("afwijking"), "bevindingen": bevindingen}
    print(json.dumps(uit, indent=2, ensure_ascii=True))
    return 1 if uit["fouten"] else 0
