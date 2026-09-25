# The round record stops being hand-parsed — backlog #117

> **Anchor:** `review-decides-itself` — **ADR:** none
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded
> evidence rather than recall.

**Status:** ⟳ **DESIGN — NARROWED BY ARCHITECTURE REVIEW, 2026-09-25. §2 REPLACED IN FULL; r4 OWED.**
Three rounds, five halves, none converged — and the review convened by this branch's own
pre-commitment found the reason: ⛔ **the falsifier could not be built well because the operation it
guarded was never owed.** #117's WORK names three reshapings and no corpus, and the corpus question
is **#119**, decided 2026-09-15 as *"none required if old branches simply drain"*. **The spec
re-opened a closed question under a different word and spent three rounds guarding it.** The
substrate choice and §1's layer model survive; the migration does not. Verdict:
`docs/reviews/architecture-review-2026-09-25-conversion-falsifier.md`.
Nothing implemented. NOT YET AT THE HUMAN GATE.** Round 1 returned **4 Blocking, 6 High, 8 Medium,
4 Low** across the two halves, and **both halves independently found the same Blocking**: the first
draft's two-way split of *structure vs values* had no place for **schema**, so deleting the parser
deleted the refusal of an absent `findings:` key and `{"round": 1, "fixes_nontrivial": false}`
reached `STOP` — r3's Blocking restored verbatim. **The design as first written fired its own
falsifier.** The substrate choice survives; the framing around it did not.
**Date:** 2026-09-25. **Discharges:** backlog **#117**, whose `ARCHITECTURE_REVIEW — REDESIGN`
verdict has been armed since 2026-09-15. **Unblocks:** backlog **#185**, **#188**, and the parked
spec `2026-09-25-decision-card-soundness-design.md`.

---

## Why this exists

`scripts/check-review-decision.py` decides whether a review round is owed, whether a branch has
converged, and whether an architecture review is armed. It reads that evidence out of a
fenced `yaml` block in each round document using **hand-rolled regular expressions**.

⛔ **THE TOOL FILED THIS AGAINST ITSELF AND IT IS STILL TRUE TODAY.** Run it:

```
$ python3 scripts/check-review-decision.py        # on review-decision-procedure
ARCHITECTURE_REVIEW — thrashing: 'parse-header' carried fix-induced findings in r6 and r7
```

⭐ **SEVEN RECORDED DEFECTS ACROSS TWO SHAPES — ⟳ r1 corrected both the count and the claim.**
The first draft said *"six … every one is absence reads as a pass"*, **contradicted by its own table
two rows below**: r2 M and r6 M are false `CANNOT_RUN`, the opposite direction. And #117's own row
cites a **seventh**, r7 L1, which this table omitted. Every one was found by a reviewer rather than
by a test
(`scripts/check-review-decision.py`, comments at `:212`, `:219`, `:224`, `:228`, `:254`, `:260`):

