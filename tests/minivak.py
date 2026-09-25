"""Een minivak in een tijdelijke map, en een regel die erop draait.

    python -m unittest                  vanuit de root van OrionTools, alles
    python -m unittest tests.test_hub   een module

Elke test bouwt het kleinste vak waarin zijn regel iets te zien krijgt: een
dict {pad: inhoud}, een oriontools.json met alleen wat die test nodig heeft,
en naar keuze git. Geen fixture op schijf en geen kopie van een echt vak: een
echt vak verandert elke week, en dan faalt een test om een reden die niets met
de regel te maken heeft. Fixture en verwachting staan zo in dezelfde methode.

Een regel draait hier zoals de runner haar draait: alleen als ze van
toepassing is. meldingen() faalt als ze dat niet is. Anders slaagt een
test_goed ook wanneer de fixture de regel per ongeluk uitschakelt (een
overview.html op de verkeerde diepte, een vergeten orion.json), en dan test
hij niets meer. Dat is dezelfde stille no-op waartegen de check zelf bestaat.
Wie wil nakijken dat een regel niet van toepassing is, gebruikt toestand().

Elk bestand krijgt dezelfde vaste mtime, zodat een verouderingsregel niet
afhangt van de volgorde waarin de test schrijft; mtimes={pad: seconden} zet er
een voor of achter. De gedeelde stijlbladen van de exports staan buiten het
vak; huisstijl() legt ze voor een test in een tijdelijke map. Met git=True wordt de map een repo en is alles gestaged
behalve wat in ongetrackt staat; er wordt niets gecommit, want git ls-files
ziet de index en een commit vraagt een identiteit.

Stdlib alleen, zoals de check.
"""

import copy
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from oriontools import huisstijl as _huisstijl
from oriontools.check import runner
from oriontools.check.context import ORION_CSS, ORION_JS, Context
from oriontools.check.regel import REGISTER
from oriontools.repo import Vak

runner.laad_regels()

T0 = 1_750_000_000
CONFIG = {"course": {"code": "T", "title": "Testvak"}}


def pagina(body="<p>Tekst.</p>", titel="Pagina", kop=None):
    """Een sitepagina die elke regel doorstaat, met body erin."""
    kop = titel if kop is None else kop
    return (f'<!DOCTYPE html>\n<html lang="nl">\n<head>\n<meta charset="utf-8">\n'
            f"<title>{titel}</title>\n"
            f'<link rel="stylesheet" href="{ORION_CSS}">\n'
            f'<script type="text/javascript" src="{ORION_JS}"></script>\n'
            f"</head>\n<body>\n<h1>{kop}</h1>\n{body}\n</body>\n</html>\n")


def menu(*items):
    """Een orion.json met een module, en per item een topic: 'page:pad' of 'file:pad'."""
    topics = []
    for i, item in enumerate(items):
        soort, pad = item.split(":", 1)
        topics.append({"id": f"t{i}", "title": f"Topic {i}", soort: pad})
    return json.dumps({"modules": [{"id": "m", "title": "Module", "items": topics}]}, indent=2)


def _meng(basis, extra):
    uit = copy.deepcopy(basis)
    for k, v in extra.items():
        uit[k] = _meng(uit[k], v) if isinstance(v, dict) and isinstance(uit.get(k), dict) else v
    return uit


