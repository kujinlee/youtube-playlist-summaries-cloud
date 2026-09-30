---
name: coverage-verdict-union-91-merged
description: "FIRES-WHEN: citing backlog #91 or PR #269 — ⭐ Backlog #91 MERGED 2026-09-09 (PR #269, squash 307423f1) after FOUR review rounds. The open question is not a defect: 0 of 92 plans exercise the mode all four rounds reviewed — escalated to the user, then DISSOLVED BY EVENTS when plan mode was retired (#270/#271)"
metadata: 
  node_type: memory
  type: project
  originSessionId: facc1a89-d756-4f48-bd37-576633ad0751
  modified: 2026-09-09T00:05:28.698Z
---

**Backlog #91 is MERGED — PR #269, squash `307423f1`, on `master` 2026-09-09.**
`scripts/coverage_verdict.py` holds `Measured | NotMeasured`; `NotMeasured` has no `survivors`
field and its list is `entries`, so copying a line from the measured path raises `AttributeError`
rather than printing a plausible wrong number.

**Final numbers (CI, not local):** self-test 207 → **231**; `coverage_verdict` 22 → **27**;
`EXPECTED_MUTATIONS` 362 → **374**; sweep = 32 files, **374 mutations, 0 survivors**.

## Four rounds, and the trajectory is the useful part

| round | Highs | introduced by the previous round's fix? | class |
|---|---|---|---|
| 1 | 3 | — | fail-open **defaults** |
| 2 | 3 | 3 of 3 | **sentinels with an OR** |
| 3 | 4 | 3 of 4 | **one fix, one of two paths**; two narrators, no shared owner |
| 4 | **1** | **0 of 1** | a **comment asserting a class was closed** (pre-existing on `master`) |

Round 4 introduced no regression and its own fix survived being attacked as a subject —
19 inputs through both `extract()` versions, zero behaviour differences. First time on the branch.

## ✅ WAS ESCALATED — and ANSWERED BY EVENTS, not by a reply (closed 2026-09-09)

`dev-process.md` fires Phase 6 at four non-converging rounds. **The literal trigger fired** (round 4
found a self-contradicting artifact) **and the CAUSE the r3 rule named was measured FALSE** — the
three narrators (`evidence()` subject, `verify_evidence` mode, `main()` mode) all derive from the
flag and agree. `review-method.md` says read the trigger off the cause, so Phase 6 was **not**
convened on `evidence()`.

**What was escalated instead, and it is the sharper question:** since backlog #70 retargeted
mutations onto `scripts/mutations/*.json`, **0 of 92 plans on disk reach plan mode's file path.**
Four adversarial rounds went into a renderer whose only exerciser is its own `--self-test`. So the
honest framing of every finding is *"the durable artifact WOULD lie if this mode were used"*, not
that it is lying today. **Should the mode exist, or get a real exerciser?** ⭐ **ANSWERED: the mode does not exist.** Plan mode was RETIRED (#270) and its code DELETED (#271) on 2026-09-09 — one day after this was escalated. `check-plan-code.py <plan>` now exits 2. ⚠ **Nobody connected the two at the time:** the dashboard ask (`2026-09-08/15`) stayed open in *What needs you*, and backlog row #91 kept carrying the question, until a status reconciliation found it 2026-09-09 (PR #278). **An escalation has no closer** — a question raised to a human is closed by a reply, so work that moots it leaves the question standing. See [[a-measurement-is-only-as-good-as-its-corpus]] and [[an-escalation-has-no-closer]].

## Residue carried, not dropped

* The two **declaration** refusal causes still share one sentence — separating them needs
  `mut_readable` to carry its reason, which is a fifth return value growing a second meaning: the
  shape this branch spent three rounds deleting. The class a reader confuses (suite-was-red vs
  declaration-lost) IS separated.
* **L2 — "one line, one mutation" is a property of the INSTRUMENT, not the code.** The manifest's
  anchor-dedupe guard forced a code split; the split was an improvement, but the precedent
  generalises and belongs in `review-method.md` before it shapes a third refactor.
* The **orphaned-anchor class still has no cheap detector** — only a full sweep sees it, and it bit
  three more times on this branch. See [[a-mutation-loses-its-binding]].

⚠ Merge authority was granted for THIS series only (*"goal fix #91 do not stop for merge decision"*)
and does not carry to new work. The branch merged on CI's sweep, **not** on a claim of convergence —
no round produced zero findings.
