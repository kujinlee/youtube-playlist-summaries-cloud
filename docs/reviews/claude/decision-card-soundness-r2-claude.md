# Claude adversarial review — `decision-card-soundness` r2

Subject: `docs/superpowers/specs/2026-09-25-decision-card-soundness-design.md` at `dd7757e9` (504 lines).
Read first, in order: the r2 coordinator record, `docs/reviews/codex/decision-card-soundness-r2-codex.md`,
`docs/reviews/claude/decision-card-soundness-r1-claude.md`, the spec, `git diff 9d1987ca..dd7757e9`,
`scripts/check-review-decision.py`.

**Mandate: refute the folds.** Rounds 2+ alternate so this half reviews r2's fixes. Every finding
below is attached to something the r1 or r2 fold *did*, except H4, which is about an input both folds
inherited and neither looked at.

## Verdict

**NOT CONVERGED.** The r2 Blocking's withdrawal of r1's third clause is **correct** — I constructed
the sequence independently and it holds (see *What I checked and found clean*). But the two largest
r2 folds are each wrong in a way the fold itself created:

1. the `covers:` block — r2's fix for the escape's scoping — **cannot be read by the reader the spec
   names as its precedent**, and three malformed shapes of it are indistinguishable to the live
   parser, one of which silently restores the semantics r2 condemned (**B1**);
2. the commit-stamp remedy for the stale-number defect was applied to **3 figures out of at least
   ten**, and the document still carries, at HEAD, the exact number (`145`) whose two corrections
   are the evidence the r2 record uses to argue *thrashing* — so **the pre-committed falsifier for
   r3 is already tripped by the fold that wrote it** (**H1**).

And one finding neither half has raised: the corpus's `fix_induced` flag is **undefined at round 1**
under the template's own words, 6 of 8 parseable r1 documents set it anyway, and both this branch's
`ARCHITECTURE_REVIEW` verdict and the spec's headline *"owed after two [rounds]"* depend on it
(**H4**).

---

## Findings

### B1 — Blocking · `escape-grammar` · deliverable · fix_induced: **true** (r2's `covers` fold)

**The reader the spec cites as its precedent cannot read the key the spec proposes, and I measured
three malformed shapes that the live parser accepts or misdiagnoses.**

§2 (lines 156-161) makes `fixes_nontrivial` the precedent, explicitly because `REVIEW GAP:`
*"supplied a grammar and no reader"*. That reader is:

```python
# scripts/check-review-decision.py:246
mm = re.search(rf"^{key}:\s*(\S+)\s*$", body, re.M)
```

It requires a **scalar on the same line**. `components_distinct:` as §2 now specifies it
(lines 203-207) is a **nested block** — `covers:` and `reason:` on following lines — so the line is
`components_distinct:` with nothing after the colon and `(\S+)` cannot match. **The fold replaced a
precedent that supplied a grammar and no reader with one that supplies a placement and no reader.**
That is r1's finding 4, reintroduced by its own fix, one layer in.

I ran the four shapes an implementer or a declarer will actually produce, against the shipped
`parse_header` (command: `python3 -` importing `scripts/check-review-decision.py`, `parse_header` on
a minimal r3 header with each block substituted):

