"""Hoe tekst en code op een pagina eruitzien."""

import re

from ..regel import Regel

OPERATOR_RE = re.compile(r"[A-Za-z0-9_\)\]](==|!=|<=|>=|&&|\|\||=(?!=))[A-Za-z0-9_\(\"']"
                         r"|[A-Za-z0-9_\)\]](?<![<>!=])=(?!=)[A-Za-z0-9_\(\"']")
# Uit de bash-check van Microcontrollers: een K&R-accolade ergens op de regel,
# ook na een ingeklapte body ("if (x) { doe(); }"). Een initialiser (= {) valt
# er nooit onder: daar staat geen ), else of do voor de accolade.
KR_RE = re.compile(r"\) ?\{|\belse ?\{|\bdo ?\{")


def codeblok_re(ctx):
    """Een <pre class="code-wrapper ... language-X ..."> van een taal uit code_style_languages.

    Groep 2 is de inhoud tot </pre>. Andere attributen na class mogen
    (data-start="15" op een blok dat verder telt).
    """
    talen = "|".join(re.escape(t) for t in ctx.config["check"]["code_style_languages"])
    return re.compile(r'<pre class="code-wrapper[^"]*language-(' + talen
                      + r')[^"]*"[^>]*>(.*?)</pre>', re.S)


def _ontsnap_niet(c):
    for ent, teken in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        c = c.replace(ent, teken)
    return c.replace("&amp;", "&")


def krappe_operatoren(regel):
    """Welke operatoren zonder spaties staan, volgens de awk van Microcontrollers.

    Vier dingen op een pagina lijken precies op een overtreding: een attribuut
    (width=device-width), een YouTube-URL (?wmode=opaque), inline <code>i=9</code>
    in proza, en vooral de Nederlandse decimale komma ("0,17 Hz"). Een naieve
    grep gaf 151 meldingen, bijna allemaal vals. Twee filters gaven er samen
    nul over de hele repo:

    1. geen ruwe HTML-tag op de regel: code in een <pre> ontsnapt zijn "<" als
       "&lt;", dus een ruwe tag is proza (of het </code> van de laatste regel);
    2. de regel eindigt op ;{}(), zodra het //-commentaar weg is: proza eindigt
       op een punt of een woord, code op een puntkomma of een haakje.

    #include <Wire.h> is vrijgesteld. Strings en chars worden eerst leeggemaakt,
    want een komma of = in een literal is data, en dat gebeurt voor het
    commentaar eraf gaat, zodat "http://" in een string zijn regel houdt.
    -> << >> worden nooit gespatieerd.

    Bewust niet: * / % + - & |. "char* p", "-1", "i++", "&buffer" en "1 << 3"
    zijn terecht krap, en bij een blokkerende regel is een valse melding erger
    dan een gemiste.
    """
    regel = re.sub(r"^\s*<code>", "", regel)
    if re.search(r"<[a-zA-Z/!]", regel) or re.match(r"^\s*#\s*include", regel):
        return []
    c = _ontsnap_niet(regel)
    c = re.sub(r'"[^"]*"', '""', c)
    c = re.sub(r"'[^']*'", "''", c)
    c = re.sub(r"\s*//.*$", "", c).rstrip()
    if not re.search(r"[;{}(),]$", c):
        return []
    c = re.sub(r"->|<<|>>", "@@", c)
    slecht = []
    if (re.search(r"[A-Za-z0-9_)\]]=[^=]", c)
            or re.search(r"(^|[^=!<>+*/%&|^-])=[A-Za-z0-9_(\"'-]", c)):
        slecht.append("=")
    if (re.search(r"[A-Za-z0-9_)\]](==|!=|<=|>=|<|>)", c)
            or re.search(r"(==|!=|<=|>=|<|>)[A-Za-z0-9_(]", c)):
        slecht.append("vergelijking")
    if re.search(r"[A-Za-z0-9_)\]](&&|\|\|)", c) or re.search(r"(&&|\|\|)[A-Za-z0-9_(!]", c):
        slecht.append("&&/||")
    if re.search(r";[A-Za-z0-9_]", c):
        slecht.append(";")
    if re.search(r",[A-Za-z0-9_(\"'{-]", c):
        slecht.append(",")
    if re.search(r"(^|[^A-Za-z0-9_.])(if|for|while|switch)\(", c):
        slecht.append("sleutelwoord(")
    return slecht


