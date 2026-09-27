"""Toon wat je ANS-token ziet: de vragenbanken en de cursussen van een jaar.

    python ../OrionTools/orion.py ans-verken
    python ../OrionTools/orion.py ans-verken --jaar 2025

Enkel lezen. Het commando is er om de id te vinden die in oriontools.json
hoort (ans.course_id), en om na te gaan dat het token werkt voor er iets
geschreven wordt. Een vak dat hem al invulde, ziet erbij of zijn token die
cursus nog ziet.

De API heeft geen "wie ben ik", en een lijst van cursussen vraagt een
school-id. De zoekfunctie heeft die niet nodig, maar zoekt alleen exact, dus
zoekt dit op het jaar van de cursus. Een cursus draagt zijn school_id, en zo
komt ook die op het scherm.
"""

import argparse
import datetime
import sys

from .. import repo
from .client import AnsFout, Client


def academiejaar(vandaag=None):
    """Het jaar waarin het lopende academiejaar begon: september 2026 tot augustus 2027 is 2026."""
    vandaag = vandaag or datetime.date.today()
    return vandaag.year if vandaag.month >= 9 else vandaag.year - 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="orion.py ans-verken", description=__doc__.split("\n")[0])
    repo.voeg_repo_toe(parser)
    parser.add_argument("--jaar", type=int, default=None,
                        help="het jaar van de cursussen in ANS (standaard: het begin van het lopende academiejaar)")
    args = parser.parse_args(argv)
    vak = repo.vind(args)
    ans = vak.config["ans"]
    jaar = args.jaar or academiejaar()

    try:
        client = Client()
        banken = [b for b in client.alles("/question_banks") if not b.get("trashed")]
        cursussen = [c for c in client.alles("/search/courses", query=f"year:{jaar}")
                     if not c.get("trashed")]
    except AnsFout as e:
        sys.exit(f"ans-verken: {e}")

    # Een naam uit ANS draagt tekens (een trema als combinerend teken) die de
    # codepagina van een Windows-console niet kent.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(f"Vragenbanken ({len(banken)}):")
    for b in sorted(banken, key=lambda b: b["name"].lower()):
        print(f"   {b['id']:>8}  {b['name']}")

    print(f"\nCursussen van {jaar} ({len(cursussen)}):")
    for c in sorted(cursussen, key=lambda c: c["name"].lower()):
        teken = "*" if c["id"] == ans["course_id"] else " "
        code = f"  [{c['course_code']}]" if c.get("course_code") else ""
        print(f" {teken} {c['id']:>10}  {c['name']}{code}  (school {c.get('school_id')})")

    print(f"\noriontools.json van {vak.code or vak.root.name}:")
    waarde = ans["course_id"]
    if not waarde:
        print("  ans.course_id: niet ingesteld")
    elif waarde in {c["id"] for c in cursussen}:
        print(f"  ans.course_id: {waarde}, gemarkeerd met *")
    else:
        print(f"  ans.course_id: {waarde}, niet in de lijst hierboven (een cursus van een ander jaar? probeer --jaar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
