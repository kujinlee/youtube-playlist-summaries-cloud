# The round record stops being hand-parsed — backlog #117

> **Anchor:** `review-decides-itself` — **ADR:** none
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded
> evidence rather than recall.

**Status:** ⛔ **DESIGN — r1 RAN BOTH HALVES AND DID NOT CONVERGE. r1 FOLDED HERE; r2 OWED.
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
| `round:` present and an int | `:203-205` — **inside the deleted region** | ⛔ **no** |
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
| **1 · syntax** | `json.loads` — malformed text raises | ⭐ **replaces** the regex body |
| **2 · schema** | ⛔ **NEW, AND IT IS BUILT, NOT KEPT** — required top-level keys `round` (int), `fixes_nontrivial` (bool), `findings` (list), each refusing on **absence** and on **wrong type** | ⛔ **must be written** |
| **3 · values** | `_validate` + `REQUIRED` — a finding with `severity: "Wrong"` still raises | ✅ kept, unchanged |

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
| of those, **parseable** by `parse_header` | **31** (42 not) |

**JSON is longer in 31 of 31 parseable headers, median +1 line.** ⚠ **And every one of these numbers
moved during this review, because recording these rounds moved them** — the same structural staleness
that cost the spec this one unblocks five corrections. They are snapshots at a named commit.

⭐ **The case for this substrate does not rest on density and must not be written as if it does.** It
rests on malformed input becoming *impossible to misread as valid* — and on layer 2 above, which any
substrate would need equally.

## §2 — Migration

**Every round document that is parseable at merge time is converted in the same PR, and the old
parser is deleted in that PR.** ⚠ **No count is pinned here on purpose** — it was 28, then 30, then
**31**, moving each time a round was recorded.

⛔ **A FALLBACK YAML READER IS REFUSED, AND THIS IS THE WHOLE POINT.** Keeping one means the parser
is not deleted, the six fail-open shapes remain reachable, and #117's REDESIGN is **not discharged** —
only postponed behind a flag. A migration that leaves the subject alive is not a migration.

⛔ **THE FIRST DRAFT'S FEASIBILITY EVIDENCE MEASURED THE WRONG OBJECT (r1, both halves).** It ran
`parse_header` over each document and round-tripped **its return value** through JSON — but that
return value is only `round`, `fixes_nontrivial` and `findings`. **It is a tautology over an `int`, a
`bool` and a `list`**, and it says nothing about converting a *document*.

**What the corpus actually contains** *(regex over every `yaml` block, not through the parser)*:

| | |
|---|---|
| top-level keys in use | ⛔ **9**, not 3 — `round`, `fixes_nontrivial`, `subject`, `halves`, `findings`, **`architecture_review`**, **`deliverable_findings`**, **`deliverable_code_findings`**, **`stopping_rule`**. The last four the first draft never mentioned |
| headers with a YAML comment | ⛔ **1**, not 0 — `seed-explainer-serve-manifest-r2-coordinator.md:9` carries an inline `#` comment explaining a REVIEW GAP. ⚠ **The first measurement used `^\s*#`, which sees only line-start comments**; this one is inline. JSON would delete it silently |
| headers with a block scalar | 0 — reproduces |

⭐ **So the conversion is NOT a re-emission of parsed output. It must read the document**, carry all
nine keys, and make a **stated decision** about the one comment: move it into a value, move it to
prose below the header, or lose it deliberately. **Losing it silently is not available.**

### ⛔ The residual risk, stated before it is discovered

**The converter reads through the BROKEN parser.** If that parser misread a document, the conversion
preserves the misreading faithfully — *absence reads as a pass*, one last time, on the way out.
⚠ **This is the one real hazard in this change and it is not hypothetical**: mis-parsing is the
documented behaviour of the thing doing the reading.

⛔⛔ **THE FIRST DRAFT'S TWO FALSIFIERS COULD NOT FIRE. r1 (both halves, Blocking) — and one of them
was a TEST THAT CANNOT FAIL, written in the paragraph that was being careful about exactly that.**

- **The parity check was vacuous by construction.** `parse_header:243-246` *already* refuses unless
  the list-marker count equals the parsed finding count, so for every document that parses today the
  parity holds necessarily. **Measured: 0 disagreements across all 30.**
- **And it could not be made independent without reintroducing a fixed defect** — counting markers
  over the whole header is **r2's Medium** (a bullet inside a `halves` block scalar counted as a
  finding). *A second implementation of one rule drifts*, arriving in the falsifier rather than the code.
- **Verdict invariance is a five-value collapse.** `decide()` reduces a whole record to one of five
  strings, and the corpus currently produces **two** across **8** subjects. A misread must flip one of
  eight coarse labels to be seen.
- ⛔ **And a real misread passes both.** `_scalarise` splits flow mappings on `,` (`:302-311`), so a
  comma inside a quoted `component` silently truncates it — parity passes `1 == 1`, the verdict is
  unchanged, and the conversion writes the **truncated** value in permanently. ⚠ `component` is the
  thrashing axis, so a truncation inert today can arm or disarm `ARCHITECTURE_REVIEW` in a later
  round. ⚠ **Honest bound: 0 live instances of this shape in the corpus** — a hole in the falsifier, not a
  live corruption.

### The falsifier that actually covers the class

