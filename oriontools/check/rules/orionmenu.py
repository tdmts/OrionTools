"""orion.json, het Orion-menu: klopt het met de bestanden, en respecteert een pagina het."""

import json
import os
import re
from pathlib import Path
from urllib.parse import unquote

from ..regel import Regel
from ._gedeeld import COMMENTAAR_RE, heeft_orion, orion_doelen


class OrionDoelen(Regel):
    """Elke page en file in orion.json bestaat, met exact dezelfde hoofdletters.

    OrionSync bouwt de modules en topics van de cursus uit orion.json. Een pad
    dat niet bestaat of waarvan de hoofdletters niet kloppen, wordt in Orion een
    dode link, terwijl de pagina lokaal gewoon opent. Een kapotte orion.json
    wordt hier gemeld, een keer; de andere regels die het menu lezen, zien dan
    een leeg menu.

    Drie dingen meer, uit de bash-check van Microcontrollers en IR:

    - het pad is een kaal pad vanaf de root (geen ./, geen .., geen dubbele
      slash): de sync zoekt het doel op onder die naam;
    - een page is een .html; een PDF of zip is een file, en als page krijgt
      hij een topic dat de iframe niet kan tonen;
    - het doel zit in git, want OrionSync spiegelt alleen wat getrackt is. Een
      doel dat lokaal bestaat maar niet gecommit is, is in Orion een dood topic.
    """

    id = "orion-targets"
    legacy = ("DeN:2", "ICEES:2", "MC:2", "IR:2")

    def van_toepassing(self, ctx):
        return heeft_orion(ctx)

    def controleer(self, ctx):
        doelen, fout = orion_doelen(ctx)
        if fout:
            ctx.fout("orion.json", fout)
        getrackt = ctx.getrackt
        for soort, doel in doelen:
            kaal = "/".join(s for s in doel.split("/") if s not in ("", "."))
            if kaal != doel or ".." in doel.split("/"):
                ctx.fout("orion.json", f"{soort} is geen kaal pad vanaf de root: {doel}")
                continue
            if soort == "page" and not doel.endswith(".html"):
                ctx.fout("orion.json", f'page is geen html, gebruik "file": {doel}')
            pad = ctx.root / doel
            if pad.name.startswith("TODO-"):
                continue
            if not pad.is_file():
                ctx.fout("orion.json", f"{soort} bestaat niet: {doel}")
            elif not ctx.exacte_hoofdletters(pad):
                ctx.fout("orion.json",
                         f"hoofdletters kloppen niet, dit wordt een dode link in Orion: {doel}")
            elif getrackt is not None and doel not in getrackt:
                ctx.fout("orion.json", f"{soort} zit niet in git, dus de sync laadt het nooit "
                                       f"op: {doel}")


ID_RE = re.compile(r"^[a-z0-9-]+$")


def _ids(item, uit):
    if isinstance(item, dict):
        if "id" in item:
            uit.append(item["id"])
        for waarde in item.values():
            _ids(waarde, uit)
    elif isinstance(item, list):
        for kind in item:
            _ids(kind, uit)
    return uit


