# orion-check: check and tidy a course repo

The shared procedure behind every course's `orion-check` skill. The skill in a course
(`.claude/skills/orion-check/SKILL.md`) points here and adds only what that course does
differently; read both.

`orion-convert` writes a page, this one verifies the whole repo. Everything here is
`python ../OrionTools/orion.py check`, which is the single source of truth for what "correct"
means in a course. Do not reimplement its rules or grep for them by hand. A finding names its rule
id (`[em-dash]`, `[topic-frame]`); `check --explain <id>` prints why the rule exists, and
`check --rules` lists every rule with the ones that apply to this course.

**The user does not remember these commands and does not need to.** They ask for the outcome, you
pick the mode. Never answer with only "run this command"; run it and act on what it says.

## The three modes

| Mode | Command | Effect |
|---|---|---|
| Verify | `python ../OrionTools/orion.py check` | Reports breakage. Exit 1 if anything is wrong. |
| Repair | `python ../OrionTools/orion.py check --fix` | Fixes the mechanical violations first, then reports the rest. Rewrites files. |
| Tidy | `python ../OrionTools/orion.py check --audit` | Adds an advisory house-style pass. Never fails. |

Modes combine: `--fix --audit` repairs and then reports everything, which is the right call for
"clean up this repo".

## Process

1. **Run the plain check first**, always, whatever the user asked. It takes seconds and tells you
   which of the other modes is worth using.
2. **If it reports breakage**, offer or apply `--fix`. What it repairs, and why only that, is in the
   docstring of `oriontools/check/fix.py`. It needs a clean working tree (`--force` overrides), so
   commit first, and show the resulting `git diff` rather than claiming success.
3. **Fix the rest by hand.** What `--fix` deliberately leaves needs words or a decision:
   - a page missing from `orion.json`: it needs a title and a place in the menu, so ask;
   - a remote image: download it into `img/` under a descriptive name, `git add` it, repoint the
     `src`;
   - a Chamilo link (`chamilo-downloads.hogent.be`): download it like a remote image, since the
     DocumentDownloader URL still answers once `&amp;` is unescaped to `&`. Only if that fails, a
     `TODO-*` placeholder with the URL in a comment above it;
   - a stylesheet or script left over from the old Brightspace template: delete it;
   - a link that loads another page into the frame: name the page and drop the link, or add
     `target="_blank" rel="noopener"`. Ask which;
   - a `*-stale` finding (`syllabus-stale`, `handout-stale`, `verslag-stale`): a derived file is
     older than its source, so regenerate it with the export `check --explain <id>` names and commit
     it with the change. The syllabus export takes minutes; run it in the background. A `git pull`
     in OrionTools or OrionCSS can make every PDF stale at once, because the stylesheets are shared.
4. **Run `--audit` when tidying**, not on every task. It reports house-style drift (code block
   classes, a page without a `lead`, an image outside a `figure`) and the greppable patterns of
   `SCHRIJFSTIJL.md`.
5. **Before silencing an audit finding, check whether the page is right and the rule is wrong.** A
   genuinely different page records the deviation in the page itself with
   `<!-- audit-skip: <rule> -->` plus a comment saying why. Never add a marker just to make a
   finding go away.
6. **Report in plain language**: what was broken, what you repaired, what is left and why it needs
   a human. Do not paste raw script output as the answer.

## What already runs without anyone asking

Say this when the user worries about forgetting: the plain check runs as a blocking `Stop` hook at
the end of every Claude Code session in a course repo (`.claude/settings.json`), and the workflow
in `.github/workflows/` runs it with `--ci` on every push. Only `--fix` and `--audit` are manual.

## A rule that seems wrong

A rule and its reasoning live in OrionTools, in the rule's docstring. What a course configures
differently is in its `oriontools.json`, and a course opts out of a rule there with
`check.disable`, never by a branch in OrionTools. A fix to a rule is a change in OrionTools and
reaches every course; say so before making it.

## Reviewing a contribution

A course with a second author who edits by hand has a `CONTRIBUTING.md`, in Dutch. For "look at
what they pushed": `git pull`, the plain check, then `--fix`, review the diff, then `--audit` for
the stylistic leftovers. When a rule changes in a way a contributor notices, update
`CONTRIBUTING.md` too.
