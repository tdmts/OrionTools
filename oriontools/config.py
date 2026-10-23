"""oriontools.json: wat een vak anders doet dan de andere, en niets meer.

Het bestand staat in de root van de vakrepo. OrionSync spiegelt het niet
(courses.json sluit het uit bij elk vak), want het stuurt de scripts aan en is
geen cursusinhoud.

Wat hier niet staat, is een standaard die voor elk vak geldt. Die standaarden
staan in STANDAARD hieronder, en een sleutel die daar niet in staat is een
fout: een tikfout in een sleutel mag niet stil de standaard laten gelden.

Een lege dict in STANDAARD is een vrije tabel (check.disable, de
afkortingen): daar zijn de sleutels van het vak zelf en wordt niets
nagekeken. De inhoud van check.disable kijkt de check zelf na, tegen de
regels die ze kent.
"""

import copy
import json

BESTAND = "oriontools.json"

STANDAARD = {
    "course": {
        "code": "",            # korte naam: DeN, ICEES, MC, IR; zit in bestandsnamen
        "title": "",           # voluit, zoals op de kaft
    },
    "paths": {
        "labo": "Labo",
        "syllabus_src": "Theorie/Syllabus/Theorie",
        "syllabus_dir": "Theorie/Syllabus",
        "decks": "Hoorcollege",
        "downloads": "downloads",
        "img": "img",
        "datasheets": "datasheets",
        "oplossingen": "_oplossingen",
        "toets": "_toets",           # export-qti; git moet de map negeren
        "feedback": "_feedback",     # feedback-voorbereiden; git moet de map negeren
        "incoming": "_incoming",
        "export": "_export",
        "startbestanden": "startbestanden",
    },
    # Mappen die de check overslaat: ruwe import, eigen uitvoer, oplossingen, toetsen,
    # ingediende verslagen. Waarom: zie Context.overgeslagen in check/context.py.
    "staging": ["_incoming", "_export", "_oplossingen", "_toets", "_feedback"],
    # Pagina's in de repo die geen pagina van de site zijn.
    "exempt_pages": ["pasteInOrion.html", "template.html"],
    # Mappen met html die geen sitepagina is (een deck laadt geen OrionCSS).
    "non_site_dirs": ["Hoorcollege"],
    "check": {
        "disable": {},          # {regel-id: reden}
        "orphan_roots": ["Labo"],
        "remote_document_exts_extra": [],
        "code_style_languages": ["arduino", "cpp", "c", "csharp", "python"],
        # Pagina's die buiten elke regel vallen behalve em-dash en code-style:
        # een stijlgids die elke component demonstreert, ook met kapotte demo-links.
        "skip_pages": [],
        # Een titel "<woord> N" zegt niet wat de student bouwt (exercise-name).
        "exercise_title_words": ["oefening", "opdracht"],
        # Het eerste woord van een dropbox zonder score en van een test (orion-names).
        "names": {"ungraded": "Verslag", "test": "Test labo"},
        # --audit. De woordenlijsten staan in rules/audit.py; *_extra vult ze aan.
        "audit": {
            "stock_lead_extra": [],
            "diminutives_extra": [],
            "noord_nl_extra": [],
            "fillers_extra": [],
            # Engelse identifiers die in een codeblok Nederlands horen (leeg: n.v.t.).
            "identifier_words": [],
            # Toegelaten language-* van een codeblok; leeg: elke language-*.
            "code_languages": [],
            # Talen die geen show-language dragen (de badge zou "plaintext" zeggen).
            "code_no_badge": ["plaintext"],
            # fnmatch op het relatieve pad. Waar audit-lead kijkt: alleen waar het
            # vak een lead zet, want een theoriepagina zonder lead is geen fout.
            "lead_patterns": ["*"],
            # Waar audit-figure kijkt. Een kale afbeelding is overal een
            # afwijking, dus een vak laat dit meestal op elke pagina staan.
            "figure_patterns": ["*"],
            # Waar audit-indienen en audit-oplossing kijken (leeg: n.v.t.).
            "exercise_patterns": [],
        },
    },
    "syllabus": {
        "manifest": "reference.js",
        "manifest_key": "",
        "pdf": "",
        "logo": "",
        "docx": "",
        "afkortingen": {},
        "vet_uit_de_word": True,
        # dpi 0: niet krimpen. onaangeroerd: bestandsnamen in img/ die met hun
        # tekst gelezen moeten worden en dus op volle resolutie blijven.
        "krimp": {"dpi": 0, "onaangeroerd": []},
        # De cover, zoals nagemeten van de bestaande syllabus: een regel per
        # element van een lijst. De titel is course.title.
        "cover": {
            "opleiding": "",
            "auteur": "",
            "departement": [],
            "voet": [],
        },
    },
    "handout": {
        "prefix": "",
    },
    "import_brightspace": {
        # Een document boven deze grens wordt overgeslagen. GitHub waarschuwt
        # vanaf 50 MB en weigert 100 MB.
        "max_mb": 50,
        # Hoe diep een geconverteerde pagina staat: zoveel keer ../ voor img/,
        # datasheets/ en startbestanden/ in een herschreven link. 2 voor
        # LaboN/Exercises/, 3 voor Labo/<Naam>/Theorie/.
        "page_depth": 2,
        # Wat een pagina linkt en wij dus zelf hosten. Slides en office-bestanden
        # ontbreken met opzet: ze zijn intern, niet iets wat een pagina linkt, en
        # groot (de grootste .pptx in een echte export is 200 MB).
        "doc_exts": [".pdf", ".zip"],
        # Welke van doc_exts een startbestand is (paths.startbestanden) in plaats
        # van een datasheet: wat een student in een tool opent.
        "start_exts": [],
    },
    "feedback": {
        # feedback-json zet dit onder elke feedback die naar een student gaat, na een
        # lege regel. De student hoort te weten dat AI meeschreef en wat hij kan doen
        # als hij de feedback niet vertrouwt (lector DeN, 23 oktober 2026). Het staat
        # niet in de spreadsheet, zodat de lector het niet per rij naleest en een
        # ongewijzigd voorstel ongewijzigd blijft. Er staat niet in dat de lector alles
        # naleest: dat doet hij niet altijd. Leeg: geen vermelding.
        "vermelding": (
            "Deze feedback is opgesteld met behulp van AI. "
            "Ze is een hulpmiddel: Goed zegt wat je zo houdt, Werkpunten wat je nog eens "
            "bekijkt voor een volgend verslag of een test. Je score komt van je lector, "
            "nooit van de AI. Vermoed je een fout in de feedback? Dan mag je altijd om "
            "manuele feedback vragen."
        ),
    },
    # De koppeling met ANS (oriontools/ans/). 0 is niet ingesteld; ans-verken
    # toont welke id's je token ziet. Een vragenbank staat hier niet: elke
    # vragenpagina krijgt haar eigen bank. Het token staat nooit hier: zie
    # oriontools/ans/client.py.
    "ans": {
        "course_id": 0,
        # fnmatch op het relatieve pad: de pagina's waarover ans-dekking een
        # vraag in ANS verwacht. Leeg is geen dekking; een vragenpagina telt nooit.
        "dekking": [],
        # fnmatch op het relatieve pad: de pagina's met een <h2 id="doelstellingen">
        # waarvan ans-dekking elke doelstelling nagaat (DeN: Labo/*/overview.html).
        # Leeg is geen rapport per doelstelling.
        "doelstellingen": [],
        # De instellingen van een toets van ans-toets, met de veldnamen van de
        # ANS-API. None en {} sturen niets mee: dan geldt wat de school of ANS
        # instelt. cover en publication (de inzage) gaan elk naar
        # /assignments/{id}/<naam>.
        #
        # De labotest van elk vak (keuze 5 oktober 2026): wat DeN en ICEES elk
        # apart hadden staan, en dat was op de letter hetzelfde. Een vak zet
        # in zijn oriontools.json alleen wat afwijkt. summative omdat de test
        # meetelt; op 20, geslaagd vanaf 9,99; giscorrectie enkel op beantwoorde
        # vragen, anders is open laten nooit beter dan gokken en heeft
        # "Onbeantwoord laten" geen zin. Een minuut per vraag besliste de
        # lector op 30 september 2026: de toets is berekend op 40 seconden,
        # IOEM op een minuut, en wie IOEM heeft, is niet te achterhalen.
        "toets": {
            # De naam van de toets en van haar itembanktoets. {labo} is de titel
            # van de module in orion.json zonder "Labo:", of wat ans.toets.labo
            # voor de map zegt; {jaar} is het jaar van de cursus in ANS. Zie
            # ans-toets.
            "naam": "Labo {labo} {jaar}",
            # {map: labo} voor een test die meer dan een labo dekt
            # ({"Labo/Virtualiseren": "Virtualiseren + Partitioneren"}).
            "labo": {},
            "assignment_type": "Quiz",
            "summative": True,
            "accessibility_settings": {"attempts": 1},
            "grades_settings": {
                "grade_calculation": "formula",
                "grade_formula": "points/total*20",
                "rounding": "two_decimal",
                "grade_lower_bound": True,
                "grade_lower_limit": "0.0",
                "grade_upper_bound": True,
                "grade_upper_limit": "20.0",
                "passed_grade": 9.99,
                "guess_correction": True,
                "guess_correction_lower_bound": True,
                "apply_guess_correction_to_answered_questions_only": True,
            },
            "cover": {
                "description_before": (
                    "<div>Je legt deze test af met gesloten boek.</div><ul>"
                    "<li>Op de meerkeuzevragen staat giscorrectie. Een vraag die je onbeantwoord laat, "
                    "kost geen punten.</li><li>Je hebt 1 minuut per vraag.</li>"
                    "<li>Je kan heen en weer tussen de vragen.</li></ul>"),
                "display_headers": False,
                "enumerate_questions": True,
                "indicate_points": True,
                "shuffle_choices": True,
                "shuffle_sections": "all",
            },
            # De inzage, voor elk vak dezelfde (keuze 27 september 2026): het
            # cijfer, het totaal en meteen na het indienen het voorlopige
            # resultaat, en niets waaruit een volgende groep de vragen of hun
            # antwoorden leert. Een tak van de boom gaat volledig uit (zie
            # ans-toets). Elk veld staat erin, zodat een vak er elk kan
            # overschrijven; None stuurt niets mee.
            "publication": {
                "show_preliminary_result": True,
                "show_grade": True,
                "show_total_points": True,
                "show_points_per_question": False,
                "show_questions": False,
                "show_given_answers": False,
                "show_criteria": False,
                "show_grading_description": False,
                "allow_export": False,
                "show_domains": False,
                "show_objectives": False,
                "show_average_objective_score": False,
                "active": None,
                "show_letter_grade": None,
                "show_review_consensus": None,
                "exclude_correctly_answered_questions": None,
                "excluded_exercise_ids": None,
                "location_ids": None,
                "password": None,
            },
            # Wat de API niet zet en niet leest; ans-toets drukt het elke run af,
            # bij elke toets van elk vak (keuze 27 september 2026). Een lijst
            # in oriontools.json vervangt deze, dus een vak dat er een toevoegt,
            # neemt deze mee over.
            "met_de_hand": [
                "optie \"Onbeantwoord laten\" aan bij meerkeuze- en meerantwoordvragen",
                "per paar (de h3 van de vragenpagina, in de titel van elke vraag) een van de twee "
                "vragen laten trekken, en het aantal getrokken vragen nakijken",
            ],
        },
    },
    "export_pdf": {
        "group": "module",     # lab of module
        # De bestandsnaam zonder .pdf. Velden: {code} van het vak, {id} van de
        # module in orion.json, {n} het labo- of modulenummer. Nooit de titel:
        # een titel die in Orion verandert, mag de naam van een gepubliceerde
        # PDF niet meenemen.
        "naam": "{code}-{id}",
        # Wat bovenop .pdf .zip .docx .pptx .xlsx een los document is, geen pagina.
        "doc_exts_extra": [],
        # Bij group=lab: een pagina in deze map is een oefening, een andere naslag.
        "oefeningen_map": "Exercises",
    },
}


