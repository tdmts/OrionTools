"""Waar de stijlbladen van de exports staan: hier, en in de checkout van OrionCSS.

Een vak draagt geen opmaak voor zijn PDF's meer. syllabus.css en handout.css
leest alleen een export, dus ze staan in OrionTools, in oriontools/export/stijl/,
met de icoontjes van de syllabuskaders ernaast. hoorcollege.css laadt ook het
deck zelf in de cursus, dus dat staat in OrionCSS en wordt gespiegeld zoals
style.css.

De export leest hoorcollege.css uit de CHECKOUT van OrionCSS naast OrionTools,
niet van GitHub Pages: wat je drukt, moet zijn wat je hebt, ook als het nog niet
gepusht is, en een export werkt dan ook zonder netwerk. Die checkout ontbreekt
alleen in CI, en daar draait geen export en slaat handout-stale over.

De paden zijn functies en geen constanten, zodat de tests STIJL en ORIONCSS
naar een tijdelijke map kunnen verleggen: een verouderingsregel vergelijkt
mtimes, en die van de echte bestanden zijn die van de laatste checkout.
"""

from pathlib import Path

STIJL = Path(__file__).resolve().parent / "export" / "stijl"
ORIONCSS = Path(__file__).resolve().parents[2] / "OrionCSS"
ORIONCSS_URL = "https://tdmts.github.io/OrionCSS/"


def syllabus_css():
    return STIJL / "syllabus.css"


def handout_css():
    return STIJL / "handout.css"


def hoorcollege_css():
    return ORIONCSS / "hoorcollege.css"
