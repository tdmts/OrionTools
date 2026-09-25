"""De Claude-skills van een vak: een gedeelde procedure in OrionTools, en per vak wat erbij komt."""

from pathlib import Path

from ..regel import Regel

# De procedures staan naast de commando's die ze aanroepen, niet in een vak.
BASIS = Path(__file__).resolve().parents[3] / "skills"
MAP = Path(".claude") / "skills"
PREFIX = "orion-"


def skillmappen(root):
    """De mappen .claude/skills/orion-* van een vak, gesorteerd."""
    map_ = root / MAP
    if not map_.is_dir():
        return []
    return sorted(p for p in map_.iterdir() if p.is_dir() and p.name.startswith(PREFIX))


class SkillBasis(Regel):
    """Een orion-skill van een vak vult de procedure in OrionTools/skills aan.

    Tot september 2026 hadden Microcontrollers en IR elk een volledige kopie
    van de vijf skills orion-check, -convert, -pdf, -review en -style, en die
    liepen uit elkaar zoals de scripts en SCHRIJFSTIJL.md voor hen: IR nam ze
    over van Microcontrollers en schreef ze om, en de kopie van
    Microcontrollers droeg nog de dertien schrijfstijlpatronen van voor de
    gedeelde basis. DeN en ICEES hadden er geen. Nu staat de procedure een keer
    in OrionTools/skills/<naam>.md, en zegt de SKILL.md van een vak alleen wat
    dat vak anders doet: de eenheid van een ronde, de naam van het grootboek,
    de paginasoorten die alleen daar bestaan.

    Een orion-skill zonder verwijzing naar zijn basis is een skill die alleen
    zijn aanvullingen laadt, en wie hem gebruikt, denkt dat dat de procedure
    is. Een orion-skill zonder basis in OrionTools is een procedure die in een
    vak ontstaat en daar blijft, precies zoals de kopieën uit elkaar liepen:
    een nieuwe gedeelde skill begint in OrionTools, en een skill die echt
    alleen van een vak is, heet niet orion-*.
    """

    id = "skill-basis"
    legacy = ()

    def van_toepassing(self, ctx):
        return True if skillmappen(ctx.root) else f"geen {MAP.as_posix()}/{PREFIX}*"

    def controleer(self, ctx):
        for map_ in skillmappen(ctx.root):
            pad = map_ / "SKILL.md"
            naam = map_.name[len(PREFIX):]
            if not pad.is_file():
                ctx.fout(map_, "skillmap zonder SKILL.md")
            elif not (BASIS / f"{naam}.md").is_file():
                ctx.fout(pad, f"OrionTools/skills/{naam}.md bestaat niet; een gedeelde skill begint "
                              f"daar, een skill van dit vak alleen heet niet {PREFIX}*")
            elif f"OrionTools/skills/{naam}.md" not in pad.read_text(encoding="utf-8"):
                ctx.fout(pad, f"verwijst niet naar de basis (../OrionTools/skills/{naam}.md); dit "
                              "bestand zegt alleen wat het vak toevoegt")
