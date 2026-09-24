"""De huisstijl (--audit): adviserend, zonder invloed op de exitcode.

Huisafspraken en geen breuk: een pagina die hier opduikt, werkt perfect, ze
ziet er alleen niet uit als haar buren. Adviserend met opzet, dus nooit rood in
CI en nooit een collega geblokkeerd over een stijlkeuze. Je draait het als je
wil opruimen, niet bij elke push.

Een audit kijkt naar ctx.auditpaginas: de sitepagina's die git trackt, dus
niet pasteInOrion.html, geen deck en geen ongetrackt klad.

Een pagina kan vastleggen dat een afwijking bewust is:

    <!-- audit-skip: oplossing -->
    <!-- audit-skip: lead, figure -->

De naam is de regel-id zonder "audit-". De afwijking is dan geen bevinding
meer, zodat de beslissing in het bestand staat dat afwijkt en de audit naar
nul kan. Een audit die niemand stil kan krijgen, leest niemand.

De woordenlijsten hieronder zijn de gedeelde standaard; een vak vult ze aan
met check.audit.*_extra in oriontools.json. Ze komen uit SCHRIJFSTIJL.md, uit
de vier van zijn patronen die een grep kan zien (9, 11/12 en 13). De andere
(een slotzin met pointe, een retorische drieslag) vragen een lezer, en precies
daarom zijn deze vier adviserend: een stijlronde die op het mechanische derde
blokkeert, gaf de rest een gezag dat ze nooit verdiend heeft.
"""

import re
from fnmatch import fnmatch

from ..regel import REGISTER, Regel

SKIP_RE = re.compile(r"<!--\s*audit-skip:([^>]*?)-->")

# Patroon 9: de lead kondigt zichzelf aan met een vaste formule. Een enkele is
# prima; het verraad is dat ze allemaal dezelfde zijn, zodat elke lead de
# volgende aankondigt. Bewust smal: "Hier lees je" wel, "In deze oefening bouw
# je" niet, want dat beschrijft de taak in plaats van de pagina aan te kondigen.
# De we-vormen kwamen er in de stijlronde van labo 0 bij.
STOCK_LEAD = ["Hier lees je", "Hier zie je", "Hier ontdek je", "Hieronder lees je",
              "Hieronder zie je", "Op deze pagina (lees|zie|ontdek|vind|leer) je",
              "Op deze pagina (behandelen|bespreken) we", "In dit artikel"]

# Patroon 11 (12 in ICEES en IR): een verkleinwoord dat een onderdeel
# opsmukt. Een expliciete lijst en geen -je/-tje-regex: die raakt ook
# "haakjes", "netjes", "eventjes", "oranje" en "vrije", en kan een versiering
# niet onderscheiden van de vaste term voor een onderdeel ("pootjes",
# "rekstrookje", "ezelsbruggetje" staan er bewust niet in). De lijst mag
# groeien, maar krijgt nooit een technische term. Meet de tekst van het vak
# voor je aanvult.
DIMINUTIVES = ["eentje", "blokjes?", "draadjes?", "schermpje", "lampje", "knopje", "regeltje",
               "woordje", "zinnetje", "lettertje", "motortje", "rommeltje", "duwtje", "trucje",
               "lijstjes?", "stukjes?", "stapjes?"]

# Patroon 12: Noord-Nederlandse woordkeuze in een cursus voor Vlaamse
# studenten. "best" ("neem best een weerstand") is Belgisch Nederlands en
# "hoor" is ook het werkwoord ("hoor je dat"): gemeten en bewust weggelaten. De
# lijst vraagt ook nooit om een belgicisme ("vijs", "kuisen"). "kunt" en "wilt"
# staan los, want het onderwerp staat niet altijd naast het werkwoord ("een
# waarde die je in je programma kunt gebruiken"); "kunt u" en "wilt u" laat ze
# aan audit-u-vorm.
NOORD_NL = ["[Kk]un je", "kunt", "wilt", "flinke?", "prima", "eventjes", "hartstikke", "gaaf",
            "nou ja"]

