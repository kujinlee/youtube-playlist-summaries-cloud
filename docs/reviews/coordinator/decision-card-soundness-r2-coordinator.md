# Round 2 — `decision-card-soundness` — coordinator

```yaml
round: 2
fixes_nontrivial: true
subject: decision-card-soundness
halves:
  codex: ran
  claude: "GAP: not yet dispatched — rounds 2+ ALTERNATE, so it reviews this round's fixes"
findings:
  - {id: B1, severity: Blocking, aim: deliverable, fix_induced: true, component: hidden-thrashing-condition, disposition: fixed}
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: prior-art, disposition: fixed}
  - {id: H2, severity: High, aim: deliverable, fix_induced: true, component: escape-grammar, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: calibration-claims, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: true, component: prior-art, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: true, component: calibration-claims, disposition: fixed}
```

## ⛔ The Blocking WITHDREW A FIX MADE IN ROUND 1

r1 proposed a one-clause addition to the condition — *do not refuse if the trigger fired on the
previous pair* — and the coordinator folded it into §1. Codex refuted it with a constructed
three-round sequence (`[[A], [A,B], [C]]`): the clause suppresses the refusal for the unjudged
`B`-vs-`C` pair, and by that point the r1/r2 arming on `A` has **already expired**, because
`thrashing_component` compares the last two rounds only. The loop reaches r3 with no verdict at all.

⭐ **r1's PREDICTION was right and its REASONING was wrong.** Replayed over the corpus, the clause
does remove exactly the `peer-sites` r3/r4 refusal r1 said it would (5 → 4). It did the right thing
on the one case r1 examined and the wrong thing on a case nobody had constructed. **A finding's
proposed fix is a hypothesis.**

## Where the coordinator DIVERGED from Codex's own labels, and why

| | Codex | recorded here | reason |
|---|---|---|---|
| `aim` on all six | `instrument` | **`deliverable`** | the deliverable of a Phase 1 branch is the spec; Codex was labelling the mechanism the spec *describes*. r1 recorded `deliverable` for the same subject |
| finding 4 (`147` findings) | `fix_induced: no` | **`true`** | the wrong number **is** r1's fix. The spec shipped 145, r1 corrected it to 147, and 147 was stale one commit later |
| findings 2 and 5 | `backlog-136 scope`, `exit-code settlement` | both **`prior-art`** | one concept under two names — *the spec's stated relationship to a filed backlog item is wrong* — which is the exact merge this branch exists to make possible |
| finding 6 | `card-mention measurement` | **`calibration-claims`** | same concept as finding 4: a measured number in the spec is wrong |

⚠ **That last merge is the coordinator judging its own subject.** Recorded explicitly so a later
reader can disagree with it; splitting them back out would silence the trigger below, which is
precisely the defect this branch is about.

## What the halves found

| Half | Found |
|---|---|
| **Codex** | 1 Blocking, 2 High, 2 Medium, 1 Low — the Blocking by **construction**, not reproduction, and one High by reading a backlog row the spec cited but had not finished reading |
| **Claude** | ⏳ not yet run |

Round 1's pattern (Codex numeric, Claude structural) did **not** repeat: the Codex half found the
structural Blocking this time. One round is not a trend, and the brief was different — it named
*refute, do not confirm* and listed the specific claims to attack.

---

## ⛔ THE CARD FIRED ON THIS BRANCH, FROM THE MECHANISM THIS BRANCH IS ABOUT

```
ARCHITECTURE_REVIEW — thrashing: 'calibration-claims' carried fix-induced findings in r1 and r2
  branch=decision-card-soundness  scope=one-round  rounds=2  tree_reviewed=True
```

`docs/dev-process.md` requires this round document to answer **thrashing, or prose floor?** with
per-finding evidence. **Answer: thrashing.**

| round | finding | the claim | what it became |
|---|---|---|---|
| r1 | M1 | corpus was `7 / 28 / 145` | corrected to `8 / 29 / 147` — **stale in its own commit** |
| r2 | M1 | corpus is `8 / 29 / 147` | **`152`** — stale at `ebd982d2`, the commit that recorded r1 |
| r2 | L1 | `7 of the 14 mentions are on the two subjects about the card` | **`8`**, so independent use is 6, not 7 |

⭐ **Each correction produced the next error, and the CHARACTER DID NOT SHIFT** — all three are the
identical defect: *a measured number written into prose that the act of recording the review then
falsifies.* That is the distinction `review-method.md` draws. A prose floor looks like **improving
findings of changing character**; this is **one defect, three times**.

### The redesign test — *can a redesign remove it?* — **YES, and the redesign is applied in r2**

Stop stating the figure in prose. `--calibrate` derives it from the live corpus on demand, and every
figure that remains in §3 now carries the commit it was taken at (`9d1987ca`). The defect is not
*"the coordinator keeps miscounting"* — the counts were right when taken. It is *"a document inside
the corpus it measures cannot hold a stable count"*, which no amount of care fixes and a derivation
does.

### ⚠ PRE-COMMITTED FALSIFIER for that claim

**If `calibration-claims` carries another fix-induced finding in r3, the redesign did not work and
the architecture review is convened unconditionally** — no further argument, no re-litigating this
paragraph. Writing the escape before the next round is what stops it being written afterwards.

### ⛔ r2 IS NOT COMPLETE

The Claude half has not run. This verdict is computed over a round whose `halves.claude` is a
declared `GAP:`. Rounds 2+ alternate deliberately, so the Claude half reviews the fixes recorded
above — including the withdrawal of r1's clause, which is the change most likely to be wrong.
