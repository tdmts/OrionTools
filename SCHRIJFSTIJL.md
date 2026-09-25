# Schrijfstijl

Hoe het proza van de Orion-vakken klinkt: DeN, ICEES, IR en Microcontrollers. Dit is de gedeelde
basis. Elk vak heeft daarnaast een eigen `SCHRIJFSTIJL.md` in zijn root, en die zegt alleen wat er in
dat vak bij komt: waar de regels er gelden, voorbeelden uit dat vak, en waar het vak bewust afwijkt.
Wat hier staat, staat daar niet nog eens. Lees dus altijd allebei, dit bestand eerst.

**Een aanvulling hangt aan een nummer.** In het bestand van een vak staat een aanvulling onder het
nummer van het patroon dat ze aanvult ("### 17. Waar je in DeN op mag rekenen"). Een nieuw patroon
komt hier en krijgt hier zijn nummer, ook als het in een vak ontdekt is; de regel
`schrijfstijl-nummers` van de check faalt op een vak dat een nummer gebruikt dat hier niet bestaat.
Zo ontstonden de vier kopieën die dit bestand vervangt: elk vak voegde patronen toe, voegde er samen
of hernummerde, en na een jaar citeerde "patroon 12" in twee vakken iets anders.

Het gaat hier **alleen over de vorm van de tekst**. Of een pagina correct aan elkaar hangt is een
technische vraag en hoort bij de check (`python ../OrionTools/orion.py check`). Wat een pagina moet
uitleggen is een didactische vraag, en die hoort bij het review-protocol van het vak, waar er een is.

**Waar het geldt: overal waar een student meeleest.** Lopende tekst, koppen en kadertitels, de
`lead`, titels van accordions, `alt`-teksten, `figcaption`s, en elke titel in het Orion-menu. De
cursus hoort als één stem te klinken, en een titel in het menu is even goed tekst als een alinea.
Ook tekst die de student in een ander formaat leest, valt eronder: het verslag dat uit een
`Opdracht.html` gegenereerd wordt, de syllabus-PDF en de handouts.

**Waar het niet geldt: de documentatie van de repo's zelf.** Dit bestand, een CLAUDE.md, een
CONTRIBUTING.md, `NOTITIES.md` en de registers in `review/` zijn werkmateriaal voor wie schrijft. De
patroontitels hieronder zijn zelf werkwoordloos en ontkennend, en dat blijft zo: ze zijn de naam van
een regel en worden ook zo geciteerd ("patroon 6").

**Taalfouten vallen er buiten.** Een kommasplitsing, een spatiefout, een verkeerd onderwerp bij het
werkwoord: dat is geen stijl. Verzamel ze en leg ze apart voor, zodat de diff van een stijlronde één
soort wijziging bevat.

**Bijna alles hieronder is een leesregel.** De check dwingt één stijlregel af, de em-dash (regel
`em-dash`, en `--fix` herstelt ze). `--audit` meldt vrijblijvend wat een woordenlijst kan zien: de
vaste openingsformule (patroon 9), het verkleinwoord en de Noord-Nederlandse woordkeuze (12), de
vulwoorden (13), de u-vorm en `LED` in de lopende tekst. De lijsten staan in
[`oriontools/check/rules/audit.py`](oriontools/check/rules/audit.py), met de aanvullingen van een vak
in zijn `oriontools.json`; dit document geeft het criterium en niet de woorden. Meer automatiseren
is een bewuste keuze niet te doen: de andere patronen hebben woorden nodig die ook volkomen legitiem
voorkomen, en een woordenlijst zou vooral goede zinnen afkeuren.

**Waar het vandaan komt.** Het document is geschreven in Microcontrollers, tegen tekst die
*opgevoerd* was: elke alinea bouwde op naar een pointe en eindigde op een zin die moest blijven
hangen. De andere vakken namen het over voor tekst met het omgekeerde probleem, zakelijk tot kaal
uit een Brightspace-export, met hier en daar een grapje of een emoji. Daar slaan de patronen 1 tot
10 vooral aan op tekst die nieuw geschreven wordt, en dat is precies het moment waarop ze nodig
zijn. De voorbeelden hieronder komen uit alle vier de vakken.

## Wat blijft

Lees dit eerst. Alles hieronder gaat over vorm, en niets ervan is een excuus om korter of karig te
schrijven.

- **Het waarom** achter elke stap, in gewone mededelende zinnen. Een student die niet weet waarom er
  een afsluitweerstand aan elk uiteinde van de bus hoort, heeft aan de opdracht alleen niets.
- **De terugkoppeling** naar wat de student al kan, maar als feit en niet als opbouw: "Je gebruikte
  `analogRead()` al in labo 2" in plaats van "Twee labo's lang heb je...". Waar een vak op mag
  rekenen, verschilt per vak (patroon 17).
- **Concrete voorbeelden.** Die horen in de hoofdzin, niet tussen haakjes. Als een walkietalkie het
  beste voorbeeld van half duplex is, dan is de walkietalkie belangrijk genoeg voor een eigen zin.
- **De kruislinks** naar de theoriepagina's, waar de student het kan nalezen.
- **De je-vorm**, warm en niet formeel. De warmte komt uit de je-vorm en uit het uitleggen van het
  waarom, niet uit ritme of woordkeuze. `men` en `we` gaan allebei naar de je-vorm: `men` is formeel,
  en de inclusieve `we` schuift de student weg van wat hij zelf doet.

  > **Voor:** Voor grotere afstanden of storingsgevoelige omgevingen gebruikt men differential
  > signaling.
  >
  > **Na:** Voor grotere afstanden of storingsgevoelige omgevingen gebruik je differential signaling.

