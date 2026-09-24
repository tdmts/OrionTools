"""Links en assets: bestaan ze, met exact die hoofdletters, en zitten ze in git."""

import re

from ..regel import Regel
from ._gedeeld import lokaal_doel

URL_RE = re.compile(r'(?:href|src)\s*=\s*"([^"]+)"')


class Links(Regel):
    """Elke relatieve href en src bestaat, met exact dezelfde hoofdletters, en zit in git.

    Een webserver is hoofdlettergevoelig en serveert alleen wat er staat, en
    OrionSync spiegelt alleen wat gecommit is. Een tikfout in de hoofdletters of
    een niet-toegevoegde afbeelding werkt dus lokaal, op een Windows- of
    macOS-schijf die geen onderscheid maakt, en geeft 404 zodra de bestanden op
    de server staan.

    Het doelpad wordt bewust niet met Path.resolve() bepaald: dat verbetert de
    hoofdletters stil naar wat er op schijf staat, en dan test de regel niets
    meer. Elk segment wordt vergeleken met de echte inhoud van zijn map.

    Een asset met de naam TODO-* is een waarschuwing en geen fout: dat is
    tekenwerk dat gepland is maar nog niet getekend.

    Ze kijkt naar elke html in de repo, ook naar een deck en een pagina die
    geen sitepagina is: een link of afbeelding die niet bestaat, drukt in een
    handout als een leeg vlak.
    """

    id = "links"
    legacy = ("DeN:1", "ICEES:1")

    def controleer(self, ctx):
        getrackt = ctx.getrackt
        if getrackt is None:
            ctx.waarschuw(".", "git niet beschikbaar, de controle op getrackte bestanden "
                               "is overgeslagen")
        for pad in ctx.html:
            for m in URL_RE.finditer(ctx.tekst(pad)):
                url = m.group(1)
                if url.startswith(("http://", "https://", "#", "mailto:", "data:")):
                    continue
                doel = lokaal_doel(pad, url)
                if doel is None:
                    continue
                if doel.name.startswith("TODO-"):
                    ctx.waarschuw(pad, f"nog te maken asset: {url}")
                    continue
                if not doel.exists():
                    ctx.fout(pad, f"link wijst nergens heen: {url}")
                    continue
                if not ctx.exacte_hoofdletters(doel):
                    ctx.fout(pad, f"hoofdletters kloppen niet, dit geeft 404 op de server: {url}")
                    continue
                if getrackt is not None:
                    try:
                        rel = doel.relative_to(ctx.root).as_posix()
                    except ValueError:
                        continue
                    if rel not in getrackt:
                        ctx.fout(pad, f"nog niet in git, dus niet gespiegeld: {url}")
