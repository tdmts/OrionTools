"""Zet de meerkeuzevragen van een vragenpagina in een vragenbank van ANS.

    python ../OrionTools/orion.py ans-push Labo/RS485/Theorie/TestJezelf.html
    python ../OrionTools/orion.py ans-push Labo/RS485/Theorie/TestJezelf.html --droog

Het pakket is dat van export-qti, gebouwd met dezelfde functies; wat daar
staat over de markup, de figuren en QTI 2.1, geldt hier ook. Alleen gaat de
zip niet naar schijf maar rechtstreeks naar ANS.

EEN BANK PER PAGINA
-------------------
Zoals de banken die met de hand gemaakt zijn ("DEN - Labo Managed Switch -
Theorie - Test jezelf"). De bank wordt gevonden op haar external_id, en dat is
de pakketnaam uit export-qti (DeN-Labo-RS485-Theorie-TestJezelf), dus er staat
geen bank-id in oriontools.json. Bestaat ze niet, dan wordt ze aangemaakt, met
als naam het pad van de pagina in orion.json: wie de bank in ANS ziet, vindt
de pagina in het menu terug. Een toets, die niet in het menu staat, krijgt de
titel van haar pagina (zie banknaam). De naam mag je in ANS wijzigen; de external_id
niet, want dan maakt de volgende push een tweede bank.

WAT EEN ITEM ONTHOUDT
---------------------
Een QTI-import zet qti_identifier op de identifier van het item
(DeN-Labo-RS485-Theorie-TestJezelf-11). Daarna zet dit commando external_id op
de bron en een hash van het item: Labo/RS485/Theorie/TestJezelf.html#11@<hash>.
Tags zouden kunnen, maar een GET geeft ze niet terug, en wat je niet kan
lezen, kan geen verouderd item aanwijzen.

De hash is die van het item zelf (de XML en zijn figuren), niet van de pagina
en geen commit. Een hash van de pagina verandert voor elke vraag wanneer er
een verandert, en een commit bestaat niet voor een toets in _toets/, die git
negeert. Zo wijst de hash precies de vraag aan die anders is dan in ANS.

--feedback en --niet-schudden veranderen de XML en dus de hash: push een
pagina telkens met dezelfde vlaggen, anders geldt elke vraag als gewijzigd.
--feedback heeft in ANS geen zin (zie export-qti, IN ANS NAGEKEKEN).

EEN GEWIJZIGDE VRAAG: TRASHEN, DAN IMPORTEREN
---------------------------------------------
Op 27 september 2026 in ANS nagekeken, in de bank Orion-proef (221613), met
de Test jezelf van labo RS485:
- Dezelfde zip twee keer importeren gaf de tweede keer niets: geen nieuw item,
  geen updated_at die veranderde. ANS verdubbelt dus niet.
- Een zip waarin vraag 23 een andere titel en stam had, veranderde evenmin
  iets: naam, updated_at en de inhoud van de vraag (GET
  /exercises/{id}/questions) bleven die van de eerste import. Een item waarvan
  de qti_identifier al in de bank staat, slaat ANS over; het vervangt niet.
- Na DELETE van item 23 (een soft delete, trashed) maakte dezelfde zip een
  nieuw item 23 met de nieuwe inhoud. Een getrasht item houdt zijn
  qti_identifier dus niet vast, en de lijst van de bank toont het niet meer.

Daarom trasht dit commando eerst elk item waarvan de external_id niet meer
klopt, en importeert dan het hele pakket: wat nog klopt, slaat ANS over.
Mislukt de import halverwege, dan ontbreken er items en zet de volgende push
ze erin. Een item dat in een itembanktoets zit (assignment_ids, zie ans-toets),
vervangt het evengoed, en het meldt in welke: het nieuwe item zit er niet in,
en ans-toets --vragen zet die itembanktoets weer gelijk aan de pagina. Een
toets in een cursus raakt het niet, want die heeft een kopie. Een item
waarvan de vraag van de pagina verdween, blijft staan en wordt gemeld: of het
weg mag, beslist de docent, niet een push.

Een vraag die van nummer verandert (er komt een vraag voor), krijgt een andere
qti_identifier. Voor ANS is dat een ander item; elke vraag erna wordt dus
vervangen.

HET VERKEER
-----------
Een import gaat in drie stappen: de API geeft een put_url (een uur geldig) en
een background job, de zip gaat met een PUT naar die url, en de job gaat van
"initialized" naar "pending". Daarna volgt dit commando de job tot hij niet
meer loopt; een geslaagde import eindigt op "success". Een record mag vijf
keer per minuut gewijzigd worden; per item is er hoogstens een DELETE en een
PATCH met external_id, dus dat blijft eronder.

--droog leest alleen: welke bank, hoeveel items er al zijn, wat er zou gebeuren.
--proef schrijft naar de bank "Orion-proef" in plaats van de bank van de pagina.
"""

