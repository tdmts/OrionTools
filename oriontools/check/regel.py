"""Wat een regel is, en de lijst van alle regels.

Een regel is een subklasse van Regel in een module onder rules/. Ze draagt:

- id: een stabiele kebab-slug. Dat is de naam waaronder een vak haar uitzet
  (check.disable in oriontools.json) en waaronder een CLAUDE.md haar noemt.
  Geen nummer: DeN en Microcontrollers nummerden hun regels elk anders, en
  "regel 9" was in het ene vak het verloop en in het andere de topicgrens.
- legacy: de oude nummers, zoals "DeN:10" of "MC:9", zodat een oude
  verwijzing terug te vinden is met `check --rules`.
- modus: "standaard" draait altijd, "audit" alleen met --audit.
- van_toepassing(ctx): True, of een korte reden waarom niet ("geen
  orion.json"). Een regel geldt voor elk vak waar het ding bestaat dat ze
  nakijkt; een vak dat haar toch niet wil, zet haar uit met een reden.
- controleer(ctx): meldt via ctx.fout en ctx.waarschuw.

De docstring van de klasse is de uitleg die `check --explain <id>` toont, en
het verslag van waarom de regel bestaat. Die hoort bij de code, niet in een
CLAUDE.md.
"""

REGISTER = {}


class Regel:
    id = ""
    legacy = ()
    modus = "standaard"

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        if not cls.id:
            return
        if cls.id in REGISTER:
            raise RuntimeError(f"regel {cls.id} bestaat twee keer")
        REGISTER[cls.id] = cls

    def van_toepassing(self, ctx):
        return True

    def controleer(self, ctx):
        raise NotImplementedError
