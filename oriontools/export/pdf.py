"""Export een module of een labo naar een enkele PDF.

    python ../OrionTools/orion.py export-pdf 4            # module 4 (group=module)
    python ../OrionTools/orion.py export-pdf 4 5 test1    # op nummer of op id
    python ../OrionTools/orion.py export-pdf 6            # Labo 6 (group=lab)
    python ../OrionTools/orion.py export-pdf 6 --reference-only
    python ../OrionTools/orion.py export-pdf --all

Wat een argument aanwijst, hangt af van export_pdf.group in de vakconfig.

group=module (IR): een module kies je op haar nummer (het getal waarmee haar
titel in orion.json begint) of op haar id. Een submodule wordt een hoofdstuk in
de inhoudstafel, een geneste submodule krijgt de titel van haar ouder ervoor.

group=lab (Microcontrollers): een labo kies je op zijn nummer. Het labo is de
module in orion.json waarvan de submodules (Theorie, Downloads, Oefeningen) de
pagina's onder LaboN/ bevatten. Een pagina in export_pdf.oefeningen_map is een
oefening, een andere pagina is naslag; de naslag komt eerst, tenzij
--exercises-first. --reference-only laat de oefeningen weg en hangt -theorie
aan de naam: de versie die in downloads/ gepubliceerd wordt.

De naam van de PDF komt uit export_pdf.naam, met {code}, {id} en {n}, nooit uit
de titel: een titel die in Orion verandert, mag de naam van een gepubliceerde
PDF niet meenemen. Om dezelfde reden heet een labo op de cover "Labo N" en niet
naar zijn moduletitel.

De volgorde komt uit orion.json, niet uit de map: de volgorde van het
Orion-menu, submodule na submodule, en daarbinnen de topics. Een dropbox-topic
staat in de inhoudstafel als "indienen", zonder pagina.

Een link naar een pagina in de bundel wordt een sprong binnen de PDF. Een link
naar een ander bestand van de repo wordt gewone tekst en staat in het verslag
na de run. Een PDF verwijst nooit naar een adres van ons buiten de cursus: in
een PDF kan niemand zo'n adres achteraf nog aanpassen.

Elke pagina wordt uit haar HTML gehaald, statisch gemaakt (oplossingen,
spoilers en accordions open, checkboxes als lege vakjes, video's als zichtbare
link, JS-widgets zoals de QR-code als verwijzing naar de pagina online), en
achter een cover met inhoudstafel geplakt. Die ene bundel gaat daarna door
headless Chrome of Edge met --print-to-pdf.

Kwam uit de vakrepo's, waar IR het uit Microcontrollers had overgenomen en
verder gebouwd: modules naast labo's, geneste submodules, dropboxen in de
inhoudstafel, Brightspace-iframes als verwijzing, Panopto en youtube-nocookie
als video, en geen em-dash in de gegenereerde tekst. Dat geldt nu voor elk vak.

Dit is een auteurstool: hij draait nooit in CI of in de Stop-hook, en schrijft
alleen in --out (standaard paths.export, gitignored).

Opties:
    --out DIR         doelmap voor de PDF's (standaard paths.export)
    --no-solutions    studentenversie: knip de oplossingssecties eruit
    --page-numbers    laat Chrome zijn eigen kop- en voettekst zetten
                      (datum, titel, url, paginanummer)
    --html-only       schrijf alleen de gebundelde HTML, start Chrome niet
    --keep-html       schrijf de bundel naast de PDF, voor als er iets misgaat
    --chrome PAD      pad naar chrome.exe of msedge.exe (anders autodetectie,
                      of de omgevingsvariabele CHROME)
    --exercises-first (group=lab) oefeningen voor de naslag in plaats van erna
    --reference-only  (group=lab) alleen de theorie, zonder de oefeningen
"""

import argparse
import datetime
import html as html_mod
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from .. import repo
from ..chrome import zoek_chrome

# Een topic met zo'n extensie is een los document, geen pagina. Een vak voegt er
# eigen soorten aan toe met export_pdf.doc_exts_extra (IR: RobotStudio en CAD).
DOC_EXTS = ('.pdf', '.zip', '.docx', '.pptx', '.xlsx')

# Inline scripts die alleen een engine opstarten: die vallen gewoon weg.
INIT_ONLY = re.compile(r'^\s*initChecklistSync\s*\([^)]*\)\s*;?\s*$')


