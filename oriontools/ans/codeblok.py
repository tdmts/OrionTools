"""Zet een codeblok dat de QTI-import van ANS in stukken knipte, terug in een <pre>.

    python ../OrionTools/orion.py ans-codeblok --bank 225605 --toets 1948494
    python ../OrionTools/orion.py ans-codeblok --bank 225605 --droog

WAT DE IMPORT DOET
------------------
export-qti schrijft een codeblok als <pre><code>, met zijn regeleinden. De
QTI-import van ANS maakt daar <pre><code><code>regel</code><code>regel</code>
...</code></pre> van, zonder regeleinden, en ANS toont die regels naast elkaar:
de uitvoer van ipconfig of show vlan staat dan op een regel. Vastgesteld op 24
oktober 2026 in de toetsen van labo Draadloos netwerk en Managed switch.

Diezelfde dag is in een vraag van de bank 225605 via de API nagekeken wat ANS
wel goed toont: een <pre> met regeleinden, een <pre> met <br> tussen de regels,
en een regel per <div><code> met harde spaties. Alle drie bleven ongewijzigd
staan en kwamen regel per regel in beeld. Gekozen is het <pre> met
regeleinden, omdat het de pagina het dichtst volgt.

Een PATCH op /questions/{id} slaat de inhoud op zoals hij verstuurd wordt; de
import is het enige dat knipt. Daarom herstelt ans-push elk item meteen na de
import, en kopieert ans-toets het herstelde item naar de toets. Voor wat al in
ANS stond, is er dit commando: een bank en de toets die er een kopie van heeft,
moeten allebei hersteld worden, want een kopie volgt de bank niet.

Een toets die loopt, weigert elke wijziging (422, "It is not possible to update
while test is in progress", de RS485-toets 1911107 op 24 oktober 2026). Zo'n
vraag wordt gemeld en overgeslagen; draai het commando opnieuw als de toets
gesloten is.

--droog leest alleen en toont hoeveel vragen een geknipt codeblok hebben.
"""

import argparse
import re
import sys

from .client import AnsFout, Client

# Wat de import van een codeblok maakt: een <code> per regel in een <code>.
GEKNIPT = re.compile(r"<pre>\s*<code[^>]*>((?:\s*<code>.*?</code>)+)\s*</code>\s*</pre>", re.S)
REGEL = re.compile(r"<code>(.*?)</code>", re.S)


def herstel(inhoud):
    """De inhoud met elk geknipt codeblok als <pre> met regeleinden, of None als er geen is."""
    if not inhoud or not GEKNIPT.search(inhoud):
        return None
    return GEKNIPT.sub(lambda m: "<pre>" + "\n".join(REGEL.findall(m.group(1))) + "</pre>", inhoud)


def herstel_oefeningen(client, oefening_ids, droog=False, geweigerd=None):
    """Herstel elke vraag van deze oefeningen; geeft het aantal geknipte vragen.

    Een vraag die ANS weigert te wijzigen (422), komt in de lijst geweigerd als
    die er is; zonder lijst gaat de fout door.
    """
    aantal = 0
    for oid in oefening_ids:
        for vraag in client.haal(f"/exercises/{oid}/questions"):
            nieuw = herstel(vraag.get("content"))
            if nieuw is None:
                continue
            aantal += 1
            if droog:
                continue
            try:
                client.vraag("PATCH", f"/questions/{vraag['id']}", body={"content": nieuw})
            except AnsFout as e:
                if geweigerd is None or e.status != 422:
                    raise
                geweigerd.append((vraag["id"], str(e)))
    return aantal


def main(argv=None):
    parser = argparse.ArgumentParser(prog="orion.py ans-codeblok", description=__doc__.split("\n")[0])
    parser.add_argument("--bank", type=int, action="append", default=[], help="id van een vragenbank")
    parser.add_argument("--toets", type=int, action="append", default=[], help="id van een toets in een cursus")
    parser.add_argument("--droog", action="store_true", help="alleen tellen")
    args = parser.parse_args(argv)
    if not (args.bank or args.toets):
        parser.error("geef minstens een --bank of een --toets")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        client = Client()
        for bank in args.bank:
            ids = [e["id"] for e in client.alles(f"/question_banks/{bank}/question_bank_exercises")
                   if not e.get("trashed")]
            n = herstel_oefeningen(client, ids, args.droog)
            print(f"bank {bank}: {len(ids)} items, {n} met een geknipt codeblok"
                  + ("" if args.droog or not n else ", hersteld"))
        for toets in args.toets:
            ids = [e["id"] for e in client.alles(f"/assignments/{toets}/exercises")]
            geweigerd = []
            n = herstel_oefeningen(client, ids, args.droog, geweigerd)
            print(f"toets {toets}: {len(ids)} oefeningen, {n} met een geknipt codeblok"
                  + ("" if args.droog or not n else f", {n - len(geweigerd)} hersteld"))
            for vid, reden in geweigerd:
                print(f"  let op: vraag {vid} niet gewijzigd: {reden}")
    except AnsFout as e:
        sys.exit(f"ans-codeblok: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
