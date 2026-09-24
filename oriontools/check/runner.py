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

Een regel geldt voor elk vak waar het ding bestaat dat ze nakijkt. Een vak
zet er een uit in oriontools.json, met de reden erbij:

    "check": {"disable": {"code-style": "RAPID kent geen accolades"}}

Een lege reden of een onbekende id is een fout: een uitzondering zonder reden
wordt nooit meer herbekeken.
"""

import argparse
import importlib
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
    args = p.parse_args(argv)

    if args.hook and (args.audit or args.fix):
        p.error("--hook gaat niet samen met --audit of --fix")

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
    return rapporteer(ctx, args.hook)


def rapporteer(ctx, hook):
    fouten = [b for b in ctx.bevindingen if b.ernst == "fout"]
    rest = [b for b in ctx.bevindingen if b.ernst != "fout"]
    if hook:
        if not fouten:
            return 0
        for b in fouten:
            print(f"  FOUT [{b.regel}] {b.plaats()}: {b.boodschap}", file=sys.stderr)
        print(f"\n{len(fouten)} fout(en). Los ze op voor je afrondt.", file=sys.stderr)
        return 2
    for b in rest:
        label = "waarschuwing" if b.ernst == "waarschuwing" else b.ernst
        print(f"  {label:12}  [{b.regel}] {b.plaats()}: {b.boodschap}")
    for b in fouten:
        print(f"  FOUT          [{b.regel}] {b.plaats()}: {b.boodschap}")
    if fouten:
        print(f"\n{len(fouten)} fout(en), {len(rest)} waarschuwing(en).")
        return 1
    print(f"\nAlles in orde. {len(rest)} waarschuwing(en).")
    return 0
