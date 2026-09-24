"""Welke vakrepo een commando bewerkt.

De scripts stonden vroeger in de vakrepo zelf en vonden die met
Path(__file__).parent.parent. Hier staan ze ernaast, dus het vak komt van
buiten: --repo, anders de git-root van de huidige map, anders die map zelf.
Wat het ook wordt, er moet een oriontools.json in staan. Zonder die eis draait
een export vanuit de verkeerde map stil op een willekeurige boom.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from . import config


class Vak:
    """Een vakrepo: de root en de gemengde config."""

    def __init__(self, root, configbestand=None):
        self.root = Path(root).resolve()
        self.config = config.laad(self.root, configbestand)

    def pad(self, sleutel):
        """Een map uit config.paths, als absoluut pad."""
        return self.root / self.config["paths"][sleutel]

    @property
    def code(self):
        return self.config["course"]["code"]

    @property
    def titel(self):
        return self.config["course"]["title"]


def _git_root(map_):
    try:
        uit = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=map_,
                             capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return Path(uit.stdout.strip())


def voeg_repo_toe(parser):
    """Het gedeelde --repo voor elk commando."""
    parser.add_argument("--repo", type=Path, default=None,
                        help="de vakrepo (standaard: de git-root van de huidige map)")
    # Een config van buiten de repo: om een vak na te kijken dat nog niet
    # gemigreerd is, zonder er een bestand in te schrijven.
    parser.add_argument("--config", type=Path, default=None, help=argparse.SUPPRESS)


def vind(args):
    """Het Vak voor --repo of de huidige map; stopt met een boodschap als het niet kan."""
    root = args.repo or _git_root(Path.cwd()) or Path.cwd()
    try:
        return Vak(root, args.config)
    except config.ConfigFout as e:
        sys.exit(f"oriontools: {e}")
