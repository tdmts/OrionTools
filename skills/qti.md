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
<li>Stem, as a question or an incomplete sentence.
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

- **Exactly one `class="juist"`.** A question with more than one right answer is rewritten, not
  marked twice: pair the options so one pairing is right and say how many there are, or invert
  the stem to "welke is niet". The export stops on zero or two.
- **Every item stands alone.** ANS imports each question as a separate item and may draw them in
  any order. No "zie vraag 3", and nothing in a sentence above the list that a question needs.
- **Options are shuffled** by default. So no "alle bovenstaande" or "geen van bovenstaande" (the
  export warns), and no option that refers to another by letter.
- **Distractors are the mistakes a student actually makes**: a neighbouring concept, a
  confused unit, a step left out of a calculation. Not nonsense, and not jokes.
- **Options alike in length and form.** The right answer is not the longest or the most careful
  one. A giveaway word ("altijd", "nooit") never appears only in the distractors.
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