- **Kadertitels die iets zeggen** ("PWM werkt alleen op de pinnen met een `~`") in plaats van
  "Belangrijk". Een kop noemt wel zijn onderwerp en niet zijn pointe, en bevat geen `geen` of `niet`:
  zie patroon 6.
- **Volledige code** in een voorbeeld en een oplossing, geen fragmenten, behalve waar de opdracht
  juist vraagt om een fragment aan te vullen.

**En de rem boven de hele lijst.** Alle patronen hieronder zijn ontkennend: ze zeggen wat weg mag. Je
kan er dus aan allemaal tegelijk voldoen door minder te zeggen, en niets in die lijst houdt dat
tegen. Dat gebeurde in ICEES bij de lead van Labo Assemblage: "volledig uit elkaar" werd
"openhalen", "tot hij opstart" werd "tot hij draait", en de installatie van het besturingssysteem
viel helemaal weg, terwijl de zin bij elke stap beter scoorde op de patronen.

Leg daarom elke herschreven zin naast de oude met een vraag: **welk feit staat er niet meer?**
Ontbreekt er een, dan is de herschrijving fout, hoeveel patronen ze ook oplost. Patroon 15 en 17
dragen die rem al voor zichzelf; dit is dezelfde rem voor de rest.

## Wat eruit gaat

Zestien patronen. Geen enkel patroon is op zich fout: het probleem is dat ze allemaal samen, op elke
pagina, van uitleg een voordracht maken. Patroon 1 tot 10 gaan over opsmuk, 12 en 13 over
woordkeuze, 14 en 15 kwamen er later bij (allebei opsmuk).

Patroon 16 en 17 zitten een niveau hoger: ze gaan niet over een zin maar over de vorm van een
alinea, en daarom overleeft elke zin afzonderlijk de andere veertien.

Patroon 18 en 20 staan nog een niveau hoger: ze gaan niet over de vorm maar over het onderwerp. 18
gaat over wat de student niet weet omdat hij niet bij het gesprek was, 20 over wat hij niet weet
omdat hij die bladzijde nog niet gezien heeft.

**Het waren er tweeëntwintig.** Zes gingen op in een ander patroon zonder dat er een toets verdween,
omdat ze in de praktijk telkens dezelfde vraag stelden. **De nummers van de overblijvende zestien
liggen vast**, ook al loopt de reeks daardoor met gaten, want een patroon wordt op zijn nummer
geciteerd, ook in oudere registers en notities van de vakken. Wie een oud nummer tegenkomt, vindt het
hier terug:

| Was | Staat nu in | Waarom |
|---|---|---|
| 4, de dubbele punt | 3 | Allebei een aankondiging van een pointe in plaats van de pointe |
| 8, de verplichte tegenhanger | 16 | Een vierde vorm van hetzelfde: de lezer vertellen hoe hij het moet wegen |
| 11, het verkleinwoord | 12 | 11 verwees zelf naar 12, en zijn hele grond was het register |
| 19, het voorschrift | 18 | 19 zei zelf: "Dit patroon en patroon 18 komen uit dezelfde bron" |
| 21, de glosse te veel | 13 | 21 zei zelf: "De toets is dezelfde als bij patroon 13, met een groter voorwerp" |
| 22, het algemenere woord | 20 | Allebei het woord gemeten aan wat de lezer op dat punt heeft |

### 1. Geen slotzin die moet blijven hangen

Eindig op de laatste zin die iets vertelt, niet op een zin die iets doet.

> **Voor:** Hier schrijf jij het met `digitalRead()` en `digitalWrite()`, en bewaakt niemand iets.
>
> **Na:** Hier doe je dat zelf met `digitalRead()` en `digitalWrite()`, en de cyclustijd wordt niet
> bewaakt.

Andere voorbeelden van hetzelfde: "Een rolluik dat aan volle snelheid tegen zijn eindaanslag knalt,
is een rolluik dat je één keer bouwt." en "Verbind je Tx met Tx, dan zitten twee zenders tegen
elkaar te roepen en luistert er niemand."

### 2. Geen retorische drieslag

Drie parallelle **stellingen** als betoogfiguur.

> **Voor:** Omdat je in echte code programmeert in plaats van in functieblokken, omdat de chip een
> paar euro kost en in het product zelf past, en omdat jij bepaalt wat er aan de pinnen hangt.
>
> **Na:** Zo'n chip kost een paar euro en is klein genoeg om in het product zelf te zitten. Je
> programmeert hem in C++ in plaats van in functieblokken, en je bepaalt zelf wat er aan elke pin
> hangt.

Een opsomming van drie concrete dingen ("USB, Ethernet en SATA") mag wel. Dat is een lijst en geen
figuur.

### 3. Geen aankondiging van een pointe

Zet de bewering neer. De retorische vraag en de dubbele punt zijn twee manieren om te melden dat er
iets komt in plaats van het te zeggen. Dit was patroon 3 en 4.

