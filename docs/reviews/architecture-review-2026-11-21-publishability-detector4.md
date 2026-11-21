# Architecture review (Phase 6) — `check-publishability.py`, the Markdown prose judgement (detector 4, and detector 1)

**Date:** 2026-11-21 · **Convened on:** THRASHING (backlog #680) · **Subject at:** `40c009a3` (`scripts/check-publishability.py`
is byte-identical to the round-3 fold `0c451cbd`) · **Reviewer:** Claude (Fable 5.2), one agent, no second half.

Every claim is tagged **[M]** (a command this review ran, on the commit above, Python 3.14.4) or **[I]** (inferred or
judged by the reviewer; not a measurement). Labels of the form "true dependency / false finding" are the reviewer's own
reading of a line and are always **[I]**.

Prototype, corpus and every output file:
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/b387c8e6-9003-42f5-a944-1d4eb1de0c9b/scratchpad/p6d4/`
(`candidates.py`, `corpus.py`, `attack.py`, `run_corpus.py`, `run_live.py`, `run_selftest.py`, `run_diff_all.py`).
It is throwaway and unreviewed; it is evidence, not the build.

---

## 1. Verdict

**Split. The thrash had two mechanisms in one function, and they get opposite answers.**

| Half | "Can a redesign remove it?" | Verdict |
|---|---|---|
| **Mood** — is the introducing paragraph an instruction, or a prohibition/description? (`NEGATES`, lines 335–342) | **No.** It is a prose floor. | **STOP FOLDING — and delete the filter**, do not refine it. Fail toward a finding. State the bound. |
| **Structure** — which paragraph introduces this list item / fence, and where a sentence starts and ends (lines 287–309, 325–334) | **Yes.** Three separate backward line-walkers; a fourth is needed for the only fix with live yield. | **REDESIGN once**: one reading of block structure, one `introduces()` question. |

**Recommended candidate: F** — one block model, sentence shapes judged on the wrapped sentence and on every code span of
one imperative, **no negation filter**. Measured **[M]**:

| | corpus (57 rows) | refutation corpus (30 rows) | live findings vs HEAD | self-test |
|---|---|---|---|---|
| HEAD = "stop folding and state the bounds" | EXACT 32 · MISS 22 · FALSE 3 | EXACT 25 · MISS 5 · FALSE 0 | 302 findings (baseline) | 105/105 |
| **F (recommended)** | **EXACT 44 · MISS 7 · FALSE 6** | **EXACT 28 · MISS 2 · FALSE 0** | **+4 gained, 0 lost** (306) | 104/105 (the one failure is the r3 negation case, intended) |

**Does "stop folding and state the bounds" win?** For the **mood half, yes, outright**: every refinement of the negation
filter measured **0 live findings gained or lost** (§4, candidates B and N), while its last fold opened a MAJOR silent miss.
For the **whole component, no**: HEAD leaves 4 live dependencies of `skill-brief` unreported that F reports (§4), and
the fix for them needs a paragraph notion — a fourth walker if it is folded in, which is the thrash mechanism itself.

**The uncomfortable number.** Of the four rounds' recorded findings in this component, the r3 and r4 ones (the two rounds
that armed THRASHING) have **zero instances on the live tree** **[M]**: candidate B, which folds all of backlog #673's
directions, changes 0 of 302 live findings. Meanwhile the 4 live misses in `.agents/skills/brief/SKILL.md:62` sat
untouched through all four rounds, in the very file r2's finding CM4 quoted (lines 52–56).

---

## 2. The arming evidence, re-run

Each recorded input was replayed against the script at each round's head (`git show <sha>:scripts/…` copied to scratch,
loaded in-process, `_kind` called on a fixture file). `.` = judged as the round document wanted. **[M]**

| Finding (input) | wanted | r1 head `c4861690` | r1 fold `9984c3c1` | r2 fold `53f2f20f` | r3 fold `0c451cbd` = HEAD | Caused by |
|---|---|---|---|---|---|---|
| r1 Codex XM3 — ``Use `TaskList` to …`` | dep | MISS | . | . | . | original build |
| r2 Claude CM4 ×3 — numbered list under "Then read, in this order …:" | dep | MISS | MISS | . | . | original build |
| r2 Claude CM5 — untagged fence under "…stop the strays BEFORE arming…:" | dep | MISS | MISS | . | . | original build |
| r3 Codex XM2 — blank lines between numbered items | dep | MISS | MISS | MISS | . | original build (not fix-induced) |
| **r3 Codex Xm1** — "…tools that we never use:" + list | mention | . | . | **FALSE** | . | **the r2 fold** |
| **r3 Codex Xm2** — "Read the section headings:" list, then a second list | mention | . | . | **FALSE** | . | **the r2 fold** |
| **r4 Claude MAJOR ×3** — "Do not guess. Read these first:", "No shortcuts here; run these:", "This step is not optional.⏎Read these files:" | dep | MISS | MISS | . | **MISS** | **the r3 fold** |
| r4 Claude MINOR — loose item with an indented continuation paragraph | dep | MISS | MISS | MISS | MISS | original build |
| r4 Claude MINOR — "- Then read these:" + nested item | dep | MISS | MISS | MISS | MISS | original build |

Rounds 3 and 4 each carry a finding the previous round's fold caused: the arming condition held as recorded. The r4
`_always_none` MINOR is detector 6 and outside this component.

**The component is mis-named.** "Detector 4 (prose)" is `_markdown_kind`, reached through `_kind` by **both**
`_vocabulary_matches` (detector 1, line 379) and `_bare_names` (detector 4, line 518). At HEAD the live Markdown
rows are: detector 1 — 5 findings, 211 mentions; detector 4 — 9 findings, 465 mentions **[M]**. Any build here moves
detector 1 too.

---

## 3. The mechanism — why each fold opened a new hole

Quoted from `scripts/check-publishability.py` at HEAD.

### 3.1 Structure: three walkers, each with its own idea of a list

```
288      for ln in lines[:line - 1]:                                   # walker 1: fences
289          m = re.match(r"\s*(?:```|~~~)\s*([\w-]*)", ln)
…
302          while i > 0:                                              # walker 2: up through list items
304              while j > 0 and not lines[j].strip():  # a blank line between two items keeps the list (review r3)
306              if not (LIST_ITEM.match(lines[j]) or (j == i - 1 and lines[j][:1] in (" ", "\t"))):
…
331      while start > 0 and lines[start - 1].strip() and not re.match(r"\s*(?:#|```|~~~)", lines[start - 1]) \
332              and not LIST_ITEM.match(lines[start - 1]):  # an earlier list ends the paragraph (review r3)   # walker 3
```

- Walker 2 knows blank lines (since r3) and a continuation line only when it is **adjacent** (`j == i - 1`); it has no
  notion of indentation depth. Hence r4's two MINORs (continuation paragraph after a blank; nested item under a
  colon-ending parent) and, added by this review, a fence between items and a tab-indented child **[M: MISS at HEAD]**.
- Walker 3 learned in r3 that a list item ends a paragraph, because walker 2's notion of "list" was not available to it.
  That is r3 Xm2: the r2 fold wrote a paragraph walk that could cross a list, and the r3 fold patched the walk rather
  than sharing the model.
- The sentence shapes are **line-local**: `re.search(INSTRUCTS + tok, text, re.I)` (line 298) sees one physical line.
  `INSTRUCTS` (281–282) ends ``\b[^`.]*`[^`]*``, so it reaches the **first** code span after the verb only.
  Measured at HEAD **[M]**: ``Read `docs/a.md` and `docs/b.md` first.`` leaves `docs/b.md` a mention; a verb on one line
  with its code span on the next is a mention. This is the live miss at `brief/SKILL.md:61–62`.

