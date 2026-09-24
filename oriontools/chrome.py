"""Waar staat de headless Chrome, voor elk commando dat er een nodig heeft.

Alleen de standaardbibliotheek, met opzet: export-verslag laadt dit en heeft
verder niets nodig dan python-docx, en mag er geen pypdf bij slepen.

Een lijst, niet een kopie per script. Twee kopieen van dezelfde zoekpaden
lopen uit elkaar zodra er ergens een browser bijkomt, en dat was gebeurd: de
lijst van Microcontrollers en IR kende %LOCALAPPDATA% en chromium-browser, die
van DeN niet. Dit is de unie.
"""

import os
import shutil
import sys
from pathlib import Path

KANDIDATEN = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]
OP_PAD = ["chrome", "google-chrome", "chromium", "chromium-browser", "msedge"]


def zoek_chrome(opgegeven=None, verplicht=True):
    """Het pad naar Chrome of Edge.

    Een opgegeven pad (--chrome of $CHROME) telt alleen als het bestaat: een
    tikfout daarin moet niet stil terugvallen op een andere browser en ook niet
    pas bij het afdrukken als raadselachtige fout opduiken. Zonder browser stopt
    het met een boodschap, tenzij verplicht=False, dan geeft het None.
    """
    for kandidaat in filter(None, [opgegeven, os.environ.get("CHROME")]):
        if Path(kandidaat).exists():
            return kandidaat
    for kandidaat in KANDIDATEN:
        pad = Path(os.path.expandvars(kandidaat))
        if pad.is_file():
            return str(pad)
    for naam in OP_PAD:
        gevonden = shutil.which(naam)
        if gevonden:
            return gevonden
    if verplicht:
        sys.exit("geen Chrome of Edge gevonden; geef --chrome PAD of zet CHROME")
    return None
