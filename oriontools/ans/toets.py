"""Maak de toets van een labo aan in ANS, met de instellingen uit oriontools.json.

    python ../OrionTools/orion.py ans-toets Labo/RS485
    python ../OrionTools/orion.py ans-toets Labo/RS485 --vragen _toets/LaboRS485.html
    python ../OrionTools/orion.py ans-toets Labo/RS485 --droog

EEN TOETS PER MAP
-----------------
Evaluatie.html van DeN geeft elk labo een eigen test, dus een toets hoort bij
een map van het vak. Hij wordt gevonden op zijn external_id in ans.course_id:
de map met streepjes en -Toets (DeN-Labo-RS485-Toets), zoals ans-push een bank
vindt op haar pakketnaam. Er staat dus geen toets-id in oriontools.json. De
naam bij het aanmaken komt uit orion.json: het deel van het menupad dat elke
pagina van de map deelt ("DEN - Labo: RS485 - Toets"). De naam mag je in ANS
wijzigen, de external_id niet, want dan maakt de volgende run een tweede toets.

DE INSTELLINGEN ZIJN DIE VAN ANS
--------------------------------
ans.toets in oriontools.json neemt de velden van de API zonder vertaling over:
assignment_type en summative, de objecten accessibility_settings en
grades_settings, en cover en publication, die elk een eigen endpoint hebben
(/assignments/{id}/cover, /assignments/{id}/publication). Wat een veld
doet, staat in de swagger van ANS; een eigen naam ertussen zou elk veld twee
keer documenteren. Een veld dat niet in de config staat, stuurt dit commando
niet mee: dan geldt de instelling van de school, of wat er in ANS al staat. Een
tikfout in een veldnaam weigert ANS met een 422, want de API aanvaardt geen
onbekende velden.

publication is de inzage: wat een student van zijn resultaat ziet, ook het
voorlopige resultaat meteen na het indienen (show_preliminary_result). Een
nieuwe toets kreeg op 27 september 2026 een publication met active,
show_questions en show_given_answers aan. Voor een labotoets die de groepen na
elkaar afleggen, betekent dat de vragen met hun antwoorden doorgeven aan de
volgende groep. In het scherm is de inzage een boom: Vraagstelling
(show_questions), daaronder Gegeven antwoorden (show_given_answers), en
daaronder Beoordelingscriteria (show_criteria) en Modelantwoord
(show_grading_description). Een ouder uitzetten terwijl een kind aan staat,
weigert ANS met een 422 "is required": dat gaf op 27 september 2026 een PATCH
met enkel show_questions of enkel show_given_answers op false. Een PATCH met
die vier samen op false werd aanvaard (toen ze al false stonden; de overgang
vanuit true zelf is nog niet gezien). Een vak zet dus een tak volledig uit in
de config, niet enkel haar top. Zolang er geen publication_timeslots zijn,
gaat de inzage niet open.

Niet elke instelling uit het scherm van ANS zit in de API. "Onbeantwoord
laten" als optie bij een meerkeuzevraag aanzetten veranderde op 27 september
2026 niets in wat de API teruggeeft: niet in de toets, de cover of de
publication, en niet in een oefening of een vraag, ook hun updated_at niet.
Dit commando kan het dus niet zetten en niet nakijken. ans.toets.met_de_hand
is daarom een lijst van zulke instellingen, die elke run afdrukt, ook met
--droog: wat je met de hand doet, vergeet je anders. Een tweede run laat ze
staan, maar een toets die opnieuw aangemaakt wordt (zie DE VRAGEN) verliest
ze.

Datums staan er niet in, en de API aanvaardt ze ook niet in een assignment:
wanneer een toets open staat en wanneer de inzage opengaat, loopt via
timeslots en publication_timeslots, en dat beslist de docent per zittijd, niet
de config.

EEN TWEEDE RUN ZET DE CONFIG TERUG
----------------------------------
oriontools.json is de bron. Bestaat de toets al, dan vergelijkt dit commando
elk veld uit de config met wat ANS teruggeeft, en zet het wat verschilt.
Een veld dat je in ANS met de hand wijzigt en dat in de config staat, keert
dus terug; een veld buiten de config blijft zoals het in ANS staat. --droog
toont het verschil per veld en schrijft niets.

Een object als grades_settings gaat bij een PATCH volledig mee: wat ANS al
had, met de velden uit de config erover. De swagger zegt niet of een PATCH
met een deel van het object de rest laat staan of wist, en zo maakt dat niet
uit.

ANS geeft een getal soms als tekst terug (passed_grade "9.99",
grade_lower_limit "0.0"), terwijl de POST een getal aanvaardt. gelijk()
vergelijkt daarom op waarde, niet op type.

Een PATCH per record en per run: een voor de toets, een voor de cover en een
voor de publication. Dat blijft onder de vijf wijzigingen per minuut die ANS
toelaat.

DE VRAGEN: EEN KOPIE BIJ HET AANMAKEN
-------------------------------------
Op 27 september 2026 in ANS nagekeken, met twee proeftoetsen in de cursus en
een itembanktoets in de bank van een labotoets, alles daarna getrasht:
- assignment_ids van een bankitem wijst niet naar een toets in een cursus,
  maar naar een itembanktoets (question bank assignment): een toets die in de
  bank zelf staat. Met het id van een cursustoets geeft die PATCH een 404.
- Een cursustoets krijgt vragen uit een bank enkel bij het aanmaken, met
  question_bank_assignment_id op de POST. ANS kopieert dan de vragen van die
  itembanktoets in de volgorde van haar exercise_ids, op de achtergrond en
  zonder job in het antwoord: meteen na de POST had de toets nog geen vragen,
  twee seconden later alle drie. Een kopie draagt de naam van het bankitem en
  geen external_id, en de toets onthoudt niet uit welke itembanktoets ze komt.
- Bij een PATCH op een bestaande toets doet ANS niets met dat veld, zoals de
  swagger zegt.

Daarom werkt --vragen in twee stappen. Eerst wordt een itembanktoets in de
bank van de vragenpagina gelijk aan die pagina: precies haar vragen, in haar
volgorde, ook als er daarvoor een uit moet. Ze heeft dezelfde external_id als
de toets, zoals de itembanktoets die vroeger per labo met de hand gemaakt werd.
Daarna komt de cursustoets uit die itembanktoets:
- bestaat ze niet, dan wordt ze aangemaakt met question_bank_assignment_id;
- is ze leeg, dan wordt ze getrasht en opnieuw aangemaakt, met dezelfde naam
  en external_id maar een nieuw id. Een lege toets heeft geen resultaten, en
  anders krijgt ze nooit vragen;
- heeft ze vragen, dan blijven die, want vervangen neemt de resultaten mee.
  Wijken hun namen af van de pagina, dan meldt dit commando dat.

Een gevulde toets is dus een momentopname. Een vraag die daarna verandert,
zet ans-push in de bank, en een volgende run zet het nieuwe item in de
itembanktoets; in de toets pas je ze met de hand aan, of je trasht de toets en
draait dit opnieuw, zolang niemand ze aflegde.

De bank moet bij zijn. Is een vraag nieuw of gewijzigd tegenover de bank
(zoals ans-dekking het ziet, met de vlaggen die het best kloppen), dan stopt
dit commando voor het iets schrijft: anders kopieert de toets een oudere
versie. Na het kopiëren leest het de toets opnieuw en zet het wat nog van de
config verschilt, want of ANS instellingen van de itembanktoets overneemt, is
niet nagekeken.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from .. import repo
from ..export import qti
from . import dekking, push
from .client import AnsFout, Client
from .push import menupad

OBJECTEN = ("accessibility_settings", "grades_settings")
VELDEN = ("assignment_type", "summative")
ONDER = ("cover", "publication")  # elk op /assignments/{id}/<naam>
GEDULD = 120


def toets_id(vak, rel):
    return qti.identifier(f"{vak.code}-{rel.replace('/', '-')}-Toets")


def pagina_menupaden(root, rel):
    """Het menupad van elke pagina van orion.json onder de map rel."""
    try:
        doc = json.loads((root / "orion.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    paginas = []

    def loop(items):
        for item in items:
            pagina = item.get("page") or ""
            if pagina.startswith(rel + "/"):
                paginas.append(pagina)
            loop(item.get("items", []))

    loop(doc.get("modules", []))
    return [p for p in (menupad(root, pagina) for pagina in paginas) if p]


def toetsnaam(vak, rel):
    paden = pagina_menupaden(vak.root, rel)
    gedeeld = list(Path(rel).parts)
    if paden:
        gedeeld = os.path.commonprefix(paden) or gedeeld
    return " - ".join([vak.code.upper(), *gedeeld, "Toets"])


def gelijk(a, b):
    """Dezelfde waarde, ook als ANS een getal als tekst teruggeeft."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b  # in Python is True == 1
    if a == b:
        return True
    if a is None or b is None:
        return False
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return False


