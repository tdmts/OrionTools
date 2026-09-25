# orion-review: read a unit as a student who knows nothing yet

The shared protocol behind every course's `orion-review` skill. The skill in the course points here
and says what that course reviews one pass at a time (its *unit*: a lab, a module), what the ledger
is called, and which shapes to look for in its kind of page. Read both.

`orion-check` asks *is this page wired correctly*, `orion-convert` asks *how do I build this page*,
and this one asks the only question neither can: **would a student who knows nothing actually
learn this?**

Nothing here is automatable, so nothing here is a script. It is a reading protocol plus a place to
write down what was decided, so that a judgement made today still counts next month.

**The user does not remember command names.** They ask for the outcome ("kijk eens naar labo 2"),
you run the protocol.

## What this reviews, and what it deliberately does not

Four kinds of finding, and only these four. Each gets a code, because a finding is referred to by
code months later. The course's skill gives the examples in its own subject.

| Code | Finding |
|---|---|
| `BEGRIP` | A term or concept is used before, or without, being explained anywhere the student can reach. |
| `SPRONG` | A page or task assumes much more than the one before it. A missing intermediate step. |
| `OPDRACHT` | The assignment is ambiguous: what to build, when am I done, what do I hand in. A checklist or rubric that asks something the assignment never mentioned. |
| `BEELD` | The explanation or step cannot be followed without a drawing or screenshot, one is missing (`TODO-*`), or the one there does not show what the text says. |

**Out of scope, on purpose:**

- **Technical and factual correctness.** The user reviews that themselves. If the reader doubts a
  fact, it may note it under a separate heading, but it is never a finding and never enters the
  ledger.
- **Everything `orion.py check` already covers**: links, `orion.json`, page wiring, hotlinked
  images, code style, em-dashes, house-style drift. Run `orion-check` for that. A review finding a
  script could have caught is a wasted finding.
- **Spelling, tone and phrasing**, unless the phrasing is what makes the assignment ambiguous, in
  which case it is an `OPDRACHT`. How the prose *reads* belongs to `SCHRIJFSTIJL.md` and the
  `orion-style` pass. A review that starts editing sentences stops seeing the gaps it exists to
  find. The two never ask for opposite things: the style rules explicitly protect the *why*, the
  callbacks and the cross-links, which are exactly what a `BEGRIP` or `SPRONG` asks for.

## Severity

- **blokkeert**: the student cannot continue without guessing or asking.
- **vertraagt**: the student gets there, but loses time to something the page could have told them.
- **detail**: a real improvement, no one is stuck.

## The shape that keeps showing up

In every course reviewed so far the heaviest finding has had the same shape: **one task carrying
several new ideas at once, with the explanation for them somewhere else or nowhere.** The fix has
been the same shape too: unbundle, so each task adds exactly one thing, and put the concept on a
page the student reaches *before* the solution. So ask of every task: *what is the one new thing
here?* If the answer is a list, that is a `SPRONG`, even when nothing on the page is wrong. A
concept that only appears inside a hidden solution is a `BEGRIP`, because the student trying not to
peek is exactly the one who needs it.

## Process

### 1. Pick the unit and check who is reading

One unit per pass. If the user did not name one, ask; suggest the one most recently edited
(`git log --name-only -20`).

**Check whether you wrote or converted this unit in this same session.** If you did, say so: your
eyes are not fresh for content you just authored, and step 3 exists to solve that.

### 2. Build the prior-knowledge baseline

What a student may be assumed to know is already decided, in pattern 17 of the course's
`SCHRIJFSTIJL.md` (*Waar je in <vak> op mag rekenen*): in one course the units build on each
other, in another groups rotate through them and only the theory track comes first. Build the
baseline from that rule and `orion.json`: list the page titles it allows. Titles only, there is no
summary field, so open a page's `lead` only when its title does not say enough. Anything the unit
under review uses that is not on that list, and not explained on the page itself, is a `BEGRIP`
candidate. Open an earlier page only to settle a specific finding, never to read ahead.

