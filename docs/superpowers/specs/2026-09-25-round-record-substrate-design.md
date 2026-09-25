# The round record stops being hand-parsed — backlog #117

> **Anchor:** `review-decides-itself` — **ADR:** none
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded
> evidence rather than recall.

**Status:** ⏳ **DESIGN — Phase 1, awaiting the human gate. Nothing implemented.**
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

⭐ **SIX RECORDED DEFECTS, ONE SHAPE — and the shape is the point.** Every one is
*absence reads as a pass*, and every one was found by a reviewer rather than by a test
(`scripts/check-review-decision.py`, comments at `:212`, `:219`, `:224`, `:228`, `:254`, `:260`):

| # | what happened | what it read as |
|---|---|---|
| r1 B1 | parser read only `{...}` flow mappings; block-style items parsed to **zero** findings | a clean round |
| r2 B | `severity High` with no colon dropped the field | neither Blocking nor deliverable |
| r2 M | finding markers counted outside the `findings:` span | a **false** CANNOT RUN on a valid header |
| r3 B | `_findings_span` returned `""` for an **absent** key | *"a missing key is a silence"* — clean round |
| r6 M | braces in ordinary prose counted as findings | a false CANNOT RUN |
| r6 H | `fixes_nontrivial` was unreadable, so a stated CONTINUE rule could not be enforced | convergence |

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
| `parse_header` itself | ⛔ **No — it IS the subject.** 121 lines, 6 recorded fail-opens |
| `check-anchors.parse_header`, `gen-goals-page.parse_header` | **No, and they are NOT this function** — they parse a spec's `> **Anchor:**` line. ⚠ Measured: a **name collision**, three functions, three jobs. Out of scope, noted so a reader does not think the blast radius is three files |
| `check-review-rounds.py` | **No** — it answers *did both halves run*, from **file existence** under `docs/reviews/<writer>/`, never from this header. Confirmed: it contains no reference to `halves` |
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
— the four functions that exist only to recover structure from text. **121 lines.**

**What is kept, unchanged:** `_validate`, `REQUIRED`, `ROUND_REQUIRED` — these are **rules about
values**, not parsing, and they are not the defect. A finding with `severity: "Wrong"` must still
raise; JSON will happily carry it.

⛔ **THIS IS THE LOAD-BEARING DISTINCTION AND IT MUST NOT BE BLURRED:** `json.loads` removes the
*structural* failure class. It does **nothing** about a well-formed header stating a false judgement.
⭐ **Anyone reading this as "the header is now validated" will delete `_validate` and reopen r2's
Blocking.**

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

**14 lines today, 13 as JSON** — one line shorter, at the same density. One finding per line, which
is how the record already reads.

## §2 — Migration

**All 30 currently-parseable round documents are converted in the same PR, and the old parser is
deleted in that PR.**

⛔ **A FALLBACK YAML READER IS REFUSED, AND THIS IS THE WHOLE POINT.** Keeping one means the parser
is not deleted, the six fail-open shapes remain reachable, and #117's REDESIGN is **not discharged** —
only postponed behind a flag. A migration that leaves the subject alive is not a migration.

**Measured feasibility, by running it** *(import `check-review-decision`, `parse_header` each
document, `json.dumps`, `json.loads`, compare)*:

```
round-tripped cleanly through json: 30   failed: 0
headers with a YAML comment: 0
headers with a block scalar:  0
```

So nothing in the corpus uses a YAML feature JSON lacks, and the conversion is mechanical.

### ⛔ The residual risk, stated before it is discovered

**The converter reads through the BROKEN parser.** If that parser misread a document, the conversion
preserves the misreading faithfully — *absence reads as a pass*, one last time, on the way out.
⚠ **This is the one real hazard in this change and it is not hypothetical**: mis-parsing is the
documented behaviour of the thing doing the reading.

**Two falsifiers, pre-committed:**

1. **Verdict invariance.** `decide()` must return an **identical** `(decision, reason)` for **every**
   subject before and after conversion. A differing verdict is a misread caught.
2. **Per-document finding-count parity against the SOURCE TEXT, not against the parser.** For each
   document, count `findings:` list markers in the original YAML by an independent count and compare
   to the JSON array length. ⭐ **This is the one that can catch what (1) cannot** — a misread that
   happens not to change a verdict. Checking only (1) would be *fixing a premise rather than covering
   the branch*.

⚠ **Neither falsifier can see a document the old parser rejected outright.** The 42 round-shaped
documents that do not parse today (39 with no header block at all) are **untouched and remain
unreadable** — no regression, no improvement. Stated so a reader does not read *30 converted* as
*the corpus is now readable*.

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
| a malformed record must not read as a clean round | `json.loads` raises; nothing recovers structure from text | 6 recorded defects, all *absence reads as a pass* |
| a well-formed record stating an out-of-range value must be refused | `_validate` + `REQUIRED` + `ROUND_REQUIRED` — **unchanged** | r2 Blocking: *"validate the VALUES, not the shape that carried them"* |
| the existing record must remain decidable after the change | one-shot conversion of all 30 parseable documents, old reader deleted | 30/30 round-trip, 0 failures |
| a conversion must not silently alter the record | verdict invariance **and** per-document count parity against source text | §2 |
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
- **It does not widen `disposition`** — backlog #187. Four out-of-set values exist in the record
  (`retreat`, `refuted`, `redesigned`, `moot`) and will still be refused after this change.
- **It does not rescue the 42 unreadable documents.**
- **It does not change any decision rule** — `scope_for`, `thrashing_component`, `converged`,
  `sequence_error`, `decide` and `exit_code_for` are untouched. ⭐ **A verdict that changes is a
  migration defect, which is why §2's first falsifier is verdict invariance.**

## How we would know it failed

- A round document is malformed and `decide()` returns a verdict instead of `CANNOT_RUN` →
  **the substrate did not remove the class.**
- Any subject's verdict differs before and after conversion → **a misread was preserved** (§2.1).
- A converted document's finding count differs from its source text → **same, caught earlier** (§2.2).
- A fallback YAML reader appears in a later commit → **#117 was postponed, not discharged.**
- `_validate` is deleted as redundant → r2's Blocking reopens; a well-formed header with
  `severity: "Wrong"` reaches a decision.

## Sizing

| Piece | Cost |
|---|---|
| swap the reader | **small, and NET NEGATIVE** — 121 lines deleted, ~5 added |
| convert 30 documents + both falsifiers | small; the conversion is mechanical, the falsifiers are the real work |
| `round-header-template.md` | small |
| `--self-test` | ⭐ **the real work** — 61 declared cases today, many of which exist **only to exercise malformed YAML**. Those cases lose their subject and must be **retired with it and recorded as such**, not orphaned. `check-selftest-counts.py` verifies the declared count by running it |
| mutation manifest | entries anchored in deleted code must be retired at both sites with the count and reason |

⚠ **The `--self-test` count will FALL.** That is the one sanctioned kind of ratchet fall — cases
retired *with their subject* — and it is recorded at both sites with the count and the reason, as
the plan-mode retirement did (`3,607 → 1,983`).

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
reliably than a YAML subset. Measured, the residual cost is **quotes**, at one line shorter.