def verschil(gewenst, huidig):
    """[(veld, huidig, gewenst)] voor elk veld van gewenst dat anders is.

    Een veld met _ vooraan is commentaar, zoals elders in oriontools.json.
    config.py slaat het over in een tabel met vaste sleutels, maar niet in een
    vrije zoals cover, en ANS weigert elk veld dat het niet kent.
    """
    return [(k, huidig.get(k), v) for k, v in gewenst.items()
            if not k.startswith("_") and not gelijk(v, huidig.get(k))]


def lees_onder(client, toets_id, cfg):
    """{naam: wat ANS teruggeeft} voor elk deel van ONDER dat in de config staat."""
    return {naam: client.haal(f"/assignments/{toets_id}/{naam}") for naam in ONDER if cfg.get(naam)}


def plan(cfg, toets, onder):
    """Wat een run verandert: (toets-body, {deel: body}, regels).

    toets is wat ANS teruggeeft en onder dat van lees_onder(), of {} voor een
    toets die nog niet bestaat; dan is alles uit de config een verandering. De
    toets-body is None als er niets te veranderen valt en draagt geen name; een
    deel van ONDER zonder verandering staat niet in de dict. regels zegt per
    veld wat er verandert, voor --droog en voor de uitvoer.
    """
    regels = []
    body = {}
    for k in VELDEN:
        if cfg.get(k) is not None and not gelijk(cfg[k], toets.get(k)):
            regels.append((k, toets.get(k), cfg[k]))
            body[k] = cfg[k]
    for k in OBJECTEN:
        huidig = toets.get(k) or {}
        anders = verschil(cfg.get(k) or {}, huidig)
        if anders:
            regels += [(f"{k}.{veld}", oud, nieuw) for veld, oud, nieuw in anders]
            body[k] = {**huidig, **{veld: v for veld, v in cfg[k].items() if not veld.startswith("_")}}
    onder_body = {}
    for naam in ONDER:
        anders = verschil(cfg.get(naam) or {}, (onder or {}).get(naam) or {})
        regels += [(f"{naam}.{veld}", oud, nieuw) for veld, oud, nieuw in anders]
        if anders:
            onder_body[naam] = {veld: nieuw for veld, _, nieuw in anders}
    return body or None, onder_body, regels


