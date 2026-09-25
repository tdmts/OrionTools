"""De gedeelde procedures in OrionTools/skills, en de orion-skills van een vak die ze aanvullen."""

import re
import unittest

from oriontools.check.rules.skills import BASIS
from tests.minivak import RegelTest

SKILL = "---\nname: orion-{naam}\ndescription: Test.\n---\n\n{tekst}\n"
LINK = "Lees eerst [de basis](../../../../OrionTools/skills/{naam}.md)."


def skill(naam, tekst=None):
    return SKILL.format(naam=naam, tekst=LINK.format(naam=naam) if tekst is None else tekst)


class Basis(unittest.TestCase):
    def test_elke_basis_is_een_procedure(self):
        # Een basis zegt in haar kop van welke skill ze is; een los bestand in
        # skills/ dat niemand aanvult, is geen basis maar een verdwaalde notitie.
        bestanden = sorted(BASIS.glob("*.md"))
        self.assertTrue(bestanden)
        for pad in bestanden:
            with self.subTest(pad=pad.name):
                kop = pad.read_text(encoding="utf-8").splitlines()[0]
                self.assertRegex(kop, rf"^# orion-{re.escape(pad.stem)}: ")


class SkillBasis(RegelTest):
    regel = "skill-basis"

    def test_goed_aanvulling_met_verwijzing(self):
        self.assertSchoon({".claude/skills/orion-check/SKILL.md": skill("check"),
                           ".claude/skills/orion-style/SKILL.md": skill("style")})

    def test_goed_eigen_skill_van_het_vak(self):
        # Alleen orion-* is een aanvulling; een andere skill van het vak valt erbuiten.
        self.assertSchoon({".claude/skills/orion-check/SKILL.md": skill("check"),
                           ".claude/skills/compileer/SKILL.md": "---\nname: compileer\n---\n"})

    def test_fout_geen_verwijzing(self):
        self.assertMeldt({".claude/skills/orion-check/SKILL.md": skill("check", "De hele procedure.")},
                         (".claude/skills/orion-check/SKILL.md", "verwijst niet naar de basis"))

    def test_fout_verwijzing_naar_een_andere_basis(self):
        self.assertMeldt({".claude/skills/orion-check/SKILL.md":
                          skill("check", LINK.format(naam="style"))},
                         (".claude/skills/orion-check/SKILL.md", "skills/check.md"))

    def test_fout_geen_basis_in_oriontools(self):
        self.assertMeldt({".claude/skills/orion-compile/SKILL.md": skill("compile")},
                         (".claude/skills/orion-compile/SKILL.md", "bestaat niet"))

    def test_fout_map_zonder_skill(self):
        self.assertMeldt({".claude/skills/orion-check/SKILL.md": skill("check"),
                          ".claude/skills/orion-style/notities.txt": "x"},
                         (".claude/skills/orion-style", "zonder SKILL.md"))

    def test_goed_geen_skills(self):
        self.assertEqual(self.toestand({})[0], "n.v.t.")