⛔ **r2 (Codex, Blocking) REFUTED THE FIRST VERSION OF THIS FIX: a field-level diff CANNOT catch the
comma case without knowing that `component: "check-docs, check-backlog"` is ONE field — which is a
YAML-subset parser, i.e. the thing being deleted, reintroduced inside the falsifier.** The r1 fold
replaced a falsifier that could not fire with one that could not be built.

### The resolution: the converter MAY parse, because the converter is DELETED

⭐ **#117 forbids a STANDING hand-rolled parser in the decision path. A one-shot migration script is a
different object** — written once, reviewed once, run once, deleted with the migration, and never
consulted by `decide()`. Conflating the two is what made the first two falsifier attempts fail in
opposite directions.

**So the falsifier is human review at a size that makes it honest:**

| | |
|---|---|
| **the check** | the converter emits, per document, a **side-by-side field table** — source text vs converted JSON, every top-level key and every finding field |
| **the falsifier** | ⭐ **a human reads all of them.** At **31** documents that is a bounded, one-time read, not a standing cost |
| **why not automate it** | any automated comparator must itself decide what a field *is*, which is the parser question again. **A reviewer reading 31 tables does not.** |
| **verdict invariance** | kept, **demoted to a cheap smoke test** and labelled as one |

⚠ **The parity check is DROPPED and must not reappear.** It is a regression guard on an invariant the
old parser enforces, not a misread detector.

**Verdict invariance is kept as a cheap smoke test, demoted and labelled as one.** The parity check
is **dropped**: it is a regression guard on an invariant the old parser enforces, not a misread
detector, and calling it a falsifier was the defect.

### ⛔ Cutover — branches in flight, which the first draft did not mention at all

`rounds_for()` globs coordinator documents for **the current branch's** subject. So a branch already
in flight whose round documents are YAML moves from *decidable* to `CANNOT_RUN` the moment this
merges. ⚠ **Measured: 4 of the 8 subjects are mid-flight**, and *this* round adds to the corpus it
converts — **any count here is taken inside the set it measures**, the same shape that went stale
five times in the spec this one unblocks.

⛔ **r2 (Codex, High): THE FIRST VERSION OF THIS PARAGRAPH WAS A SENTENCE, NOT A MECHANISM.** It said
*"a branch carrying YAML converts its own"* and named no gate, command or check that makes it happen.
**A stated intention is not a scheduler** — the failure this repository has recorded five times.

**The mechanism, so it can be pointed at:**

1. **The converter ships as a script that survives the migration** — `scripts/migrate-round-headers.py`,
   idempotent, safe to run on a branch that is already converted. It is the *reader* that is deleted,
   not the converter.
2. **`check-review-rounds.py` gains a refusal:** a round document under `docs/reviews/coordinator/`
   carrying a `yaml` header after the cutover **fails**, naming the converter in its message. That is
   the forcing function, it runs in CI, and it is the one thing a branch in flight cannot miss.
3. **The conversion runs over whatever exists at merge time** — no count is pinned now, because every
   count in this document has moved while it was being written.

⛔ **This is the cost of no-fallback and it is accepted, not waved away** — the alternative keeps the
parser alive, which is the thing being removed.

⚠ **Neither falsifier can see a document the old parser rejected outright.** The 42 round-shaped
documents that do not parse today (39 with no header block at all) are **untouched and remain
unreadable** — no regression, no improvement. Stated so a reader does not read *the parseable set
was converted* as *the corpus is now readable*.

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
| the existing record must remain decidable after the change | one-shot conversion of every parseable document, old reader deleted | ⟳ *the original evidence here — "30/30 round-trip" — was refuted in r1 as a tautology over the parser's projection; the evidence is now §2's field-level table* |
| a conversion must not silently alter the record | a per-document **field-level side-by-side table, read by a human**, over 31 documents; verdict invariance as a smoke test | §2 — ⟳ *r2: the first two answers here were a vacuous check and an unbuildable one* |
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
  ⛔ **r2 (Codex, High) is right that "settled first, or narrower and say why" is a FORK, not a
  decision, and Phase 1 must not ship a fork. DECIDED: the schema carries TODAY'S NARROWER SET, and
  #187 widens it afterwards.** Reasons: widening the enum inside this change would **enlarge the
  migration corpus mid-migration** (the three `ship-src-root-alone` documents become convertible, so
  the set being converted changes while it is being converted); and it couples two backlog rows whose
  falsifiers are unrelated. ⚠ **The cost is stated:** those three documents stay unreadable one row
  longer, which is the status quo, not a regression. **Verified for #187's benefit:** widening
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
| convert the parseable documents + the field table | ⟳ **not "mechanical" — r1 and r2 both refuted that.** The converter must read the DOCUMENT (nine keys, one inline comment), and the falsifier is a human reading ~31 side-by-side tables |
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

⛔ **AND THE SWEEP ITSELF MISSED ONE, WHICH IS THE POINT.** After eight sites were fixed, §1's
*"What is deleted"* still read **121 lines** — the very number r1 corrected to 109, standing as a
live claim four lines below the table that corrects it. It was caught by re-grepping the corrected
strings rather than by re-reading. ⭐ **A sweep is a claim like any other and needs its own check:
grep for the OLD value, not for the new one.**