# ---------------------------------------------------------------- orion.json

def orion_modules(root):
    """De modules op het hoogste niveau van orion.json, in menuvolgorde."""
    path = root / 'orion.json'
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding='utf-8')).get('modules', [])


def pick_module(modules, key):
    """Een module op nummer ("4", het getal voor de punt in de titel) of op id."""
    for module in modules:
        if module['id'] == key:
            return module
        m = re.match(r'(\d+)\.', module['title'])
        if m and m.group(1) == key:
            return module
    return None


def orion_labs(modules, labo_map):
    """De labo's die orion.json beschrijft, als {'labo0': module}.

    Het labo is de module waarvan de submodules (Theorie, Downloads,
    Oefeningen) de pagina's onder LaboN/ bevatten. labo_map is paths.labo.
    """
    labs = {}
    patroon = re.compile(re.escape(labo_map) + r'(\d+)/')

    def walk(module, top):
        for sub in module.get('items', []):
            if 'items' not in sub:
                continue
            for topic in sub['items']:
                m = patroon.match(topic.get('page', ''))
                if m:
                    labs.setdefault('labo' + m.group(1), top)
            walk(sub, top)

    for module in modules:
        walk(module, module)
    return labs


# ----------------------------------------------------------------- ordering

def slugify(text):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', text.lower())).strip('-')


def collect_pages(root, orion_module, doc_exts, self_name=None, oefeningen_map=None,
                  exercises_first=False, reference_only=False):
    """Alle topics van een module, in de volgorde waarin ze in de PDF komen.

    Een submodule wordt de categorie van haar topics; een geneste submodule
    krijgt de titel van haar ouder ervoor. self_name is de bestandsnaam van de
    PDF die we net maken: het Orion-menu linkt die PDF zelf als download, en een
    bundel in haar eigen inhoudstafel leest als een fout; ze valt hier dus weg.

    Met oefeningen_map (group=lab) is een pagina in die map een oefening en een
    andere naslag, en komen de twee als blok na elkaar. Een dropbox telt daar
    als oefening: het is wat je na de oefening indient.
    """
    items, notes = [], []

    def walk(module, category):
        for topic in module.get('items', []):
            if 'items' in topic:
                sub = topic['title'] if category == orion_module['title'] \
                    else category + ' > ' + topic['title']
                walk(topic, sub)
                continue
            if 'dropbox' in topic:
                items.append({'kind': 'dropbox', 'category': category,
                              'title': topic['dropbox'], 'path': None, 'slug': ''})
                continue
            path = topic.get('page') or topic.get('file')
            if not path:
                continue
            if oefeningen_map is None:
                kind, prefix = 'page', 'p-'
            elif '/' + oefeningen_map + '/' in path:
                kind, prefix = 'exercise', 'ex-'
            else:
                kind, prefix = 'reference', 'ref-'
            item = {'kind': kind, 'category': category, 'title': topic['title'],
                    'slug': prefix + slugify(topic['id']), 'path': path}
            if path.lower().endswith(doc_exts):
                if self_name and os.path.basename(path).lower() == self_name.lower():
                    continue
                item['document'] = True
            items.append(item)

    walk(orion_module, orion_module['title'])

    if oefeningen_map is not None:
        ref = [i for i in items if i['kind'] == 'reference']
        ex = [] if reference_only else [i for i in items if i['kind'] != 'reference']
        items = ex + ref if exercises_first else ref + ex

    for item in items:
        if item['kind'] == 'dropbox':
            continue
        if item.get('document'):
            notes.append('los document, niet ingesloten: %s' % item['path'])
        elif not (root / item['path']).is_file():
            notes.append('pagina niet gevonden, overgeslagen: %s' % item['path'])
            item['missing'] = True
    return items, notes


# ------------------------------------------------------------ page rewriting

ATTR = r'''(?:"([^"]*)"|'([^']*)')'''


def attr(tag, name):
    m = re.search(r'\b' + name + r'\s*=\s*' + ATTR, tag, re.I)
    if not m:
        return None
    return m.group(1) if m.group(1) is not None else m.group(2)


def body_of(html):
    m = re.search(r'<body[^>]*>(.*)</body>', html, re.S | re.I)
    return m.group(1) if m else html


