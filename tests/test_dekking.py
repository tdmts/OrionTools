"""Elke regel heeft een fixture die ze laat melden, en een die ze stil laat.

Een regel zonder test_fout kan stil stukgaan: een regex die nergens meer op
grijpt, geeft een groene check en een groene test. Een regel zonder test_goed
kan stil te veel gaan melden. Beide gebeuren bij een verbreding, zoals toen de
vragen-regels van de syllabus naar de labo-zelftests gingen.
"""

import importlib
import pkgutil
import unittest

import tests
from oriontools.check.regel import REGISTER
from tests.minivak import RegelTest


def testklassen():
    for mod in pkgutil.iter_modules(tests.__path__):
        if mod.name.startswith("test_"):
            importlib.import_module(f"tests.{mod.name}")
    uit, stap = [], [RegelTest]
    while stap:
        for kind in stap.pop().__subclasses__():
            uit.append(kind)
            stap.append(kind)
    return uit


class Dekking(unittest.TestCase):
    def test_elke_regel_heeft_een_testklasse(self):
        getest = {k.regel for k in testklassen()}
        self.assertEqual(sorted(set(REGISTER) - getest), [], "regels zonder testklasse")
        self.assertEqual(sorted(getest - set(REGISTER) - {""}), [], "testklasse voor een onbekende regel")

    def test_elke_testklasse_heeft_goed_en_fout(self):
        for klasse in testklassen():
            if not klasse.regel:
                continue
            namen = dir(klasse)
            with self.subTest(regel=klasse.regel):
                self.assertTrue(any(n.startswith("test_goed") for n in namen), "geen test_goed*")
                self.assertTrue(any(n.startswith("test_fout") for n in namen), "geen test_fout*")
