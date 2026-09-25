# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

The tooling shared by the Orion course repos (DeN, ICEES, IR, Microcontrollers), which sit beside
this one under `Orion/`. It holds no course content. A course repo calls it by relative path from
its own root:

```
python ../OrionTools/orion.py check
python ../OrionTools/orion.py export-syllabus
```

Before this repo existed, every course carried a copy of the scripts, and the copies drifted apart:
a fix made in one course never reached the others, and nothing noticed. That is the one problem
this repo exists to solve, so **nothing here may know which course it runs for**. Everything that
differs per course is read from `oriontools.json` in the course root. The keys, their defaults and
the validation are in [`oriontools/config.py`](oriontools/config.py). An unknown key is an error,
so a typo cannot silently fall back to a default.

Public on purpose: a private course repo's CI checks it out without a token, and there is nothing
in it a student may not see. Course names, the path to the Word and the like are course config, not
code.

## Layout

```
orion.py                 the entry point; one command per module, imported only when chosen
oriontools/
    repo.py              which course repo: --repo, else the git root of cwd; demands oriontools.json
    config.py            oriontools.json: defaults, merge, validation
    chrome.py            the one list of places a headless Chrome or Edge lives
    huisstijl.py         where the stylesheets of the exports live, here and in OrionCSS
    check/               the content check: runner, rules/, audit, fix
    export/              syllabus, handout, verslag, oplossing, pdf
    export/stijl/        syllabus.css and handout.css, shared by every course
    importers/           brightspace, syllabus, slides
tests/                   a fixture per rule, and check --fix; `python -m unittest` from this root
SCHRIJFSTIJL.md          the shared prose style; each course's own SCHRIJFSTIJL.md only adds to it
skills/                  the procedures of the orion-* Claude skills; each course's SKILL.md only adds to one
tools/parity.py          old check against new, per course
```

The skills work like `SCHRIJFSTIJL.md`: `skills/check.md` holds the procedure, and a course's
`.claude/skills/orion-check/SKILL.md` carries the description Claude triggers on plus what that course
does differently. Rule `skill-basis` holds the two together; its docstring says why the copies per
course went. Not a plugin, decided 25 September 2026: a plugin needs a trust prompt and a
marketplace path per repo, and gives every course the same five skills with one description, while a
course here chooses which skills it has (only a course with `export_pdf` has `orion-pdf`) and what a
unit is called in its description.

## Conventions

- Every command module has `main(argv) -> int` and adds the shared options with
  `repo.voeg_repo_toe(parser)`, then gets its course with `vak = repo.vind(args)`. The course root
  is `vak.root`; a configured folder is `vak.pad("decks")`. `Path(__file__)` never locates a course.
- `check` uses the standard library only, and so does everything it imports. The Stop hook and CI
  run it on a bare Python. Third-party imports (`docx`, `pypdf`, `reportlab`, `PIL`, `pypdfium2`)
  happen inside the command that needs them. `requirements.txt` lists them.
- Code and messages are in Dutch, as in the scripts this came from. The docstrings carry the
  reasoning, next to the code it explains; they came over from the course repos with the code and
  are the record of why a rule exists.
- A fix belongs in all courses. If a behaviour genuinely differs per course, it gets a config key
  with a default, never a branch on `vak.code`.

## Adding a rule

Subclass `Regel` in a module under `oriontools/check/rules/`. Give it an `id` (a stable kebab
slug, never a number), `legacy` (the old per-course numbers, or `()` for a new rule), and a
`van_toepassing(ctx)` that decides by presence: the rule applies wherever the thing it checks
exists, and returns a short reason when it does not. The class docstring is the reason the rule
exists; `check --explain <id>` prints it. The contract is in the header of
[`oriontools/check/regel.py`](oriontools/check/regel.py).

Give it a test class in `tests/` as well, with at least one `test_goed*` and one `test_fout*`;
`tests/test_dekking.py` fails without them. How a fixture is built, and why a rule that does not
apply fails the test instead of passing it, is in the docstring of
[`tests/minivak.py`](tests/minivak.py). Run the tests after any change under `oriontools/check/`.

A new rule applies to every course by default. A course that does not want it opts out in its own
`oriontools.json` with `check.disable: {"<id>": "<reason>"}`, never by a branch here.