def strip_scripts(html):
    """Haal alle scripts weg; meld waar een echte widget stond.

    Een script met src, een leeg script en een dat alleen een engine opstart
    (INIT_ONLY) vallen stil weg; al de rest was iets wat de lezer zag.
    """
    widgets = []

    def repl(m):
        tag, inner = m.group(0), m.group(1) or ''
        if attr(tag, 'src') or not inner.strip() or INIT_ONLY.match(inner):
            return ''
        widgets.append(True)
        return ('<div class="pdf-note"><strong>Interactief onderdeel.</strong> '
                'Dit stuk werkt alleen in de browser. Open de pagina online om het te gebruiken.</div>')

    html = re.sub(r'<script\b[^>]*>(.*?)</script>', repl, html, flags=re.S | re.I)
    return html, len(widgets)


def rewrite_iframes(html):
    """Een iframe drukt niet af; zet er de link naartoe in de plaats."""
    def repl(m):
        tag = m.group(0)
        src = attr(tag, 'src') or ''
        title = attr(tag, 'title') or ''
        # Een pad onder /d2l/ is een onderdeel van Brightspace zelf (een LTI-quicklink):
        # buiten Orion is er geen adres dat werkt.
        if src.startswith('/d2l/'):
            return ('<div class="pdf-note"><strong>Onderdeel in Orion.</strong> '
                    'Open deze pagina in Orion om het te bekijken.</div>')
        video = any(host in src for host in ('youtube', 'vimeo', 'panopto'))
        label = 'Video' if video else 'Ingesloten pagina'
        vid = re.search(r'youtube(?:-nocookie)?\.com/embed/([A-Za-z0-9_-]+)', src)
        link = 'https://www.youtube.com/watch?v=' + vid.group(1) if vid else html_mod.unescape(src)
        extra = ''
        if title and title.lower() not in ('youtube video player', ''):
            extra = ' ' + html_mod.escape(title)
        return ('<div class="pdf-note"><strong>%s.</strong>%s<br><a href="%s">%s</a></div>'
                % (label, extra, html_mod.escape(link), html_mod.escape(link)))

    return re.sub(r'<iframe\b[^>]*>.*?</iframe>|<iframe\b[^>]*/?>', repl, html, flags=re.S | re.I)


def rewrite_images(root, html, page_dir, missing):
    """Relatieve src -> absolute file:-url, zodat de bundel elders kan staan."""
    def repl(m):
        tag = m.group(0)
        src = attr(tag, 'src')
        if not src or src.startswith(('http', 'data:', 'file:')):
            return tag
        target = (root / page_dir / src).resolve()
        if not target.is_file():
            missing.append(os.path.relpath(target, root).replace('\\', '/'))
            alt = attr(tag, 'alt') or 'afbeelding ontbreekt'
            return ('<div class="pdf-missing-img"><strong>Afbeelding ontbreekt</strong><br>%s</div>'
                    % html_mod.escape(alt))
        return tag.replace(src, target.as_uri())

    return re.sub(r'<img\b[^>]*?/?>', repl, html, flags=re.I)


def rewrite_links(root, html, page_dir, in_bundle, unresolved, unlinked):
    """Interne links worden ankers in de bundel, de rest van de repo gewone tekst.

    Een <a> zonder href is geen link meer, en Bootstrap tekent hem als gewone
    tekst. De sluittag blijft dus gewoon staan.
    """
    def repl(m):
        tag = m.group(0)
        href = attr(tag, 'href')
        if not href or href.startswith(('http', 'mailto:', 'tel:', '#', 'file:')):
            return tag
        base, _, frag = href.partition('#')
        target = os.path.relpath(os.path.normpath(os.path.join(page_dir, base)), '.').replace('\\', '/')
        if target.lower() in in_bundle:
            slug = in_bundle[target.lower()]
            new = '#' + (slug + '--' + frag if frag else slug)
        elif (root / target).exists():
            unlinked.append(target)
            return re.sub(r'\s+(?:href|target|rel)\s*=\s*' + ATTR, '', tag, flags=re.I)
        else:
            unresolved.append(href)
            return tag
        return tag.replace(href, new)

    return re.sub(r'<a\b[^>]*?>', repl, html, flags=re.I)


def namespace_ids(html, slug):
    """Elke id krijgt de sectie-slug ervoor.

    In een bundel van twintig pagina's staat "het-schema" anders vijf keer, en
    dan wijst elke link naar de eerste.
    """
    html = re.sub(r'(\bid\s*=\s*")([^"]+)(")', lambda m: m.group(1) + slug + '--' + m.group(2) + m.group(3), html)
    html = re.sub(r'(\bhref\s*=\s*")#([^"]+)(")', lambda m: m.group(1) + '#' + slug + '--' + m.group(2) + m.group(3), html)
    return html