| # | what happened | what it read as |
|---|---|---|
| r1 B1 | parser read only `{...}` flow mappings; block-style items parsed to **zero** findings | a clean round |
| r2 B | `severity High` with no colon dropped the field | neither Blocking nor deliverable |
| r2 M | finding markers counted outside the `findings:` span | a **false** CANNOT RUN on a valid header |
| r3 B | `_findings_span` returned `""` for an **absent** key | *"a missing key is a silence"* — clean round |
| r6 M | braces in ordinary prose counted as findings | a false CANNOT RUN |
| r6 H | `fixes_nontrivial` was unreadable, so a stated CONTINUE rule could not be enforced | convergence |
| r7 L1 | malformed block-scalar text under `halves` (`claude: \` with nothing indented) was accepted and read | a valid half-record |

⛔ **FIVE read as a PASS; TWO (r2 M, r6 M) read as a FALSE REFUSAL.** Both directions are defects and
they need different fixes — a parser that raises kills the first shape and can *worsen* the second.
⚠ **And r7 L1 lives in `halves`, the field §3 calls untouched documentation.**

⛔ **A wrong parse here does not fail loudly — it yields a confident wrong DECISION**, and two of the
six reached `CONVERGED` on a branch that had not converged. ⚠ **Bounded today only because the script
declares `NO-CALLER:`** (backlog #184); the day anything consumes its exit code, this is a different
severity.

⭐ **And the defect is still producing work.** The `decision-card-soundness` spec was parked on
2026-09-25 after two rounds and **three Blockings that were one defect one layer deeper each time** —
all three because it was adding another hand-rolled reader to this same component.

---

## PRIOR ART — what already does this?

| Thing | Does it cover this concern? |
|---|---|
| `parse_header` itself | ⛔ **No — it IS the subject.** **109** lines across four functions, **7** recorded defects |
| `check-anchors.parse_header`, `gen-goals-page.parse_header` | **No, and they are NOT this function** — they parse a spec's `> **Anchor:**` line. ⚠ Measured: a **name collision**, three functions, three jobs. Out of scope, noted so a reader does not think the blast radius is three files |
| `check-review-rounds.py` | **No** — it answers *did both halves run* from **file existence** under `docs/reviews/<writer>/`, never from this header. ⟳ *r1 Medium: the first draft's stated evidence — "it contains no reference to `halves`" — is **false**; it defines `HALVES = ("codex", "claude")` at `:81` and uses it twice. The first grep was case-sensitive and lowercase. The conclusion holds; the evidence for it did not.* |
| a YAML library (`pyyaml`) | **Not available, and adopting it is larger than the defect** — see *Rejected* |
| `json` (stdlib) | ⭐ **Yes.** `json.loads` raises on malformed input; it cannot return a partial mapping |

---

## §1 — The mechanism

**The round header becomes a fenced `json` block, read by `json.loads`.**

```
round document
  └── ```json  ──►  json.loads  ──►  dict  ──►  _validate (unchanged rules)
                        │
                        └── malformed ──► raises ──► CANNOT_RUN (exit 2), unchanged
```

**What is deleted:** `parse_header`'s regex body, `_findings_span`, `_scalarise`, `_block_findings`
— the four functions that exist only to recover structure from text. **109 lines** (AST spans at `bef49007`).

⛔⛔ **THE FIRST DRAFT SPLIT THIS TWO WAYS AND THERE ARE THREE. BOTH r1 HALVES FOUND IT
INDEPENDENTLY, AS A BLOCKING.** It said the deleted regexes were *parsing* and everything surviving
was *values*. But the checks that refuse an **absent or wrong-typed top-level key** are neither —
they are **schema**, they live inside `parse_header`'s deleted region, and nothing in the "kept" list
replaces them:

| check | where it lives today | survives the deletion? |
|---|---|---|
| `round:` present and an int | `:209` — **inside the deleted region** | ⛔ **no** |
| `findings:` key present at all | `:232` — the explicit repair for **r3's Blocking** | ⛔ **no** |
| `ROUND_REQUIRED` enforcement loop | `:245-251` — **inside the deleted region** (`ROUND_REQUIRED` at `:263` is only a constant) | ⛔ **no** |
| `_validate` on each finding | `:273-284` — **per-finding only, never sees a top-level key** | ✅ yes |

**Measured, applying only what the first draft said survives:**

```
absent `findings` key        -> _validate raises? no  |  decide() = STOP
absent `fixes_nontrivial`    -> _validate raises? no  |  decide() = STOP
findings not a list          -> _validate raises? no  |  decide() = STOP
fixes_nontrivial as a string -> _validate raises? no  |  decide() = ROUND_OWED
```

⛔ **`{"round": 1, "fixes_nontrivial": false}` is well-formed JSON and reaches `STOP`.** That is r3's
Blocking restored verbatim — *"a missing key is a silence"* — and `{"round": 1, "findings": []}`
reaching `STOP` is r6's High restored. **The design as first written fired its own falsifier.**

### The three layers, named so they cannot be merged again

| layer | mechanism | status |
|---|---|---|
| **0 · presence** | ⛔ **r2 (Claude, Medium): NO LAYER OWNED THIS.** A document with **no fenced `json` block at all** must raise — the exact shape of r3's Blocking one level up, and `json.loads` is never reached to refuse it | ⛔ **must be written** |
| **1 · syntax** | `json.loads` — malformed text raises | ⭐ **replaces** the regex body |
| **2 · schema** | ⛔ **NEW, AND IT IS BUILT, NOT KEPT** — required top-level keys `round` (int), `fixes_nontrivial` (bool), `findings` (list), each refusing on **absence** and on **wrong type** | ⛔ **must be written** |
| **3 · values** | `_validate` + `REQUIRED` — a finding with `severity: "Wrong"` still raises | ⛔ **NOT "unchanged" — r2 (Claude, High)** |

⛔ **`_validate` CANNOT BE CARRIED OVER UNTOUCHED, AND CALLING IT "KEPT, UNCHANGED" WAS WRONG IN
EVERY DRAFT SO FAR.** It was written against a reader that could only ever hand it `str` and `bool`,
because `_scalarise` produced nothing else. **JSON hands it `int`, `list`, `dict` and `null`.** A
membership test against a set of strings behaves differently for each — and an unhashable value makes
`f[key] not in allowed` raise `TypeError` rather than the intended `ValueError`, which is a refusal
with the wrong diagnosis. ⛔ **r3 (Codex, High): THE TYPE ASSERTIONS AS STATED ARE INCOMPLETE, IN THREE MEASURED WAYS.** *(a)* `isinstance(True, int)` is **`True`**, so `round: true` passes an int check — a trap `check-review-rounds.py:191-194` already documents. *(b)* Layer 2 says `findings` is a *list*, not a list of **objects**, so `json.loads` can hand `_validate` a `1`, a `[]` or a `null`, which raise `TypeError`/`AttributeError` rather than the intended `ValueError` — a refusal with the wrong diagnosis. *(c)* `_validate` accepts `component: []`, `{}` and `null` today because it only tests `str(f.get("component", "")).strip()`. ⭐ **So layer 3 gains type assertions of its own**, and the spec stops
claiming this function survives the substrate change untouched. ⚠ **This is the third time a draft
has asserted `_validate` is fine and been wrong** — r1 found it unfalsified (gutting it leaves
61/61 green), r2 finds it mistyped. **It is the least-examined load-bearing thing in this design.**

⚠ **The first draft warned that a reader would delete `_validate`. The real hazard is believing
`_validate` was ever enough** — the convening architecture review says the reshaping *"reduces
`_validate` to a schema check"* (`architecture-review-2026-09-25-decision-family.md:180`), i.e.
**changed**, not *kept unchanged*. The spec and the review disagreed about the one function both call
load-bearing, and the review was right.

⭐ **Layer 2 is backlog #185's seam falling out of the redesign** — the rules stop being reachable
only through the reader.

⚠ **THE OTHER SIX TOP-LEVEL KEYS NEED A STATED OWNER, OR THE NEXT DEFECT MOVES OUT OF SCHEMA AND INTO
SILENT EVIDENCE LOSS (r2, Codex, Medium).** Layer 2 requires `round`, `fixes_nontrivial` and
`findings`; the corpus carries nine. The rule for the rest:

- `subject`, `architecture_review`, `deliverable_findings`, `deliverable_code_findings`,
  `stopping_rule` — **carried through verbatim, not validated.** They are documentation today and
  this change does not promote them. **An unknown key is preserved, never dropped** — the converter
  refuses rather than discards.
- ⛔ **`halves` gets a TYPE rule, because r7 L1 was a `halves` defect** — a malformed block scalar
  under it was accepted and read. It must be an object of string values, or the header refuses.
  ⚠ **This is the one place §3's *"untouched documentation"* framing was wrong**: a field with a
  recorded parsing defect is not untouched.

### What the header looks like

Today — and the identical header as JSON, machine-emitted from it:

```yaml
round: 1
fixes_nontrivial: true
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: cost-evidence, disposition: fixed}
```
```json
{
  "round": 1,
  "fixes_nontrivial": true,
  "findings": [
    {"id": "H1", "severity": "High", "aim": "deliverable", "fix_induced": false, "component": "cost-evidence", "disposition": "fixed"}
  ]
}
```

⛔ **"14 today, 13 as JSON — one line shorter" WAS WRONG IN SIGN, AND THIS IS THE ONE PLACE THE SPEC
ANSWERS #117's ACTUAL QUESTION (r1, both halves).** The 13 was JSON of `parse_header`'s *projection*,
which drops `subject` and `halves` — it compared a full YAML header against a JSON rendering of part
of one.

⛔ **TWO DIFFERENT POPULATIONS WERE USED IN ADJACENT SENTENCES (r2, Codex, High).** *"30 parseable"*
came from `parse_header`; *"33 of 33"* came from a regex over `yaml` blocks — a **larger** set that
includes documents the parser rejects. Measured again at `bef49007`, and stated as three distinct
numbers because they are three distinct questions:

| population | count |
|---|---|
| round-shaped files by name | **73** |
| of those, carrying a `yaml` block | **34** |
| of those, **parseable** by `parse_header` | **31** — so **3** of the 34 carry a block the parser rejects |
| round-shaped but carrying no block at all | **39** |

⛔ ⟳ *r2 (Claude, High): the first version of this row read "**31** (42 not)" — and **42 is of 73, not
of 34**. A denominator error inside the table written to fix denominator confusion. The three
populations are now each stated against their own base.*

**JSON is longer in every parseable header measured, median +1 line.** ⛔ **r2 (Claude, High): the
first version of this table reintroduced the very confusion it was written to fix** — it restated
`31` as a fixed fact four paragraphs after declaring counts unpinnable, and `31` had already moved
because **this branch's own round records are inside the set**. ⭐ **The rule replaces the number:
every figure over `docs/reviews/coordinator/` is derived at read time by a `--calibrate` mode that
⛔ **DOES NOT EXIST YET — r3 (Codex, High) grepped for it and found zero occurrences in either
script. It is proposed work, and this document was writing as though it were built.** The snapshot
above is stamped `bef49007`, is not authority for any later claim, and has **already moved**: at
`54176525` the same derivation gives **74 / 35 / 32 / 39**, because this round's own records joined
the set.**

⭐ **The case for this substrate does not rest on density and must not be written as if it does.** It
rests on malformed input becoming *impossible to misread as valid* — and on layer 2 above, which any
substrate would need equally.

## §2 — There is NO migration. The old records drain.

⛔⛔ **REPLACED IN FULL BY THE ARCHITECTURE REVIEW, 2026-09-25.** Everything that stood here — a
converter, a field-level table, a human-read artifact, `--calibrate`, a nine-key carry-through, an
in-PR `disposition` widening — existed to guard **an operation this change never owed**. Three rounds
and four falsifier designs were spent protecting it.

### ⭐ The policy was already decided, ten days earlier, and I never cited it

**Backlog #119, 2026-09-15, verbatim:** *"**WORK:** none required if old branches simply drain."*
And, in the same row: ⛔ *"**BACKFILLING WAS CONSIDERED AND REJECTED BY THE USER** … the reason is
filed here **so it is not re-proposed as an obvious cleanup**."*

⚠ **Conversion is not literally backfilling** — it rewrites claims already made rather than inventing
claims never made, and that distinction is real. **It does not rescue the design**, because the
second half of #119 disposes of it independently: the corpus question was **asked and answered**, and
this spec re-opened it under a different word without citing the row that closed it.

### And what the migration was protecting has almost no reader

`main()` calls `rounds_for(git rev-parse --abbrev-ref HEAD)`, so a round document is decision-relevant
**only while a branch of exactly its subject name is checked out.** Measured at `4118a592`:

| | |
|---|---|
| parseable coordinator documents | **32** |
| of those, reachable by `rounds_for` | ⛔ **4** |
| unreachable | **28** |

⭐ **This branch is the proof.** It is called `backlog-117-parser-substrate`; its own records are
`round-record-substrate-*`. `rounds_for` returns **0 rounds** for the branch that produced them — so
the decision card has been blind to this entire review loop the whole time.

### Therefore

1. **Nothing is converted.** Round documents written from here on carry a `json` header. Existing
   YAML-headered documents join the 42 that already do not parse, and **drain** — #119's policy,
   applied rather than re-litigated.
2. **No converter exists**, so there is no `migrate-round-headers.py`, no ratchet obligation that
   `GUARD_PATH_RE` cannot enforce, no attestation nothing validates, and **no falsifier for any of
   it.** The four failed designs are not replaced; their subject is removed.
3. ⛔ **The CI refusal is scoped to the DIFF, not the directory** — a round document *added or
   modified in this branch* must carry a `json` header. It never fires on history, so it cannot
   become the unsatisfiable gate that forced #187's enum into this PR.
4. **`disposition` is NOT widened here.** With no migration there is no corpus to enlarge, so the
   r2 reversal is itself reversed and **#187 goes back to being independent work** — which is where
   r2's Codex half put it before the CI refusal created a false coupling.

### The one check that remains, and it is an INVARIANT

⭐ **A ~20-line projection comparator, as a committed fixture pair** — a source header and its
expected JSON, both in the repository. The test asserts that reading each yields the same projection:
`round`, `fixes_nontrivial`, and the finding list.

⚠ **This is the only shape that survives `portable-practices` §26**: fixed input, fixed output,
nothing outside the test can move it. Every one of the four dead designs asserted something about a
**live corpus** — which is why each failed differently and why a fifth would have too.

**Prototyped by the architecture review at `4118a592`** against a real header: a correct conversion
agrees; **a key omitted, a value altered, and a finding dropped are all three caught** — including the
omission class design 4 was blind to.
## §3 — The template moves with the mechanism

`docs/round-header-template.md` is the authoring contract; it changes in the same PR or the record
and its documentation disagree from the first commit.

⚠ **`subject` and `halves` are carried through unchanged.** They are `NOT required and NOT
validated` today and nothing reads them (`check-review-rounds.py` answers the half question from
file existence). They are documentation, they stay documentation, and this spec does not promote or
demote them.

---

## The concern → mechanism table

| Concern | Mechanism | Evidence |
|---|---|---|
| a malformed record must not read as a clean round | `json.loads` (syntax) **+ layer 2 schema validation** — see §1; `json.loads` alone does **not** do this | 7 recorded defects: **5** read as a pass, **2** as a false refusal |
| a well-formed record stating an out-of-range value must be refused | `_validate` + `REQUIRED` + `ROUND_REQUIRED` — **unchanged** | r2 Blocking: *"validate the VALUES, not the shape that carried them"* |
| existing records must not silently become wrong | ⟳ **the concern itself was retired by the architecture review** — nothing is converted, so nothing can be altered. Old records **drain**, per backlog #119 | §2 |
| the new reader must agree with the old one on a known input | a **committed fixture pair** — source header beside expected JSON — compared as a projection | ⟳ *four previous answers here all asserted something about a LIVE corpus and each failed differently; `portable-practices` §26 is why* |
| the authoring contract must match the substrate | `round-header-template.md` changes in the same PR | §3 |

**One mechanism per concern; no mechanism appears twice.**

---

## What this does not do — stated, not implied

- ⛔ **It does not make the header HONEST.** `aim`, `fix_induced` and `component` remain judgements.
  A sincere, well-formed, wrong header still produces a confident wrong verdict — and backlog #186
  (`fix_induced` defined twice) and #188 (relabelling governed by nothing) are exactly that, unfixed.
- **It does not give the script a caller** — backlog #184, deliberately untouched. #134's measured
  lesson: *do not build the caller in the same breath as changing the script it calls.*
- **It does not split the rules from the reader** — backlog #185, which is blocked on this and
  becomes easy after it.
- ⛔ **`disposition` is NOT cleanly out of scope — #187 is ENTANGLED, and r1 (High) was right.**
  The three `ship-src-root-alone` documents fail on **nothing but** `disposition`, and all three are
  recoverable **today** by widening the set — through the reader this change deletes. ⚠ **And the
  convening architecture review already said so**: the call *"must be made before #117's schema pins
  the enum"* (`architecture-review-2026-09-25-decision-family.md:337`). **Layer 2 pins the enum.**
  ⟳⟳ **DECIDED TWICE, AND THE FIRST DECISION WAS WRONG (r2 Claude, Blocking).** r2's Codex fold said
  *carry today's narrower set and let #187 widen it later*, on the grounds that widening would enlarge
  the migration corpus mid-migration. **The same commit also added a CI refusal against any coordinator
  document still carrying a `yaml` header — and those two folds priced their costs against worlds that
  exclude each other.** Under both, the documents that cannot be converted *because* the enum is narrow
  become **permanently red in CI**: unconvertible by the migration and refused for still being YAML,
  with no action available to anyone. ⛔ **A gate that no action can satisfy gets switched off — #56.**

  ⭐ **DECIDED: `REQUIRED["disposition"]` is widened IN THIS PR** — four strings, measured: `refuted`,
  `redesigned`, `retreat`, `moot`. Verified: all three `ship-src-root-alone` documents then parse (10,
  9 and 7 findings), so they fail on **nothing but** `disposition`. The migration corpus growing by
  three **before** conversion starts is a smaller cost than a permanently unsatisfiable CI gate, and
  #187 closes as a side effect rather than waiting. **Verified for #187's benefit:** widening
  `REQUIRED["disposition"]` with `refuted`, `redesigned`, `retreat`, `moot` makes all three parse —
  10, 9 and 7 findings — so they fail on **nothing but** `disposition`.
- **It does not rescue the 42 unreadable documents.**
- **It does not change any decision rule** — `scope_for`, `thrashing_component`, `converged`,
  `sequence_error`, `decide` and `exit_code_for` are untouched. ⭐ **A verdict that changes is a
  migration defect, which is why §2's first falsifier is verdict invariance.**

## How we would know it failed

- A round document is malformed and `decide()` returns a verdict instead of `CANNOT_RUN` →
  **the substrate did not remove the class.**
- Any subject's verdict differs before and after conversion → **a misread was preserved** (§2.1).
- A field in a converted document differs from its source text → **a misread was preserved** (§2).
- ⛔ **A comparator is written to replace the human read** → the parser question has returned under a
  new name, and the class this change exists to remove is back inside its own falsifier.
- A fallback YAML reader appears in a later commit → **#117 was postponed, not discharged.**
- `_validate` is deleted as redundant → r2's Blocking reopens; a well-formed header with
  `severity: "Wrong"` reaches a decision.

## Sizing

| Piece | Cost |
|---|---|
| swap the reader | **small, and net negative** — ⟳ *r1: **109** lines, not 121; the first measurement included `_validate` (12 lines), the function this spec explicitly **keeps**. A measurement of one set reported as a measurement of another.* Plus layer 2, which is new code |
| convert the parseable documents + the field table | ⟳ **not "mechanical" — r1 and r2 both refuted that.** The converter must read the DOCUMENT (nine keys, one inline comment), and the falsifier is a human reading **one table per parseable document at merge time** — ⟳ *r2: this line pinned `~31`, which §2 forbids four paragraphs earlier* |
| `round-header-template.md` | small |
| `--self-test` | ⛔ **the count may RISE, not fall — r1 (Medium) counted them.** Of 61 cases, **16** touch the record: ~**5** genuinely retire, **8** must be **rewritten** against JSON rather than deleted, and **3 would go RED** against the design as first written (absent `round`, absent `findings`, `fixes_nontrivial`) — which is B1 seen from the suite's side. ⚠ **A case that tested a RULE through a malformed header is not a case that tested the PARSER**, and only the latter may retire |
| ⛔ `_validate` needs cases it does not have | **r1 (High), measured: gutting `_validate`'s missing-field refusal leaves `61/61` GREEN** — its branch is satisfied by an ambient missing `component`. The one function this spec calls "kept, unchanged" and load-bearing is pinned by **zero** cases, so "unchanged" is currently unfalsifiable |
| mutation manifest | ⟳ **re-anchor, do NOT retire (r1 Medium).** 2 of 10 entries anchor in deleted code, and one of them is *"an absent `findings` key stops being refused"* — **the guard for the very defect B1 reopens.** Retiring it would remove the alarm at the moment the risk is highest |

⟳ **AN EARLIER LINE HERE SAID THE COUNT "WILL FALL" WHILE THE TABLE ABOVE SAYS IT "MAY RISE". THE
FOLD LEFT BOTH IN PLACE (r2, Codex, Medium) — two incompatible sizing instructions in one section.**
**The direction is NOT KNOWN and must not be asserted:** ~5 cases retire with their subject, 8 are
rewritten against JSON, and layer 2 needs new cases of its own — including one for a missing
`fixes_nontrivial`, which r2 measured **does not exist today** as a parser/schema case. ⛔ **A fall
is sanctioned only for cases retired WITH their subject, and is recorded at both sites with the
count and the reason.** Whether the net moves up or down is an outcome of the work, not a plan for it.

---

## ⛔ What the tests may and may not assert — raised by the user, 2026-09-25

⭐ **FILED AS `docs/portable-practices.md` §26 at the user's instruction, 2026-09-25** — this
section states what binds *this* change; §26 states the portable rule and is the owner.

**The user generalised this branch's recurring defect past documents:** *"if a document cannot hold a
derived value honestly, trying to match an exact number in tests may not be the right criteria to
pass."* ⭐ **It is right, and it decides how this change is tested — so it is a design constraint, not
a note.**

This branch found the same defect through four surfaces — corpus counts, line counts, the
`--self-test` total, citations — and every one was **a value derived from something that moves,
written down as though it were fixed.** A test is a document that executes. It inherits the defect.

**Three kinds of number, and only one of them is safe to pin:**

| kind | example here | pin it? |
|---|---|---|
| **observation** — derived from a world that moves | *"31 documents parse"*, *"109 lines"*, *"9 top-level keys"* | ⛔ **never.** It fails for reasons unrelated to the code, so it gets deleted or the number gets bumped until nobody reads it |
| **invariant** — fixed input, fixed output | *"this exact header converts to this exact JSON"*; *"verdict is unchanged for a given record"* | ✅ **yes.** The number is the function's contract, and nothing outside the test can move it |
| **policy / ratchet** — a decision, deliberately edited | `EXPECTED_MUTATIONS`; *"coverage may not shrink"* | ✅ **yes, and the edit must be conscious** — that IS the mechanism |

⭐ **THE REPOSITORY ALREADY DRAWS THIS LINE AND DOES NOT NAME IT.**
`scripts/check-selftest-counts.py` compares *"the declared count against the number of cases that
actually ran"* — **two derived values, never a literal.** It holds the **rule**, which is why it has
not rotted. `EXPECTED_MUTATIONS` pins a literal on purpose, because *coverage cannot shrink silently*
is a policy and a silent fall is the thing being caught.

### Binding on this change

- ⛔ **No test may assert a count over `docs/reviews/coordinator/`.** Not 31, not 73, not 34. Those
  move every time a round is recorded — **including by the round that records the test.**
- ✅ **The conversion fixture is a fixed pair**: committed source header → committed expected JSON.
  Byte-exact, and safe, because both sides are in the repository and neither is an observation.
- ✅ **The corpus check is a RULE, quantified over whatever exists**: *for every parseable document,
  convert, re-read, and the verdict is unchanged.* It passes on 31 documents and on 300.
- ⚠ **The `--self-test` count stays declared-and-verified-by-running**, which is the safe pattern
  already: nothing compares it to a literal written in prose.

⚠ **And this is why §3's `--calibrate` exists rather than a number.** The same rule, applied to the
document instead of the suite.

## Rejected, with reasons

**Vendor a minimal YAML-subset parser** (#117's reshaping 2). Keeps authoring identical and requires
no migration. ⛔ **But it is still a hand-rolled parser with the same failure mode available, so it
resets #117's clock rather than discharging it** — and it is the only option that *adds* code to own
on a file already carrying five backlog rows. This repository has recorded *a second implementation
of one rule drifts* **seventeen** times.

**Adopt `pyyaml`** (not in #117). A real parser, authoring unchanged, strictly better than vendoring.
⛔ **Measured: there is no `requirements.txt`, `pyproject.toml` or `setup.py` in this repository** —
every script is stdlib-only by construction. Adoption means a Python dependency mechanism across two
CI workflows, every developer machine, and every guard invoking bare `python3`. `check-python-pin.py`
exists *because* CI and a developer machine already disagreed once about the same commit. **A larger
change than the defect.**

**Drop the header; pass counts on the command line** (#117's reshaping 3, proposed by Codex at r3).
Removes the parser entirely. ⛔ **But it moves the bookkeeping to the caller, and #184 establishes
there is no caller** — so "the caller" is a human retyping counts, which is the failure the header
exists to prevent.

⚠ **#117's stated cost for the chosen option — *"costs the hand-writability the header exists to
offer"* — was priced against an author who does not exist.** `docs/round-header-template.md:3` says
*"Every **coordinator** round document carries this block"* and `:39` calls the fields **"agent
records"**. These are serialised by an agent, not typed by a person, and an agent emits JSON more
reliably than a YAML subset. ⟳ ⛔ **This sentence used to end "the residual cost is quotes, at one
line shorter" — corrected in r1 and STILL STALE HERE until r2's sweep.** Faithful JSON is **longer in
31 of 31** parseable headers. The residual cost is **quotes plus about a line per document**, and the
case rests on layer 1 + layer 2 making malformed input impossible to misread — never on density.


---

## ⟳ The sweep that r2 forced, recorded so the pattern is visible

**r2 (Codex, Low) found that r1's folds repaired headlines and left downstream copies standing** —
the concern table still said *"6 defects, all absence reads as a pass"* after the inventory went to
seven and split two ways; *"count parity"* survived in two places after §2 dropped it; and the
*Rejected* section still ended *"one line shorter"* after §2 corrected the sign.

⭐ **Eight stale sites, all downstream of a fix that was itself correct.** This is the repository's
recorded *after fixing, SEARCH for the class* — an instance-fix leaves the document asserting the
premise its own correction removed, and a reader who lands on the downstream copy has no way to know.
**Every count that moved is now either restated at a named commit or removed in favour of a rule.**

⛔⛔ **THE SWEEP MISSED ONE, AND THEN r2 FOUND THREE MORE. IT HAS NOW FAILED TWICE.** After eight sites were fixed, §1's
*"What is deleted"* still read **121 lines** — the very number r1 corrected to 109, standing as a
live claim four lines below the table that corrects it. It was caught by re-grepping the corrected
strings rather than by re-reading. ⭐ **A sweep is a claim like any other and needs its own check:
grep for the OLD value, not for the new one.**


---

## ⛔ THRASHING WATCH — `conversion-falsifiers`, three rounds, three failures

**Recorded by r2's Claude half, and recorded here rather than left in a review document.**

| round | falsifier proposed | how it failed |
|---|---|---|
| spec | verdict invariance + finding-count parity | **could not fire** — parity is enforced by the parser already, 0 disagreements across the corpus |
| r1 fold | a field-level text diff | **could not be built** — telling one field from two needs the parser being deleted |
| r2 fold | converter emits tables, a human reads them | **audited itself** — the source column was the broken reading, so it matches on the one case it exists to catch |

⛔ **`docs/review-method.md`'s arming condition is MET** — three consecutive rounds, one component,
each defect created by the previous round's fix. **It is not convened, and the reason is stated so it
can be disagreed with:** the method's own test is *can a redesign remove it?*, and here it can, in one
sentence — **the left column is raw source text**. That is a fix, not a prose floor.

⛔⛔ **PRE-COMMITTED, SO IT CANNOT BE ARGUED AWAY LATER: if r3's fold produces a FOURTH falsifier
design that fails a fourth way, the architecture review is convened unconditionally.** No further
argument, no re-reading this paragraph.

## ⛔⛔ IT FIRED. r3, CODEX HALF, 2026-09-25 — AND THE FALSIFIER IS NOT BEING PATCHED AGAIN

| round | falsifier | how it failed |
|---|---|---|
| spec | verdict invariance + count parity | **could not fire** |
| r1 fold | field-level text diff | **could not be built** |
| r2 fold | table read by a human | **audited itself** |
| **r3 fold** | **left column is raw source text** | ⛔ **NO SIGNAL FOR AN OMISSION** |

**The fourth failure is a NEW class, not a repeat** — which is the distinction the pre-commitment
turns on, and the reviewer was asked to be precise about it. The left column is *whole raw text*; the
right renders *only the fields the converter produced*. **A dropped key therefore produces no
mismatch row at all** — there is nothing to line it up against. The design catches a value that
*changed* and is blind to one that *vanished*, which is this component's founding defect
(*absence reads as a pass*) arriving inside the check built to detect it.

⛔ **FOUR DESIGNS, FOUR DISTINCT FAILURE MODES, ONE COMPONENT. That is no longer a sequence of
mistakes; it is evidence that the thing is being approached wrongly.** Per the pre-commitment, the
architecture review is **convened, not re-argued** — and the falsifier is deliberately **left
unfixed in this document** so the review examines the approach rather than a fifth patch.


⟳ **r2 (Claude, Medium) — the sweep's second failure, recorded rather than quietly patched.** After
declaring itself complete it had left a `(42 not)` hanging off the wrong denominator *inside the
table written to fix denominator confusion*, two sites still pinning `~31` four paragraphs after §2
forbids pinning a count, and two `file:line` citations naming the wrong statement (`:203-205` for a
check that is at `:209`; `:243-246` for one at `:235-236`).

⭐ **The lesson is not "sweep harder".** Three of those four are **derived** claims — a denominator, a
pinned count, a line number — and every one of them is a value that moves when its source moves. **A
document cannot hold a derived value honestly; it can only hold the rule that produces it.** That is
the same finding this branch has now made about corpus counts, about line counts, and about the
`--self-test` total, arriving a fourth time through a fourth surface.