# Patroon 13: een bijwoord dat niets toevoegt. Smal met opzet: "gewoon" en
# "letterlijk" betekenen meestal iets, "eigenlijk" is vaak het bijvoeglijk
# naamwoord of een echte vraag aan de student. De \b aan beide kanten houdt
# "natuurlijke" erbuiten.
FILLERS = ["netjes", "heel even", "uiteraard", "natuurlijk"]

U_VORM_RE = re.compile(r"\b([Uu]w|[Uu] (kunt|kan|moet|hebt|zult|krijgt|ziet|maakt))\b")
LED_RE = re.compile(r"\bLEDs?\b")
PROZA_LED = ("<p", "<li", "<td", "<th", "<h1", "<h2", "<h3", "<title>", "<caption>",
             "<figcaption", 'alt="', '"title":')
PROZA_ID = ("<p>", "<p ", "<li", "<td", "<th", "<h1", "<h2", "<h3", "<title>", "<caption>",
            "<figcaption", 'alt="')


def _audit(ctx):
    return ctx.config["check"]["audit"]


def skips(ctx, pad):
    """De audit-skip-namen van een pagina, een keer gelezen."""
    cache = ctx.__dict__.setdefault("_audit_skips", {})
    if pad not in cache:
        namen = set()
        for m in SKIP_RE.finditer(ctx.tekst(pad)):
            namen.update(m.group(1).replace(",", " ").split())
        cache[pad] = namen
    return cache[pad]


class AuditRegel(Regel):
    modus = "audit"
    legacy = ("MC:audit", "IR:audit")

    @property
    def skip(self):
        return self.id.removeprefix("audit-")

    def overgeslagen(self, ctx, pad):
        return self.skip in skips(ctx, pad)


def _woordregel(ctx, regel, lijst, extra_sleutel, boodschap):
    woorden = lijst + _audit(ctx)[extra_sleutel]
    patroon = re.compile(r"\b(" + "|".join(woorden) + r")\b")
    for pad in ctx.auditpaginas:
        if regel.overgeslagen(ctx, pad):
            continue
        for woord in sorted(set(m.group(0) for m in patroon.finditer(ctx.tekst(pad)))):
            ctx.waarschuw(pad, boodschap.format(woord))


class AuditSkip(AuditRegel):
    """Een audit-skip noemt een regel die bestaat, en blijft zichtbaar.

    Een tikfout in een audit-skip zet stil niets uit, en dat is precies het
    soort stille no-op waartegen de hele check bestaat. Een geldige skip wordt
    niet als bevinding gemeld maar wel opgesomd, als afwijking: wat een pagina
    bewust anders doet, moet bij elke audit nog eens langs de lezer komen.
    """

    id = "audit-skip"

    def controleer(self, ctx):
        geldig = {cls.id.removeprefix("audit-") for cls in REGISTER.values()
                  if cls.modus == "audit" and cls.id != self.id}
        for pad in ctx.auditpaginas:
            for naam in sorted(skips(ctx, pad)):
                if naam in geldig:
                    ctx.meld(pad, f"audit-skip: {naam}", "afwijking")
                else:
                    ctx.waarschuw(pad, f"onbekende audit-skip '{naam}' (geldig: "
                                       f"{' '.join(sorted(geldig))})")