### 3. Read with fresh eyes

Being surprised is the entire instrument, so the reading has to happen somewhere that has not
already absorbed the unit. In order of preference:

1. **A session that has not touched this unit.** Say which it is.
2. **A subagent** (`general-purpose`, `run_in_background: false`), never for content that same agent
   just wrote. Give it the persona, the baseline, the four codes and severities, the reading order
   and the output format; tell it to **read every page in full rather than skim** and that it is
   **read-only: it must not edit any file**.
3. **A fresh Claude Code session** that opens with this skill and nothing else: the right call when
   the unit was authored in the current session.

**One reader for the whole unit**, not one per page: the reader has to carry what it learned from
page to page, and that carried state is what makes a `SPRONG` detectable at all. **The reader never
sees the ledger.** Someone who knows which findings were rejected before is no longer naive, and a
finding resurfacing on its own is useful signal.

**The reading order is the honest student path**, which is the menu in `orion.json`, top to bottom:
each task as a student would meet it (understand the assignment, imagine building it, then read the
solution), and another page only when the page sends the student there or a term cannot be resolved
otherwise. If the student would not think to open a page, that is itself the finding. Afterwards,
the pages of the unit that were never reached: is each clear on its own, and would a student find it?

### 4. Reconcile against the ledger

Read the unit's ledger if it exists. For every finding the reader returned:

- **Already `opgelost` or `aanvaard`**: drop it, unless the reader hit it again on a page that was
  supposedly fixed, in which case the fix did not land and that is worth saying.
- **Previously `verworpen`**: report it as *"opnieuw opgedoken, eerder verworpen omdat ..."*. Not
  silently dropped, not re-asked as if it were new. A naive reader tripping over the same thing
  twice is evidence, and revisiting it is the user's call.
- **New**: into the interview.

### 5. Interview, do not fix

Report the surviving findings grouped by severity, compactly: the page, what the student hits, and
why it stops them, anchored to `file:line`.

Then interview with `AskUserQuestion`, **blokkeert first, then vertraagt**, at most four findings
per call. Bundle the `detail` findings into a single question.

Per finding, offer **two or three concrete fixes plus "verwerpen"**, not an open question. Concrete
means the actual edit: a sentence added to the lead that says what, a link to which page, a drawing
of what in `img/`. A fix that needs an image that does not exist yet is legitimate: a `TODO-*`
filename, which the check reports as a warning.

**Change nothing before the user has chosen.** The point of the pass is their judgement.

### 6. Write the ledger, then apply what was accepted

Update the ledger with every finding and its outcome, the rejected ones with their reason: that is
what stops the next pass from relitigating them. Then make the accepted edits and run
`python ../OrionTools/orion.py check` before calling it done.

## The ledger

One file per unit under `review/`, committed, in Dutch, because a second author may read it. The
course's skill gives the file name and the id prefix.

```markdown
# Review <unit>, studentenbril

Laatste ronde: 2026-07-26. Gelezen: alle 5 oefeningen, 3 theoriepagina's.

## L4-01 · BEGRIP · blokkeert · open
**Pagina:** [DrukknoppenInlezen.html:31](../Labo4/Exercises/DrukknoppenInlezen.html#L31)
**Wat de student raakt:** "..."
**Status:** open
```

- **The id is permanent.** It stays after the finding is fixed. Never renumber; a new finding takes
  the next free number.
- **Status is one of** `open`, `aanvaard` (decided, not yet edited, with what was decided),
  `opgelost` (with the date), `verworpen` (with the reason, always).
- **A rejected finding keeps its reason forever.** Without it the next pass cannot tell a
  considered decision from an oversight.
- Findings stay in the file after they are solved. The file is the history of the unit's teaching
  quality, not a to-do list.

## More than one unit

One unit at a time, in course order when the goal is the whole course. Never batch units into one
reader: the baseline differs per unit, and a reader that has read unit 5 cannot be naive about unit
6. The baseline grows on its own, because step 2 rebuilds it from `orion.json` every time.
