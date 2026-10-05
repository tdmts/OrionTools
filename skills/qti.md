# orion-qti: multiple-choice questions on course material, as a QTI zip for ANS

The shared procedure behind every course's `orion-qti` skill. The skill in a course
(`.claude/skills/orion-qti/SKILL.md`) points here and adds where that course keeps its material;
read both.

The user names a piece of course material and asks for questions on it. You write them as an
ordinary question page, the user reads it in the browser, and `orion.py export-qti` turns it into
the zip ANS imports. Why the source is a question page and not a format of its own, what the
package looks like and what is still untested in ANS, is in the docstring of
`oriontools/export/qti.py`; read it before you change anything about the output.

## 1. Pin down the scope

Ask with AskUserQuestion, in one call, whatever the request leaves open:

- **Which material**: pages, a chapter, a lab. Offer the candidates you found, not a free field.
- **How many questions.**
- **Summative or practice.** Summative means no `--feedback`: the explanation names the right
  answer, and a summative test sends nothing back to the student. Practice means `--feedback`.
- **Level**: recall, understanding, applying (a calculation, reading a configuration or a
  figure), or a mix.

Do not ask what the request already says, and do not ask about the file name; propose one.

### A lab test: the shape that is settled

A summative test on a lab has a fixed shape, decided while ICEES and DeN wrote theirs (September and
October 2026). Do not ask about it again; ask only what it leaves open.

- **Fifteen questions per student, one minute each.** The cover in `ans.toets` says so, for every
  course.
- **Pairs.** One `h2` per objective of the lab (`D1 ...`, from the objectives in its `overview.html`),
  one `h3` per pair under it (`P1 ...`), and an `<ol class="vragen">` of two questions in each `h3`. The two test the same skill with
  different content, and ANS draws one of them, so fifteen pairs make fifteen questions. The export
  puts the headings in each item's title, which is how the pairs are found in ANS.
- **Every test question has a sister in the lab's Test jezelf**: the same skill, the same number of
  steps of reasoning, the same form, other content, and **as hard**. The rule behind it: whoever can do
  the Test jezelf passes the test. Write the sisters in the Test jezelf itself, not in a separate
  list, and end each explanation in the test with "Zus: Test jezelf ..., vraag N".
- **The order of work**: the objectives first; then an overview of the pairs, each with what it
  tests, its form, its source page and its sister, which the user approves; only then the questions.
- **Spread the effort over what the lab practised.** Objectives that are hands-on (configuring,
  testing) get more pairs than a definition. A practical skill is asked as a situation: choose the
  command, read an output, predict what happens.

## 2. Read the material

Read every page in scope in full, figures and code blocks included. A question tests what the
material says, in its terms; a fact that is not in it is not in the test. If the material is too
thin for the number asked for, say so instead of padding.

A question page of the course already covers the same ground (a Test jezelf, the study questions
of a chapter). Students have seen those, so for a summative test, do not reuse or lightly rephrase
them unless the user asks you to. To export an existing page as a practice test, skip to step 5
and point `export-qti` at that page. That works only for a page in `ol.vragen` markup; the course
skill says which pages are, and a course whose questions sit in other markup has none.

## 3. Write the page

`_toets/<Name>.html` (`paths.toets` in `oriontools.json`), with a PascalCase Dutch name. That folder
is ignored by git and skipped by the check, and it must stay that way: everything tracked is
mirrored into the course, where every student reads it. `export-qti` refuses to write while git
does not ignore it. Never move a test out of that folder and never commit it.

Copy the `<head>` of an existing page of the course, so the page loads OrionCSS and the reveal works
in the browser. The reveal is OrionCSS `main.js`, so it works in a course that has no question page
of its own as well. The `<h1>` is the title of the package in ANS. Then one `<ol class="vragen">`:

```html
<li data-bron="Labo/RS485/Theorie/WatIsRS485.html">Stem, as a question or an incomplete sentence.
    <ul>
        <li>Option</li>
        <li class="juist">Option</li>
        <li>Option</li>
        <li>Option</li>
    </ul>
    <div class="oplossing">Why this option is right, why the likely wrong one is wrong. Zie
        Pagina.</div>
</li>
```

The markup is OrionCSS's question list, block *Vragenlijst* in `../OrionContent/template.html`,
whatever the course's own pages use for their answers. What makes a good item:

- **`data-bron` names the page the question tests**, from the course root; several are separated
  by a space. `ans-dekking` counts it, and the export stops on a path that does not exist.
- **Exactly one `class="juist"`.** A question with more than one right answer is rewritten, not
  marked twice: pair the options so one pairing is right and say how many there are, or invert
  the stem to "welke is niet". The export stops on zero or two.
- **Every item stands alone.** ANS imports each question as a separate item and may draw them in
  any order. No "zie vraag 3", and nothing in a sentence above the list that a question needs.