def find_block_end(html, start):
    """Index net na het </div> dat hoort bij de <div> op positie start."""
    depth, i = 0, start
    for m in re.finditer(r'<div\b[^>]*>|</div>', html[start:], re.I):
        depth += 1 if m.group(0).lower().startswith('<div') else -1
        i = start + m.end()
        if depth == 0:
            return i
    return i


HEADING_BEFORE = re.compile(r'<h[1-6]\b[^>]*>\s*Oplossing\s*</h[1-6]>\s*$', re.I)


def drop_solutions(html):
    """Studentenversie: de oplossing eruit, met haar eigen titel erbij."""
    while True:
        m = re.search(r'<div\b[^>]*class="[^"]*\bsolution-container\b[^"]*"[^>]*>', html, re.I)
        if not m:
            return html
        cut = m.start()
        heading = HEADING_BEFORE.search(html, max(0, cut - 200), cut)
        if heading:
            cut = heading.start()
        html = html[:cut] + html[find_block_end(html, m.start()):]


def transform_page(root, item, in_bundle, report, keep_solutions):
    path = item['path']
    page_dir = os.path.dirname(path)
    raw = (root / path).read_text(encoding='utf-8')
    body = body_of(raw)
    body, widgets = strip_scripts(body)
    if widgets:
        report['widgets'].append(path)
    if not keep_solutions:
        body = drop_solutions(body)
    body = rewrite_iframes(body)
    body = rewrite_images(root, body, page_dir, report['missing_images'])
    body = namespace_ids(body, item['slug'])
    body = rewrite_links(root, body, page_dir, in_bundle, report['unresolved'], report['unlinked'])
    return body


# -------------------------------------------------------------- bundle & pdf

PRINT_CSS = """
@page { size: A4; margin: 15mm 12mm 13mm 12mm; }

html, body { background: #fff !important; }
body {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
    padding-top: 0;
    padding-bottom: 0;
}

/* Een A4 is bij het afdrukken zo'n 697px breed, en daar geeft Bootstrap de
   .container een max-width van 540px: een smalle kolom met een brede witte
   rand ernaast. De paginamarge hierboven doet dat werk al. */
.container {
    max-width: none !important;
    width: auto !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
}
.pdf-doc { break-before: page; }
.pdf-toc .pdf-toc-drop { color: #6b7280; font-size: 0.85rem; }
.pdf-doc:first-of-type { break-before: auto; }
.pdf-doc h1 { break-after: avoid; }
h2, h3, h4 { break-after: avoid; }
pre, figure, table, .info-box, .pdf-note, .checklist li { break-inside: avoid; }
img { max-width: 100% !important; height: auto !important; }

/* Alles wat achter een klik zit, staat in de PDF gewoon open. */
.spoiler-content, .solution-content { display: block !important; }
.spoiler-container > .hidden { display: block !important; }
.spoiler-container > .button { display: none !important; }
.btn-spoiler, .solution-reveal-btn, .btn-copy { display: none !important; }
.accordion-collapse { display: block !important; height: auto !important; visibility: visible !important; }
.accordion-button { pointer-events: none; }
.accordion-button::after { display: none !important; }

/* Een ratio-wrapper zonder iframe erin is een leeg blok van 300 pixels hoog. */
.ratio { position: static !important; height: auto !important; }
.ratio::before { display: none !important; }
.ratio > * { position: static !important; width: auto !important; height: auto !important; }

/* Checkboxes drukken standaard leeg wit af: geef ze een rand. */
.checklist input[type="checkbox"] {
    -webkit-appearance: none;
    appearance: none;
    width: 0.95em; height: 0.95em;
    border: 1.5px solid #6b7280;
    border-radius: 3px;
    display: inline-block;
    vertical-align: -0.12em;
    background: #fff;
}

.pdf-note, .pdf-missing-img {
    border: 1px dashed #9ca3af;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 14px 0;
    font-size: 0.92rem;
    color: #374151;
    background: #f9fafb;
}
.pdf-missing-img { text-align: center; }

.pdf-cover { text-align: center; padding-top: 28vh; }
.pdf-cover .pdf-course { text-transform: uppercase; letter-spacing: 0.22em; font-size: 0.85rem; color: #6b7280; }
.pdf-cover h1 { font-size: 3.4rem; margin: 0.3em 0 0.2em; border: 0; }
.pdf-cover .pdf-sub { font-size: 1.05rem; color: #4b5563; }
.pdf-cover .pdf-meta { margin-top: 3.5em; font-size: 0.82rem; color: #6b7280; }

.pdf-toc { break-before: page; }
.pdf-toc h2 { margin-top: 1.6em; font-size: 1.15rem; }
.pdf-toc ol { list-style: none; padding-left: 0; }
.pdf-toc li { padding: 4px 0; border-bottom: 1px dotted #d1d5db; }
.pdf-toc a { text-decoration: none; }
.pdf-toc .pdf-toc-doc { color: #6b7280; font-size: 0.85rem; }
.pdf-kicker { text-transform: uppercase; letter-spacing: 0.14em; font-size: 0.72rem; color: #6b7280; margin-bottom: 0.4em; }
"""