def enige(lijst, external_id, soort):
    gevonden = [x for x in lijst if x.get("external_id") == external_id and not x.get("trashed")]
    if len(gevonden) > 1:
        raise AnsFout(f"{len(gevonden)} {soort} met external_id {external_id}: "
                      + ", ".join(str(x["id"]) for x in gevonden) + ". Zet er een op trashed.")
    return gevonden[0] if gevonden else None


def zoek_toets(client, course_id, external_id):
    return enige(client.alles(f"/courses/{course_id}/assignments"), external_id, "toetsen")


def zoek_itembanktoets(client, bank_id, external_id):
    """De itembanktoets, of None. De lijst geeft geen exercise_ids, dus nog een GET."""
    gevonden = enige(client.alles(f"/question_banks/{bank_id}/question_bank_assignments"),
                     external_id, "itembanktoetsen")
    return client.haal(f"/question_bank_assignments/{gevonden['id']}") if gevonden else None


def vragen_van(client, toets_id):
    """De vragen van een cursustoets, in hun volgorde."""
    return sorted((e for e in client.alles(f"/assignments/{toets_id}/exercises") if not e.get("trashed")),
                  key=lambda e: e.get("position") or 0)


def items_van_pagina(doel, bestaande):
    """De bankitems van de vragen in doel, in de volgorde van de pagina."""
    per_id = {e.get("qti_identifier"): e for e in bestaande}
    return [per_id[q] for q in sorted(doel, key=push.nummer)]


def itembank_plan(itembanktoets, items):
    """(erbij, eruit, anders): de items die erbij komen, de ids die eruit gaan,
    en of exercise_ids verandert, ook enkel in volgorde. None is een nieuwe."""
    huidig = list((itembanktoets or {}).get("exercise_ids") or [])
    gewenst = [e["id"] for e in items]
    erbij = [e for e in items if e["id"] not in huidig]
    eruit = [i for i in huidig if i not in gewenst]
    return erbij, eruit, huidig != gewenst


def wacht_op_vragen(client, toets_id, aantal, slapen=time.sleep):
    """Het aantal vragen, zodra de kopie van ANS er allemaal zijn."""
    gewacht = 0
    while True:
        n = len(vragen_van(client, toets_id))
        if n >= aantal:
            return n
        if gewacht >= GEDULD:
            raise AnsFout(f"toets {toets_id} heeft na {GEDULD} s {n} van de {aantal} vragen")
        slapen(push.WACHT)
        gewacht += push.WACHT


