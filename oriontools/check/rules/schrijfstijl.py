"""SCHRIJFSTIJL.md: een gedeelde basis in OrionTools, en per vak wat erbij komt."""

import re
from pathlib import Path

from ..regel import Regel

# De basis staat naast deze code, niet in een vak: ze hoort bij de woordenlijsten
# van audit.py, die haar patronen citeren.
BASIS = Path(__file__).resolve().parents[3] / "SCHRIJFSTIJL.md"
BESTAND = "SCHRIJFSTIJL.md"
KOP_RE = re.compile(r"^#{2,6}\s+(\d+)\.", re.M)


def patroonnummers(tekst):
    """De nummers van de koppen "### N. ...", in volgorde."""
    return [int(n) for n in KOP_RE.findall(tekst)]


class SchrijfstijlNummers(Regel):
    """De SCHRIJFSTIJL.md van een vak vult de basis aan en nummert niet zelf.

    Tot september 2026 had elk vak een eigen kopie van de hele schrijfstijl, en
    die liepen uit elkaar: DeN schreef er twee patronen bij, ICEES voegde er zes
    samen, IR nam de versie van ICEES over, en het verkleinwoord had in twee
    vakken een ander nummer dan in de andere twee. audit.py kon dat nummer
    daardoor niet eens noemen. Nu staat het document in
    OrionTools en zegt het bestand van een vak alleen wat er bij komt, onder het
    nummer van het patroon dat het aanvult.

    Een kop met een nummer dat de basis niet kent, is een patroon dat in een vak
    ontstaat en daar blijft, en dat is precies hoe de kopieën uit elkaar liepen.
    Een nieuw patroon krijgt zijn nummer in de basis. En het bestand van een vak
    moet naar de basis verwijzen, anders leest wie het opent alleen de
    aanvullingen en denkt dat dat de regels zijn.
    """

    id = "schrijfstijl-nummers"
    legacy = ()

    def van_toepassing(self, ctx):
        return True if (ctx.root / BESTAND).is_file() else f"geen {BESTAND}"

    def controleer(self, ctx):
        pad = ctx.root / BESTAND
        tekst = pad.read_text(encoding="utf-8")
        if "OrionTools/SCHRIJFSTIJL.md" not in tekst:
            ctx.fout(pad, "verwijst niet naar de basis (../OrionTools/SCHRIJFSTIJL.md); dit "
                          "bestand zegt alleen wat het vak toevoegt")
        bekend = set(patroonnummers(BASIS.read_text(encoding="utf-8")))
        for m in KOP_RE.finditer(tekst):
            if int(m.group(1)) not in bekend:
                ctx.fout(pad, f"patroon {m.group(1)} bestaat niet in de basis; een nieuw patroon "
                              "krijgt zijn nummer in OrionTools/SCHRIJFSTIJL.md",
                         regelnr=tekst.count("\n", 0, m.start()) + 1)
