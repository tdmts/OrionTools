"""Assethygiene: wat een pagina insluit of aanbiedt, host het vak zelf."""

import re

from ..regel import Regel
from ._gedeeld import document_re


class BrightspaceHotlink(Regel):
    """Geen pad in de Brightspace-bestanden (/content/enforced/) in een pagina.

    Zo'n pad noemt de cursus, en die verandert elk academiejaar bij de Course
    Copy. Een relatieve link lost op in welke cursus de spiegel ook landt; een
    /content/enforced/-pad breekt het jaar erna.
    """

    id = "brightspace-hotlink"
    legacy = ("DeN:4", "ICEES:4")

    def controleer(self, ctx):
        for pad in ctx.html:
            if "/content/enforced/" in ctx.tekst(pad):
                ctx.fout(pad, "hotlinkt naar Brightspace (/content/enforced/), dat breekt elk jaar")


class ExterneAfbeelding(Regel):
    """Geen <img src="http..."> : een afbeelding staat in img/ van het vak zelf.

    Een gehotlinkte afbeelding verdwijnt zodra de andere server ze weghaalt of
    zijn URL's laat verlopen. Dat gebeurde met de schermafbeeldingen die naar
    het vorige leerplatform wezen, via URL's met een verlopende security_code.
    """

    id = "remote-image"
    legacy = ("DeN:4", "ICEES:4")

    def controleer(self, ctx):
        for pad in ctx.html:
            for m in re.finditer(r'<img[^>]+src="(https?://[^"]+)"', ctx.tekst(pad)):
                ctx.fout(pad, f"externe afbeelding, host ze zelf in img/: {m.group(1)}")


class ExternDocument(Regel):
    """Geen link naar een extern document: een datasheet of handleiding host het vak zelf.

    Een URL van een fabrikant sterft midden in het semester, net zoals een
    gehotlinkte afbeelding. Wat een document is, zegt de extensie (pdf, zip,
    doc(x), ppt(x), xls(x)), aangevuld met check.remote_document_exts_extra.
    """

    id = "remote-document"
    legacy = ("DeN:4", "ICEES:4")

    def controleer(self, ctx):
        doc = document_re(ctx)
        for pad in ctx.html:
            for m in re.finditer(r'href="(https?://[^"]+)"', ctx.tekst(pad)):
                if doc.search(m.group(1)):
                    ctx.fout(pad, f"externe documentlink, host ze zelf: {m.group(1)}")


class YoutubeReferrer(Regel):
    """Een YouTube-embed draagt een referrerpolicy.

    Zonder die policy weigert YouTube de embed in de iframe van Orion met
    error 153, en de student ziet een zwart vlak in plaats van de video.
    """

    id = "youtube-referrer"
    legacy = ("DeN:4", "ICEES:4")

    def controleer(self, ctx):
        for pad in ctx.html:
            for m in re.finditer(r"<iframe[^>]+youtube[^>]*>", ctx.tekst(pad), re.I):
                if "referrerpolicy" not in m.group(0):
                    ctx.fout(pad, "YouTube-embed zonder referrerpolicy (geeft error 153)")