class RegelTest(unittest.TestCase):
    """Een testklasse per regel: regel is haar id, config wat elke test erbij krijgt.

    De dekkingstest (test_dekking.py) eist een klasse per regel in REGISTER,
    met minstens een test_goed* en een test_fout*.
    """

    regel = ""
    config = {}

    def huisstijl(self, mtimes=None):
        """syllabus.css, handout.css en hoorcollege.css in een tijdelijke map, op T0.

        Die drie staan buiten het vak (zie oriontools/huisstijl.py), en de echte
        dragen de mtime van de laatste checkout: tegen T0 zijn ze altijd nieuwer,
        en elke verouderingsregel zou dan melden. mtimes={naam: seconden} zoals
        bij vak(). Geeft {naam: pad} terug.
        """
        tmp = tempfile.TemporaryDirectory(prefix="huisstijl-", ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        stijl, orioncss = Path(tmp.name) / "stijl", Path(tmp.name) / "OrionCSS"
        for patch in (mock.patch.object(_huisstijl, "STIJL", stijl),
                      mock.patch.object(_huisstijl, "ORIONCSS", orioncss)):
            patch.start()
            self.addCleanup(patch.stop)
        paden = {"syllabus.css": _huisstijl.syllabus_css(),
                 "handout.css": _huisstijl.handout_css(),
                 "hoorcollege.css": _huisstijl.hoorcollege_css()}
        for naam, pad in paden.items():
            pad.parent.mkdir(parents=True, exist_ok=True)
            pad.write_text("", encoding="utf-8")
            t = T0 + (mtimes or {}).get(naam, 0)
            os.utime(pad, (t, t))
        return paden

    def vak(self, bestanden, config=None, git=False, ongetrackt=(), mtimes=None):
        tmp = tempfile.TemporaryDirectory(prefix="minivak-", ignore_cleanup_errors=True)
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        cfg = _meng(_meng(CONFIG, self.config), config or {})
        alles = {"oriontools.json": json.dumps(cfg, indent=2), **bestanden}
        for rel, inhoud in alles.items():
            pad = root / rel
            pad.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(inhoud, bytes):
                pad.write_bytes(inhoud)
            else:
                pad.write_text(inhoud, encoding="utf-8", newline="\n")
        if git:
            self._git(root, "init", "-q")
            te_stagen = [rel for rel in alles if rel not in ongetrackt]
            if te_stagen:
                self._git(root, "add", "--", *te_stagen)
        for rel in alles:
            t = T0 + (mtimes or {}).get(rel, 0)
            os.utime(root / rel, (t, t))
        return Vak(root)

    @staticmethod
    def _git(root, *args):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)

    def toestand(self, bestanden, config=None, ci=False, **kw):
        """('actief'|'uit'|'n.v.t.', reden) van deze regel in het minivak."""
        ctx = Context(self.vak(bestanden, config, **kw), ci=ci)
        return runner.toestand(ctx, REGISTER[self.regel], ctx.config["check"]["disable"])

    def bevindingen(self, bestanden, config=None, ci=False, **kw):
        """De Bevinding-objecten van deze regel alleen, met hun regelnr."""
        ctx = Context(self.vak(bestanden, config, **kw), ci=ci)
        stand, reden = runner.toestand(ctx, REGISTER[self.regel], ctx.config["check"]["disable"])
        self.assertEqual(stand, "actief", f"{self.regel} draait niet in deze fixture: {reden}")
        ctx._huidige_regel = self.regel
        REGISTER[self.regel]().controleer(ctx)
        return ctx.bevindingen

    def meldingen(self, bestanden, config=None, ci=False, **kw):
        """De bevindingen van deze regel alleen, als (ernst, pad, boodschap)."""
        return [(b.ernst, b.pad, b.boodschap)
                for b in self.bevindingen(bestanden, config, ci, **kw)]

    def assertSchoon(self, bestanden, config=None, **kw):
        m = self.meldingen(bestanden, config, **kw)
        self.assertEqual(m, [], f"{self.regel} meldt iets in een fixture die klopt")

    def assertMeldt(self, bestanden, *verwacht, config=None, ernst="fout", **kw):
        """Precies de verwachte meldingen: elk (pad, fragment uit de boodschap) een keer.

        Een melding te veel faalt net zo goed als een te weinig; zo ziet een
        test ook een regel die hetzelfde ding twee keer meldt.
        """
        m = self.meldingen(bestanden, config, **kw)
        over = list(m)
        for pad, fragment in verwacht:
            gevonden = next((x for x in over if x[0] == ernst and x[1] == pad
                             and fragment in x[2]), None)
            self.assertIsNotNone(gevonden, f"geen {ernst} op {pad} met '{fragment}' in {m}")
            over.remove(gevonden)
        self.assertEqual(over, [], "meldingen die de test niet verwacht")
        return m