- **No item gives another away, and no stem gives its own answer.** A student sees every stem and
  every option of the test, but not the `div.oplossing`. So once the set is written, read the
  stems and options together, as the student will, and ask of each fact they state whether another
  question tests it. The RS485 test had three: a stem that described the circuit as "die enkel
  ontvangt" while asking whether it was simplex; a question on why circuit 6 is half duplex whose
  key answered the question on four-wire RS-485; and a stem that stated "/RE is active low", which
  is half of what another question asked the student to work out. A wrong option leaks as well
  when knowing it is wrong settles another question. The fix is to describe the situation rather
  than name the concept (the modes of the two ICs, not "enkel ontvangt"), or to ask the general
  form ("een ingang is active low") and leave the specific one to the question that applies it.
- **A question asks for knowledge, not for reading.** A figure question whose stem hands over the
  rule ("de ontvanger leest een 1 wanneer A hoger ligt dan B") leaves only reading the figure off;
  let the figure carry the situation and the options carry the knowledge. And only what the
  material says or the lab had the student do: a situation nobody built and no page explains
  (DE high and /RE low on two separate pins) is not a hard question but an unfair one, however
  derivable it looks.
- **A stem does not presuppose its answer.** "Wat is er mis?" tells the student something is, and
  an option "niets" is then dead on arrival. "Welke bewering is waar?" makes every option a claim
  to judge, including "er is niets mis". It also carries distractors that are
  misconceptions stated as reasons, which is where the knowledge sits.
- **Options are shuffled** by default. So no "alle bovenstaande" or "geen van bovenstaande" (the
  export warns), and no option that refers to another by letter, nor an explanation that points
  at "het laatste antwoord".
- **Spread the right answers over the letters** anyway. The page is read unshuffled, by the user
  and on paper, so a key that always sits on a gives the test away there; the export warns when
  more than half share a letter. Write them on varying letters from the start, and never the same
  letter three times in a row. The Test jezelf is never shuffled, so it counts there as well.
- **Distractors are the mistakes a student actually makes**: a neighbouring concept, a
  confused unit, a step left out of a calculation. Not nonsense, and not jokes. The best ones are the
  misconceptions the page itself corrects, and an option that has the right choice with the wrong
  reason.
- **Not too easy.** Recognising a definition ("which task belongs to the kernel") or filling in a
  2x2 of two definitions is too easy for a test; so is a stem that names the very thing the options
  test (both VLANs in the stem of "does the HMI reach the server?"). Give a situation to reason
  about. Questions about the rules of the lab and common-sense questions do not belong in a test at
  all. ICEES had two pairs sent back twice for this.
- **Options alike in length and form.** The right answer is not the longest or the most careful
  one, and does not carry a reason the distractors lack: the reason goes in the `div.oplossing`.
  Two options that share the right half give it away too, and so does a combination question
  where each distractor changes one part of the answer: make it a full 2x2, or ask for one value.
  Prefer bare, parallel options (four commands, four port numbers). The export warns when the
  right answer is clearly the longest; Managed Switch had nine such questions before that check
  existed. A giveaway word ("altijd", "nooit") never appears only in the distractors.
- **A negation in the stem is `<strong>niet</strong>`.**
- **Four options** unless the question calls for three or five.
- **A figure** is an existing file of the course, linked relatively (`../img/...`), with an `alt`.
  It goes into the zip. A remote image fails the export.
- **Code or configuration** is a `<pre><code>` block and stays literal.
- **The `div.oplossing` is always there**, also for a summative test: it is how the user checks
  your key, and it names the page the answer comes from. A link in it becomes plain text in ANS.
- **The Dutch follows the course's `SCHRIJFSTIJL.md`**, on top of `../OrionTools/SCHRIJFSTIJL.md`:
  "je", no em-dashes, no theatre.

## 4. Let the user review

Report the file path and ask the user to open it in the browser: every answer is behind its reveal
there. Then ask with AskUserQuestion whether to export, with the feedback choice from step 1 as
the recommended option. Corrections go into the page, never into the zip.

## 5. Export

```
python ../OrionTools/orion.py export-qti _toets/<Name>.html              # summative
python ../OrionTools/orion.py export-qti _toets/<Name>.html --feedback   # practice
python ../OrionTools/orion.py export-qti <question page of the course> --feedback
```

`--niet-schudden` keeps the options in page order; use it only when the order carries meaning
(values in increasing order, for instance). Every `let op:` line in the report is something in the
page to fix, then export again; the zip is derived and is never edited.

Report the zip path, the number of questions, whether feedback went in, and where to import:
ANS, School, Question banks, Settings, Import, QTI 2.1. Not 3.0: ANS reads the points of an item only from a QTI 2.x package, and imports a 3.0 item at 0 points.

## 6. Or straight into ANS

When the course has `ans.course_id`, a lab test goes in through the API instead of a zip, in two
commands, each first with `--droog`:

```
python ../OrionTools/orion.py ans-push _toets/<Name>.html
python ../OrionTools/orion.py ans-toets Labo/<Lab> --vragen _toets/<Name>.html
```

`ans-push` puts the questions in a bank named after the `<h1>` ("Test labo ..."); `ans-toets` makes
the test and its item bank test, named "Labo <lab> <jaar>", with the settings of `ans.toets`. What
each does and why is in their docstrings in `oriontools/ans/`. What the API cannot set, such as
drawing one question per pair, `ans-toets` prints as "met de hand nakijken"; pass that list on to
the user. ANS is full enough: reuse what is found by its external_id, and make no trial banks.