# main.js bouwt spoilers en accordions pas na het laden op, en highlight.js
# komt daar nog eens achteraan. De CSS hierboven regelt het uitklappen, dit
# ruimt alleen op wat daarna nog verschijnt.
PRINT_JS = """
(function () {
    function statisch() {
        document.querySelectorAll('.spoiler-content, .solution-content').forEach(function (el) {
            el.classList.add('active');
        });
        document.querySelectorAll('.accordion-collapse').forEach(function (el) {
            el.classList.add('show');
        });
        document.querySelectorAll('.accordion-button').forEach(function (el) {
            el.classList.remove('collapsed');
            el.setAttribute('aria-expanded', 'true');
        });
        document.querySelectorAll('.btn-spoiler, .solution-reveal-btn, .btn-copy').forEach(function (el) {
            el.remove();
        });
        // main.js zet een figure-zoom in een link naar img.src, en in de bundel
        // is dat een file:-pad: een dode link naar de schijf van wie exporteert.
        document.querySelectorAll('a.zoom-link').forEach(function (el) {
            while (el.firstChild) el.parentNode.insertBefore(el.firstChild, el);
            el.remove();
        });
    }
    document.addEventListener('DOMContentLoaded', statisch);
    var n = 0;
    var timer = setInterval(function () { statisch(); if (++n > 20) clearInterval(timer); }, 250);
})();
"""


def cover_subtitel(root, items, keep_solutions, per_labo):
    """De regel onder de titel op de cover.

    Een labo zegt of het naslag en oefeningen bevat; een module heeft die
    indeling niet en zegt alleen of er oplossingen in staan.
    """
    if per_labo:
        has_exercises = any(i['kind'] == 'exercise' for i in items)
        subtitel = 'Naslag en oefeningen' if has_exercises else 'Naslag'
        if has_exercises and keep_solutions:
            subtitel += ', met oplossingen'
        return subtitel
    has_solutions = any('solution-container' in (root / i['path']).read_text(encoding='utf-8')
                        for i in items if i.get('path') and not i.get('missing')
                        and not i.get('document'))
    return 'met oplossingen' if has_solutions and keep_solutions else ''


def kicker(item, per_labo):
    """Het kleine opschrift boven een pagina: de soort bij een labo, anders de submodule."""
    if per_labo:
        return 'Naslag' if item['kind'] == 'reference' else 'Oefening'
    return item['category']