class OrionIds(Regel):
    """Elke id in orion.json is kebab (kleine letters, cijfers, streepjes) en uniek.

    De sync maakt voor elk item een topic of module en onthoudt het onder zijn
    id. Een id die twee keer voorkomt, laat twee items een record delen: het
    ene overschrijft het andere bij elke sync, en in Orion verdwijnt een topic
    zonder dat iets faalt. De vorm houdt de ids bruikbaar als sleutel en in een
    bestandsnaam (export_pdf.naam gebruikt {id}).
    """

    id = "orion-ids"
    legacy = ("MC:2", "IR:2")

    def van_toepassing(self, ctx):
        return heeft_orion(ctx)

    def controleer(self, ctx):
        try:
            doc = json.loads((ctx.root / "orion.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return  # orion-targets meldt een kapot bestand
        gezien = set()
        for rid in _ids(doc, []):
            if not isinstance(rid, str) or not ID_RE.match(rid):
                ctx.fout("orion.json", f"id '{rid}' mag alleen kleine letters, cijfers en "
                                       "streepjes bevatten")
            if rid in gezien:
                ctx.fout("orion.json", f"id '{rid}' komt twee keer voor")
            gezien.add(rid)


class OrionWees(Regel):
    """Elke sitepagina onder check.orphan_roots staat als page in orion.json.

    Het Orion-menu is de enige weg naar een pagina. Een pagina die er niet in
    staat, krijgt geen topic en is voor de student onvindbaar, terwijl ze in een
    browser gewoon opent. Er is geen navigatie van de site zelf die haar nog
    bereikbaar zou maken.

    Welke mappen meetellen, zegt check.orphan_roots. Een vak waar de theorie
    als losse syllabus-PDF bestaat, kijkt alleen naar Labo/; een vak waarvan elk
    bestand een topic is, geeft ".".
    """

    id = "orion-orphan"
    legacy = ("DeN:2", "ICEES:2", "MC:2", "IR:2")

    def van_toepassing(self, ctx):
        return heeft_orion(ctx)

    def controleer(self, ctx):
        doelen, _ = orion_doelen(ctx)
        # Alleen een page die er precies zo staat, dekt een pagina: een verkeerde
        # hoofdletter in orion.json maakt in Orion een dode link, en de pagina
        # zelf is dan even onvindbaar als wanneer ze er niet in stond.
        paginas = {os.path.normcase(str(ctx.root / d)) for soort, d in doelen
                   if soort == "page" and (ctx.root / d).is_file()
                   and ctx.exacte_hoofdletters(ctx.root / d)}
        wortels = [(ctx.root / w).resolve() for w in ctx.config["check"]["orphan_roots"]]
        paginas_gecontroleerd = set(ctx.paginas)
        for pagina in ctx.sitepaginas:
            if pagina not in paginas_gecontroleerd:
                continue
            if not any(w == pagina or w in pagina.parents for w in wortels):
                continue
            if os.path.normcase(str(pagina)) not in paginas:
                ctx.fout(pagina, "staat niet als page in orion.json, dus geen topic en "
                                 "onvindbaar in Orion")


ANKER_RE = re.compile(r"<a\s[^>]*>", re.I | re.S)
HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)
BLANK_RE = re.compile(r"""target\s*=\s*["']_blank["']""", re.I)


class TopicGrens(Regel):
    """Geen link die in de iframe een andere pagina opent.

    Elke page in orion.json is een eigen topic in Orion, met het menu ernaast.
    Dat menu verspringt niet mee met de iframe, dus een link die de iframe naar
    een andere pagina stuurt, laat het menu een topic aanwijzen dat de student
    niet leest: hij zit bij "Inleiding" en heeft de opdracht voor zich.

    Verwijzen naar een andere pagina mag dus, maar niet in de iframe. Ofwel laat
    je de link weg en noem je het topic bij naam ("staat bij Theorie"), ofwel
    open je hem met target="_blank", voor een pagina die de student nodig heeft
    terwijl hij bezig is, zoals de "Zie ..." in een Test jezelf. Dezelfde
    behandeling die een PDF al kreeg.

    De regel kijkt naar elke page in orion.json, en naar elke link van daar naar
    een andere HTML-pagina van de repo, ook naar een die zelf geen topic is.
    Wat in commentaar staat telt niet: het verslagcommentaar komt in een docx
    terecht, en een document heeft geen iframe om te verwisselen.
    """

    id = "topic-frame"
    legacy = ("DeN:10", "ICEES:10", "MC:9", "IR:9")

    def van_toepassing(self, ctx):
        return heeft_orion(ctx)

    def controleer(self, ctx):
        doelen, _ = orion_doelen(ctx)
        for pad in sorted({ctx.root / d for soort, d in doelen if soort == "page"}):
            if not pad.is_file():
                continue  # orion-targets meldt dat al
            tekst = COMMENTAAR_RE.sub("", ctx.tekst(pad))
            for anker in ANKER_RE.findall(tekst):
                m = HREF_RE.search(anker)
                if not m:
                    continue
                href = m.group(1)
                if href.startswith(("http", "#", "mailto:", "/", "tel:", "data:", "javascript:")):
                    continue
                doel = Path(os.path.normpath(
                    pad.parent / unquote(href.split("#")[0].split("?")[0])))
                if doel.suffix.lower() != ".html" or doel == pad or not doel.exists():
                    continue
                if BLANK_RE.search(anker):
                    continue
                ctx.fout(pad, f"linkt in de iframe naar {ctx._rel(doel)}, en elke pagina is "
                              "een eigen Orion-topic: laat de link weg of open hem met "
                              'target="_blank"')