> **Voor:** Waarom? Omdat de compiler slim is, en die slimheid hier tegen je werkt.
>
> **Na:** De reden zit in de compiler, die de variabele in de processor bijhoudt in plaats van hem
> telkens opnieuw uit het geheugen te halen.

> **Voor:** Serieel betekent: achter elkaar.
>
> **Na:** Serieel betekent dat de bits achter elkaar over één draad gaan.

Ook zo: "Het idee: je ISR doet niets anders dan..." en "Regel: elke variabele die je in een ISR
aanraakt, krijgt `volatile`."

Twee uitzonderingen, allebei echt. Een vraag **aan** de student mag, want daar hoort een antwoord
bij: "Is de input /RE active low of active high?" En een dubbele punt voor een opsomming, een tabel
of een codevoorbeeld is gewoon interpunctie en blijft.

### 5. Geen korte zin voor het effect

> **Voor:** Nu zet je er één regel bij. Eentje maar.
>
> **Na:** Nu zet je er één regel bij.

Ook zo: "Zonder uitzondering.", "Terecht.", "Eén draad." Voeg ze samen met de zin ervoor of laat ze
weg.

De toets is de persoonsvorm. Een zin zonder werkwoord gaat weg of gaat op in de zin ervoor; een korte
zin mét persoonsvorm blijft, ook wanneer hij nadruk legt. Hier zijn geen uitzonderingen op, want dan
wordt het opnieuw een oordeel. Een vaste aankondiging die je wil houden, krijgt gewoon een werkwoord:
"Nog een denkoefening." wordt "Denk hier eerst zelf na."

**Alleen in lopende tekst.** Koppen, kadertitels, `alt`-teksten, `figcaption`s, checklistregels en
titels in het menu zijn van nature naamwoordgroepen ("Het probleem", "Voordelen", "Oplossing"). Daar
is een fragment de normale vorm en geen effectbejag.

### 6. Geen ontkennende opening

Begin bij wat het ding wél is, niet bij wat het niet is.

> **Voor:** Een unmanaged switch kan je niet configureren. Hij leert de MAC-adressen zelf.
>
> **Na:** Een unmanaged switch leert zelf welk MAC-adres achter welke poort zit, en werkt zonder dat
> je er iets aan instelt.

Hier is geen uitzondering op, ook niet wanneer de zin een misvatting corrigeert die de student echt
heeft. De correctie komt dan in dezelfde alinea, na de bewering: niet "Een led is geen weerstand",
maar "Een led heeft een vaste doorlaatspanning, dus je kan hem niet doorrekenen als een weerstand."

**In koppen geldt dit strenger.** Een kop of kadertitel bevat helemaal geen `geen` of `niet`, ook
niet in het midden. "Gebruik geen `delay()`" wordt "Vervang `delay()` door `millis()`". Een
beschrijvend `zonder` valt er niet onder: "Drukken tellen zonder dender" zegt wat een oefening maakt.
De `id` van een kop blijft ongewijzigd wanneer de tekst verandert, want andere pagina's linken ernaar.

### 7. Geen bemenste machines

> **Voor:** Wanneer de compiler ziet dat je steeds dezelfde variabele uitleest, denkt hij: die
> verandert hier toch nergens.
>
> **Na:** Wanneer de compiler ziet dat je steeds dezelfde variabele uitleest, houdt hij die waarde
> bij in de processor omdat er in je `loop()` niets aan verandert.

Een werkwoord dat de vakterm is, blijft: "de switch beslist" en "de transceiver luistert" heten zo.
"De switch weet niet goed wat hij ermee moet" is patroon 7.

### 9. Geen vaste openingsformule

"Hier lees je...", "Op deze pagina zie je..." Elke lead die op dezelfde manier begint, maakt de
volgende voorspelbaar. Zeg waar de pagina over gaat in de vorm die bij díe pagina past, en soms is
dat gewoon de eerste feitelijke zin van het onderwerp.

Het gevaar is het grootst waar pagina's naast elkaar een zelfde rol spelen: de inleidingen van zes
labo's, of vier reeksen oefeningen die elk met "In deze oefening leer je..." openen. Wie ze na elkaar
leest, leest zes keer dezelfde zin. `--audit` kent de bekende formules.

### 10. Geen theatrale nadruk

Vet en cursief zijn om een **term**, een pinnaam of een componentnaam te markeren, niet om een zin te
laten landen.

> **Voor:** Door hogere klokfrequenties en efficiënte protocollen is seriële communicatie vaak
> **sneller én betrouwbaarder** dan parallel.
>
> **Na:** Door hogere klokfrequenties en efficiënte protocollen haalt seriële communicatie in de
> praktijk meer doorvoer dan parallel, met minder kans op fouten.

Een vetgedrukte **deelzin** valt hier ook onder ("**Per PCF8574 krijg je 8 extra I/O-lijnen**"). De
grens ligt niet bij hele zinnen: vet komt om een woord, een term, een pinnaam of een getal, nooit om
een zinsdeel.

### 12. Vlaamse woordkeuze, en geen verkleinwoord als verzachter

De studenten zijn Vlaams, en de cursus is dat ook. Schrijf dus **Nederlands zoals het in Vlaanderen
geschreven wordt**, en vermijd woorden die typisch Noord-Nederlands aanvoelen. Dit was patroon 11 en
12: het verkleinwoord als verzachter hoort hier omdat het diezelfde grens raakt.

