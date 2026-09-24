"""Wat elke regel nodig heeft over de vakrepo, een keer gelezen.

Elke regel leest dezelfde pagina's. In de bash-versie van de check was dat een
grep per regel, en een grep per bestand dreef een oudere versie naar 48
seconden, voorbij de time-out van de Stop-hook. Hier wordt elk bestand een keer
gelezen en git ls-files een keer gedraaid, en regels vragen het aan de context.
"""

import os
import subprocess
from functools import cached_property

ORION_CSS = "https://tdmts.github.io/OrionCSS/style.css"
ORION_JS = "https://tdmts.github.io/OrionCSS/main.js"


class Bevinding:
    __slots__ = ("regel", "pad", "regelnr", "boodschap", "ernst")

    def __init__(self, regel, pad, boodschap, ernst="fout", regelnr=None):
        self.regel, self.pad, self.boodschap = regel, pad, boodschap
        self.ernst, self.regelnr = ernst, regelnr

    def plaats(self):
        return f"{self.pad}:{self.regelnr}" if self.regelnr else str(self.pad)


class Context:
    def __init__(self, vak, ci=False):
        self.vak = vak
        self.root = vak.root
        self.config = vak.config
        self.ci = ci                 # in CI: geen verouderingsregels
        self.bevindingen = []
        self._teksten = {}
        self._huidige_regel = None

    # ---------------------------------------------------------- bevindingen

    def fout(self, pad, boodschap, regelnr=None):
        self.bevindingen.append(Bevinding(self._huidige_regel, self._rel(pad), boodschap,
                                          "fout", regelnr))

    def waarschuw(self, pad, boodschap, regelnr=None):
        self.bevindingen.append(Bevinding(self._huidige_regel, self._rel(pad), boodschap,
                                          "waarschuwing", regelnr))

    def meld(self, pad, boodschap, ernst, regelnr=None):
        """Een melding die geen fout en geen waarschuwing is (een afwijking)."""
        self.bevindingen.append(Bevinding(self._huidige_regel, self._rel(pad), boodschap,
                                          ernst, regelnr))

    def _rel(self, pad):
        try:
            return pad.relative_to(self.root).as_posix()
        except (AttributeError, ValueError):
            return str(pad)

    # ----------------------------------------------------------- bestanden

    @cached_property
    def staging(self):
        return set(self.config["staging"])

    @cached_property
    def getrackt(self):
        """De getrackte paden (posix, relatief), of None zonder git."""
        try:
            uit = subprocess.run(["git", "ls-files", "-z"], cwd=self.root, capture_output=True,
                                 text=True, encoding="utf-8", check=True).stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
        return set(filter(None, uit.split("\0")))

    def overgeslagen(self, pad):
        """Valt pad buiten de check: .git, node_modules of een staging-map?

        _incoming is ruwe Brightspace-inhoud, en die breekt met opzet precies
        wat de regels verbieden: geen OrionCSS, YouTube zonder referrerpolicy,
        em-dashes. Telde de check hem mee, dan stond ze rood zolang een import
        loopt en riep de Stop-hook bij elke beurt, en zo leer je haar niet meer
        lezen. _oplossingen houdt modeloplossingen die .gitignore buiten git
        houdt: OrionSync spiegelt ze nooit, dus er is niets om na te kijken.
        _export is eigen uitvoer. De lijst is config "staging".
        """
        delen = pad.relative_to(self.root).parts
        return ".git" in delen or "node_modules" in delen or bool(self.staging.intersection(delen))

    @cached_property
    def html(self):
        """Elke html-pagina van de repo, buiten staging, gesorteerd."""
        return [p for p in sorted(self.root.rglob("*.html")) if not self.overgeslagen(p)]

    @cached_property
    def paginas(self):
        """De html die de regels nakijken: alles buiten check.skip_pages.

        Een stijlgids (template.html in Microcontrollers) demonstreert elke
        component, ook met demo-afbeeldingen van een andere server en links naar
        bestanden die de repo niet heeft. Alleen em-dash en code-style kijken er
        wel naar, via html: de codevoorbeelden van de stijlgids zetten de
        huisstijl voor alles wat eruit gekopieerd wordt.
        """
        skip = set(self.config["check"]["skip_pages"])
        return [p for p in self.html
                if p.name not in skip and p.relative_to(self.root).as_posix() not in skip]

    @cached_property
    def sitepaginas(self):
        """De html die een pagina van de site is: geen exempt, geen deck."""
        exempt = set(self.config["exempt_pages"])
        geen_site = set(self.config["non_site_dirs"])
        uit = []
        for p in self.html:
            rel = p.relative_to(self.root)
            if rel.as_posix() in exempt or p.name in exempt:
                continue
            if geen_site.intersection(rel.parts[:-1]):
                continue
            uit.append(p)
        return uit

    @cached_property
    def auditpaginas(self):
        """De pagina's die --audit nakijkt: gepubliceerde sitepagina's.

        Dezelfde set als de siteregels (sitepaginas), zonder check.skip_pages,
        en alleen wat git trackt. Een audit gaat over wat de student leest:
        pasteInOrion.html en een deck zijn geen sitepagina, en een ongetrackt
        klad (een Sessie1Beta.html naast het echte deck) spiegelt OrionSync
        niet, dus een bevinding daarop is ruis. Zonder git telt alles.
        """
        site = set(self.sitepaginas)
        getrackt = self.getrackt
        return [p for p in self.paginas if p in site and
                (getrackt is None or p.relative_to(self.root).as_posix() in getrackt)]

    def tekst(self, pad):
        if pad not in self._teksten:
            self._teksten[pad] = pad.read_text(encoding="utf-8", errors="replace")
        return self._teksten[pad]

    def exacte_hoofdletters(self, doel):
        """Staat elk segment onder de root er precies zo op schijf?

        Windows en macOS zijn hoofdletterongevoelig, een webserver niet. Een link
        naar 'opdracht.html' opent dus lokaal en breekt zodra de bestanden op een
        server staan die wel onderscheid maakt. Elk segment wordt vergeleken met
        de echte inhoud van zijn map. Bewust niet Path.resolve(): dat verbetert
        de hoofdletters stil en dan test de regel niets meer.
        """
        try:
            rel = doel.relative_to(self.root)
        except ValueError:
            return True  # buiten de repo, dat vangt een andere regel
        huidig = self.root
        for segment in rel.parts:
            if segment in ("", "."):
                continue
            if segment == "..":
                huidig = huidig.parent
                continue
            try:
                if segment not in os.listdir(huidig):
                    return False
            except OSError:
                return False
            huidig = huidig / segment
        return True

    # --------------------------------------------------------------- tijd

    def tijd(self, pad):
        """Wanneer pad laatst veranderde: de mtime.

        Een verouderingsregel vergelijkt een afgeleid bestand met zijn bron, en
        dat kan alleen in een werkkopie. Een checkout zet elke mtime op het
        moment van uitchecken, en de committijd helpt ook niet: een export die
        byte voor byte gelijk uitkomt, laat git niets zien, dus de bron lijkt
        nieuwer dan een PDF die klopt. Daarom draaien die regels niet met --ci
        (Regel.alleen_lokaal); de Stop-hook vangt ze op de machine waar de
        export gebeurt.
        """
        return pad.stat().st_mtime
