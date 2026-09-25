# orion-pdf: a module or lab as one printable PDF

The shared procedure behind the `orion-pdf` skill of a course that configures `export_pdf` in its
`oriontools.json`. The skill in the course points here and adds what that course does differently;
read both. A course without `export_pdf` prints other things (a syllabus, a handout, a verslag) with
their own commands, and has no `orion-pdf` skill.

Everything here is `python ../OrionTools/orion.py export-pdf`. Do not build a PDF by hand, and do not
print pages one at a time: the ordering, the static rewriting and the link handling live in that
command, and a hand-made bundle drifts from the Orion menu the first time `orion.json` changes.

```
python ../OrionTools/orion.py export-pdf 4          # one module or lab, by number
python ../OrionTools/orion.py export-pdf 4 5        # several
python ../OrionTools/orion.py export-pdf --all
```

`export_pdf.group` decides what a number means: `lab` counts labs, `module` counts the top-level
modules of `orion.json` (and also takes an id). `export_pdf.naam` decides the file name, never the
title, so a title changed in Orion cannot rename a PDF someone already has.

## What it produces

A cover, a table of contents, then the pages in menu order. Each page is stripped of its scripts
and made static: solutions open, accordions expanded, embedded video replaced by a visible link, a
widget replaced by a note that it only works online. Ids are namespaced per page, so links between
pages of the same bundle become internal jumps. A link to any other file of the repo becomes plain
text: a PDF cannot be corrected once downloaded, and must never point at an address of ours. A
`file` topic (a datasheet, a start file) is listed in the table of contents and never inlined.

It prints through headless Chrome or Edge, found automatically (else `--chrome PATH` or `$CHROME`),
and writes only into `_export/`, which git ignores. The PDF is derived material: regenerate it,
never edit it, and commit it only where the course says a copy is published.

## Options

`export-pdf --help` lists them. The ones worth knowing:

- `--no-solutions`: drops each `.solution-container` with its `Oplossing` heading.
- `--page-numbers`: Chrome's own header and footer. Off by default, because the footer also prints
  the temp path of the bundle.
- `--html-only` / `--keep-html`: keep the bundled HTML to inspect in a browser.
- `--out DIR`: somewhere other than `_export`.

## Reading the report

Every deviation between the PDF and the live page is printed after the export, and is meant to be
read, not dismissed:

- `los document`: a `file` topic, listed but not embedded.
- `afbeelding ontbreekt`: almost always a planned `TODO-*` image; the PDF shows a box with the alt
  text. The content check reports the same gap as a warning.
- `link niet gevonden`: a relative href resolving to nothing. A real fault in the page: fix it
  there (`orion-check`), not here.
- `interactief onderdeel`: a widget that cannot print.
- `is gewone tekst geworden`: a link to a file of the repo outside this bundle, printed as its text
  without the link.

## Scope

What `export_pdf` in `oriontools.json` covers, nothing else. When the user asks for something the
command does not do (a test module, a mix of two modules), say so rather than improvising it.