class AuditCodeKlasse(AuditRegel):
    """Elk codeblok draagt een highlight.js-taal, regelnummers en de taalbadge.

    Zo leest een blok hetzelfde op een theoriepagina en in een oplossing.
    Welke talen mogen, zegt check.audit.code_languages (Microcontrollers: alleen
    cpp; leeg is elke language-*). Een taal uit check.audit.code_no_badge
    draagt geen show-language: RAPID heeft geen highlight.js-grammatica, en een
    onbekende language-* laat highlight.js struikelen, waarna geen enkel later
    blok op de pagina nog kleurt. Dus is RAPID language-plaintext, en de badge
    zou dan "plaintext" zeggen.
    """

    id = "audit-code-class"

    def controleer(self, ctx):
        talen = _audit(ctx)["code_languages"]
        zonder_badge = set(_audit(ctx)["code_no_badge"])
        for pad in ctx.auditpaginas:
            if self.overgeslagen(ctx, pad):
                continue
            for m in re.finditer(r'class="(code-wrapper[^"]*)"', ctx.tekst(pad)):
                cls = m.group(1)
                taal = re.search(r"\blanguage-(\S+)", cls)
                if talen and not (taal and taal.group(1) in talen):
                    ctx.waarschuw(pad, f"codeblok is '{cls}' (huisstijl: "
                                       f"{', '.join('language-' + t for t in talen)})")
                    continue
                if not taal:
                    ctx.waarschuw(pad, f"codeblok '{cls}' heeft geen language-*")
                    continue
                if "linenumbers" not in cls:
                    ctx.waarschuw(pad, "codeblok zonder linenumbers")
                if taal.group(1) in zonder_badge:
                    if "show-language" in cls:
                        ctx.waarschuw(pad, f"{taal.group(1)}-blok met show-language (de badge "
                                           f"zou {taal.group(1)} zeggen)")
                elif "show-language" not in cls:
                    ctx.waarschuw(pad, "codeblok zonder show-language")


class AuditLeadOpener(AuditRegel):
    """De lead opent niet op een vaste formule ("Hier lees je"). SCHRIJFSTIJL.md patroon 9.

    Gezocht over de hele regel van de lead en niet alleen de eerste tekst: de
    formule staat vaak in de laatste zin, na een inline <code>. Aan te vullen
    met check.audit.stock_lead_extra.
    """

    id = "audit-lead-opener"

    def controleer(self, ctx):
        formules = STOCK_LEAD + _audit(ctx)["stock_lead_extra"]
        patroon = re.compile(r'class="lead">.*(' + "|".join(formules) + ")")
        for pad in ctx.auditpaginas:
            if not self.overgeslagen(ctx, pad) and patroon.search(ctx.tekst(pad)):
                ctx.waarschuw(pad, "de lead opent op een vaste formule, varieer "
                                   "(SCHRIJFSTIJL.md 9)")


class AuditVerkleinwoord(AuditRegel):
    """Geen verkleinwoord dat een onderdeel opsmukt ("het zwarte blokje"). Zie DIMINUTIVES."""

    id = "audit-verkleinwoord"

    def controleer(self, ctx):
        _woordregel(ctx, self, DIMINUTIVES, "diminutives_extra",
                    "'{}' is een verkleinwoord dat een onderdeel opsmukt, noem het ding "
                    "(SCHRIJFSTIJL.md)")


class AuditNoordNederlands(AuditRegel):
    """Vlaamse woordkeuze, niet de Noord-Nederlandse ("kun je", "prima"). Zie NOORD_NL.

    "kan je" stond 101 keer tegen 6 voor "kun je", dus dit is evenzeer een
    consistentieregel als een regionale, en de noordelijke vormen zitten bijna
    allemaal in tekst die van een Nederlandse bron overgenomen werd.
    """

    id = "audit-noord-nederlands"

    def controleer(self, ctx):
        _woordregel(ctx, self, NOORD_NL, "noord_nl_extra",
                    "'{}' leest Noord-Nederlands, gebruik de Vlaamse vorm (SCHRIJFSTIJL.md 12)")


class AuditVulwoord(AuditRegel):
    """Geen bijwoord dat niets toevoegt ("netjes", "uiteraard"). Zie FILLERS.

    "netjes" was de echte tic: 19 keer, bijna altijd opvulling, en in "het
    bericht wacht netjes in zijn buffer" maakt het van een buffer ook nog een
    braaf wezen.
    """

    id = "audit-vulwoord"

    def controleer(self, ctx):
        _woordregel(ctx, self, FILLERS, "fillers_extra",
                    "'{}' is opvulling, laat het weg (SCHRIJFSTIJL.md 13)")


