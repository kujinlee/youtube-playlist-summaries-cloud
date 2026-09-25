# Round 2 — `decision-card-soundness` — coordinator

```yaml
round: 2
fixes_nontrivial: true
subject: decision-card-soundness
halves:
  codex: ran
  claude: ran
findings:
  - {id: B1, severity: Blocking, aim: deliverable, fix_induced: true, component: hidden-thrashing-condition, disposition: fixed}
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: prior-art, disposition: fixed}
  - {id: H2, severity: High, aim: deliverable, fix_induced: true, component: escape-grammar, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: calibration-claims, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: true, component: prior-art, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: true, component: calibration-claims, disposition: fixed}
  - {id: B2, severity: Blocking, aim: deliverable, fix_induced: true, component: escape-grammar, disposition: fixed}
  - {id: H3, severity: High, aim: deliverable, fix_induced: true, component: calibration-claims, disposition: fixed}
  - {id: H4, severity: High, aim: deliverable, fix_induced: true, component: prior-art, disposition: fixed}
  - {id: H5, severity: High, aim: deliverable, fix_induced: true, component: prior-art, disposition: fixed}
  - {id: H6, severity: High, aim: deliverable, fix_induced: false, component: fix-induced-input, disposition: fixed}
  - {id: H7, severity: High, aim: instrument, fix_induced: true, component: round-record-labelling, disposition: fixed}
  - {id: M3, severity: Medium, aim: deliverable, fix_induced: true, component: escape-grammar, disposition: fixed}
  - {id: M4, severity: Medium, aim: deliverable, fix_induced: true, component: hidden-thrashing-condition, disposition: fixed}
  - {id: M5, severity: Medium, aim: deliverable, fix_induced: true, component: calibration-claims, disposition: fixed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: false, component: calibration-claims, disposition: declined}
```

⚠ **`B2`–`L2` are the Claude half, folded after the Codex half per the alternating protocol.** `L2`
is `declined` because it is a **clean** result — every commit-stamped figure reproduced — recorded
because the brief asked for re-derivation and a clean re-derivation is a fact about the round.

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

## ⛔⛔ THAT LAST CLAUSE IS FALSE — the Claude half refuted it by replay (H7)

**The alternative to the merge was never silence.** Replayed with **Codex's six labels and its own
`fix_induced` values verbatim**:

```
CODEX LABELS VERBATIM for r2: ('ROUND_OWED', 'r2 produced a Blocking')
   r1 induced: {'calibration-claims'}
   r2 induced: {'backlog-136 scope', 'components-distinct scope', 'card-mention measurement',
                'hidden-thrashing condition', 'exit-code settlement'}
   would the PROPOSED refusal fire? True
```

`thrashing_component` returns `None` — **and both rounds carry fix-induced findings whose component
sets are disjoint, which is exactly the condition §1 proposes.** The shipped card says `ROUND_OWED`;
this spec's card says `CANNOT_RUN`. ⭐ **That is the branch demonstrating its own mechanism on
itself, and it is a better datum than the merged firing.** It is now recorded in the spec's §3 as the
only case in the corpus where the proposed refusal and the existing trigger disagree on a live branch.

**Three things follow, and the record carries all three:**

- **The merge's DIRECTION stays.** #136 carries the standing instruction *"treat any proposal that
  makes a gate fire LESS with suspicion"*; choosing the heavier verdict and disclosing the conflict of
  interest is the right posture, and the Claude half says so explicitly.
- ⛔ **The stated REASON was wrong, in the direction that made the merge look forced.** *"The
  alternative is silence"* is what removes the choice. There was a choice.
- ⛔ **And the episode is this spec's motivating defect RUN IN REVERSE.** *Why this exists* is built on
  *three findings relabelled into one name made the trigger fire*. Here: **six findings relabelled
  into four names made the trigger fire**, on the branch about that lever, by the same free-text
  mechanism, decided by one person with a stake in the answer. That is the measured cost of *"it does
  not make `component` mechanical"*, produced by the branch itself.

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

## ⛔⛔ IT FIRED IN THE SAME ROUND THAT WROTE IT, ON THE SENTENCE THAT WROTE IT

The Claude half's **H3** is a fix-induced `calibration-claims` finding, and its subject is the
redesign's own completeness claim. The fold had written *"every figure in this table carries the
commit it was taken at"*; **that sentence was false as written** — 5 stamps in the document, 3 of
them in the table — and the corpus had **already moved to 158 findings** because recording this very
round moved it. The number `145` also survived, unstamped, in *Rejected, with reasons*: the section
r2's own High had just reopened.

⛔ **The pre-commitment said "in r3". It fired in r2. That is EARLIER, not different, and the
escape does not apply.** ⭐ **I am not arguing it away** — a retreat authored for oneself after the
fact is not a gate, and this repository has already paid for that exact move.

**THE ARCHITECTURE REVIEW IS CONVENED.** The redesign has been applied again (§3 no longer asserts
anything about the present: every corpus figure is now a dated snapshot, and `--calibrate` is how a
reader gets today's). **That is the third remedy for this defect, which is itself the argument for
the review rather than against it.**

## What r2 cost, stated plainly

| | Codex half | Claude half |
|---|---|---|
| Blocking | 1 | 1 |
| High | 2 | 5 |
| Medium | 2 | 3 |
| Low | 1 | 1 (clean re-derivation) |

⭐ **The Claude half's Blocking is r1's finding 4 for the THIRD time, one layer down each round:**
r1 — the escape has no reader (prose); r2 Codex — the escape is scoped to the wrong thing (a round
number); r2 Claude — **the reader the fix names structurally cannot read the key it proposes**, and
three of its four malformed shapes parse silently.

⛔ **AND A SENTENCE HERE CLAIMED THAT ARMS THE TRIGGER TOO. IT DOES NOT, AND THE DRAFT WAS WRONG.**
Replayed: `r1` fix-induced components are `['calibration-claims']` — **only**. r1's two
`escape-grammar` findings (H2, H6) are both `fix_induced: false`, so `escape-grammar` recurs across
three rounds **without arming anything**. ⚠ **Recurrence is not thrashing under the recorded flags**,
and writing otherwise inside the round that folded H3 would have been that same defect a fourth
time. `calibration-claims` is the **only** armed component; the answer above stands on it alone.

⭐ **That `escape-grammar` can recur three times, each time one layer deeper, and arm nothing is
itself a datum about `fix_induced`** — and it belongs with H6's finding that the field is undefined
at round 1, not with a claim this record can make on its own.