import argparse
import hashlib
import io
import json
import re
import sys
import time
import zipfile
from pathlib import Path

from .. import repo
from ..export import qti
from .client import AnsFout, Client

PROEFBANK = "Orion-proef"
KLAAR = "success"
LOPEND = {"initialized", "pending", "queued", "processing", "running", "started", "in_progress"}
WACHT, GEDULD = 3, 300


def menupad(root, rel):
    """De titels van orion.json tot het topic van rel, zonder het nummer van de module."""
    try:
        doc = json.loads((root / "orion.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    def zoek(items, pad):
        for item in items:
            titel = re.sub(r"^\d+\.\s*", "", item.get("title", ""))
            if item.get("page") == rel:
                return [*pad, titel]
            gevonden = zoek(item.get("items", []), [*pad, titel])
            if gevonden:
                return gevonden
        return None

    return zoek(doc.get("modules", []), [])


def banknaam(vak, rel, titel=None):
    """Het menupad, anders de titel van de pagina, anders het pad.

    Een toets in paths.toets staat niet in orion.json. Haar pad zegt in ANS
    niets ("DEN - _toets - LaboRS485"), haar <h1> wel ("DEN - Toets labo RS485").
    """
    delen = menupad(vak.root, rel) or ([titel] if titel else list(Path(rel).with_suffix("").parts))
    return " - ".join([vak.code.upper(), *delen])


def items_van(bestanden):
    """{qti_identifier: hash} van elk item in het pakket."""
    uit = {}
    for naam, xml in bestanden.items():
        if naam == "imsmanifest.xml" or not naam.endswith(".xml"):
            continue
        h = hashlib.sha1(xml)
        for src in sorted(set(re.findall(rb'<img\b[^>]*\bsrc="([^"]+)"', xml))):
            h.update(bestanden[src.decode("utf-8")])
        uit[naam[:-4]] = h.hexdigest()[:10]
    return uit


def nummer(item_id):
    return int(item_id.rsplit("-", 1)[1])


def doel_van(bestanden, rel):
    """{qti_identifier: external_id} zoals een push ze zet."""
    return {i: f"{rel}#{nummer(i)}@{h}" for i, h in items_van(bestanden).items()}


def zip_van(bestanden):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for naam, inhoud in bestanden.items():
            z.writestr(naam, inhoud)
    return buf.getvalue()


def zoek_bank(client, external_id):
    banken = [b for b in client.alles("/question_banks")
              if b.get("external_id") == external_id and not b.get("trashed")]
    if len(banken) > 1:
        raise AnsFout(f"{len(banken)} vragenbanken met external_id {external_id}: "
                      + ", ".join(str(b["id"]) for b in banken) + ". Zet er een op trashed.")
    return banken[0] if banken else None


def oefeningen(client, bank_id):
    return [e for e in client.alles(f"/question_banks/{bank_id}/question_bank_exercises")
            if not e.get("trashed")]


def plan(doel, bestaande, pakket):
    """Wat een push doet: (nieuw, gewijzigd, verweesd).

    nieuw: qti_identifiers uit doel zonder item in de bank. gewijzigd: items
    in de bank waarvan de external_id niet die uit doel is (ook een item dat
    met de hand geimporteerd is en er geen heeft). verweesd: items van dit
    pakket waarvan de vraag niet meer op de pagina staat.
    """
    per_id = {e.get("qti_identifier"): e for e in bestaande}
    nieuw = sorted(q for q in doel if q not in per_id)
    gewijzigd = [per_id[q] for q in sorted(doel) if q in per_id and per_id[q].get("external_id") != doel[q]]
    eigen = re.compile(re.escape(pakket) + r"-\d+$")
    verweesd = [e for e in bestaande
                if eigen.match(e.get("qti_identifier") or "") and e["qti_identifier"] not in doel]
    return nieuw, gewijzigd, verweesd


def importeer(client, bank_id, bestandsnaam, data, slapen=time.sleep):
    """Upload de zip, start de job en wacht tot hij klaar is; geeft de job."""
    start = client.haal(f"/question_banks/{bank_id}/question_bank_exercises/import",
                        file_name=bestandsnaam, file_size=len(data))
    job = start["background_job"]
    client.upload(start["put_url"], data)
    job, _ = client.vraag("PATCH", f"/background_jobs/{job['id']}", body={"status": "pending"})
    gewacht = 0
    while job["status"] in LOPEND:
        if gewacht >= GEDULD:
            raise AnsFout(f"de import (job {job['id']}) loopt na {GEDULD} s nog, "
                          f"met status {job['status']}")
        slapen(WACHT)
        gewacht += WACHT
        job = client.haal(f"/background_jobs/{job['id']}")
    return job


def main(argv=None):
    parser = argparse.ArgumentParser(prog="orion.py ans-push", description=__doc__.split("\n")[0])
    repo.voeg_repo_toe(parser)
    parser.add_argument("pagina", type=Path, help='een pagina met een <ol class="vragen">')
    parser.add_argument("--feedback", action="store_true",
                        help="de uitleg (div.oplossing) als feedback meegeven; niet voor een summatieve toets")
    parser.add_argument("--niet-schudden", action="store_true",
                        help="de mogelijkheden in de volgorde van de pagina laten")
    parser.add_argument("--droog", action="store_true", help="alleen lezen en tonen wat er zou gebeuren")
    parser.add_argument("--proef", action="store_true", help=f'naar de bank "{PROEFBANK}" schrijven')
    args = parser.parse_args(argv)
    vak = repo.vind(args)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    pagina = args.pagina if args.pagina.is_absolute() else (Path.cwd() / args.pagina)
    if not pagina.is_file():
        pagina = vak.root / args.pagina
    pagina = pagina.resolve()
    if not pagina.is_file():
        sys.exit(f"ans-push: {args.pagina} bestaat niet")
    rel = pagina.relative_to(vak.root).as_posix()

    naam = qti.naam_van(pagina, vak.root, vak.pad("toets"))
    pakket = qti.identifier(f"{vak.code}-{naam}")
    try:
        bestanden, meldingen, _ = qti.bouw(pagina, vak.root, f"{vak.code}-{naam}",
                                           not args.niet_schudden, args.feedback)
    except qti.Fout as e:
        sys.exit(f"ans-push: {rel}: niets verstuurd\n{e}")
    doel = doel_van(bestanden, rel)
    for m in meldingen:
        print(f"  let op: {m}")

    bank_ext = PROEFBANK if args.proef else pakket
    bank_naam = PROEFBANK if args.proef else banknaam(
        vak, rel, qti.paginatitel(pagina.read_text(encoding="utf-8"), None))
    try:
        client = Client()
        bank = zoek_bank(client, bank_ext)
        voor = oefeningen(client, bank["id"]) if bank else []
    except AnsFout as e:
        sys.exit(f"ans-push: {e}")
    nieuw, gewijzigd, verweesd = plan(doel, voor, pakket)

    print(f"{rel}: {len(doel)} meerkeuzevragen")
    print(f"bank: {bank['id']} {bank['name']}" if bank else f"bank: nieuw, {bank_naam} ({bank_ext})")
    print(f"  {len(nieuw)} nieuw, {len(gewijzigd)} gewijzigd, "
          f"{len(doel) - len(nieuw) - len(gewijzigd)} ongewijzigd")
    if gewijzigd:
        print("  gewijzigd: vraag " + ", ".join(str(nummer(e["qti_identifier"])) for e in gewijzigd))
    for e in verweesd:
        print(f"  let op: item {e['id']} ({e['name']}) staat niet meer op de pagina; "
              "het blijft in de bank, trash het met de hand als het weg mag")
    if args.droog or not (nieuw or gewijzigd):
        return 0

    try:
        # De lijst van de bank geeft geen assignments; een GET per item wel.
        in_itembanktoets = {}
        for e in gewijzigd:
            for a in client.haal(f"/question_bank_exercises/{e['id']}").get("assignments") or []:
                in_itembanktoets.setdefault(f"{a.get('name')} ({a['id']})", []).append(
                    str(nummer(e["qti_identifier"])))
        if not bank:
            bank, _ = client.vraag("POST", "/question_banks", body={"name": bank_naam, "external_id": bank_ext})
            print(f"  bank aangemaakt: {bank['id']}")
        for e in gewijzigd:
            client.vraag("DELETE", f"/question_bank_exercises/{e['id']}")
        # Het hele pakket: ANS slaat een item over waarvan de qti_identifier al
        # in de bank staat, dus komt alleen binnen wat nieuw of net getrasht is.
        job = importeer(client, bank["id"], f"{naam}-qti.zip", zip_van(bestanden))
        print(f"import: job {job['id']}, status {job['status']}")
        if job["status"] != KLAAR:
            sys.exit(f"ans-push: de import eindigde met status {job['status']}")
        na = {e.get("qti_identifier"): e for e in oefeningen(client, bank["id"])}
        for q, waarde in doel.items():
            e = na.get(q)
            if e and e.get("external_id") != waarde:
                # name staat als verplicht in de swagger, ook bij een PATCH
                client.vraag("PATCH", f"/question_bank_exercises/{e['id']}",
                             body={"name": e["name"], "external_id": waarde})
    except AnsFout as e:
        sys.exit(f"ans-push: {e}")

    ontbreekt = [str(nummer(q)) for q in doel if q not in na]
    if ontbreekt:
        sys.exit(f"ans-push: niet in de bank na de import: vraag {', '.join(ontbreekt)}")
    print(f"  {len(nieuw) + len(gewijzigd)} items in de bank gezet")
    for itembanktoets, nummers in in_itembanktoets.items():
        print(f"  let op: vraag {', '.join(nummers)} stond in itembanktoets {itembanktoets}, het "
              f"nieuwe item niet; zet ze gelijk met ans-toets <map> --vragen {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