def kr_accolade(kaal):
    """Een openende accolade die niet op haar eigen regel staat (kaal: zonder //-commentaar)."""
    return ((kaal.endswith("{") and kaal.strip() != "{" and "=" not in kaal)
            or bool(KR_RE.search(kaal)))


class EmDash(Regel):
    """Geen em-dash in de tekst: gebruik een komma of een dubbele punt.

    De enige regel uit SCHRIJFSTIJL.md die de check afdwingt. Een em-dash is
    het vaste kenmerk van tekst die niemand herlezen heeft, en in het Nederlands
    hoort er bijna altijd een komma of een dubbele punt. Een melding per pagina
    volstaat: wie er een vindt, zoekt de rest zelf. --fix maakt er een komma
    van, de vervanging die in het Nederlands altijd leest; een dubbele punt of
    "en"/"maar" leest soms beter, en daarom is de diff er om na te lezen.

    Ook op een pagina uit check.skip_pages: de codevoorbeelden en de tekst van
    een stijlgids zetten de huisstijl voor alles wat eruit gekopieerd wordt.
    """

    id = "em-dash"
    legacy = ("DeN:5", "ICEES:5", "MC:5", "IR:5")

    def controleer(self, ctx):
        for pad in ctx.html:
            if re.search(r"&mdash;|—", ctx.tekst(pad)):
                ctx.fout(pad, "em-dash in de tekst, gebruik een komma of een dubbele punt")


class CodeStijl(Regel):
    """Codestijl in een codeblok: Allman-accolades en spaties rond operatoren.

    Geen enkele compiler geeft erom, maar een eerstejaars die tegen een muur
    van tekens aankijkt, besteedt aan de syntaxis precies de aandacht die de
    les elders nodig had: "int macht=1;" en "for(byte i=0;i<10;i++)" zijn
    dezelfde bytes als de gespatieerde vorm.

    Een openende accolade staat op haar eigen regel. Twee vangsten, samengevoegd
    uit DeN en Microcontrollers: een regel die op { eindigt (behalve een
    initialiser met =), en een ) { / else { / do { ergens op de regel, ook na
    een ingeklapte body.

    Spaties rond operatoren: de set van DeN (= == != <= >= && ||) op elke
    regel, en de set van Microcontrollers (ook < en >, een ; of , zonder spatie
    erna, if/for/while/switch zonder spatie voor de haak) met haar twee
    filters, zie krappe_operatoren.

    Alleen de talen uit check.code_style_languages, op een
    <pre class="code-wrapper language-...">. Microcontrollers keek elke regel
    van het bestand na, ook inline <script>; hier alleen het codeblok. Cisco
    IOS-configuratie en terminaluitvoer vallen er bewust buiten: die worden
    letterlijk overgenomen uit een toestel, en ze herformatteren is liegen over
    wat het toestel afdrukte. --fix herstelt een accolade die de regel afsluit
    en de spaties; een ingeklapte body vraagt een mens die beslist waar de
    regels breken.
    """

    id = "code-style"
    legacy = ("DeN:5", "ICEES:5", "MC:5")

    def van_toepassing(self, ctx):
        return True if ctx.config["check"]["code_style_languages"] else "geen code_style_languages"

    def controleer(self, ctx):
        blok_re = codeblok_re(ctx)
        for pad in ctx.html:
            tekst = ctx.tekst(pad)
            for blok in blok_re.finditer(tekst):
                eerste = tekst.count("\n", 0, blok.start(2))
                for nummer, regel in enumerate(blok.group(2).split("\n"), 1):
                    kaal = re.sub(r"//.*$", "", regel).rstrip()
                    if not kaal.strip():
                        continue
                    if kr_accolade(kaal):
                        ctx.fout(pad, f"codeblok regel {nummer}: K&R-accolade, "
                                      f"zet '{{' op zijn eigen regel -> {kaal.strip()}",
                                 regelnr=eerste + nummer)
                    krap = krappe_operatoren(regel)
                    if OPERATOR_RE.search(kaal) or krap:
                        welke = f" ({' '.join(krap)})" if krap else ""
                        ctx.fout(pad, f"codeblok regel {nummer}: zet spaties rond de operator"
                                      f"{welke} -> {kaal.strip()}", regelnr=eerste + nummer)
