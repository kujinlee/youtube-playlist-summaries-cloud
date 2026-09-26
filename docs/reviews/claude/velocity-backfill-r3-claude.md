# velocity-backfill round 3, Claude half — ⛔ RECONSTRUCTED, NOT THE ORIGINAL TESTIMONY

REVIEW GAP: codex — rounds 2+ ALTERNATE by design (`docs/review-method.md` step 4); the Codex half ran
as round 2 and this round reviewed its fold.

> ## ⛔ THIS IS A RECONSTRUCTION. THE ORIGINAL DOCUMENT WAS DESTROYED BY THE COORDINATOR.
>
> **What happened, 2026-09-26.** The original `docs/reviews/claude/velocity-backfill-r3-claude.md`
> (32,331 bytes) was written by the review agent and committed on `backlog-177-velocity-backfill`. The
> coordinator then committed the migration, discovered that `git log --follow` did not traverse the
> rename, and ran **`git reset --hard b8a8a828`** — a commit that sits *before* the r3 commit. On
> restoring, it used the **migration commit's file list**, which never contained r3's review. The file
> was therefore never re-added, PR #348 merged without it, and a later `git gc --prune=now` — run while
> proving an archive tag protected a different commit — collected the unreachable object.
>
> **Measured: `git log --all --oneline -- "*velocity-backfill-r3*"` returns ZERO commits.** The archive
> tag `archive/2026-09-26-mixed-branch-117-177` points at `e4d3449b`, which predates this round.
> **The original is unrecoverable.**
>
> ⛔ **AND NO GATE SAW IT.** `check-review-rounds.py` returned rc=0 with *"0 silent gaps"* on the branch
> and on master, and says nothing about `velocity-backfill` at all — because it checks that a round has
> **both halves**, and a round whose documents vanish entirely leaves **nothing to check**. A green tick
> was accurate and meaningless. Filed as a gate finding; see the companion backlog row.
>
> ### What this document is, and what it is not
>
> **It is:** the coordinator's record of r3's findings, reconstructed from the portions read verbatim
> into the session transcript while folding them, plus the **14 surviving citations** of r3 on `master`
> (7 in `…-development-velocity-RECONSTRUCTED-design.md`, 7 in `velocity-evidence-2026-09-24.md`), each
> naming a severity and what it found.
>
> ⛔ **It is NOT testimony.** It was not written by the reviewer. Severities, components and the verdict
> are reproduced as read; the wording of individual `evidence:` fields is the coordinator's summary and
> **must not be quoted as the reviewer's words.** Where the original's exact phrasing is known it is
> marked as a quotation.
>
> ⚠ **Every finding below was FOLDED before the loss** — the repair landed in `ce224b44` and merged as
> `054b676e` (PR #348). Nothing in this round was lost as *work*; what was lost is the evidence of who
> found it and how.

---

## Verdict, as recorded at the time

**NOT CONVERGED.** **20 findings — 1 Blocking, 7 High, 8 Medium, 4 Low. 16 of 20 `fix_induced: true`.**

⛔ **The architecture-review arming condition was MET**, and the round answered *thrashing or prose
floor?* as required: **THRASHING**, with per-finding evidence.

| round | component | whose fix caused it |
|---|---|---|
| r2 | `scope-cut-inbound` | **r1's fold** — missed the backlog row and the status table |
| r3 | `retirement-completeness` | **r2's fold** — repaired one clause of that row and missed four more in it |

Its named structural cause, quoted as read: *"no document lists the inbound sites, so each round's sweep
is performed from scratch by hand and each one is incomplete in a different place."* Its named fix: **an
enumerated citing-sites list that the banner owns** — which is what shipped, as the tombstone's table.

## The findings, by severity

**Blocking — `retirement-completeness`** *(fix_induced: true)*. The spec's own falsifier — *"the retired
document is cited for a RULE rather than a measurement → the retirement is decorative"* — fired at HEAD,
mostly inside the single backlog row the previous fold had edited: it still routed a reader to the
retired document as the authority for the whole subject, cited §3 for the four signals **twice**, §8 for
the rejections, and §9 for the settled answers. Quoted: *"This repair mapped ONE CLAUSE of one row and
treated that as the row."*

**High ×7**

| component | fix_induced | what it found |
|---|---|---|
| `ci-measurement-corpus` | true | the 6-run *"3.3-point band"* is a property of the selection; over 26 runs the share spans **73.5%–82.8%**, a 9.3-point band. *"Six of ≥32."* |
| `ci-measurement-corpus` | true | the figures retracted as *"NOT REPRODUCIBLE"* reproduce — `78 ← 35947529595` 77.7%, `83 ← 36094717914` 82.6%. The defect was **provenance**, not invention |
| `inbound-references` | true | the **sixth** stale site, `process-checklists.md` — *"That document's banner marks §3 not built"*: the antecedent moved in r1's fold and the pronoun did not, and the sentence **contains no filename**, so a 3,267-file sweep could not see it |
| `cracked-comparison-propagation` | true | the *"~2× faster"* retraction reached **one of five** sites; still live in the retired doc's §5 and §9 Q3 (where it is the whole stated case for shipped strand ⑵), plus the backlog row and the roadmap |
| `cracked-comparison-propagation` | true | the plan still carried *"488s → 673–680s"*, refuted by run `36049305547` giving **419s** |
| `self-found-corrections` | true | the coordinator's line-count correction was itself wrong: 326 went stale at **285** in `e0cb2ca8`, downward by 41 lines, wrong through three commits; **335** was merely the count when the correction was written |
| `dashboard-entry` | false | `check-dashboard-entry.py` rc=1 — 8 tracked files changed, no entry, and no PR to carry a `NO-ENTRY:` |

**Medium ×8** — `replaced-text-orphans` (two orphaned continuation lines from two different folds, *"a
class, not a typo"*); `retirement-banner` ×2 (the banner contradicted itself about decisions in three
consecutive blocks; and demoting the status table removed §5's **only** status marker, leaving *"Proposed:"*
over a mixed set); `derived-values` ×2 (*"Ten adversarial rounds"* is the same defect as the removed line
count, with two defensible populations; and the goals-page claim was present-tense and half-falsified by
this document's own landing); `inbound-references` (a sibling spec asserted *"§4 stays — it is measurement,
not design"*, refuted two steps later); `deletion-condition` (evaluable in principle, mis-evaluated by
every attempt, mechanised by nothing); `goals-page-identity` (`177` appears **zero** times on the page
while ten other backlog ids do — `ROOTS` in `gen-backlog-page.py` has one key).

**Low ×4** — `self-found-corrections` (`1.76×` **was** derivable: 587/333 = 1.7628, the sweep-step spread
of the same pair — *"a transposed statistic, not an invented one"*); `derived-values` ×2
(`check-plan-code.py:501` is a continuation line and the figure lives ~3,200 lines away; and a
`process-checklists.md:767` line citation in prose); `ci-measurement-corpus` (*"the corrected
sweep-to-sweep ratio is NOT KNOWN"* has two readings and is false under one).

## What it verified clean

**All six CI runs in the spec's table reproduced exactly — 6 of 6**, run id, job id, branch, verify
total, sweep seconds and share matching to the digit. The `1.69×` and `737s` arithmetic held. And it
confirmed it had **fixed nothing, committed nothing, and regenerated the goals page to a scratch path**
rather than the reader's live directory.
