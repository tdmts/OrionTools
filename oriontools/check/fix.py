"""check --fix: herstel eerst de mechanische fouten, en rapporteer dan de rest.

Alleen wat precies een juist antwoord heeft: een em-dash, een K&R-accolade die
de regel afsluit, de spaties rond een operator, een ontbrekende
referrerpolicy, een solution-reveal.js die niets meer te tonen heeft, en een
asset die bestaat maar nooit gestaged werd. Wat woorden vraagt (een menutitel)
of een beslissing (waar in orion.json een weespagina hoort, hoe een gedownloade
afbeelding moet heten), blijft voor het rapport erna.

Het wil een schone tree, zodat "git diff" precies toont wat het veranderde;
--force gaat er toch door. Een ongetrackt bestand telt niet als vuil: dat
stagen is net een van de herstellingen. Nooit vanuit de hook: dat zou bij het
afsluiten van een sessie bestanden herschrijven zonder dat iemand de diff ziet.

Overgenomen van do_fix in de bash-check van Microcontrollers en IR, met een
verschil: de accolades en de operatoren worden alleen binnen een codeblok van
check.code_style_languages hersteld, dezelfde grens die code-style trekt. De
bash-versie herschreef elke regel van elk bestand die door haar filters kwam,
inline <script> inbegrepen.
"""

import re
import subprocess
import sys

from .rules._gedeeld import lokaal_doel, orion_doelen
from .rules.codestijl import codeblok_re
from .rules.links import URL_RE

EMDASH_RE = re.compile(r"[ \t]*(?:&mdash;|—)[ \t]*")
KR_EINDE_RE = re.compile(r"(\)|\belse\b|\bdo\b)[ \t]*\{[ \t]*\r?$")
KR_SPLITS_RE = re.compile(r"^([ \t]*)(\S.*?)[ \t]*\{[ \t]*(\r?)$")
PRE_PREFIX_RE = re.compile(r'^(\s*<pre class="code-wrapper[^>]*>(?:<code>)?)')
YOUTUBE_RE = re.compile(r"youtube(?:-nocookie)?\.com/embed")
POLICY = 'referrerpolicy="strict-origin-when-cross-origin"'
REVEAL_INCLUDE_RE = re.compile(r'^\s*<script src="[^"]*solution-reveal\.js"></script>\s*\r?$')


def _git(ctx, *args):
    return subprocess.run(["git", *args], cwd=ctx.root, capture_output=True, text=True,
                          encoding="utf-8")


def spatieer(regel):
    """De operatorspaties van een regel zonder regeleinde (de perl van Microcontrollers).

    Het herhaalt de twee filters van de check (geen ruwe tag, eindigt op
    ;{}(),) en werkt dan op een gedecodeerde kopie: de entiteiten worden weer
    < > en &, de operatoren die nooit gespatieerd worden (-> << >>) en de
    tweetekenoperatoren (== != <= >= && ||) worden geparkeerd onder
    schildwachtbytes zodat de regel voor een losse = ze niet splitst, en alles
    wordt achteraf opnieuw gecodeerd, & eerst. Alleen een entiteit die de regel
    al had, komt terug: anders wordt een ruwe < in een inline <script> een
    syntaxfout.

    Twee dingen blijven er helemaal buiten, want allebei proza: een string
    (geparkeerd onder \\x01) en het //-commentaar achteraan, zodat "// a,b,c"
    in een segmenttabel niet uit elkaar getrokken wordt. Samengestelde
    toekenningen (+= -= ...) blijven onaangeroerd.
    """
    m = PRE_PREFIX_RE.match(regel)
    prefix = m.group(1) if m else ""
    rest = regel[len(prefix):]
    if re.search(r"<[a-zA-Z/!]", rest) or re.match(r"^\s*#\s*include", rest):
        return regel
    m = re.match(r"^(.*?)(\s*//.*)$", rest, re.S)
    code, commentaar = (m.group(1), m.group(2)) if m else (rest, "")
    if not re.search(r"[;{}(),]$", code.rstrip()):
        return regel
    strings = []

    def parkeer(m):
        strings.append(m.group(1))
        return f"\x01{len(strings) - 1}\x01"

    code = re.sub(r'("(?:[^"\\]|\\.)*")', parkeer, code)
    had_lt, had_gt, had_amp = "&lt;" in code, "&gt;" in code, "&amp;" in code
    code = code.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    code = code.replace("->", "\x02").replace("<<", "\x03").replace(">>", "\x04")
    code = re.sub(r"([+\-*/%&|^])=", "\\1\x12", code)
    for op, teken in (("==", "\x05"), ("!=", "\x06"), ("<=", "\x0e"), (">=", "\x0f"),
                      ("&&", "\x10"), ("||", "\x11")):
        code = code.replace(op, teken)
    code = re.sub(r"([A-Za-z0-9_)\]\x01])=", r"\1 =", code)
    code = re.sub(r"=([A-Za-z0-9_(\x01!~+-])", r"= \1", code)
    code = re.sub(r"([A-Za-z0-9_)\]\x01])([<>\x05\x06\x0e\x0f\x10\x11])", r"\1 \2", code)
    code = re.sub(r"([<>\x05\x06\x0e\x0f\x10\x11])([A-Za-z0-9_(\x01!~-])", r"\1 \2", code)
    code = re.sub(r";([A-Za-z0-9_(\x01])", r"; \1", code)
    code = re.sub(r",([A-Za-z0-9_({\x01!~-])", r", \1", code)
    code = re.sub(r"\b(if|for|while|switch)\(", r"\1 (", code)
    for teken, op in (("\x12", "="), ("\x11", "||"), ("\x10", "&&"), ("\x0f", ">="),
                      ("\x0e", "<="), ("\x06", "!="), ("\x05", "=="), ("\x04", ">>"),
                      ("\x03", "<<"), ("\x02", "->")):
        code = code.replace(teken, op)
    if had_amp:
        code = code.replace("&", "&amp;")
    if had_lt:
        code = code.replace("<", "&lt;")
    if had_gt:
        code = code.replace(">", "&gt;")
    code = re.sub(r"\x01(\d+)\x01", lambda m: strings[int(m.group(1))], code)
    return prefix + code + commentaar