def build_bundle(root, course, title, items, report, keep_solutions, per_labo):
    today = datetime.date.today().strftime('%d/%m/%Y')
    in_bundle = {i['path'].lower(): i['slug'] for i in items
                 if i.get('path') and not i.get('missing') and not i.get('document')}

    parts = ['<!DOCTYPE html>', '<html lang="nl">', '<head>', '<meta charset="utf-8">',
             '<title>%s</title>' % html_mod.escape(title),
             '<link rel="stylesheet" href="https://tdmts.github.io/OrionCSS/style.css">',
             '<script src="https://tdmts.github.io/OrionCSS/main.js"></script>',
             '<style>%s</style>' % PRINT_CSS,
             '<script>%s</script>' % PRINT_JS,
             '</head>', '<body>', '<div class="container">']

    parts.append('<div class="pdf-cover">'
                 '<div class="pdf-course">%s</div>'
                 '<h1>%s</h1>'
                 '<div class="pdf-sub">%s</div>'
                 '<div class="pdf-meta">Gegenereerd op %s</div>'
                 '</div>'
                 % (html_mod.escape(course), html_mod.escape(title),
                    cover_subtitel(root, items, keep_solutions, per_labo), today))

    toc = ['<div class="pdf-toc"><h1>Inhoud</h1>']
    current = None
    for item in items:
        if item['category'] != current:
            if current is not None:
                toc.append('</ol>')
            current = item['category']
            toc.append('<h2>%s</h2><ol>' % html_mod.escape(current))
        if item['kind'] == 'dropbox':
            toc.append('<li>%s <span class="pdf-toc-drop">indienen in Orion</span></li>'
                       % html_mod.escape(item['title']))
        elif item.get('document'):
            toc.append('<li>%s <span class="pdf-toc-doc">los bestand</span></li>'
                       % html_mod.escape(item['title']))
        elif item.get('missing'):
            continue
        else:
            toc.append('<li><a href="#%s">%s</a></li>'
                       % (item['slug'], html_mod.escape(item['title'])))
    toc.append('</ol></div>')
    parts.append(''.join(toc))

    for item in items:
        if item['kind'] == 'dropbox' or item.get('missing') or item.get('document'):
            continue
        parts.append('<section class="pdf-doc" id="%s"><div class="pdf-kicker">%s</div>%s</section>'
                     % (item['slug'], html_mod.escape(kicker(item, per_labo)),
                        transform_page(root, item, in_bundle, report, keep_solutions)))

    parts += ['</div>', '</body>', '</html>']
    return '\n'.join(parts)


def print_pdf(chrome, bundle, pdf, page_numbers):
    with tempfile.TemporaryDirectory() as profile:
        cmd = [
            chrome, '--headless=new', '--disable-gpu', '--no-first-run',
            '--no-default-browser-check', '--disable-extensions',
            '--user-data-dir=' + profile,
            '--run-all-compositor-stages-before-draw',
            '--virtual-time-budget=20000',
            '--print-to-pdf=' + str(pdf),
            Path(bundle).as_uri(),
        ]
        if not page_numbers:
            cmd[-2:-2] = ['--no-pdf-header-footer', '--print-to-pdf-no-header']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if not pdf.is_file():
        sys.stderr.write(result.stdout + result.stderr + '\n')
        return False
    return True


# ------------------------------------------------------------------ main

def kies(args, ap, vak, modules, per_labo):
    """[(nummer, orion-module, titel)] voor de gevraagde labo's of modules."""
    if per_labo:
        labs = orion_labs(modules, vak.config['paths']['labo'])
        if args.all:
            keys = sorted(labs, key=lambda k: int(re.sub(r'\D', '', k) or 0))
        elif args.keys:
            keys = ['labo' + re.sub(r'\D', '', k) for k in args.keys]
        else:
            ap.error('geef een labonummer op, of --all')
        return [(k[len('labo'):], labs.get(k), 'Labo ' + k[len('labo'):]) for k in keys]

    if args.all:
        selected = list(modules)
    elif args.keys:
        selected = []
        for key in args.keys:
            module = pick_module(modules, key)
            if module is None:
                sys.exit('%s is geen modulenummer of id in orion.json' % key)
            selected.append(module)
    else:
        ap.error('geef een modulenummer of id op, of --all')
    out = []
    for module in selected:
        m = re.match(r'(\d+)\.', module['title'])
        out.append((m.group(1) if m else '', module, module['title']))
    return out


