"""Assethygiene: wat een pagina insluit of aanbiedt, host het vak zelf."""

import re

from ..context import ORION_CSS, ORION_JS
from ..regel import Regel
from ._gedeeld import document_re


class BrightspaceHotlink(Regel):
    """Geen pad in de Brightspace-bestanden (/content/enforced/) in een pagina.

    Zo'n pad noemt de cursus, en die verandert elk academiejaar bij de Course
    Copy. Een relatieve link lost op in welke cursus de spiegel ook landt; een
    /content/enforced/-pad breekt het jaar erna. Ook zonder de slash ervoor:
    een ingeplakte URL als https://orion.hogent.be/content/enforced/... breekt
    op dezelfde manier.
    """

    id = "brightspace-hotlink"
    legacy = ("DeN:4", "ICEES:4", "MC:4", "IR:4")

    def controleer(self, ctx):
        for pad in ctx.paginas:
            if "content/enforced" in ctx.tekst(pad):
                ctx.fout(pad, "hotlinkt naar Brightspace (/content/enforced/), dat breekt elk jaar")


class ExterneAfbeelding(Regel):
    """Geen <img src="http..."> : een afbeelding staat in img/ van het vak zelf.

    Een gehotlinkte afbeelding verdwijnt zodra de andere server ze weghaalt of
    zijn URL's laat verlopen. Dat gebeurde met de schermafbeeldingen die naar
    het vorige leerplatform wezen, via URL's met een verlopende security_code.
    """

    id = "remote-image"
    legacy = ("DeN:4", "ICEES:4", "MC:4", "IR:4")

    def controleer(self, ctx):
        for pad in ctx.paginas:
            for m in re.finditer(r'<img[^>]+src="(https?://[^"]+)"', ctx.tekst(pad)):
                ctx.fout(pad, f"externe afbeelding, host ze zelf in img/: {m.group(1)}")


class ExternDocument(Regel):
    """Geen link naar een extern document: een datasheet of handleiding host het vak zelf.

    Een URL van een fabrikant sterft midden in het semester, net zoals een
    gehotlinkte afbeelding. Wat een document is, zegt de extensie (pdf, zip,
    doc(x), ppt(x), xls(x)), aangevuld met check.remote_document_exts_extra.
    """

    id = "remote-document"
    legacy = ("DeN:4", "ICEES:4", "MC:4", "IR:4")

    def controleer(self, ctx):
        doc = document_re(ctx)
        for pad in ctx.paginas:
            for m in re.finditer(r'href="(https?://[^"]+)"', ctx.tekst(pad)):
                if doc.search(m.group(1)):
                    ctx.fout(pad, f"externe documentlink, host ze zelf: {m.group(1)}")


class YoutubeReferrer(Regel):
    """Een YouTube-embed draagt een referrerpolicy.

    Zonder die policy weigert YouTube de embed in de iframe van Orion met
    error 153, en de student ziet een zwart vlak in plaats van de video.
    """

    id = "youtube-referrer"
    legacy = ("DeN:4", "ICEES:4", "MC:4", "IR:4")

    def controleer(self, ctx):
        for pad in ctx.paginas:
            for m in re.finditer(r"<iframe[^>]+youtube[^>]*>", ctx.tekst(pad), re.I):
                if "referrerpolicy" not in m.group(0):
                    ctx.fout(pad, "YouTube-embed zonder referrerpolicy (geeft error 153)")


class ChamiloLink(Regel):
    """Geen src of href naar Chamilo, het platform van voor Brightspace.

    Chamilo verdwijnt, en een link ernaar breekt dan mee. De
    DocumentDownloader-URL's antwoordden in september 2026 nog (met & in plaats
    van &amp;), dus zolang dat kan: het bestand downloaden en zelf hosten.
    Toegevoegd in IR; elk vak komt uit dezelfde Brightspace-export, en wat
    daarin nog naar Chamilo wijst, is een lek van dezelfde soort.
    """

    id = "chamilo-link"
    legacy = ("IR:4",)

    def controleer(self, ctx):
        for pad in ctx.paginas:
            for m in re.finditer(r'(?:src|href)="(https?://chamilo[^"]*)"', ctx.tekst(pad)):
                ctx.fout(pad, "Chamilo-link: download het bestand (de URL werkt nog, met & "
                              f"in plaats van &amp;) en host het zelf: {m.group(1)}")


STIJLBLAD_RE = re.compile(r'<link[^>]+rel="stylesheet"[^>]*>', re.I)
SCRIPT_RE = re.compile(r'<script[^>]+src="([^"]*)"', re.I)
HREF_RE = re.compile(r'href="([^"]*)"', re.I)


class VreemdeAssets(Regel):
    """Een sitepagina laadt OrionCSS en de eigen scripts van de repo, en niets anders.

    De Brightspace-export sleept de oude HOGENT-template mee: zijn stylesheet
    onder /shared/HTML-Template-Library, Bootstrap 3 en jQuery van een CDN,
    Brightspace's eigen fonts.css. OrionCSS brengt zelf Bootstrap 5 mee, dus
    een tweede Bootstrap vecht ermee, en /shared/... is een adres van het
    platform en niet van de cursus.

    Vreemd is een stylesheet of script op een absolute URL (http(s)://, // of
    /) die niet de gehoste OrionCSS is. Een relatief pad is een bestand van de
    repo zelf, en of dat bestaat en in git zit, kijkt links na. Het IR-origineel
    liet alleen ../ en ./ door en ving zo ook een los "script.js" naast de
    pagina; dat was geen vreemde asset maar een toevallige vorm van het patroon.

    Alleen sitepagina's: een deck laadt hoorcollege.css en geen style.css, en een
    pagina uit exempt_pages (pasteInOrion.html) is geen pagina van de cursus.
    """

    id = "foreign-assets"
    legacy = ("IR:3",)

    def controleer(self, ctx):
        skip = set(ctx.paginas)
        for pad in ctx.sitepaginas:
            if pad not in skip:
                continue
            tekst = ctx.tekst(pad)
            urls = [m.group(1) for m in SCRIPT_RE.finditer(tekst)]
            for tag in STIJLBLAD_RE.findall(tekst):
                m = HREF_RE.search(tag)
                if m:
                    urls.append(m.group(1))
            for url in urls:
                if url in (ORION_CSS, ORION_JS):
                    continue
                if url.startswith(("http://", "https://", "//", "/")):
                    ctx.fout(pad, f"laadt iets anders dan OrionCSS en de eigen scripts: {url}")
