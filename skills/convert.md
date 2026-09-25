# orion-convert: turn source content into an Orion page

The shared procedure behind every course's `orion-convert` skill. The skill in the course points
here and adds that course's page types, component habits and code conventions; those differ more
between courses than anything else in the skills, so read both before the first page.

The component reference with the exact markup of every component is
`../OrionContent/template.html` (`tdmts/OrionContent`). Read it before you use a component you have
not used this session, rather than reproducing markup from memory.

**The output must pass `python ../OrionTools/orion.py check`.** Running it is the last step of the
process, and a green result is part of "done": the same check runs in CI, so a red result here is a
red X on the user's next push.

## Where the source comes from

- **One page**: raw HTML pasted from Brightspace or CKEditor, plain text or Markdown, or an existing
  page that needs to be brought up to current conventions. If it is not clear what the user gave
  you, ask them to paste the content or point at a file.
- **A whole Brightspace course** is never pasted topic by topic. Ask for a course export zip and run
  `python ../OrionTools/orion.py import-brightspace <export.zip>`. That stages every topic as raw
  HTML in `_incoming/NNN-title.html`, with the module, title, order and kind in a header comment,
  and self-hosts the images into `img/` with the `/content/enforced/` sources rewritten. Then
  convert per staged file, working down `_incoming/WORKLIST.md`.

Where a page goes and what it is called is decided with the user, never guessed. A course that
agreed the whole mapping up front keeps it in a file (its skill says which); otherwise suggest a
default derived from the `<h1>` and confirm.

## Every page is a topic in orion.json

Brightspace serves every page itself through OrionSync, each page a topic of its own in the Orion
menu, built from `orion.json`. There is no navigation of our own: no hub of links, no nav row, no
"volgende". So for every page:

- **It has a topic in `orion.json`** at its place in the menu. The `id` is lowercase letters,
  digits and dashes and stays fixed once synced, since the sync keeps the Brightspace topic under
  it. Show the user the entry and where it goes: its position is the menu order. Rule
  `orion-orphan` fails a page nobody can reach.
- **No link loads another page into the frame.** Orion's menu does not follow the frame. Name the
  page and drop the link ("staat bij **Theorie**"), or open it with
  `target="_blank" rel="noopener"` when the student needs it beside the page. Rule `topic-frame`
  fails anything else, a link carried over from the source included.
- **A file the student downloads** (a datasheet, a start file) is linked by its relative path. That
  is a download, not a page, so `topic-frame` leaves it alone.
- **Load nothing but OrionCSS** (`style.css` and `main.js`, by absolute URL, see the skeleton),
  unless the course's skill names a script of its own. `main.js` drives every reveal. The export
  drags along the old HOGENT template (a stylesheet under `/shared/HTML-Template-Library`,
  Bootstrap 3, jQuery, `fonts.css`); all of it goes.

## Process

1. **Read the source**, and for a staged file its header comment.
2. **Keep the language and the content.** Conversion changes markup, not what the page teaches. Do
   not add explanations, do not rewrite sentences for style (that is `orion-style`, a separate
   pass), and do not fix language errors: list them in your report instead. The course's skill says
   where it authors something itself.
3. **Build the page** with the skeleton and the component rules below.
4. **Fix every relative path for the page's depth.** The importer wrote `../../img/` for
   everything; a page one folder deep needs `../img/`.
5. **Write the page** to its agreed path. If the file already exists, ask before overwriting.
6. **Add or check its topic in `orion.json`**, and `git add` the page and any image you added: the
   check sees only tracked files, and OrionSync mirrors only tracked files.
7. **Run the check** and fix what it reports about your pages. Other pages may still be red while a
   conversion is in progress; judge only your own.
8. **Report**: what you changed beyond markup, every `TODO-*` placeholder, every remote asset you
   downloaded, every `src` the user should double check, every judgement call, and every language
   error you left in place.

## Base page skeleton

```html
<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{Titel}</title>
    <link rel="stylesheet" href="https://tdmts.github.io/OrionCSS/style.css">
    <script type="text/javascript" src="https://tdmts.github.io/OrionCSS/main.js"></script>
</head>
<body>
<div class="container">
    <h1>{Titel}</h1>
    <p class="lead">{Wat deze pagina doet, in een of twee zinnen}</p>

    <h2 id="{slug}">{Sectietitel}</h2>
    {...}
</div>
</body>
</html>
```

- The OrionCSS URLs stay absolute; OrionSync rewrites them to its mirror on the way up, and a local
  preview still styles.
- `<title>` and `<h1>` are the page's title, the same string as its `title` in `orion.json`.
- **The `lead`**, on the pages where the course puts one (`check.audit.lead_patterns` in its
  `oriontools.json`). Use the source's own introductory sentence when it has one. When it has none,
  write one sentence that says what the page does, built only from what the page itself says: no new
  facts, and none of the stock openers of SCHRIJFSTIJL.md pattern 9.
- Drop the source's empty filler: `<p>&nbsp;</p>`, `<br>&nbsp;`, inline `style="text-align:
  justify"`, the `hogent_ckeditor_*` wrapper divs, an `<hr>` used as a spacer between every
  paragraph (keep one that separates real sections), and `<strong>` around a whole heading.
- Every `<h2>` gets a slugified `id`: lowercase, spaces become hyphens, punctuation and diacritics
  stripped ("Deel 1: Targets" becomes `deel-1-targets`). No ids on `<h3>` and `<h4>`.

