# orion-feedback: short feedback on submitted reports, published on the lecturer's word

The shared procedure behind every course's `orion-feedback` skill. The skill in a course
(`.claude/skills/orion-feedback/SKILL.md`) points here and adds its course id and which
assignments have a report; read both.

The lecturer asks for feedback on a dropbox ("geef feedback op de verslagen van RS485"). You write,
per student, what is good and what to work on, in a few lines. **You never give a score**, and
nothing reaches a student before the lecturer has said so. The decisions behind this (interview of
23 October 2026): the yardstick is the model answer plus general quality, it runs in a session and
not through the API, and the cover page goes before you read.

**The lecturer skims the proposals at most and does not check each one** (later the same day). So a
proposal has to be right without a second reader: what you cannot judge goes in the note, never in
the feedback, and every point must hold against the answer file and the student's own screenshot.
The student is told under every feedback that AI wrote it (`feedback.vermelding` in
`oriontools/config.py`), and may always ask for manual feedback.

## 1. Fetch and anonymise

The folder is `_feedback/<path with dashes>/` in the course repo (`Labo/RS485` becomes
`_feedback/Labo-RS485/`). Git ignores it; the command refuses otherwise.

```
# in OrionSync: find the folder id, then fetch (read-only)
npm run dropbox -- list <orgUnitId>
npm run dropbox -- export <orgUnitId> <folderId> --out ../<Vak>/_feedback/<map>/inzendingen.json --files ../<Vak>/_feedback/<map>/bestanden
# in the course repo
python ../OrionTools/orion.py feedback-voorbereiden _feedback/<map>
```

What `feedback-voorbereiden` removes and what it cannot, is in its docstring
(`oriontools/feedback/voorbereiden.py`). Fetching again later is safe: the codes stay.

**Read only `anoniem/`.** Never open `inzendingen.json`, `sleutel.json` or `bestanden/`: they carry
the names, and the point of the whole step is that you do not see them. Start with
`anoniem/OVERZICHT.md`. A code whose cover page was not recognised (`geen voorblad gevonden`,
`deels`) is one the lecturer looks at before you read it; ask with AskUserQuestion.

## 2. Read the yardstick first

Before a single report:

1. **The assignment**: the `<!-- verslag -->` block of `Opdracht.html`, numbered the way the docx
   numbers it (one counter through the whole block).
2. **The answer file**: `_oplossingen/<path without the lab folder>.md` (`Labo/RS485` gives
   `RS485.md`), answers by question number. **No answer file, no feedback**: say so and offer to
   write one for the lecturer to approve first. Feedback on content without it is a guess.
3. **The notes**: `_oplossingen/<same name>-feedback.md`, if it exists: frequent mistakes, how
   strict the lecturer is on what, wording the lecturer prefers. They outrank this file.

## 3. Read a report

`anoniem/Sxx/verslag.md` holds the questions with their numbers and each answer as a `>` quote
under it; a table answer stays a table. Open every image it links (`img/`): a screenshot is often
the answer, and "a screenshot is there" is not the same as "it shows the pin configuration". The
code under `code/` is evidence for the circuit questions, not a second assignment.

Compare per question with the answer file, then look at the whole: is every question answered, is
the reasoning the student's own, can a reader follow it.

## 4. Write the proposal

```
Goed
- Vraag 9: je verklaart Rt als terminatie en zegt waarom die aan de uiteinden zit.
- Je schermafdrukken tonen telkens wat de vraag vraagt.

Werkpunten
- Vraag 3: A en B zijn de pinnen voor differential signaling, niet 1 en B.
- Vraag 14 is niet beantwoord.
```

- **One to three points under each heading**, one sentence each. A point about a question starts
  with `Vraag N:`.
- **Werkpunten in order of weight**: a content error before a missing answer, a missing answer
  before a missing screenshot, all of those before form.
- **Say what is wrong and why.** The right answer may follow when it fits in the same sentence;
  the model answer opens to the student after submitting anyway.
- **A Goed is specific.** "Netjes verslag" says nothing; name the question or the thing done well.
  A report with nothing good to name gets one honest point about what is there.
- **No score, no grade words** (`onvoldoende`, `8/10`, `geslaagd`), no exclamation marks, no
  praise inflation. The prose follows `SCHRIJFSTIJL.md` of OrionTools and the course: je-vorm, no
  em-dashes, no diminutives.
- **Never a name**, and nothing that identifies the student, even when a screenshot shows it.
- **Do not guess.** A photo you cannot read or a claim you cannot check goes in the note for the
  lecturer, not in the feedback.
- **Never compare students.** Two students may write one report together, so matching answers are
  legitimate (the lecturer, 23 October 2026). Each code is judged on its own, and the note for the
  lecturer is only for what you could not judge.
- No report, only code: the feedback says the report is missing, and may still say something about
  the code.

## 5. Where the proposals go

`_feedback/<map>/voorstellen.md`, one section per code, in this shape:

```
## S03

Goed
- ...

Werkpunten
- ...

Voor de lector: <optional; never sent>
```

The section is exactly what the student will read, minus the `Voor de lector` line. Write the
codes you were asked for and leave the others alone; a second run adds sections, it does not
rewrite approved ones.

**A pilot comes first** for a new assignment: about five codes, spread over the kinds of
submission in `OVERZICHT.md` (docx, pdf, code only). The lecturer judges them, and what they change
goes into the notes file (step 2) before you write the rest.

## 6. The lecturer looks, then it is published

The pilot is the lecturer's real check; after it, the spreadsheet gets a skim. Point the lecturer to the codes
with a `Voor de lector` note: those are the ones only the lecturer can settle.

```
python ../OrionTools/orion.py feedback-spreadsheet _feedback/<map>   # voorstellen.md -> feedback.xlsx, names back
#   the lecturer may edit the column Feedback; an empty cell sends nothing
python ../OrionTools/orion.py feedback-json _feedback/<map>          # feedback.xlsx -> feedback.json + correcties.md
# in OrionSync: dry run first, --apply only on the lecturer's word
npm run dropbox -- feedback <orgUnitId> <folderId> --in ../<Vak>/_feedback/<map>/feedback.json
```

**Never open `feedback.xlsx` or `feedback.json`**: they carry the names. The dry run of
`npm run dropbox` prints names too; run it for the lecturer and report only the counts. In a folder
with a score, a student without a score yet is skipped; the docstring of `scripts/dropbox.js` in
OrionSync says why. `--apply` publishes to students at once, so it waits for the lecturer to say
so in this conversation.

## 7. Learn from the corrections

`correcties.md`, written by `feedback-json`, holds per code your proposal and the lecturer's
version where they differ, with the names replaced. Read it and propose additions to
`_oplossingen/<name>-feedback.md`: a mistake many students make, a point the lecturer always
removes, a level of strictness. Ask before writing; the notes are the lecturer's.