def main(argv):
    ap = argparse.ArgumentParser(prog='orion.py export-pdf',
                                 description='Exporteer een module of labo naar PDF.')
    repo.voeg_repo_toe(ap)
    ap.add_argument('keys', nargs='*', metavar='module',
                    help='modulenummers of ids (group=module), labonummers (group=lab)')
    ap.add_argument('--all', action='store_true', help='elke module of elk labo uit orion.json')
    ap.add_argument('--out', default=None, help='doelmap (standaard paths.export)')
    ap.add_argument('--no-solutions', action='store_true', help='studentenversie zonder oplossingen')
    ap.add_argument('--page-numbers', action='store_true', help='kop- en voettekst van Chrome mee afdrukken')
    ap.add_argument('--html-only', action='store_true', help='alleen de bundel-HTML, geen PDF')
    ap.add_argument('--keep-html', action='store_true', help='bewaar de bundel-HTML naast de PDF')
    ap.add_argument('--chrome', help='pad naar chrome.exe of msedge.exe')
    ap.add_argument('--exercises-first', action='store_true', help='(group=lab) oefeningen voor de naslag')
    ap.add_argument('--reference-only', action='store_true',
                    help='(group=lab) alleen de theorie, zonder de oefeningen')
    args = ap.parse_args(argv)

    vak = repo.vind(args)
    root = vak.root
    cfg = vak.config['export_pdf']
    if cfg['group'] not in ('lab', 'module'):
        sys.exit('export_pdf.group moet "lab" of "module" zijn, niet %r' % cfg['group'])
    per_labo = cfg['group'] == 'lab'
    if not per_labo and (args.exercises_first or args.reference_only):
        ap.error('--exercises-first en --reference-only gelden alleen bij export_pdf.group "lab"')
    doc_exts = DOC_EXTS + tuple(e.lower() for e in cfg['doc_exts_extra'])

    selected = kies(args, ap, vak, orion_modules(root), per_labo)

    chrome = None
    if not args.html_only:
        chrome = zoek_chrome(args.chrome, verplicht=False)
        if not chrome:
            sys.exit('Geen Chrome of Edge gevonden. Geef --chrome PAD op, zet CHROME, '
                     'of draai met --html-only en druk de HTML zelf af.')

    out_dir = root / args.out if args.out else vak.pad('export')
    out_dir.mkdir(parents=True, exist_ok=True)
    keep_solutions = not args.no_solutions
    failures = 0

    for n, module, title in selected:
        if module is None:
            print('%s staat niet in orion.json, overgeslagen' % title)
            failures += 1
            continue
        # De naam komt uit de config, niet uit de titel: zie de kop van dit bestand.
        stem = cfg['naam'].format(code=vak.code, id=module['id'], n=n)
        if args.reference_only:
            stem += '-theorie'
        if not keep_solutions:
            stem += '-student'
        items, notes = collect_pages(root, module, doc_exts, stem + '.pdf',
                                     cfg['oefeningen_map'] if per_labo else None,
                                     args.exercises_first, args.reference_only)
        pages = [i for i in items if i['kind'] != 'dropbox'
                 and not i.get('missing') and not i.get('document')]
        if not pages:
            if per_labo or not args.all:
                print('%s heeft geen pagina\'s in orion.json' % title)
                failures += 1
            continue

        report = {'missing_images': [], 'unresolved': [], 'unlinked': [], 'widgets': []}
        bundle_html = build_bundle(root, vak.titel, title, items, report, keep_solutions, per_labo)

        pdf = out_dir / (stem + '.pdf')
        bundle_path = out_dir / (stem + '.html') if (args.html_only or args.keep_html) \
            else Path(tempfile.gettempdir()) / (stem + '-bundle.html')
        bundle_path.write_text(bundle_html, encoding='utf-8')

        if per_labo:
            print('\n%s: %d pagina\'s (%d naslag, %d oefeningen)'
                  % (title, len(pages),
                     sum(1 for p in pages if p['kind'] == 'reference'),
                     sum(1 for p in pages if p['kind'] == 'exercise')))
        else:
            print('\n%s: %d pagina\'s' % (title, len(pages)))

        if args.html_only:
            print('  bundel: %s' % os.path.relpath(bundle_path, root))
        else:
            if print_pdf(chrome, bundle_path, pdf, args.page_numbers):
                print('  PDF:    %s (%.1f MB)' % (os.path.relpath(pdf, root), pdf.stat().st_size / 1e6))
            else:
                print('  PDF mislukt, Chrome gaf niets terug')
                failures += 1
            if args.keep_html:
                print('  bundel: %s' % os.path.relpath(bundle_path, root))
            elif bundle_path.is_file() and not args.html_only:
                bundle_path.unlink()

        for note in notes:
            print('  ! %s' % note)
        for img in sorted(set(report['missing_images'])):
            print('  ! afbeelding ontbreekt: %s' % img)
        for href in sorted(set(report['unresolved'])):
            print('  ! link niet gevonden: %s' % href)
        for target in sorted(set(report['unlinked'])):
            print('  i link naar %s is gewone tekst geworden, want die staat niet in deze bundel' % target)
        for page in sorted(set(report['widgets'])):
            print('  i interactief onderdeel vervangen door een verwijzing: %s' % page)

    return 1 if failures else 0
