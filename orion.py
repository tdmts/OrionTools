#!/usr/bin/env python3
"""De gedeelde tooling van de Orion-vakken, via een enkel ingangspunt.

    python ../OrionTools/orion.py <commando> [--repo PAD] [opties]

Draai het vanuit de root van een vakrepo, of geef die met --repo. Welk vak het
is en wat daar anders is dan elders, staat in oriontools.json in die root; de
scripts zelf weten niets over een vak. Zonder commando toont het de lijst.

Elk commando is een module met een main(argv). De import gebeurt pas als het
commando gekozen is: `check` gebruikt alleen de standaardbibliotheek, en de
Stop-hook en CI mogen niet stuklopen op een ontbrekende python-docx die alleen
een export nodig heeft.
"""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

COMMANDOS = {
    "check": ("oriontools.check.runner", "de publiceerbaarheidscontrole"),
    "import-brightspace": ("oriontools.importers.brightspace", "een Brightspace-export naar _incoming/"),
    "import-syllabus": ("oriontools.importers.syllabus", "een hoofdstuk van de Word naar html"),
    "import-slides": ("oriontools.importers.slides", "een pptx naar een deck onder Hoorcollege/"),
    "export-syllabus": ("oriontools.export.syllabus", "de syllabus-PDF"),
    "export-handout": ("oriontools.export.handout", "de handout-PDF van een deck"),
    "export-verslag": ("oriontools.export.verslag", "het verslagsjabloon (docx) van een Opdracht.html"),
    "export-oplossing": ("oriontools.export.oplossing", "de modeloplossing (PDF) van een opdracht"),
    "export-pdf": ("oriontools.export.pdf", "een labo of module als PDF"),
}


def gebruik():
    breed = max(map(len, COMMANDOS))
    regels = [f"  {naam.ljust(breed)}  {uitleg}" for naam, (_, uitleg) in COMMANDOS.items()]
    return "gebruik: orion.py <commando> [--repo PAD] [opties]\n\n" + "\n".join(regels)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(gebruik())
        return 0
    naam, rest = argv[0], argv[1:]
    if naam not in COMMANDOS:
        print(f"onbekend commando: {naam}\n\n{gebruik()}", file=sys.stderr)
        return 2
    module = importlib.import_module(COMMANDOS[naam][0])
    return module.main(rest) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