class AuditLedSpelling(AuditRegel):
    """In proza is het "led" en "leds", niet "LED".

    Spelling en geen versiering. De hoofdletters stonden in 43 bestanden tot
    een stijlronde er 400 verkleinde, en alleen een regel houdt ze tegen dat
    ze pagina per pagina terugkruipen.

    LED hoort wel in code: pinLED is een identifier, en in een protocol kan
    "LED" de sleutel zijn ("LED:1"). Een regelgebaseerde grep ziet geen
    <pre>-grenzen, dus de regel moet een prozatag dragen en mag niet de
    <pre ...><code>-openingsregel zijn. Dat mist liever een overtreding dan er
    een te verzinnen, en zo hoort het bij een adviserende regel. orion.json
    telt mee: zijn titels zijn het menu dat de student leest. Een melding per
    bestand.
    """

    id = "audit-led-spelling"

    def controleer(self, ctx):
        doelen = list(ctx.auditpaginas)
        if (ctx.root / "orion.json").is_file():
            doelen.append(ctx.root / "orion.json")
        for pad in doelen:
            tekst = ctx.tekst(pad)
            if not LED_RE.search(tekst):
                continue
            for regel in tekst.split("\n"):
                if not LED_RE.search(regel) or "<pre" in regel or "<code>" in regel:
                    continue
                if not any(t in regel for t in PROZA_LED):
                    continue
                if not self.overgeslagen(ctx, pad):
                    ctx.waarschuw(pad, "'LED' in de proza, de huisspelling is 'led'")
                break


class AuditIdentifierTaal(AuditRegel):
    """Identifiers zijn Nederlands, met het hoofdwoord achteraan: ledPin, knopPin.

    Dat is correct Nederlands (een samenstelling, "de ledpin") en tegelijk
    correct Engels, en daarom overleefden die namen de omzetting waar pinLed en
    pinButton dat niet deden. Het spiegelbeeld van audit-led-spelling: daar
    moest de regel een prozatag dragen, hier juist niet, want een identifier
    staat in een <pre>. De lijst (check.audit.identifier_words) bestaat alleen
    uit samenstellingen: een los "value" of "state" is ook value="0" in een
    attribuut, en een adviserende regel die loos alarm slaat, is erger dan een
    die iets mist. De Arduino-API houdt haar eigen Engelse namen; een pagina die
    ze documenteert, zet een audit-skip.
    """

    id = "audit-identifier-taal"

    def van_toepassing(self, ctx):
        return True if _audit(ctx)["identifier_words"] else "geen check.audit.identifier_words"

    def controleer(self, ctx):
        patroon = re.compile(r"(^|[^A-Za-z0-9_.])(" + "|".join(_audit(ctx)["identifier_words"])
                             + r")\b")
        for pad in ctx.auditpaginas:
            for nr, regel in enumerate(ctx.tekst(pad).split("\n"), 1):
                if not patroon.search(regel) or any(t in regel for t in PROZA_ID):
                    continue
                if not self.overgeslagen(ctx, pad):
                    ctx.waarschuw(pad, "Engelse identifier, de huisregel is Nederlands met het "
                                       f"hoofdwoord achteraan (ledPin, knopPin): {regel.strip()}",
                                  regelnr=nr)
                break


class AuditUVorm(AuditRegel):
    """De pagina's staan in de je-vorm, niet in de u-vorm.

    Een huisregel sinds de eerste commit, en niets keek hem na. Geimporteerde
    inhoud is waar de u-vorm binnensluipt. Adviserend, want "u" is op andere
    plaatsen een gewoon Nederlands woord.
    """

    id = "audit-u-vorm"

    def controleer(self, ctx):
        for pad in ctx.auditpaginas:
            if self.overgeslagen(ctx, pad):
                continue
            for nr, regel in enumerate(ctx.tekst(pad).split("\n"), 1):
                if U_VORM_RE.search(regel):
                    ctx.waarschuw(pad, f"u-vorm, deze pagina's staan in de je-vorm: "
                                       f"{regel.strip()}", regelnr=nr)


def _past(ctx, pad, sleutel):
    rel = pad.relative_to(ctx.root).as_posix()
    return any(fnmatch(rel, p) for p in _audit(ctx)[sleutel])