| shape | result |
|---|---|
| A — correct nested block, after `findings:`, non-indented | **parses**, and `components_distinct` is **absent from the returned dict** (`keys=['findings','fixes_nontrivial','round']`) |
| B — pasted **indented**, as the refusal message prints it | `RAISED ValueError: header declares 1 finding item(s) but 3 parsed — refusing to guess` |
| C — `components_distinct:` present, **`covers:` omitted** | **parses**, silently, indistinguishable from A |
| D — scalar form `components_distinct: <reason>` (the spec's own pre-r2 shape) | **parses**, silently, indistinguishable from A and C |

C is the Blocking. The spec states what happens when `covers` **changes** — *"If either set changes,
the declaration stops matching and the refusal returns"* (line 211) — and says nothing about what
happens when it is **absent or unparseable**. The natural implementation of an *optional* key is
*present → satisfied*, and that reading is not hypothetical: **it is the spec's own r1 semantics**,
the pair-scoped declaration that r2's High refuted (lines 192-199). So a declarer who drops the
`covers:` line, or an implementer who reads the key without validating its body, lands back on the
behaviour this round removed — and `parse_header` reports nothing, because it never looks.

⭐ **This is the exact class `parse_header` has already paid for four times, in its own comments:**
r1 B1 (flow-only parsing → zero findings → clean round), r2 Medium (markers counted outside the
span), r3 Blocking (`_findings_span` returns `""` when the key is absent → *"a missing key is a
silence"*), r6 Medium (braces in prose). Every one is *absence reads as a pass*. The spec adds a
fifth optional key and does not say, in the one place it would be binding, that absence of `covers:`
under a present `components_distinct:` must **raise**.

**What would fix it, as spec text:** state that `components_distinct` is read as a two-key block;
that a present key with a missing, malformed or non-matching `covers` **raises** (i.e. `CANNOT_RUN`,
not *escaped*); and that the reader is a **new** optional block reader, not `ROUND_REQUIRED`'s
scalar regex — because the sizing line that calls it *"an optional sibling of the existing
`ROUND_REQUIRED` read"* (line 390) is measurably wrong about what that read can do.

---

### H1 — High · `calibration-claims` · deliverable · fix_induced: **true**

**The commit-stamp remedy covers 3 figures out of at least ten, the document still contains the
number the remedy exists to stop being wrong, and the pre-committed r3 falsifier is therefore
already tripped.**

The r2 fold's new sentence (`git diff 9d1987ca..dd7757e9 -- docs/superpowers/specs/`, line 317 at
HEAD) claims:

> *"…and hence **every figure in this table carries the commit it was taken at**."*

`grep -n "9d1987ca" docs/superpowers/specs/2026-09-25-decision-card-soundness-design.md` → **5 hits
in the whole document, 3 of them in §3's table** (lines 317, 318, 319). Unstamped, and measured
stale at HEAD (`dd7757e9`) by re-running the parser over `docs/reviews/coordinator/`:

| site | spec says | measured at `dd7757e9` |
|---|---|---|
| line 320 | `…on velocity-doc-consistency` **3** | 3 — still right, still unstamped |
| line 321 | `…where doing nothing already reached the right answer` **2** | 2 — still right, still unstamped |
| line 331 | `docs/reviews/coordinator/` holds **134** documents | **135** |
| line 332 | only **71** are round records by name | **72** |
| line 333 | **29** parse and **42** do not | **30** parse, 42 do not |
| line 174 | *"all **29** existing rounds must still parse"* — the fixture's falsifier | **30** |
| line 266 | *"✅ **29** rounds, **152** findings"* | **30** rounds, **158** findings |
| line 496 | *"**0 of 152** findings carry that input"* | 0 of **158** (claim survives, denominator does not) |
| line 499 | *"**83** distinct names across **145** findings, **67%** used exactly once"* | **89** across **158**, **66%** |

⛔ **Line 499 is the finding, not the arithmetic.** `145` is the number §3's own cell (line 317)
calls out as wrong **twice**, tracing `145 → 147 → 152`. It survives, uncorrected and unstamped, in
*Rejected, with reasons* — the section r2's own High reopened. And it was **already wrong at the
commit the fold stamped everything else to**: replaying at `9d1987ca` in a throwaway worktree gives
**88 distinct components over 152 findings**, not 83 over 145. So the remedy was applied to the
instance that was pointed at and not to the class — this repo's *fixing a PREMISE rather than
covering the BRANCH*, inside the document whose subject is that shape.

⚠ **Consequence for the round-2 record, stated plainly.** Its *PRE-COMMITTED FALSIFIER* reads: *"If
`calibration-claims` carries another fix-induced finding in r3, the redesign did not work and the
architecture review is convened unconditionally."* This finding is a fix-induced
`calibration-claims` finding, and it is about the redesign's own completeness claim. **By the record's
own pre-commitment, the architecture review is convened.** I am not arguing the pre-commitment away;
I am reporting that it fired, one round earlier than it expected, and on the sentence that wrote it.

**Also, smaller, same component (folded here rather than filed separately):** *"14 of 134 documents
… mention the card"* (line 473) reproduces exactly — `grep`ping the literal string
`check-review-decision` over `docs/reviews/coordinator/*.md` gives **14**, and **8** of them are
`review-decision-procedure` r1-r7 plus `decision-card-soundness` r1, so r2's Low correction (7 → 8)
is right. But the metric is **filename matching**, and by it `decision-card-soundness-r2-coordinator.md`
— which quotes the card's verdict string verbatim — **does not count as a mention**. A metric whose
denominator grew by one document this week and whose numerator excludes that document is measuring
the population the grep sees, not the one the sentence claims.

---

### H2 — High · `prior-art` · deliverable · fix_induced: **true** (r2's #136 fold)

**The #136 concession is honest about the half Codex named and silent about two further halves, one
of which is a defect this spec's mechanism inherits whole.**

I read `docs/backlog.md` row 136 in full (`awk -F'|' '$2 ~ /^ *136 *$/' docs/backlog.md`). Its
**WORK** list has four numbered items plus a closing paragraph of mechanical defects. The spec's
*Scope* section now answers:

- **(2)** the route question — answered at length, correctly;
- the derivation sentence — answered, measured, and labelled transitional (r2's fold);
- **(1)** decompose severity into measured axes — named as untouched at line 291.

It does not mention:

- **(3)** *"Ask the root-cause question routinely, not only as a thrashing escape. `Can a redesign
  remove it?` exists in `review-method.md` but **fires only when thrashing is already armed**"* —
  this spec's whole mechanism is a new arming path, so it is directly in (3)'s subject matter;
- **(4)** *"a fix that introduces a NEW ARTIFACT restarts that artifact's clock rather than riding
  the current round"* — a candidate policy that changes what a *round* means, which is the unit both
  `thrashing_component` and this spec's refusal are computed over;
- ⛔ and, most consequentially, #136's **third** mechanical defect: *"it is **sensitive to round
  granularity**, since the same defects folded into one round would not fire."* The spec quotes
  #136's free-text sentence and the blind-to-a-moving-defect sentence, and stops one clause short of
  this one.

Granularity is not a neighbouring concern — **the proposed refusal requires fix-induced findings in
*both* of the last two rounds, so folding one round's worth of work into its predecessor suppresses
the refusal exactly as it suppresses the trigger.** The spec's *What this does not do* (lines
356-367) lists six things and this is not among them, while §2's escape is scoped per-pair, which
inherits the same sensitivity a second time. A reader cannot currently tell whether the design
considered granularity and accepted it or never saw it.

**So: the concession is real but partial.** It concedes the label (*transitional*, with a
pre-committed supersession condition, which is good) for the half Codex named, and leaves the
enumeration of #136 at three of five. The *Filed consequence* line — *"#136 stays open and unclaimed
by this work. Its (1) … is untouched here"* — names one untouched item and reads as exhaustive.

---

### H3 — High · `prior-art` · deliverable · fix_induced: **true** (r2's #136 fold)

**"0 of 152 findings carry the input" is measured over the wrong corpus, and the same fact about this
spec's own new key is presented as acceptable eleven paragraphs earlier.**

Two problems, and the second is the one that matters.

**(a) The corpus.** #136 asks for a partition *"derived from the file/symbol **a finding names**"*.
The spec measures the **coordinator header**, which is a six-field summary
(`id severity aim fix_induced component disposition` — I reproduced the key union: all six on
158/158 findings, no seventh key). The place a finding *names* a file is the **half document**.
Measured: `246` documents under `docs/reviews/{claude,codex}/`, **242 (98%) contain at least one
file path** matching `[\w./-]+\.(py|sh|ts|tsx|md|json|yml|toml|sql)`. ⚠ I did **not** derive a
per-finding rate — the half documents have no machine-readable finding boundary, which is itself
part of #136's problem — so the honest claim is bounded: *the input is absent from the header and
near-universal in the corpus the header summarises*, and the spec's table row *"⛔ 0 findings carry
the input"* does not say which of the two it measured.

**(b) The symmetry, which is fatal to the argument as written.** §2 line 172-175 justifies making
`components_distinct` **optional** precisely because *"every round document already committed lacks
it, and making it required would refuse the entire existing corpus."* That is the same corpus fact —
**a key carried by 0 of the existing records** — and the spec draws the opposite conclusion from it
in the two places:

| | the fact | the spec's conclusion |
|---|---|---|
| `components_distinct` (§2) | 0 of 30 round documents carry it | *therefore read it optionally and ship* |
| a derived file/symbol key (*Scope*) | 0 of 158 findings carry it | *therefore derivation **⛔ starts empty** and is not runnable on the record as it exists* |

⛔ **The argument proves too much: applied to itself it refutes this spec.** It would equally have
refuted `fix_induced` and `aim` before they were added, and #136's own scope line — *"design first,
no code until a spec exists"* — says the field's absence is the **state a design task starts from**,
not a verdict against it. The table row *"corpus available to calibrate against | the existing 29
rounds | **starts empty**"* is the honest cost of doing a design task second; it is not evidence that
the alternative is worse.

This does not overturn the *transitional* label, which I think is right and is r2's best fold. It
means the measurement offered as the reason is doing less work than the prose around it claims — and
*Rejected*'s new preamble (lines 494-497) presents it as the closing evidence.

---

### H4 — High · `fix-induced-input` *(new component — see note)* · deliverable · fix_induced: **false**

**`fix_induced` is undefined at round 1 by the template's own definition, 6 of 8 parseable round-1
documents set it `true`, and both this branch's `ARCHITECTURE_REVIEW` and the spec's headline number
depend on it.**

`docs/round-header-template.md:32` defines the field as:

> `fix_induced` | `true` `false` | was the defect introduced by a fix written **after a previous
> round**?

A round-1 finding has no previous round. Line 45 then glosses it more loosely — *"answers **did we
make this?**"* — and the two readings disagree exactly at r1. Measured (parse every
`docs/reviews/coordinator/*-r1-coordinator.md` with the shipped `parse_header`): **8 parse, 6 carry
at least one `fix_induced: true`** — `decision-card-soundness` (M1), `fix-src-viewer-escaping` (7),
`peer-sites` (3), `seed-explainer-serve-manifest` (8), `velocity-177` (7),
`velocity-doc-consistency` (3).

Two consequences, both load-bearing and both measured by replaying the shipped functions:

1. ⛔ **This branch's own verdict rests on one such label.** `decide(rounds_for("decision-card-soundness"), "one-round", True)` returns
   `ARCHITECTURE_REVIEW — thrashing: 'calibration-claims' carried fix-induced findings in r1 and r2`.
   Flip **r1 M1** alone to `fix_induced: false` and it returns `ROUND_OWED — r2 produced a Blocking`.
   r1's induced set is `{calibration-claims}` and it has exactly one member.
2. **The spec's headline claim moves by a round.** Replaying the merged-synonym labelling of
   `velocity-doc-consistency` (the *Why this exists* table, line 36): as recorded it fires at r2, r3
   and r4. With r1's three `fix_induced: true` flags zeroed it fires at **r3, r4** — `None` at r2.
   The sentence *"an architecture review was arguably owed **after two**"* (line 39) becomes *after
   three*, which is still a defect and still four rounds too many, but it is not the number the
   document states.

**Why this is not covered by the out-of-scope line.** Line 364 declares *"It does not touch `aim` or
`fix_induced` **honesty**"*, and line 433 dismisses the sibling as *"same class, **no measured
instance**"*. This is not a honesty problem — every one of those six documents was, as far as I can
tell, filled in sincerely under the looser gloss. It is a **definition** problem in the field that is
*"the arming condition for the architecture review"* (template line 46-47), it now has a measured
instance in 6 of 8 documents, and it changes the verdict the spec is calibrated on. An out-of-scope
declaration resting on *no measured instance* should be re-stated once one exists.

⚠ **Component note.** I introduce `fix-induced-input` rather than reuse a name, because none of
`cost-evidence`, `escape-grammar`, `caller-and-record`, `calibration-claims`, `prior-art` or
`hidden-thrashing-condition` is this concept: it is about the validity of the *input* both the
existing trigger and the proposed refusal consume, and merging it into `calibration-claims` would be
the same merge I criticise in H5.

---

### H5 — High · `round-record-labelling` *(new component — see note)* · instrument · fix_induced: **true**

**The round-2 record's justification for its own component merge states a counterfactual that is
false. Splitting Codex's labels back out does not silence the trigger — it produces this spec's own
refusal, which is a stronger result than the firing.**

The r2 coordinator record says of merging findings 2 and 5 into `prior-art` and finding 6 into
`calibration-claims`:

> *"⚠ That last merge is the coordinator judging its own subject. Recorded explicitly so a later
> reader can disagree with it; **splitting them back out would silence the trigger below**, which is
> precisely the defect this branch is about."*

I replayed it. Restoring **Codex's own six labels and its own `fix_induced` values verbatim**
(`hidden-thrashing condition`/yes, `backlog-136 scope`/yes, `components-distinct scope`/yes,
`calibration corpus`/**no**, `exit-code settlement`/yes, `card-mention measurement`/yes):

```
CODEX LABELS VERBATIM for r2: ('ROUND_OWED', 'r2 produced a Blocking')
   r1 induced: {'calibration-claims'}
   r2 induced: {'backlog-136 scope', 'components-distinct scope', 'card-mention measurement',
                'hidden-thrashing condition', 'exit-code settlement'}
   would the PROPOSED refusal fire? True
```

So under Codex's labels: `thrashing_component` returns `None` — but **both rounds carry fix-induced
findings and the sets are disjoint, which is exactly the two-clause condition §1 proposes.** The
shipped card says `ROUND_OWED`; the spec's card says `CANNOT_RUN — r1 and r2 both carry fix-induced
findings but name no component in common`. That is not silence. **It is the branch demonstrating its
own mechanism on itself**, which is a materially better piece of evidence than the merged firing and
is the single strongest calibration datum available to this spec.

Three things follow, and I want to be fair about each:

- **The merge's direction is defensible.** #136 carries the standing user instruction *"treat any
  proposal that makes a gate fire LESS with suspicion"*, and the coordinator chose the heavier
  verdict, disclosed the conflict of interest, and invited disagreement. I am not alleging
  self-serving labelling; the costlier choice is the right posture.
- **But the stated reason is wrong**, and it is wrong in the direction that makes the merge look
  forced — *"the alternative is silence"* is what removes the choice. The alternative was a refusal.
- ⛔ **And the episode is the spec's motivating defect run in reverse.** *Why this exists* is built on
  *three findings relabelled into one name made the trigger fire*. Here, **six findings relabelled
  into four names made the trigger fire**, on the branch about that lever, by the same free-text
  mechanism, decided by one person with a stake in the answer. The spec's *What this does not do*
  says it *"does not make `component` mechanical"* — this is the measured cost of that, and neither
  §1 nor §3 records that the branch produced an instance of it.

**What would fix it, as spec and record text:** correct the counterfactual in the r2 record; and add
the case to §3 as a calibration datum — it is the only instance in the corpus where the proposed
refusal and the existing trigger disagree on a live branch, and it currently exists only as a merge
note.

⚠ **Component note.** `round-record-labelling` is new for the same reason as H4: the concept is *a
coordinator's labelling decision changed a mechanical verdict*, which is neither the spec's condition
(`hidden-thrashing-condition`) nor a number in the spec (`calibration-claims`).

---

### M1 — Medium · `escape-grammar` · deliverable · fix_induced: **true** (r2's `covers` fold)

**The refusal message prints the `covers:` block indented, and pasting it as printed makes the
subject's entire round record unreadable.**

§1's refusal message (lines 143-145) renders the block indented by four spaces inside the message
body, and the instruction is *"paste this into r3's header **verbatim**"*. Measured against the
shipped parser (shape B in B1's table): an indented `components_distinct:` block falls inside
`_findings_span`, its `{r2: [a], r3: [b, c]}` flow mapping is matched by `FINDING_RE`, and
`parse_header` raises `header declares 1 finding item(s) but 3 parsed — refusing to guess`.

Two costs, neither stated:

1. **The diagnosis points at the wrong object.** A declarer told the header miscounts its findings
   will go looking at the findings.
2. ⛔ **The blast radius is the whole subject, not the round.** `rounds_for()` (`:344-356`) calls
   `parse_header` on every matching document and *"propagates its ValueError"*, so one mispasted
   escape turns **every** decision for that subject into `CANNOT_RUN` — Q1 and Q4 included. The
   escape exists so a round can proceed; mispasted as printed, it stops the subject.

The fold's own justification — *"`covers` is printed by the refusal, ready to paste … It is a
transcript, not a judgement call"* (line 209) — is the sentence that makes this land: the design
leans on paste fidelity, and the printed artefact is indented in a way the target grammar rejects.
The fix is one line of spec text: the block is pasted **at header top level**, not under `findings:`,
and the message must render it that way.

---

### M2 — Medium · `hidden-thrashing-condition` · deliverable · fix_induced: **true** (r2's withdrawal)

**The refusal message's "note a prior firing" is implementable, but nothing in §1 says the function
receives the data it needs, and §1's own explanation of the withdrawal says the opposite.**

The withdrawal's consolation (lines 119-121) is that *"the refusal message **names** a prior firing
(`r1/r2 already armed a review on A`)"* — additive, not suppressive. I agree with the direction. But:

- §1 opens by specifying *"a pure function beside `thrashing_component`, consulted only when that
  returns `None`"* and states the condition **entirely over the last two rounds** (lines 84-96). A
  note about the **previous pair** needs `thrashing_component(rounds[:-1])` — i.e. the function must
  take the whole list, and the refusal message must be composed where three rounds are visible.
  Neither is said.
- ⭐ **And §1's justification for the withdrawal reads as if the information were gone**: *"by r3 the
  r1/r2 arming has **already expired** … the card says nothing about `A` any more"* (lines 110-113).
  That is a claim about *semantics* — the arming should not persist — but on the page it reads as a
  claim about *availability*, and the very next paragraph asks the message to recover it. Both can be
  true; the spec needs to say so, or a reader resolves the contradiction by dropping the note.
- **Sizing is understated as a result.** *"the pure function | small — mirrors an existing 12-line
  function"* (line 389). A function that mirrors `thrashing_component` sees two rounds. This one
  needs three and a second call, plus the `covers:` composition from B1.

Low-ish in isolation; Medium because the note is the *entire* compensation offered for withdrawing
r1's clause, and the cost of the withdrawal (`peer-sites` r3/r4 returns, refusals back to 5) is
accepted on the strength of it.

---

### M3 — Medium · `calibration-claims` · deliverable · fix_induced: **true** (r2's `--calibrate` fold)

**`--calibrate` over the live corpus must swallow 42 parse failures to run at all, and it does not
measure the falsifier it is offered as restoring.**

- **It must fail open to work.** At HEAD, **42 of 72** round-shaped coordinator documents raise in
  `parse_header` (39 with no `yaml` block, 3 on a `disposition` value). `rounds_for` propagates. A
  `--calibrate` that reports *"would refuse: N over the live corpus"* must therefore iterate with a
  `try/except` that skips unreadable documents — a **fail-open reader over the same corpus this tool
  refuses elsewhere**, in a script whose posture is *"cannot parse is a failure, never a pass"* and
  whose `_try` helper exists (`:378-390`) specifically because a swallowed exception once scored
  *"0 cases red"*. The spec should say that `--calibrate` prints the **skipped** count beside every
  figure, or it will report a number over a corpus it silently chose.
- **It answers a different question than the one it is offered for.** *How we would know it failed*
  names *"`components_distinct:` appears in most round documents → too sensitive"* (line 373). §3
  offers `--calibrate` as the falsifier the frozen fixture cannot give (line 339). But `--calibrate`
  as described *"re-runs the condition and prints the counts"* — it counts **refusals**, not
  **declarations**, and a refusal that has been escaped still counts as a refusal unless the
  condition reads the escape. So the number can never fall, and *"the escape has become a formality"*
  remains unfalsifiable. Two questions, two mechanisms is the spec's own rule (line 343); this is one
  mechanism offered for both.

---

### L1 — Low · `calibration-claims` · deliverable · fix_induced: false

**Every stamped figure reproduces; I could not fault one.** Recording this because the brief asked me
to re-derive them and a clean result is a finding about the round.

Re-derived in a throwaway worktree at `9d1987ca` (`git worktree add … 9d1987ca`, then importing that
tree's own `check-review-decision.py`):

```
AT 9d1987ca: all docs 134  round-shaped 71 | subjects 8 rounds 29 findings 152 failed 42
   fires 11  would-refuse 5
```

and at `dd7757e9`: `would refuse (2-clause) 5`, `(3-clause) 4`, the removed one being exactly
`peer-sites` r3/r4 — so §3's account of r1's clause (*prediction right, reasoning wrong*) is exactly
right. The 5 refusals are `peer-sites` 3/4, `velocity-177` 1/2, and `velocity-doc-consistency` 1/2,
2/3, 3/4 — 3 on `velocity-doc-consistency`, matching line 320. `14 of 134` and the `8` subcount both
reproduce (see H1 for the one caveat about what "mention" means).

---

## What I checked and found clean

- ⭐ **The withdrawal of r1's third clause is CORRECT, and I reached it independently.** I did not
  take Codex's `[[A],[A,B],[C]]` on trust; I re-ran it and also enumerated the general shape. The
  clause is *"do not refuse if `thrashing_component` fired on the previous pair"*, and the refusal is
  computed on `(r_{n-1}, r_n)` while the prior firing is about `(r_{n-2}, r_{n-1})` — two different
  pairs. Any sequence where a component recurs across the first pair and a **new, disjoint** set
  appears in the last round suppresses a live candidate with an arming that
  `thrashing_component`'s two-round window has already dropped. Over the live corpus the clause
  removes one refusal (`peer-sites` r3/r4) and zero firings, so it is cheap; it is still unsound, and
  the spec's ⭐ *a correct prediction is not a correct rule* is the right lesson.
- **I looked for a *different* unsoundness the third clause was masking, and did not find one.**
  Constructed and replayed: disjoint-then-rejoining sets, a component appearing in r_{n-2} and r_n
  but not r_{n-1}, one side empty, both sides empty, single-round subjects. The two-clause condition
  answers each the way the spec says. The gap that remains is the **window**, which r1 already filed
  as M2 and which H2 above reframes as #136's granularity defect — it is not created by the
  withdrawal.
- **`components_distinct` MISSPELLED fails closed, and I expected otherwise.** The brief asked
  whether an optional key silently absent when misspelled reopens `parse_header`'s fail-open class.
  Measured: it does not. A misspelled key is simply not found, the escape is not honoured, and the
  refusal stands — `CANNOT_RUN`, the safe direction. The hazard is one level in, on `covers:` inside
  a correctly-spelled key (B1), which is where I found it.
- **The `covers:` binding does what r2 claims** for the case it was built for. A round document
  edited so its fix-induced component set changes invalidates the declaration and the refusal
  returns; edits that do **not** change that set (adding a `fix_induced: false` finding, adding a
  finding whose component is already in the set, editing prose) leave it matching. That is the right
  granularity, and it is a genuine improvement on the r1 pair-scoping. My finding is about what
  happens when `covers` is **absent**, not when it is present.
- **`thrashing_component` outranking the refusal is correctly ordered** — `decide` (`:169-194`)
  checks `sequence_error`, then thrashing, then convergence, then tree, so the refusal inserted
  between thrashing and convergence cannot displace a firing or a sequence error. I re-ran all five
  refusal pairs: none of them has `thrashing_component` non-`None`, so the two conditions are
  disjoint over the live corpus, as §1's flow diagram asserts.
- **The exit-code retraction (line 302-306) is right and is better than r2's finding asked for.**
  `exit_code_for` is still `{"STOP": 0, "CANNOT_RUN": 2}.get(decision, 1)` (`:391-393`), the spec now
  says it *proposes* a reading rather than settling #118, and it leaves the two-line change with
  #118. No finding.
- **The *thrashing, or prose floor?* answer is right on the evidence given, with one circularity
  worth naming.** All three cited instances are the same defect — *a measured number written into
  prose that the act of recording falsifies* — so *improving findings of changing character* does not
  describe it, and `review-method.md`'s test *can a redesign remove it?* answers yes. ⚠ But the
  premise that the three are **one component** is partly the product of the merge H5 describes: r2's
  L1 arrived from Codex as `card-mention measurement` and became `calibration-claims` by a
  coordinator decision. The conclusion survives on r1 M1 and r2 M1 alone — both are literally the
  corpus count — so I do not file it; I record that the record should not cite the merged third
  instance as independent support for the merge's own consequence.
- **The `NO-CALLER` / #184 answer is properly recorded** — r1's H1 is answered as an *order*, the
  cost is admitted in the document rather than discovered later, and #134's lesson against bundling
  the caller is cited correctly. I re-checked that nothing invokes the script:
  `grep -rn "check-review-decision" .claude/ .github/ scripts/*.sh` → no hook, no CI step, no shell
  caller. Unchanged, and now declared.

## Method

Everything numeric above was produced by importing `scripts/check-review-decision.py` and calling its
own `parse_header`, `rounds_for`, `thrashing_component`, `decide` and `exit_code_for` — never a second
implementation of the rule. Corpus counts were taken over the **whole** `docs/reviews/coordinator/`
directory and filtered afterwards, so the denominators are the real population rather than the
parseable subset. Figures stamped `9d1987ca` were re-derived in a throwaway `git worktree` at that
commit using **that tree's** copy of the script, then removed. The parser experiments in B1 and M1
were **run**, not reasoned about, because this repository has already paid for reasoning about a
parser instead of executing it.