## Component mapping, conservative by default

Only reach for a component when the source is an **unambiguous** match. When in doubt, plain
`<p>`, `<ul>`, `<ol>`. **Keep a component the source already uses** (an existing `info-box`,
`steps-container` or `accordion-container` stays, apart from path and filler fixes). The course's
skill adds its own rows.

| Source pattern | Component | Notes |
|---|---|---|
| Paragraph prefixed "Let op:", "Waarschuwing:", "Belangrijk:" | `.info-box` + `.info-title.warning` | Keep the label, do not invent one |
| Paragraph prefixed "Tip:" | `.info-box` + `.info-title.tip` | |
| Paragraph prefixed "Opmerking:" | `.info-box` + `.info-title.remark` | |
| Steps explicitly labelled "Stap 1", "Stap 2" | `.steps-container` with `.step-item[data-title]` | Not just any ordered list |
| Questions with an answer the student checks afterwards | `<ol class="vragen">`, `class="juist"` on the correct option, `<div class="oplossing">` with the answer or reasoning | Exactly one option is `juist`; an open question always has an `oplossing`. `main.js` makes the reveal |
| FAQ, a hint, a worked calculation, optional extra information | `.accordion-container` > `.accordion-item` > `<div class="title">` | The title says what is behind the click, never "Toon antwoord"; a hint opens with `Hint:` |
| *The* solution of an exercise | `.solution-container` under an `<h2>` whose id starts with `oplossing` | Only there: the reveal is one-way, and `solution-placement` fails it anywhere else. `.spoiler-container` is retired |
| `<table>` | `.table-responsive` > `.table.table-striped.table-bordered.align-middle` | `<caption>` only when the source has a table title |
| Terminal session (lines with a shell prompt) | `.terminal-window` with `.term-line`, `.term-prompt`, `.term-cmd`, `.term-out` | Only for a real session, not any code |
| Config listing with changed and new lines marked | `.config-window` with `.conf-line.mod`, `.conf-line.new` | Only when the source makes the distinction |
| LaTeX-style math | `.math-tex` | Inline for `$...$`, a block `<div>` for `$$...$$` |
| Image | `<figure class="figure w-100 text-center figure-zoom">` with `<img class="img-fluid">` and, when the source has one, `<figcaption class="figure-caption">` | Inside a list item the `<figure>` sits in the `<li>` |
| YouTube | `.video-container` > `.ratio.ratio-16x9` > iframe with `frameborder="0"`, `allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"`, `referrerpolicy="strict-origin-when-cross-origin"`, `allowfullscreen` | Keep the `src` exactly. Without `referrerpolicy` YouTube shows error 153 |
| Panopto (`hogent.cloud.panopto.eu/.../Embed.aspx`) | `.video-container` > `.ratio.ratio-16x9` > iframe with `allowfullscreen` and `allow="autoplay"` | Keep the `src` exactly |
| Everything else | plain `<p>`, `<ul>`/`<ol>`, `<strong>`, `<a>` | Do not force a component |

## Code blocks

`<pre class="code-wrapper language-<taal> linenumbers show-language">`, with the real highlight.js
name of the language. Which languages a course allows, and which ones carry no `show-language`
badge, are `check.audit.code_languages` and `check.audit.code_no_badge` in its `oriontools.json`;
`--audit` reports a block that deviates. An unknown `language-*` makes highlight.js throw, which
stops every later block on the page from rendering. Escape `<`, `>` and `&` inside a block. Inline
code, a command or a signal name in prose is `<code>`.

## Media

**Every image is self-hosted in the repo-root `img/`.** A remote `<img src="http...">` is a check
failure, and a hotlink rots mid-semester.

- Images the importer staged are already in `img/`: fix the relative path and write a real `alt`.
  `alt="image"` says nothing; describe what the image shows, from the text around it. Do not
  describe what you cannot infer.
- **Do not rename an image in `img/`** while pages are converted in parallel.
- A remote image: download it into `img/` under a descriptive name (`servo-aansluiting.png`, not
  `image.847213.png`), `git add` it, point the `src` at it. If the host blocks the download, retry
  with a browser `User-Agent`; some CDNs return an HTML challenge page that is easy to mistake for
  the image.
- **A Chamilo image** (`chamilo-downloads.hogent.be`): download it like any remote image. The
  DocumentDownloader URL still answers once `&amp;` is unescaped to `&`; look at the image to check
  it matches the text. Only if the download fails: a placeholder `img/TODO-<page-slug>-<n>.png`,
  depth-fixed, with the original URL in a comment right above the figure. The check reports a
  `TODO-*` as a warning.
- **A `/content/enforced/...` path** the importer could not resolve: never keep it, since it names
  this year's course and needs a login. Ask the user for the file or a working URL, and report it.

## Links

- External sites: keep, with `target="_blank" rel="noopener"`.
- `mailto:` links stay.
- A Brightspace quicklink (`/d2l/common/dialogs/quickLink/...`): keep it exactly and report it,
  because the `ou` in it ties it to this year's course.

## Prose

`SCHRIJFSTIJL.md` in the course root, on top of the shared base `../OrionTools/SCHRIJFSTIJL.md`, is
the rule, and it applies to every sentence you **write**: a `lead`, an `alt`, a `figcaption`, a
heading you had to invent, a solution. The prose you **carry over** is left for the `orion-style`
pass, with one exception that the check enforces: **no em-dashes** (`—`, `&mdash;`) anywhere. Use a
comma, a colon or a period.
