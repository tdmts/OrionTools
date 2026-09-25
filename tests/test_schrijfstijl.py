"""SCHRIJFSTIJL.md in OrionTools, en de code die haar patronen citeert."""

import re
import unittest
from pathlib import Path

from oriontools.check.rules.schrijfstijl import BASIS, patroonnummers
from tests.minivak import RegelTest

WORTEL = Path(__file__).resolve().parent.parent
SAMENGEVOEGD = {4, 8, 11, 19, 21, 22}


class Basis(unittest.TestCase):
    def test_elk_geciteerd_nummer_is_een_kop(self):
        # audit.py en de rest van de code verwijzen op nummer; een verschoven of
        # samengevoegd patroon laat die verwijzing stil naar iets anders wijzen.
        bekend = set(patroonnummers(BASIS.read_text(encoding="utf-8")))
        cite = re.compile(r"SCHRIJFSTIJL\.md (?:patroon )?(\d+)|[Pp]atroon (\d+)")
        for pad in sorted((WORTEL / "oriontools").rglob("*.py")):
            for m in cite.finditer(pad.read_text(encoding="utf-8")):
                nummer = int(m.group(1) or m.group(2))
                with self.subTest(pad=pad.name, nummer=nummer):
                    self.assertIn(nummer, bekend)

    def test_nummers_liggen_vast(self):
        nummers = patroonnummers(BASIS.read_text(encoding="utf-8"))
        self.assertEqual(nummers, sorted(set(nummers)), "dubbel of uit volgorde")
        self.assertFalse(SAMENGEVOEGD & set(nummers),
                         "een samengevoegd nummer is terug; de tabel in de basis zegt waar het staat")


LINK = "De regels staan in [de basis](../OrionTools/SCHRIJFSTIJL.md).\n\n"


class SchrijfstijlNummers(RegelTest):
    regel = "schrijfstijl-nummers"

    def test_goed_aanvulling_op_bestaand_nummer(self):
        self.assertSchoon({"SCHRIJFSTIJL.md": LINK + "## Aanvullingen\n\n### 17. Waar je op mag "
                                                     "rekenen\n\n### Een eigen notatie\n"})

    def test_fout_eigen_nummer(self):
        tekst = LINK + "### 17. Rekenen\n\n### 21. De glosse te veel\n"
        b = self.bevindingen({"SCHRIJFSTIJL.md": tekst})
        self.assertEqual([(x.regelnr, "patroon 21" in x.boodschap) for x in b], [(5, True)])

    def test_fout_geen_verwijzing(self):
        self.assertMeldt({"SCHRIJFSTIJL.md": "# Schrijfstijl\n\n### 1. Geen slotzin\n"},
                         ("SCHRIJFSTIJL.md", "verwijst niet naar de basis"))

    def test_goed_geen_bestand(self):
        self.assertEqual(self.toestand({}), ("n.v.t.", "geen SCHRIJFSTIJL.md"))