> **Voor:** Met `map()` kun je een waarde van het ene bereik omzetten naar een ander.
>
> **Na:** Met `map()` kan je een waarde van het ene bereik omzetten naar een ander.

Let bij `kunt` en `wilt` op waar het onderwerp staat. In "een waarde die je in je programma kunt
gebruiken" staat er van alles tussen `je` en het werkwoord, en toch is het dezelfde vorm. De Vlaamse
standaardvorm is `kan` en `wil`, waar het onderwerp ook staat.

Verder: `flink` wordt `ruim` of `stevig`, `prima` wordt `goed` of `zonder problemen`, en `eventjes`
wordt `even` of `kort`, of het gaat helemaal weg wanneer de zin het niet nodig heeft (patroon 13).
Preventief ook `hartstikke`, `gaaf`, `lekker` als versterker, en `hoor` of `nou` als toevoegsel aan
het einde van een zin.

**De woorden van de opleiding liggen vast.** Een lesgever is een **lector** en geen docent, en een
resultaat is een **punt** en geen cijfer. In dezelfde reeks: het is een **labo** en geen practicum,
je **dient** een verslag **in** en levert het niet in, en wat je aflegt is een **test** en geen
toets of tentamen. Twee van die woorden hebben een tweede betekenis die wel blijft staan: een
`toets` is ook een knop op je toetsenbord, en een `cijfer` is ook een getal, zoals de 4 in DDR4. De
regel gaat over het resultaat en over het examen, niet over die twee.

**Twee waarschuwingen, en dit is waar zo'n regel misgaat.**

Ten eerste: bij twijfel **wint het Belgische woord**. De scheidslijn ligt niet tussen Belgisch en
standaard, maar tussen schrijftaal en spreektaal. Wat je in een Vlaamse cursus- of krantentekst
geschreven ziet, blijft staan, ook wanneer een woordenboek er "in België" bij zet: "neem daarvoor
best een weerstand van 120 &Omega;", "op het eerste zicht", "verderzetten". Wat alleen in een gesprek
voorkomt, gaat weg: "deftig" voor behoorlijk, "een pak beter", "vijs", "kuisen", "de linkse knop".
Liever een Belgicisme dan een Hollandisme.

Ten tweede: er zijn woorden die alleen Noord-Nederlands *lijken*. `netjes` is gewoon Nederlands en
wordt in Vlaanderen even goed gebruikt (het is er wel vaak een van patroon 13). `best` in "je neemt
best" is Belgisch en niet Noord-Nederlands, en `hoor` is in "bij een echte motor hoor je dat" gewoon
het werkwoord. Meet voor je een woord aan de lijst toevoegt of het in die repo wel is wat je denkt
dat het is.

**Het verkleinwoord als verzachter.** Het Nederlands van Nederland gebruikt die vorm veel vrijer dan
dat van Vlaanderen ("een vraagje", "een momentje"), dus een Vlaamse lezer leest hem sneller als
aanstellerij dan als vriendelijkheid. Een verkleinwoord dat een technisch onderdeel gezellig moet
maken, noem je bij zijn naam.

> **Voor:** Zoek naar het tekeningetje van het IC met acht pootjes en de namen ernaast.
>
> **Na:** Zoek naar de tekening van het IC met acht aansluitingen en de namen ernaast.

De uitzondering, en die is echt: **een verkleinwoord dat de gangbare vakterm is, blijft.**
`rekstrookje` is de Nederlandse naam van het onderdeel, en een `ezelsbruggetje` heet niet anders. Ook
vaste uitdrukkingen ("tussen haakjes", "een beetje") zijn geen opsmuk. De vraag is niet of er een
verkleinvorm staat, maar of er een gewoon woord bestaat dat hetzelfde zegt. De lijst van `--audit` is
daarom opzettelijk kort en bevat geen enkele vakterm.

`pootje` valt niet onder die uitzondering, ook niet bij een potentiometer, al is het in de werkplaats
gangbaar: het gewone woord bestaat. Een potentiometer of een component op een breadboard heeft
**aansluitingen**, een IC, een transistor of een display heeft **pinnen**. Voor studenten in het hoger
onderwijs leest het verkleinwoord kinderachtig (beslist 2026-09-25, eerst in Microcontrollers).

### 13. Geen vulling, van een bijwoord tot een hele bijzin

Wat niets toevoegt aan de zin, laat je weg. Dit was patroon 13 en 21: het bijwoord en de bijstelling
zijn hetzelfde probleem op een andere schaal, en de toets is voor allebei dezelfde.

**Het bijwoord.**

> **Voor:** Het bericht wacht netjes in zijn ontvangstbuffer.
>
> **Na:** Het bericht blijft in de ontvangstbuffer staan.

Dat voorbeeld laat zien waarom dit meer is dan een woord te veel: "wacht netjes" maakt van de buffer
ook nog een braaf wezen, en dat is patroon 7. Let ook op `heel even` (een verzachter op een
verzachter), en kijk met dezelfde blik naar `eigenlijk` en `uiteraard`. `letterlijk` in
"`digitalWrite()` zet letterlijk 5 V op een pin" blijft, want daar betekent het echt iets.

