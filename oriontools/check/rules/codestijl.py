"""Hoe tekst en code op een pagina eruitzien."""

import re

from ..regel import Regel

OPERATOR_RE = re.compile(r"[A-Za-z0-9_\)\]](==|!=|<=|>=|&&|\|\||=(?!=))[A-Za-z0-9_\(\"']"
                         r"|[A-Za-z0-9_\)\]](?<![<>!=])=(?!=)[A-Za-z0-9_\(\"']")


class EmDash(Regel):
    """Geen em-dash in de tekst: gebruik een komma of een dubbele punt.

    De enige regel uit SCHRIJFSTIJL.md die de check afdwingt. Een em-dash is
    het vaste kenmerk van tekst die niemand herlezen heeft, en in het Nederlands
    hoort er bijna altijd een komma of een dubbele punt. Een melding per pagina
    volstaat: wie er een vindt, zoekt de rest zelf.
    """

    id = "em-dash"
    legacy = ("DeN:5", "ICEES:5")

    def controleer(self, ctx):
        for pad in ctx.html:
            if re.search(r"&mdash;|—", ctx.tekst(pad)):
                ctx.fout(pad, "em-dash in de tekst, gebruik een komma of een dubbele punt")


class CodeStijl(Regel):
    """Codestijl in een codeblok: Allman-accolades en spaties rond operatoren.

    Geen enkele compiler geeft erom, maar een eerstejaars die tegen een muur
    van tekens aankijkt, besteedt aan de syntaxis precies de aandacht die de
    les elders nodig had. Een openende accolade staat op haar eigen regel; een
    initialiser (= { ... }) is de uitzondering.

    Alleen de talen uit check.code_style_languages, op een
    <pre class="code-wrapper language-...">. Cisco IOS-configuratie en
    terminaluitvoer vallen er bewust buiten: die worden letterlijk overgenomen
    uit een toestel, en ze herformatteren is liegen over wat het toestel
    afdrukte.
    """

    id = "code-style"
    legacy = ("DeN:5", "ICEES:5")

    def van_toepassing(self, ctx):
        return True if ctx.config["check"]["code_style_languages"] else "geen code_style_languages"

    def controleer(self, ctx):
        talen = "|".join(re.escape(t) for t in ctx.config["check"]["code_style_languages"])
        blok_re = re.compile(
            r'<pre class="code-wrapper[^"]*language-(' + talen + r')[^"]*">(.*?)</pre>', re.S)
        for pad in ctx.html:
            for blok in blok_re.finditer(ctx.tekst(pad)):
                for nummer, regel in enumerate(blok.group(2).split("\n"), 1):
                    kaal = re.sub(r"//.*$", "", regel).rstrip()
                    if not kaal.strip():
                        continue
                    if kaal.endswith("{") and kaal.strip() != "{" and "=" not in kaal:
                        ctx.fout(pad, f"codeblok regel {nummer}: K&R-accolade, "
                                      f"zet '{{' op zijn eigen regel -> {kaal.strip()}")
                    if OPERATOR_RE.search(kaal):
                        ctx.fout(pad, f"codeblok regel {nummer}: zet spaties rond de operator "
                                      f"-> {kaal.strip()}")