Fixing the hard-wrap miss needs "the sentence this term sits in", i.e. paragraph bounds: **a fourth walker**. Each fold
so far added or patched a walker; each new walker disagreed with an older one in the next round.

### 3.2 Mood: a filter applied after the walk, with unbounded silence

```
334      para = " ".join(lines[start:i + 1])
335      return any(not re.search(NEGATES, para[max(0, m.start() - 24):m.start()], re.I)
336                 for m in re.finditer(LEAD_VERBS, para, re.I))
340  LEAD_VERBS = r"\b(?:read|load|open|run|edit|update|consult|follow|source|use|call|invoke|stop)\b"
342  NEGATES = r"\b(?:never|not|no)\b|n't\b"
```

The r2 fold made "a colon and a verb anywhere in the paragraph" the test. That admits "tools that we never **use**:"
(r3 Xm1, a false finding, MINOR). The r3 fold answered with a 24-character negation window on the joined paragraph. The
window does not know where a sentence ends, so "Do **not** guess. **Read** these first:" went silent (r4 MAJOR).

**The r3 fold traded a MINOR false finding for a MAJOR silent miss.** Nothing stopped it because the failure direction
is written nowhere (§7.1). And the next refinement does not close it: clipping the window to the sentence (backlog
#673's direction, candidates B and C2) still misses "Don't skip these, read them all:", "If you have not yet done so,
run these:", "Never guess — read these first:" **[M: 3 of 3 MISS under B and C2]**. Negation scope is grammar, and a
character window is not a grammar. This is the floor.

The same test also fails the other way on words that are not verbs here — "Files in **use**:", "Example of a
**call**:", "**Open** residuals at merge (not blocking):" (live, `docs/memory/reservation-release-slice-state.md:16`, a
finding at HEAD on line 17) **[M]**; and it cannot see "Check these before starting:" or a `## Prerequisites` heading
**[M: MISS under every candidate but the colon-only one]**. A keyword list is an open class.

