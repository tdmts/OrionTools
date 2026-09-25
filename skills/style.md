# orion-style: bring one unit's prose in line with the house style

The shared procedure behind every course's `orion-style` skill. The skill in the course points here
and says what one pass covers there (its *unit*: a lab, a module, a syllabus chapter), in which order
the units go, and what that course never touches. Read both.

The rule is two files: the shared base `../OrionTools/SCHRIJFSTIJL.md` and the course's own
`SCHRIJFSTIJL.md` in its root, which adds only what is specific to it, under the number of the
pattern it adds to. **Read both in full before touching anything**: this skill is the procedure,
those files are the content. The patterns have fixed numbers (the gaps are merged patterns, listed
in the table of the base), and the base ends with *De proef*. The course's file ends with *Het
ijkpunt*, a page rewritten in full that shows what the target reads like; where it says there is
none yet, the first unit that gets a complete pass becomes it, and you update that section.

Three groups are invisible sentence by sentence and are the ones a pass most often misses: **16**
(the paragraph that rates its own content), **17** (known material explained at full depth again),
and **18 and 20** (a sentence about the course instead of the subject, a word the reader has not met
yet). Read each page once more for those after the rest, and read whole paragraphs rather than lines.

The rules apply everywhere a student reads, including headings, box titles, checklist lines,
accordion titles, `alt`, `figcaption` and the `title` in `orion.json`, and not to the repo's own
documentation. The verbless test of pattern 5 is **body text only** (a heading is a noun phrase by
nature); the negation ban of pattern 6 is **stricter** in a heading, where no `geen` or `niet` may
appear at all.

One unit per pass. The pass **rewrites** rather than proposes, because the rules are agreed and most
edits are mechanical; anything genuinely doubtful is held back (step 5). `git diff` is the review
surface, so keep the diff readable and never mix a style pass with anything else.

## What this is not

- **Not `orion-check`.** Links, `orion.json`, wiring, em-dashes: that is `orion.py check`, and it
  still has to be green when you are done.
- **Not `orion-review`.** Whether a student can learn from the page has its own protocol and
  ledgers. Never add an explanation, reorder a page or split a task. A didactic gap goes in the
  ledger under "Voor orion-review".
- **Not a proofreading pass.** Comma splices, spelling and agreement errors are not style. Collect
  them in the report and the ledger and leave them in the file, so the diff holds one kind of change.
- **Not a content edit.** No new facts, no new claims, no changed numbers or settings, even when the
  number would be right: a style pass that quietly changes what the page teaches cannot be reviewed
  from a diff.

## The two ways this goes wrong

**Over-correcting.** Imported prose that says only "Maak een teller die telt van 0 tot 9" or "Klik
op Create tooldata" trips almost no pattern and still explains nothing. Terser is not the goal. The
base opens with *Wat blijft* for exactly this reason: the *why*, the callbacks, the concrete
examples, the cross-links, the je-vorm and the box titles that say something are protected. After
every rewrite, ask which fact is no longer there (*De proef*). A page that ends up shorter *and*
thinner is the wrong result.

**Flagging what is correct.** Every word list was measured before it was written: `best` in "neem
best" is Belgian Dutch, `hoor` is often the verb, and a diminutive can be the established term. So
**grep the repo before you act on a new instance**. If a list has a real gap, add the word to the
matching `check.audit.*_extra` list in the course's `oriontools.json` in the same pass and say so. A
word that is wrong in every course belongs in the shared list in OrionTools
(`oriontools/check/rules/audit.py`) instead: report it, that is another repo.

## Process

### 1. Pick the unit

If the user named none, take the first in course order that the course's style ledger does not
record as `klaar`. Say which, and how many pages. One unit per pass: reading a dozen pages in full
and rewriting them fills a context window, and a second unit in the same session gets skimmed.

### 2. Get the mechanical findings

`python ../OrionTools/orion.py check --audit`, filtered to the unit. The greppable patterns appear
there (stock lead opener, diminutive, Netherlandic word, filler adverb, the u-vorm, `LED`). A floor,
not a list: it is roughly a third of what a pass finds.

### 3. Read every page of the unit in full

In menu order (`orion.json`), so that repetition across pages becomes visible: the stock opener and
the closing punchline are only recognisable as tics on the fourth page. Read `alt`, `figcaption` and
box titles too; a pass that only reads paragraphs leaves those behind.

### 4. Rewrite, one small edit per passage

Keep each edit small enough that the diff shows the sentence that changed. Imported prose is treated
like any other: the whole site reads as one voice. Prose only; never touch, in this pass:

- **code blocks**, not the code and not its comments;
- **markup and structure**: no new sections, no changed nesting, no removed figures;
- **heading `id`s**, since other pages link to them;
- **`<h1>` and `<title>`**, which match the `title` in `orion.json` and change only when the page is
  renamed;
- **table data**: a cell's wording may be tightened, what it asserts may not change.

The course's skill adds what else stays untouched there. One exception to "markup": an `info-box`
that breaks the box rule of pattern 16 is unwrapped, its text moved into the running text next to
where it stood, and a box that only repeats is removed.

### 5. Hold back what is doubtful

Be generous with this. Hold back rather than decide when the fix would change or add meaning,
however slightly; the word may be the established term; the passage has two readings and you cannot
tell which the author meant; fixing it needs a fact you do not have (a value, what a screenshot
shows); or the page deviates on purpose and an `audit-skip` with a reason is the better answer.
Hold-backs go in the ledger and the report, quoted with their file and a one-line question. Five
concrete questions are worth more than fifty applied edits the user cannot check.

### 6. Verify

`python ../OrionTools/orion.py check` must pass; `--audit` should be clean for this unit or carry
audit-skips. Then re-read your own diff against *Wat blijft*. The question is not "is every pattern
gone" but "does this page still explain as much as it did".

### 7. Record the pass

In the course's style ledger: the unit's row, the pages touched, the hold-backs with their status,
and any word added to a list.

## The ledger

`review/schrijfstijl.md`, one section per unit, unless the course's skill names another. It is
deliberately thinner than an `orion-review` ledger: the rule document already *is* the decision, so
the ledger holds progress, hold-backs and the words added to a list.

A deliberate deviation does not go in the ledger but in the page, as
`<!-- audit-skip: verkleinwoord -->` with the reason beside it, so the decision lives where the
deviation does. The `audit-skip` rule of the check names the valid rule names when one is wrong.

## Report format

1. Per page one line on what changed, grouped by pattern when a fix repeats
   (`lijstje -> lijst, 7 keer op ProgrammaUploaden.html`).
2. The hold-backs, quoted, with the question for the user.
3. Anything added to a word list, with what you measured before adding it.
4. The check output, and what the audit still reports for this unit.
5. Which unit is next.

Keep it short. The diff is the deliverable; the report is the map to it.