De toets is één vraag: verliest de zin iets wanneer je het bijwoord schrapt? `gewoon` en `precies`
zijn de lastigste twee, want die betekenen vaak wel iets ("een gewone digitale uitgang", "precies
even breed") en zijn toch vaak vulling. Die staan daarom in geen enkele lijst en vragen een lezer.

**De bijstelling die het vanzelfsprekende uitlegt**, het vroegere patroon 21. Een bijzin die niets
toevoegt aan het woord ervoor, gaat weg, ook wanneer de buren in de lijst er wel een hebben.

> **Voor:** Een computer met scherm en toetsenbord, het toestel dat je uit elkaar haalt
>
> **Na:** Een computer met scherm en toetsenbord

Dat labo heet Assemblage en gaat over een computer uit elkaar halen; welk toestel dat is, was de
vraag niet, en de bijstelling is er niet eens waar, want het scherm en het toetsenbord haal je niet
uit elkaar. De twee regels eronder, "Een laptop, om je antwoorden in te vullen" en "Een smartphone,
om de foto's te nemen", verdienen hun bijzin wel: daar is niet vanzelfsprekend waarom je ze moet
meebrengen. Het eerste item stond kaal tussen items met een bijzin en kreeg er een om de vorm, niet
om de inhoud.

Ook zo: "Download het voor je begint" onder een knop die "Opdracht downloaden" heet.

### 14. Geen terzijde als knipoog

Een grapje tussen haakjes dat niets uitlegt, gaat weg. Een emoji ook.

> **Voor:** Elke goede bibliotheek (ja, er zijn er ook slechte) bevat een aantal voorbeeldprogramma's.
>
> **Na:** Elke goede bibliotheek bevat een aantal voorbeeldprogramma's.

Dezelfde grond als patroon 1: het staat er om te charmeren en niet om te informeren. Een terzijde dat
wél iets zegt, is geen knipoog en blijft, al staat het meestal beter in de hoofdzin (zie de proef
hieronder).

Informele opmaak is iets anders dan een knipoog. `TLDR:` boven een samenvatting kondigt aan wat er
komt en blijft dus staan.

### 15. Beeldspraak alleen waar het gewone woord ontbreekt

Bestaat er een letterlijk woord voor wat je bedoelt, dan schrijf je dat.

> **Voor:** ... terwijl je maar drie pinnen van je Arduino opoffert.
>
> **Na:** ... terwijl je maar drie pinnen van je Arduino gebruikt.

Een beeld dat een mechanisme uitlegt, is uitleg en valt onder *Wat blijft*. Het verschil zit in wat
er gebeurt als je het beeld schrapt: verdwijnt er alleen kleur, dan was het opsmuk; verdwijnt er
begrip, dan hoort het er.

Een stijlronde vervangt een beeld **alleen wanneer de letterlijke formulering al op de pagina staat**,
zoals `opoffert` naast `gebruikt`. Vraagt de vervanging een technisch feit dat er nog niet staat, dan
is het geen stijlingreep meer en gaat de zin naar de vragenlijst van die doorloop. Zo blijft overeind
dat een stijlronde nooit verzint wat een pagina beweert.

### 16. Stel vast, beoordeel niet

Een alinea zegt wat er gebeurt. Ze zegt er niet bij hoe erg, hoe belangrijk of hoe gemeen dat is.

> **Voor:** Zonder afsluitweerstand krijg je reflecties op de lijn, en dat is meteen de vervelendste
> fout van allemaal om te vinden.
>
> **Na:** Zonder afsluitweerstand weerkaatst het signaal aan het uiteinde van de lijn en stoort het
> zichzelf. De ontvanger leest dan bits die de zender niet gestuurd heeft.

Het oordeel komt in vier vormen, en alle vier gaan ze weg. **De rangschikking:** "Dit is de
gevaarlijkste van de drie", "die test is geen luxe". **De aankondiging:** "Twee dingen zijn de moeite
om apart te bekijken", die alleen zegt dat er iets komt en het meteen weegt. **De slotwaardering:**
een zin die het feit uit de vorige zin nog eens beoordeelt in plaats van het te zeggen. **De
tegenhanger**, het vroegere patroon 8: niet elke bewering hoeft haar nuance mee, en wie ze er uit
evenwicht bij zet, weegt opnieuw voor de lezer.

> **Voor:** Seriële communicatie is trager dan parallel. Al wordt dat natuurlijk ruimschoots
> gecompenseerd, en in de praktijk valt het dus wel mee.
>
> **Na:** Seriële communicatie is per bit trager dan parallel, maar haalt door hogere klokfrequenties
> in de praktijk meer doorvoer.

Zet een nuance er alleen bij wanneer de student de afweging echt zelf moet maken, en dan als
informatie en niet als evenwicht.

De toets: schrap het waarderende zinsdeel. Staat het feit er dan nog, dan was het een oordeel.

Dit is niet hetzelfde als patroon 1, al overlappen ze aan het eind van een alinea. Patroon 1 gaat
over een zin die moet blijven hangen en die je schrapt. Hier gaat het over de gewoonte om de lezer te
vertellen wat hij van een feit moet vinden, en de ingreep is meestal geen schrapping maar een
verplaatsing: het gewicht gaat de mededeling in.

Een waarschuwing is geen oordeel. "Sluit niets aan voor je schema gecontroleerd is" is een instructie
en blijft, ook in een `warning`-kader. "Dit is de gevaarlijkste fout van de drie" is een rangschikking
en gaat weg. Eén keer per pagina mag een echte klemtoon: het probleem is de herhaling, want een
tekst die alles weegt, weegt niets meer.

**Een kader is zo'n klemtoon.** Een `info-box` staat er alleen voor een instructie die schade of
letsel voorkomt, of voor iets dat anders ongemerkt misloopt, en er staat er hoogstens één op een
pagina. Een definitie, een lijst toepassingen of de kern van de pagina hoort in de lopende tekst: in
een kader leest ze als bijzaak, en de student ziet niet meer wat de hoofdzaak is. Een kader dat
herhaalt wat erboven staat, gaat weg; een feit dat alleen in het kader stond, gaat naar de lopende
tekst. Wat overblijft krijgt een titel die de instructie zelf zegt (*Wat blijft*).

> **Voor:** een `warning`-kader "Let op" rond de vier maatregelen van *Beperken van risico's*, en
> daaronder een `tip`-kader "Belangrijk": "Veiligheid staat altijd voorop."
>
> **Na:** de vier maatregelen als gewone lijst onder de lead, en geen kader.

Die regel is in IR afgesproken met de lector (17 september 2026) en geldt sindsdien voor elk vak.

### 17. Bekend materiaal krijgt minder plaats

Alles even diep uitleggen is zelf een vorm van opvoering. Wat de student aantoonbaar al gezien heeft,
krijgt één regel en een verwijzing; het nieuwe krijgt de ruimte.

> **Voor:** De **richting** ligt vast in 1A en 2A, die altijd tegengesteld staan. De **snelheid** is
> een `analogWrite()` op de enable, en die pin moet daarom een PWM-pin zijn.
>
> **Na:** Richting en snelheid zijn die van labo 5: 1A en 2A staan altijd tegengesteld, en de
> snelheid is een `analogWrite()` op de enable, die daarom op een PWM-pin moet.

Dit is de tegenhanger van de terugkoppeling uit *Wat blijft*: die zegt dat je naar wat al behandeld
is verwijst, deze zegt dat je er dan ook korter over doet. Twee alinea's van gelijke lengte over iets
bekends en iets nieuws vertellen de student dat allebei even zwaar weegt, en dat klopt niet.

**Waar je op mag rekenen, verschilt per vak, en staat in het bestand van dat vak.** In een vak
waarvan de labo's op elkaar voortbouwen, mag een pagina rekenen op het vorige labo. In een vak waar
de groepen door onafhankelijke modules roteren, weet je niet welke labo's een student al gedaan
heeft, en is "zoals je in het labo over wireshark gezien hebt" voor de helft van de groep onzin.

Een module die de lector nog niet opengezet heeft, bestaat voor de student niet. Verwijs dus nooit
vooruit.

Zelfde rem als bij patroon 15. Een stijlronde krimpt een uitleg **alleen wanneer wat het vak als
bekend toelaat de stof aantoonbaar behandelt**, en de verwijzing komt ervoor in de plaats. Kan je dat
niet aanwijzen, dan is inkorten geen stijlingreep en gaat de alinea naar de vragenlijst van die
doorloop. Nieuwe stof korter maken valt hier nooit onder.

### 18. De student was niet bij het gesprek, en erft er wel de voorschriften van

Schrijf over het vak, nooit over de cursus als bouwwerk. Drie soorten zinnen sluipen hier binnen, en
ze hebben dezelfde oorzaak: ze bestaan door een gesprek waar de lezer niet bij was.

**De geschiedenis van het materiaal.** Wat vroeger ergens anders stond, wat verplaatst is, wat er
nieuw bij komt. Een student die dit vak voor het eerst doet heeft geen vorige versie gezien, en kan
zo'n zin dus alleen lezen als een raadsel.

> **Voor:** De theorie blijft wel op de site staan. De zes theoriepagina's en de zelftest lees je op
> het scherm.
>
> **Na:** Lees de zes theoriepagina's en maak de zelftest voor je aan de opdracht begint.

**De verantwoording van een keuze.** Waarom het een document is en geen invulveld, waarom het een PDF
is en geen pagina: dat is een afweging van de lector. De student heeft de instructie nodig, niet het
argument. Geef je hem het argument toch, dan lees je als iemand die zich verdedigt tegen een bezwaar
dat niemand gemaakt heeft.

> **Voor:** Vul dit document in terwijl je werkt en bewaar het op je OneDrive. Zo blijft het bewaard
> als je computer crasht of als je van pc wisselt, en kan je eraan verder werken wanneer je
> netwerkverbinding wegvalt.
>
> **Na:** Vul dit document in terwijl je werkt.

Let op wat er in dat voorbeeld overblijft. Schrap je alleen de verantwoording, dan houd je "bewaar
het op je OneDrive" over, en dat is een voorschrift dat uit hetzelfde gesprek komt. Zie het derde
spoor hieronder: de twee treden bijna altijd samen op, en het voorschrift is het makkelijkst om te
missen.

Het verraderlijke is dat zulke zinnen ontstaan op het moment dat je iets verandert of beslist, en dan
volkomen logisch klinken: het argument ligt vers op tafel en je schrijft het mee op. Een dag later
zijn het de enige zinnen op de pagina die niemand kan plaatsen. Let dus vooral op wat je schrijft
tijdens een verbouwing, en op de woorden die erbij horen: *blijft wel*, *staat nu*, *voortaan*,
*vanaf dit jaar*, *zoals vroeger*, en elke *zo blijft*, *zodat je* of *dan kan je* die uitlegt waarom
de opdracht is zoals ze is.

Dit is een leesregel en geen scriptregel: die woorden komen ook volkomen legitiem voor. "Vroeger was
parallel populair" op de pagina over seriële communicatie gaat over de techniek, niet over de cursus,
en een woordenlijst kan dat verschil niet zien.

De uitzondering is de vakinhoud zelf, en die is ruim. De geschiedenis van een standaard, een techniek
of een component hoort er wel bij, en een reden die iets **technisch** verklaart ook: "zet er een
pull-up op, anders zweeft de ingang" is geen verantwoording maar leerstof. De scheidslijn ligt niet
tussen instructie en reden, maar tussen een reden over het vak en een reden over de cursus.

**Het derde spoor is het voorschrift**, het vroegere patroon 19. Zeg wat je van de student nodig
hebt, niet hoe hij zijn werk organiseert. Waar hij zijn bestand bewaart, in welke map, met welke
naam, op welk toestel: dat is zijn zaak.

De toets is één vraag: **verandert het iets aan wat wij ontvangen of beoordelen?** Zo ja, dan is het
een instructie en hoort ze er. "Je dient dit in via de opdracht op Orion" blijft, want anders komt
het nergens aan. "Laat je schakeling controleren voor je verder gaat" blijft, want dat is de
werkvorm van het labo. "Zet je naam bovenaan" blijft, als je die naam nodig hebt om te verbeteren.
"Bewaar het op je OneDrive" gaat weg, want of hij dat doet zien wij nooit.

Dit is waarom de drie in één patroon staan. Een keuze die wij maken laat sporen na op de pagina: de
uitleg waarom en het voorschrift dat eruit volgt. De uitleg valt op, want die klinkt defensief. Het
voorschrift klinkt als een gewone instructie en blijft daardoor staan, ook nadat de uitleg geschrapt
is. Kom je het ene tegen, kijk dan meteen naar de zin ernaast.

Er is een randgeval: een voorschrift over de werkwijze **wordt** onze zaak zodra het de evaluatie
raakt. In een labo waar twee studenten samen één opstelling delen, is "spreek af wie zendt en wie
ontvangt" wél een instructie, want het bepaalt wat elk van beiden kan tonen. De vraag is niet of het
over zijn werkwijze gaat, maar of wij het merken.

### 20. Geen woord dat de lezer nog niet heeft

Een term gebruik je pas nadat de student hem gezien heeft, en waar er al een woord voor het ding
bestaat, is dat het woord. Dit was patroon 20 en 22: het eerste gaat over een naam die er nog niet
is, het tweede over een naam die er wel is en die je passeert.

**Een term komt na zijn uitleg.** De volgorde die telt is die van het Orion-menu, zoals `orion.json`
ze vastlegt. Wat de theoriepagina's van een labo uitleggen, is op de inleiding ervoor nog onbekend.

> **Voor:** Daarna werk je in de firmware op het moederbord: wat ze van de hardware ziet, waar ze
> haar instellingen bewaart en in welke volgorde ze een opstartbare schijf zoekt.
>
> **Na:** Daarna ga je de BIOS- of UEFI-omgeving in: wat ze over de hardware zegt, waar ze haar
> instellingen bewaart en in welke volgorde ze een opstartbare schijf zoekt.

`firmware` stond drie keer op de twee pagina's die een student als eerste opent, en werd uitgelegd
op de vijfde theoriepagina van dat labo. `BIOS` en `UEFI` staan wel in de titel van het labo, in het
Orion-menu en in de naam van de opdracht, dus die woorden heeft hij al gezien. Een lijst met
doelstellingen is de uitzondering, want die belooft juist wat hij nog niet kent.

**En geen algemener woord dan je hebt**, het vroegere patroon 22. Staat er een naam voor het ding,
gebruik die.

> **Voor:** Je haalt het toestel uit elkaar, fotografeert elk onderdeel en vult van elk component de
> specificaties in.
>
> **Na:** Je haalt de computer uit elkaar, fotografeert elk onderdeel en vult de specificaties ervan
> in.

Die ene zin had drie woorden voor twee dingen: `toestel` voor de computer, en `component` naast
`onderdeel` voor hetzelfde. Zo komt het algemenere woord meestal binnen, om herhaling te vermijden,
en die herhaling stoort de schrijver meer dan de lezer.

Twee dingen die deze helft uitdrukkelijk toelaat. **Een naam die eenmaal gevallen is, mag daarna
korter:** `het bord` na `het moederbord`, `de omgeving` na `de BIOS- of UEFI-omgeving`. Dat is geen
algemener woord maar dezelfde naam, verkort. En **wanneer het generieke woord meer dekt, is het het
juiste woord:** de opstartvolgorde en het bootmenu tonen een schijf, een stick of een netwerkkaart,
en `toestel` is wat die drie samen dekt.

**Waar dit vandaan komt.** Je schrijft een inleiding wanneer de hele module al in je hoofd zit, dus
het vocabulaire van de laatste pagina voelt als gedeelde grond, en dat is het alleen met jezelf.
Dezelfde oorzaak als patroon 18, met een ander voorwerp: 18 gaat over de geschiedenis van het
materiaal, dit over het vocabulaire. Patroon 17 regelt wat je uit een ander labo mag veronderstellen
en zegt niets over de volgorde binnen een labo, dus dit zat in het gat tussen die twee.

De toets, twee vragen. Staat het woord eerder in dezelfde reeks, of in de titel van het labo of van
het menu-item? En: bestaat er in deze tekst al een woord voor precies dit ding? Zo ja, dan is dat
het woord.

## Spelling en notatie

### `led`, niet `LED`

Dit is geen patroon, want er is niets opgesmukt aan een kapitaal. In de lopende tekst schrijf je
`led` en `leds`, met een hoofdletter alleen waar een zin of een titel begint.

> **Voor:** De LED zou moeten branden als je de D lijn van de zender op hoog zet.
>
> **Na:** De led hoort te branden als je de D-lijn van de zender hoog zet.

In code blijft alles zoals het is. `pinLED` is een naam die de student overtypt, en waar `"LED1"`
een boodschap is die over een bus gaat, is de kapitaal gegeven. `--audit` meldt daarom alleen `LED`
in een regel met prozaopmaak en laat alles binnen een `<pre>` met rust. Schrijft een pagina de
afkorting voluit, dan blijft `LED` staan in "LED staat voor Light Emitting Diode", met
`<!-- audit-skip: led-spelling -->` erbij.

### De naam van een standaard houdt zijn streepje, een mapnaam niet

In de lopende tekst schrijf je de standaard zoals de standaard zichzelf schrijft: **RS-485**,
**RS-232**. In een bestandsnaam, een mapnaam, een id in `orion.json` en een `<h1>` of `<title>` die
daarnaar verwijst, gebruik je de vorm zonder leesteken: `Labo/RS485/`, `rs485`, "Labo RS485".

Dat is dezelfde scheiding als bij `led` tegenover `pinLED`: proza volgt de taal, een identifier volgt
wat een pad en een sleutel kunnen dragen. Zonder die afspraak staan beide vormen door elkaar op één
pagina.

### Wat de student op zijn scherm terugvindt, blijft letterlijk

De student vergelijkt wat op zijn scherm staat met wat op de pagina staat, en elk verschil dat wij
aanbrengen is er een dat hij moet uitzoeken. Wat uit een toestel of uit software komt, neem je dus
over zoals het is: geen herformattering, geen ingekorte prompts, geen rechtgezette hoofdletters, ook
niet wanneer het lelijk staat.

Dat geldt voor twee soorten tekst. **Wat een toestel krijgt en terugstuurt:** een Cisco-configuratie,
terminaluitvoer, wat een controller meldt. De check houdt de regel `code-style` daarom bewust weg van
`.terminal-window` en `.config-window`. **Wat software op het scherm zet:** een menu, een knop, een
tabblad of een instelling schrijf je zoals de software het schrijft, in de taal van de software en
met dezelfde hoofdletters. Vertaal ze niet in de uitleg ("klik op tooldata aanmaken"), want dan moet
de student terugvertalen voor hij kan klikken.

Het vakwoord rond zo'n schermtekst mag wel Nederlands zijn wanneer het Nederlands een gangbaar woord
heeft. Kies één van de twee per pagina en blijf erbij (patroon 20).

Dit geldt niet voor code die de student overtypt in een taal met een huisstijl. Die volgt de
huisstijl: Allman-accolades en spaties rond de operatoren, afgedwongen door de regel `code-style`
voor de talen in `check.code_style_languages`.

### En, nog steeds: geen em-dashes

Geen `—` en geen `&mdash;`, nergens in de tekst. Gebruik een komma, een dubbele punt, een punt of
"en"/"maar". Dit is de enige stijlregel die de check afdwingt (regel `em-dash`), en
`python ../OrionTools/orion.py check --fix` herstelt ze.

## De proef

Bij twijfel over een alinea, drie vragen:

1. **Zou ik dit zo tegen een student zeggen die naast me zit?** Een pointe die je aan een tafel niet
   uitspreekt, hoort ook niet op de pagina.
2. **Wat gebeurt er als ik de laatste zin schrap?** Verdwijnt er informatie, dan hoort ze er. Voelt
   de alinea alleen minder af, dan was het een slotzin uit patroon 1.
3. **Staat het interessantste stuk in de hoofdzin?** Als je beste voorbeeld tussen haakjes of achter
   een dubbele punt staat, staat het op de verkeerde plaats.

Voor alles wat je schrijft terwijl je aan een repo verbouwt, nog twee (patroon 18):

4. **Zou deze zin er ook staan als de cursus altijd al zo geweest was?** Zo niet, dan gaat ze over
   ons werk en niet over het vak.
5. **Merken wij het als hij dit niet doet?** Zo niet, dan is het geen instructie maar bemoeienis.

Voor elk woord dat je op een pagina vroeg in een reeks zet, nog twee (patroon 20):

6. **Staat dit woord eerder in de reeks, of in de titel van het labo?** Zo niet, gebruik de naam die
   de student wel kent.
7. **Bestaat er in deze tekst al een woord voor precies dit ding?** Zo ja, dan is dat het woord.

En na elke herschrijving, want de zeven hierboven zeggen alleen wat weg mag:

8. **Welk feit staat er niet meer?** Ontbreekt er een, dan is de herschrijving fout, hoeveel
   patronen ze ook oplost.

Het ijkpunt, een pagina die volledig volgens dit document herschreven is en die je naast haar vorige
versie kan leggen, is per vak een ander en staat in het bestand van dat vak.