class AuditLead(AuditRegel):
    """Een pagina heeft een <p class="lead"> onder de <h1>.

    Op de pagina's uit check.audit.lead_patterns (Microcontrollers: de
    oefeningen en de naslag van een labo; standaard elke pagina). Een vak dat
    de lead alleen op zijn ingangen zet, beperkt het tot die ingangen.
    """

    id = "audit-lead"

    def controleer(self, ctx):
        for pad in ctx.auditpaginas:
            if (_past(ctx, pad, "lead_patterns") and 'class="lead"' not in ctx.tekst(pad)
                    and not self.overgeslagen(ctx, pad)):
                ctx.waarschuw(pad, 'geen <p class="lead"> onder de <h1>')


class AuditFiguur(AuditRegel):
    """Een afbeelding staat in een <figure>, behalve in een tabelcel.

    Een heuristiek: meer regels met <img> dan met <figure> betekent minstens
    een kale afbeelding. Een afbeelding in een tabelcel telt niet mee, want een
    vergelijkingstabel zet ze bewust in een <td>, en die in een figure wikkelen
    zou fout zijn. Op de pagina's uit check.audit.figure_patterns (standaard
    elke pagina).
    """

    id = "audit-figure"

    def controleer(self, ctx):
        for pad in ctx.auditpaginas:
            if not _past(ctx, pad, "figure_patterns") or self.overgeslagen(ctx, pad):
                continue
            regels = ctx.tekst(pad).split("\n")
            imgs = sum("<img" in r for r in regels)
            cellen = sum(bool(re.search(r"<t[dh][ >].*<img", r)) for r in regels)
            figs = sum("<figure" in r for r in regels)
            if imgs - cellen > figs:
                ctx.waarschuw(pad, f"{imgs - cellen} <img> buiten een tabel maar maar {figs} "
                                   "<figure> (een afbeelding hoort in een figure)")


def heeft_oefeningen(ctx):
    if _audit(ctx)["exercise_patterns"]:
        return True
    return "geen check.audit.exercise_patterns"


class AuditIndienen(AuditRegel):
    """Een oefening heeft een <h2 id="indienen"> met precies "<p>Sla je oefening op.</p>".

    Het Indienen-blok is vaste tekst. Een gehoste pagina is de inleverfolder
    niet, dus het enige wat ze eerlijk kan zeggen, is dat de student zijn werk
    bewaart; alles over het indienen hoort bij de opdracht in Brightspace.
    Geimporteerde inhoud neemt zijn eigen formulering mee, en per pagina een
    andere versie van een zin is pure drift. Op de pagina's uit
    check.audit.exercise_patterns.
    """

    id = "audit-indienen"

    def van_toepassing(self, ctx):
        return heeft_oefeningen(ctx)

    def controleer(self, ctx):
        for pad in ctx.auditpaginas:
            if not _past(ctx, pad, "exercise_patterns") or self.overgeslagen(ctx, pad):
                continue
            tekst = ctx.tekst(pad)
            if not re.search(r'<h2[^>]*id="indienen"', tekst):
                ctx.waarschuw(pad, 'geen <h2 id="indienen">-sectie')
            elif "<p>Sla je oefening op.</p>" not in tekst:
                ctx.waarschuw(pad, "de Indienen-sectie is niet de vaste "
                                   "'<p>Sla je oefening op.</p>'")


class AuditOplossing(AuditRegel):
    """Een oefening heeft een <h2 id="oplossing">.

    Dat anker is waar solution-placement de eenrichtingsknop toelaat en waar de
    PDF-export met --no-solutions afknipt. Op de pagina's uit
    check.audit.exercise_patterns.
    """

    id = "audit-oplossing"

    def van_toepassing(self, ctx):
        return heeft_oefeningen(ctx)

    def controleer(self, ctx):
        for pad in ctx.auditpaginas:
            if not _past(ctx, pad, "exercise_patterns") or self.overgeslagen(ctx, pad):
                continue
            if not re.search(r'<h2[^>]*id="oplossing"', ctx.tekst(pad)):
                ctx.waarschuw(pad, 'geen <h2 id="oplossing">-sectie')