def herinner(cfg):
    """De instellingen uit ans.toets.met_de_hand, die de API niet zet en niet leest."""
    for tekst in cfg.get("met_de_hand") or []:
        print(f"met de hand nakijken in ANS: {tekst}")


def kort(waarde, lengte=60):
    tekst = repr(waarde)
    return tekst if len(tekst) <= lengte else tekst[:lengte - 3] + "..."


def pad_van(vak, pad, soort):
    """Een pad vanaf de werkmap of de root van het vak, als het daar bestaat."""
    for kandidaat in (pad if pad.is_absolute() else Path.cwd() / pad, vak.root / pad):
        kandidaat = kandidaat.resolve()
        if kandidaat.is_dir() if soort == "map" else kandidaat.is_file():
            return kandidaat
    sys.exit(f"ans-toets: {pad} is geen {soort}")


def lees_vragen(client, vak, pagina, ext):
    """(rel, bank, items, itembanktoets) voor --vragen; stopt als de bank achterloopt."""
    rel = pagina.relative_to(vak.root).as_posix()
    naam = qti.naam_van(pagina, vak.root, vak.pad("toets"))
    bank = push.zoek_bank(client, qti.identifier(f"{vak.code}-{naam}"))
    if not bank:
        sys.exit(f"ans-toets: {rel} heeft geen vragenbank in ANS; zet ze erin met ans-push {rel}")
    bestaande = push.oefeningen(client, bank["id"])
    try:
        v, doel, nieuw, gewijzigd, _ = dekking.stand(vak, pagina, rel, naam, bestaande)
    except qti.Fout as e:
        sys.exit(f"ans-toets: {rel}: niets verstuurd\n{e}")
    if nieuw or gewijzigd:
        vlag = "" if v == dekking.VLAGGEN[0] else f" {dekking.vlaggen(v)}"
        sys.exit(f"ans-toets: niets verstuurd. De bank loopt achter op {rel} ({len(nieuw)} nieuw, "
                 f"{len(gewijzigd)} gewijzigd); eerst ans-push {rel}{vlag}")
    return rel, bank, items_van_pagina(doel, bestaande), zoek_itembanktoets(client, bank["id"], ext)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="orion.py ans-toets", description=__doc__.split("\n")[0])
    repo.voeg_repo_toe(parser)
    parser.add_argument("map", type=Path, help="de map van het labo, bv. Labo/RS485")
    parser.add_argument("--vragen", type=Path, metavar="PAGINA",
                        help="de vragenpagina waarvan de toets de vragen krijgt, bv. _toets/LaboRS485.html")
    parser.add_argument("--droog", action="store_true", help="alleen lezen en tonen wat er zou gebeuren")
    args = parser.parse_args(argv)
    vak = repo.vind(args)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ans = vak.config["ans"]
    if not ans["course_id"]:
        sys.exit("ans-toets: ans.course_id staat niet in oriontools.json (zoek hem met ans-verken)")
    cfg = ans["toets"]
    rel = pad_van(vak, args.map, "map").relative_to(vak.root).as_posix()
    pagina = pad_van(vak, args.vragen, "bestand") if args.vragen else None
    ext = toets_id(vak, rel)
    naam = toetsnaam(vak, rel)

    try:
        client = Client()
        toets = zoek_toets(client, ans["course_id"], ext)
        onder = lees_onder(client, toets["id"], cfg) if toets else {}
        if pagina:
            vragen_rel, bank, items, ibt = lees_vragen(client, vak, pagina, ext)
            in_toets = vragen_van(client, toets["id"]) if toets else []
    except AnsFout as e:
        sys.exit(f"ans-toets: {e}")

    ibt_anders = vervang = False
    if pagina:
        erbij, eruit, ibt_anders = itembank_plan(ibt, items)
        vervang = bool(toets) and not in_toets
        print(f"vragen: {vragen_rel}, bank {bank['id']} {bank['name']}, {len(items)} vragen")
        if not ibt:
            print(f"itembanktoets: nieuw, {naam} ({ext}) in bank {bank['id']}")
        else:
            print(f"itembanktoets: {ibt['id']} {ibt['name']}")
            namen = {e["id"]: e.get("name") for e in ibt.get("exercises") or []}
            if erbij:
                print("  erbij: vraag " + ", ".join(str(push.nummer(e["qti_identifier"])) for e in erbij))
            for i in eruit:
                print(f"  eruit: item {i} ({namen.get(i, '?')})")
            if ibt_anders and not (erbij or eruit):
                print("  andere volgorde")
            if not ibt_anders:
                print("  gelijk aan de pagina")

    if vervang:
        # Een nieuwe toets: elk veld uit de config gaat mee.
        body, onder_body, regels = plan(cfg, {}, {})
    else:
        body, onder_body, regels = plan(cfg, toets or {}, onder)
    if toets:
        print(f"toets: {toets['id']} {toets['name']} ({ext})")
    else:
        print(f"toets: nieuw, {naam} ({ext}) in cursus {ans['course_id']}")
    if pagina and not toets:
        print(f"  met de {len(items)} vragen van de itembanktoets")
    elif vervang:
        print(f"  leeg: wordt getrasht en opnieuw aangemaakt met de {len(items)} vragen van de itembanktoets")
    elif pagina:
        print(f"  {len(in_toets)} vragen; ANS kopieert enkel bij het aanmaken, dus die blijven")
        if [e.get("name") for e in in_toets] != [e.get("name") for e in items]:
            print("  let op: de vragen in de toets zijn niet die van de pagina (aantal, volgorde of naam)")
    if toets and not regels:
        print("  instellingen zoals in oriontools.json")
    for veld, oud, nieuw in regels:
        print(f"  {veld}: {kort(oud)} -> {kort(nieuw)}")
    if args.droog or not (regels or not toets or vervang or (pagina and (not ibt or ibt_anders))):
        herinner(cfg)
        return 0

    try:
        if pagina and (not ibt or ibt_anders):
            gewenst = [e["id"] for e in items]
            if not ibt:
                ibt, _ = client.vraag("POST", f"/question_banks/{bank['id']}/question_bank_assignments",
                                      body={"name": naam, "external_id": ext, "exercise_ids": gewenst})
                print(f"  itembanktoets aangemaakt: {ibt['id']}")
            else:
                client.vraag("PATCH", f"/question_bank_assignments/{ibt['id']}",
                             body={"name": ibt["name"], "exercise_ids": gewenst})
            ibt = client.haal(f"/question_bank_assignments/{ibt['id']}")
            if list(ibt.get("exercise_ids") or []) != gewenst:
                sys.exit(f"ans-toets: itembanktoets {ibt['id']} heeft na het zetten niet de vragen "
                         "van de pagina; de toets is niet aangeraakt")
            print(f"  itembanktoets gelijk aan de pagina: {len(gewenst)} vragen")
        if vervang:
            client.vraag("PATCH", f"/assignments/{toets['id']}", body={"name": toets["name"], "trashed": True})
            print(f"  lege toets {toets['id']} getrasht")
            naam, toets = toets["name"], None
        if not toets:
            extra = {"question_bank_assignment_id": ibt["id"]} if pagina else {}
            toets, _ = client.vraag("POST", f"/courses/{ans['course_id']}/assignments",
                                    body={"name": naam, "external_id": ext, **extra, **(body or {})})
            print(f"  toets aangemaakt: {toets['id']}")
            if pagina:
                n = wacht_op_vragen(client, toets["id"], len(items))
                print(f"  {n} vragen gekopieerd uit de itembanktoets")
            # Wat ANS bij het aanmaken anders zette of uit de itembanktoets
            # overnam, zet de rest van deze run recht.
            nieuw_id = toets["id"]
            toets = client.haal(f"/assignments/{nieuw_id}")
            body, onder_body, _ = plan(cfg, toets, lees_onder(client, nieuw_id, cfg))
        if body:
            # name staat als verplicht in de swagger, ook bij een PATCH. Vlak
            # na de kopie gaf een GET de toets een keer zonder name terug.
            client.vraag("PATCH", f"/assignments/{toets['id']}",
                         body={"name": toets.get("name") or naam, **body})
        for deel, deel_body in onder_body.items():
            client.vraag("PATCH", f"/assignments/{toets['id']}/{deel}", body=deel_body)
        # Nog eens lezen: een veld dat ANS stil anders opslaat, valt zo op.
        toets = client.haal(f"/assignments/{toets['id']}")
        onder = lees_onder(client, toets["id"], cfg)
    except AnsFout as e:
        sys.exit(f"ans-toets: {e}")
    _, _, blijft = plan(cfg, toets, onder)
    print(f"  {len(regels)} velden gezet")
    for veld, oud, nieuw in blijft:
        print(f"  let op: {veld} is na het zetten {kort(oud)}, niet {kort(nieuw)}")
    herinner(cfg)
    return 1 if blijft else 0


if __name__ == "__main__":
    sys.exit(main())