def _coderegels(ctx, tekst):
    """De indexen (0-gebaseerd) van de bestandsregels die in een codeblok liggen."""
    uit = set()
    for blok in codeblok_re(ctx).finditer(tekst):
        begin = tekst.count("\n", 0, blok.start())
        einde = tekst.count("\n", 0, blok.end())
        uit.update(range(begin, einde + 1))
    return uit


def _herstel_pagina(ctx, pad, meld):
    oud = pad.read_text(encoding="utf-8", newline="")
    tekst = oud

    nieuw = EMDASH_RE.sub(", ", tekst)
    if nieuw != tekst:
        meld(pad, "em-dash -> komma")
        tekst = nieuw

    regels = tekst.split("\n")
    code = _coderegels(ctx, tekst) if ctx.config["check"]["code_style_languages"] else set()
    accolade = operator = youtube = False
    uit = []
    for i, regel in enumerate(regels):
        if i in code:
            if KR_EINDE_RE.search(regel):
                gesplitst = KR_SPLITS_RE.sub(r"\1\2\3\n\1{\3", regel)
                accolade |= gesplitst != regel
                delen = gesplitst.split("\n")
            else:
                delen = [regel]
            for j, deel in enumerate(delen):
                cr = "\r" if deel.endswith("\r") else ""
                romp = deel[:-1] if cr else deel
                gespatieerd = spatieer(romp) + cr
                operator |= gespatieerd != deel
                delen[j] = gespatieerd
            regel = "\n".join(delen)
        if YOUTUBE_RE.search(regel) and "referrerpolicy" not in regel:
            nieuw, n = re.subn(r"\s*allowfullscreen", f" {POLICY} allowfullscreen", regel,
                               count=1)
            if not n:
                nieuw = regel.replace("></iframe>", f" {POLICY}></iframe>", 1)
            youtube |= nieuw != regel
            regel = nieuw
        uit.append(regel)
    if accolade:
        meld(pad, "Allman-accolades")
    if operator:
        meld(pad, "operatorspaties")
    if youtube:
        meld(pad, "referrerpolicy op een YouTube-embed")
    tekst = "\n".join(uit)

    # Een solution-reveal.js zonder solution-container: een losse <script>-regel,
    # dus precies een juist herstel.
    if "solution-reveal.js" in tekst and not re.search(r'class="[^"]*solution-container', tekst):
        regels = tekst.split("\n")
        over = [r for r in regels if not REVEAL_INCLUDE_RE.match(r)]
        if len(over) != len(regels):
            meld(pad, "ongebruikte solution-reveal.js-include weggehaald")
            tekst = "\n".join(over)

    if tekst != oud:
        pad.write_text(tekst, encoding="utf-8", newline="")


def _te_stagen(ctx):
    """Wat een pagina of orion.json aanwijst, op schijf staat en niet in git zit."""
    # Ook niet wat met andere hoofdletters getrackt is: dat is een fout in de
    # link (links meldt hem), geen bestand dat nog gestaged moet worden.
    getrackt = {g.lower() for g in ctx.getrackt or ()}
    uit = []

    def overweeg(doel):
        try:
            rel = doel.relative_to(ctx.root).as_posix()
        except ValueError:
            return
        if doel.is_file() and rel.lower() not in getrackt and rel not in uit:
            uit.append(rel)

    for pad in ctx.paginas:
        for m in URL_RE.finditer(ctx.tekst(pad)):
            url = m.group(1)
            if url.startswith(("http://", "https://", "//", "/", "#", "mailto:", "tel:",
                               "data:", "javascript:")):
                continue
            doel = lokaal_doel(pad, url)
            if doel is not None and not doel.name.startswith("TODO-"):
                overweeg(doel)
    if (ctx.root / "orion.json").is_file():
        for _, doel in orion_doelen(ctx)[0]:
            overweeg(ctx.root / doel)
    return uit


def herstel(ctx, force=False):
    """Herstel de mechanische fouten in ctx.root; 0, of 2 bij een vuile tree."""
    heeft_git = ctx.getrackt is not None
    if heeft_git and not force:
        status = _git(ctx, "status", "--porcelain", "--untracked-files=no").stdout
        if status.strip():
            print("check --fix herschrijft bestanden en wil een schone tree, zodat 'git diff' "
                  "leesbaar blijft.\nCommit of stash eerst, of gebruik --force.", file=sys.stderr)
            return 2

    hersteld = []

    def meld(pad, wat):
        hersteld.append(f"{ctx._rel(pad)}: {wat}")

    for pad in ctx.paginas:
        _herstel_pagina(ctx, pad, meld)

    if heeft_git:
        stage = _te_stagen(ctx)
        if stage and _git(ctx, "add", "--", *stage).returncode == 0:
            hersteld += [f"{rel}: gestaged (was niet getrackt)" for rel in stage]

    if hersteld:
        print("Automatisch hersteld (nalezen met git diff):")
        for regel in hersteld:
            print(f"  {regel}")
        print()
    return 0