### 3.3 Two smaller measured facts in the same function

- `REQUIRES` (line 283) excludes the backtick from its gap (``[^.`;:,()]{0,40}``), so it **can never reach a term in a
  code span**: ``This skill requires the `TaskList` tool.`` → mention; without backticks → prerequisite **[M]**.
  Live reach: 1 of 676 Markdown mention keys has a requirement word followed by the term in a code span
  (`docs/memory/process-conventions.md:20`) **[M]**.
- `LEAD_VERBS` opens with `\b`, and `_` is a word character: `_Read these first:_` introduces nothing **[M]**.

---

## 4. Candidates, measured

**Corpus** (`corpus.py`, 57 rows): 15 REC (every recorded r1–r4 input in this component, and the controls the rounds
recorded), 35 ADJ (neighbours this review wrote **before** running candidates), 7 FLOOR (neighbours no shape rule is
expected to reach). Wanted answers for ADJ and FLOOR rows are the reviewer's **[I]**. MISS = a dependency judged a
mention; FALSE = a mention judged a dependency.

**Refutation corpus** (`attack.py`, 30 rows): written **after** the candidates, to break the block model. Its last
column counts rows where HEAD says dependency and the candidate says mention — a build-caused loss.

**Live**: the full scan (46 components, 0 CANNOT RUN, 302 findings, 1641 mentions at HEAD), with the candidate patched
in-process over `_markdown_kind`; the in-process HEAD scan was checked equal to the CLI scan first **[M]**. Gained
lines were read one by one.

| Candidate | Corpus EXACT / MISS / FALSE | REC only | Attack EXACT / MISS / FALSE · losses | Live gained / lost | Self-test |
|---|---|---|---|---|---|
| **A** — HEAD, stop folding, state the bounds | 32 / 22 / 3 | 10 / 5 / 0 | 25 / 5 / 0 · 0 | 0 / 0 | 105/105 |
| **N** — HEAD with `NEGATES` deleted | 36 / 15 / 6 | 12 / 2 / 1 | not run | **0 / 0** | not run |
| **B** — accrete: HEAD + backlog #673's three directions | 38 / 16 / 3 | 15 / 0 / 0 | not run | **0 / 0** | not run |
| **C** — block model, HEAD's negation window | 40 / 14 / 3 | 12 / 3 / 0 | not run | 4 / 0 † | not run |
| **C2** — block model, sentence-clipped negation | 44 / 10 / 3 | 15 / 0 / 0 | 28 / 2 / 0 · 0 | 4 / 0 | 105/105 |
| **D** — block model, no negation | 44 / 7 / 6 | 14 / 0 / 1 | 28 / 2 / 0 · 0 | 5 / 0 | 104/105 |
| **D+spans** — D, plus every code span of one imperative | 46 / 5 / 6 | 14 / 0 / 1 | 28 / 2 / 0 · 0 | 8 / 0 | 104/105 |
| **F** — D+spans, an item's body is **not** in its list | **44 / 7 / 6** | 14 / 0 / 1 | **28 / 2 / 0 · 0** | **4 / 0** | 104/105 |
| **S** — HEAD's walkers kept, `NEGATES` deleted, sentence tests added | 41 / 10 / 6 | 12 / 2 / 1 | 25 / 5 / 0 · 0 | 4 / 0 | 104/105 |
| **E** — block model, colon only (no verb gate) | 40 / 6 / 11 | 12 / 0 / 3 | not run | 83 / 0 † | not run |

† measured with the first prototype, before the heading fix of §4.3; all other block-model rows are the final prototype.

### 4.1 What the live lines say

- **B and N: 0 gained, 0 lost.** No live paragraph has the r4 MAJOR shape, and no live paragraph is saved from a false
  finding by `NEGATES` under HEAD's walkers. The negation filter is, on this tree, pure risk. **[M]**
- **F and S, the same 4 lines gained:** `.agents/skills/brief/SKILL.md:62` — `check-docs`, `check-roadmap-consistency`,
  `check-test-counts`, `check-producer-enumeration`, under line 61's "**Run the repo's own ratchets** and report exit
  codes, not their prose output:". All four are things the skill tells the agent to run: true dependencies **[I]**.
  `check-docs` comes from joining the wrapped sentence; the other three from reaching every span.
- **The item-body rule (C2, D, D+spans) costs 3 live false findings and buys 0 live true ones** **[M count, I labels]**:
  `docs/memory/reservation-release-slice-state.md:18` ×2 (a continuation line under "**Open** residuals at merge (not
  blocking):" — "Open" is an adjective; line 17 is already a false finding at HEAD) and
  `.agents/skills/shared/explainer-delivery.md:492` (`SendUserFile`, in a warning that the tool does **not** render the
  page; the list is "introduced" because the paragraph above holds the noun "source"). D adds a fourth,
  `docs/memory/backlog-191-semantic-recall-replicated.md:18`, under "**RULES — do not re-open these:**". **F drops the
  item-body rule for that reason**, and states it as a bound (§5.4).
- **E: +83 findings**, all in `docs/memory/` and similar notes (r2 measured +42 on its tree). Rejected: the verb gate is
  what keeps "**How to apply:**" bullets out.

### 4.2 The whole-file differential (the "filter after the walk" test)

For 296 tracked Markdown files (every tracked `*.md` outside `docs/reviews/`, `docs/superpowers/`, and three
table-heavy files: `docs/backlog.md`, `docs/roadmap-to-launch.md`, `docs/dashboard-entries.md`), every
`(line, code-span content or CamelCase word)` pair was judged by HEAD and by the candidate: **9,607 pairs** **[M]**.

| Candidate | mention → dependency | **dependency → mention** |
|---|---|---|
| F | 77 | **0** |
| S | 75 | **0** |

The 77 gains are over **all** code spans, not detector vocabulary, and were **not** labelled (§8); the live scan's +4
is what they amount to in findings today.

### 4.3 The prototype was itself refuted twice — the lesson the install-root build paid for

1. **A build-caused silent miss.** The first block model let only a paragraph or a list item introduce a block. HEAD
   also lets a heading do it (`## Run these first:` + list — line 328 tests the line, whatever it is). The refutation
   corpus caught it: 2 rows HEAD-dependency → mention **[M]**; fixed in the prototype, then 0. The 105 self-test cases
   did **not** catch it (105/105 with the defect present) **[M]**, and neither did the live scan (0 lost).
2. **A hang.** Joining "the paragraph" for the sentence test made `docs/backlog.md`'s table (lines 30–669, 1,674,291
   characters) one paragraph; one term took longer than the 8-second probe **[M]**. Bounded in the prototype (table rows
   are their own class; the joined unit looks back at most 12 lines), after which the whole file ran in 8.5 s against
   HEAD's 10.3 s, and the full live scan in 26.2 s against 25.6 s **[M]**.

Both were found by a differential against the function being replaced, not by cases written for the new one. That is
why §6 makes the differential a FAILS IF and not a suggestion.

---

## 5. Recommendation — build F once

### 5.1 The rule, in three sentences

1. **One reading of the file's blocks.** Each line is exactly one of: fence-open, fence-close, code, blank, heading,
   list item (with its indent), table row, prose. An item is owned by the nearest earlier item with a smaller indent;
   a list's first item is the earliest sibling not separated from it by a heading or by prose/a fence at or left of
   its indent.
2. **One question, `introduces(block)`:** the paragraph, list-item line or heading directly above (blank lines
   allowed) ends with a colon after emphasis markers, and holds a `LEAD_VERBS` word. **No negation test.** A list item
   is a prerequisite when the paragraph above its list introduces — at its own level or at any enclosing level; an
   untagged fence likewise, including a fence inside an introduced item.
3. **Sentence shapes on the sentence, not the line.** `INSTRUCTS`/`REQUIRES` are tried on the line as today, then on
   the paragraph joined up to the term (bounded), and an imperative that opens a sentence reaches **every** code span
   up to that sentence's end (`[.!?]`, optional closing `*_)"'`, then whitespace).

### 5.2 What is deleted and replaced

| At HEAD | Becomes |
|---|---|
| fence scan, lines 287–291 and 296 | the block reading (once per file; `_lines` is already cached per file) |
| list walk, lines 300–309 | `owner` / first-sibling on the block reading |
| `_introduced` paragraph walk, lines 325–334 | `introduces(block)` |
| `NEGATES` (line 342) and the window (lines 335–336) | **deleted**; `any(…)` becomes "a `LEAD_VERBS` word is present" |
| line-local `INSTRUCTS`/`REQUIRES` (line 298) | kept verbatim, plus the joined and every-span forms |

Not in scope, on purpose: the verb lists, `REQUIRES`'s backtick gap, the `_Read` word boundary, shell-fence and Python
judgement, every other detector. They are §5.4 bounds or backlog rows, not this build.

### 5.3 Cases and mutations that change

- **Self-test:** the case "r3: blank lines between items keep the list; a negated verb, or an imperative above an
  earlier list, introduces nothing" fails under F **[M]** — its negated-verb half asserts the deleted behaviour. Split
  it: keep the blank-line and earlier-list halves; replace the negated half with a case that asserts the **direction**
  ("a prohibition introducing a list is reported as a finding", with the r4 MAJOR's three inputs as dependencies in the
  same case). The other 104 pass unchanged **[M]**.
- **New cases, each built from two distinct inputs:** wrapped sentence (verb on one line, span on the next) vs the
  sentence-leak negative ("Read the notes.⏎`docs/a.md` is unrelated."); second span vs second sentence; nested item
  under an introduced parent vs under a plain parent; loose item with a continuation paragraph; untagged fence inside
  an introduced item vs an unindented fence between items; heading introducer; a 1 MB table row file returns within a
  stated time.
- **Mutations** (`scripts/mutations/check-publishability.json`): the anchors at manifest lines 1668, 1679, 1690, 1723
  and 1734 bind to code this build deletes or rewrites (`_introduced(lines, i)`, `_introduced(lines, opened)`, the
  `NEGATES` window ×2, the earlier-list clause) **[M: grep]**. The two `NEGATES` mutations are removed with the filter;
  the rest are re-anchored, and a call-site mutation is added for each of: the climb to an enclosing level, the heading
  introducer, the joined-sentence test, the every-span test, the unit bound.

### 5.4 Bounds F states (and does not fix)

Each was measured as a row that F gets wrong, or is a HEAD bound F inherits **[M unless marked]**:

- **FALSE, by decision:** a prohibition or a description that ends in a colon and holds a verb-list word introduces
  its list — "tools that we never use:" (r3 Xm1), "Do not run any of these:", "Stop. Do not read these:", "Files in
  use:", "Example of a call:". Corpus: 6 FALSE. Live: 0 new false findings under F.
- **MISS:** an imperative after a comma or a modal ("Before you start, run …", "You must run …"); a verb the list
  lacks ("Check these before starting:"); a `## Prerequisites` heading with no colon; an elliptical continuation
  (live: `brief/SKILL.md:58–59`, "And the artifacts of the work itself: `docs/reviews/` …" **[I]**); `REQUIRES` before
  a code span; a term in an item's continuation line or paragraph (dropped on the live evidence of §4.1); a lazy
  (unindented) continuation line; `_Read these:_`; a list inside a block quote is reached, a quote's own nesting is not
  modelled.
- **Shared with HEAD:** any ```` ``` ```` or `~~~` line toggles the fence, whatever its length or the opener's kind.

---

## 6. FAILS IF — and the stop condition, decided now

**The invariant.** *A Markdown term is judged a mention only because no structure names it — never because a filter
ran after structure had named it; and the build reports every dependency the function it replaces reported.*

It FAILS IF any one of these is observed:

1. **A loss.** Any `(file, line, term)` over the tracked Markdown set of §4.2 that the pre-build commit judges a
   dependency and the build judges a mention. The build's round document lists the run; expected: 0. (The prototype: 0
   of 9,607 pairs.)
2. **A live loss.** Any of the 302 findings at `40c009a3` absent from the build's scan, other than one whose line
   changed on the tree.
3. **A silencing filter.** Any input where removing a word *outside* the term's own sentence and *outside* the
   introducing block's own lines turns a mention into a dependency or back. (The r4 MAJOR is exactly this: deleting
   "Do not guess." flipped the answer.)
4. **A negation-shaped miss.** "Do not guess. Read these first:", "No shortcuts here; run these:", "Don't skip these,
   read them all:", "If you have not yet done so, run these:" or "Never guess — read these first:", followed by a list,
   judged a mention.
5. **A second reader of structure.** A second loop over `lines` inside the Markdown judgement that tests for a list
   marker, a fence or a blank line outside the block reading (grep-able: `LIST_ITEM.match` or a fence regex at more
   than one site).
6. **Unbounded time.** The judgement of one term in a file holding a 1 MB run of non-blank lines takes more than 1 s.

**Stop condition.**

- Build F **once**, from this section. Then **one** review round, briefed to **refute** FAILS IF 1–6 (not to confirm
  the build), with `attack.py`'s rows and the differential as its starting instruments.
- **If that round observes FAILS IF 1, 2 or 3 caused by the build:** do **not** fold. Fall back to **N** — HEAD's
  three walkers untouched, with `NEGATES` deleted — which is 2 deleted lines, cannot lose a finding by construction
  (`any(not …)` over the same matches becomes `any(…)`), and measured 0 live change. File the structural misses as
  bounds and close backlog #680. The 4 live `brief/SKILL.md:62` misses then stay open as a named backlog row.
- **If the round's findings are all FALSE-direction, or MISS rows of §5.4:** they are FILED as bounds, not folded. No
  second fold in this component under any outcome.
- **Mood is closed either way.** A finding of the form "this introducer is not really an instruction" or "this verb is
  negated" is answered by §5.4, not by code. Re-opening it requires an observed **live** false finding that costs more
  than one reading — i.e. a count, quoted from a scan.

---

## 7. What did we decide that is not written down?

1. **The failure direction.** "A false negative publishes a broken component; a false positive costs one reading" is
   the premise behind every severity call in these rounds (r3 graded the false finding MINOR, r4 the silent miss
   MAJOR), and it appears in no spec section, ADR or code comment **[M: grep of the spec §5, `CONTEXT.md`, the script;
   ADRs by title only — §8]**. The install-root review recorded the same gap. Its absence is what let the r3 fold fix
   a MINOR by opening a MAJOR: no written rule said that trade runs the wrong way. **Write it in spec §5 rule 1.**
2. **That a mention is nobody's input.** No script other than `check-publishability.py` reads the report's `mentions`
   **[M: text search over `scripts/`]**. A term judged a mention is, in effect, discarded — which is what makes the
   direction in (1) matter, and what makes 465 detector-4 Markdown mentions against 9 findings an unaudited pile.
3. **That rounds were spent on shapes with no live instance.** Nobody decided to prefer fixture forms over the tree;
   it followed from reviewers being asked for counter-examples and not for a labelled read of the live mentions. The
   r3/r4 findings change 0 live findings; the tree held 4 real misses in a file a finding had already quoted. **A
   round on a judgement over prose should owe one labelled sample of its live mentions.**
4. **That the "prose" judgement belongs to two detectors.** The rounds, backlog #673 and #680 call it detector 4.
   Detector 1 uses the same function (§2).
5. **That an item's body is not part of the list's claim.** HEAD behaves this way by accident of walker 2; F keeps it
   on evidence (§4.1). Either way it is now a decision, and belongs in §5.4's bounds.
6. **That the THRASHING answer had no reader.** The arming was recorded in a coordinator round document and the PR
   merged with no Phase 6; a backlog row caught it afterwards. This review does not propose a guard for it (§8).

---

## 8. Not measured — treat each as NOT RUN

- **The mutation sweep** under any candidate (`check-plan-code.py --mutate`). The manifest anchors were only grepped.
- **A second reviewer.** No Codex half, no independent Claude half; every "true dependency / false finding" label is
  one reader's.
- **Labelling the live mentions as a population.** Only the skill/contract Markdown mentions were read line by line
  (earlier in this review: 6 shape-reachable misses in `brief/SKILL.md` — lines 58, 59 and the four on 62 — plus one
  semantic one, `dashboard/SKILL.md:28` **[I]**). The ~650 mention keys under `docs/memory/` and the velocity docs
  were **not** labelled; nor were the 14 Markdown findings at HEAD (at least one, `reservation-release-slice-state.md:17`,
  is false **[I]**). So no precision or recall figure for the live tree exists, for HEAD or for F.
- **The 77 differential gains** of §4.2 were sampled (20 of the C2 variant's 80 were printed and skimmed), not labelled.
- **The differential on five excluded sets:** `docs/reviews/` (2,985 files), `docs/superpowers/` (203),
  `docs/dashboard-entries.md`, `docs/roadmap-to-launch.md`, and `docs/backlog.md` (run for completion and time only,
  not for flips). The first full-repo attempt did not finish inside the time bound.
- **Candidates B, C, E and N on the refutation corpus and the self-test;** C and E live figures are from the first
  prototype.
- **The install experiment** — the spec's own falsifier for the scan. Whether the 4 gained guards block a stranger's
  install of `skill-brief` is untested; "true dependency" there is a reading of the sentence.
- **`docs/adr/` 0001–0015** were read by title only; no ADR was found to bear on this judgement, on that basis.
- **Windows line endings beyond one row** (`crlf` passes under all four tested candidates), tabs beyond one row,
  Markdown inside HTML blocks, front matter, setext headings, reference-style constructs: untested.
- **A guard that a THRASHING arming cannot be merged past** (§7.6): not designed, not measured.