class ConfigFout(Exception):
    pass


def _meng(standaard, eigen, pad):
    if not isinstance(eigen, dict):
        raise ConfigFout(f"{pad or 'de root'} moet een object zijn")
    uit = copy.deepcopy(standaard)
    for sleutel, waarde in eigen.items():
        volledig = f"{pad}.{sleutel}" if pad else sleutel
        if sleutel.startswith("_"):
            continue  # "_uitleg" en dergelijke: commentaar in JSON
        if sleutel not in standaard:
            raise ConfigFout(f"onbekende sleutel {volledig}")
        basis = standaard[sleutel]
        if isinstance(basis, dict) and basis:
            uit[sleutel] = _meng(basis, waarde, volledig)
        elif isinstance(basis, dict):
            if not isinstance(waarde, dict):
                raise ConfigFout(f"{volledig} moet een object zijn")
            uit[sleutel] = waarde
        else:
            if basis is not None and not isinstance(waarde, type(basis)):
                raise ConfigFout(f"{volledig} moet een {type(basis).__name__} zijn")
            uit[sleutel] = waarde
    return uit


def laad(root, pad=None):
    """De config van de vakrepo in root, gemengd met STANDAARD."""
    pad = pad or root / BESTAND
    try:
        eigen = json.loads(pad.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigFout(f"{pad} ontbreekt; dit is geen vakrepo voor OrionTools")
    except json.JSONDecodeError as e:
        raise ConfigFout(f"{pad}: geen geldige JSON ({e})")
    return _meng(STANDAARD, eigen, "")
