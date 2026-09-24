# Round 1 — `velocity-177` — coordinator

```yaml
round: 1
fixes_nontrivial: true
subject: velocity-177
halves:
  claude: ran
  codex: ran
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: draft-pr-justification, disposition: fixed}
  - {id: H2, severity: High, aim: deliverable, fix_induced: false, component: rule-4-gate-scope, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: false, component: rule-3-worked-example, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: true, component: roadmap-prose, disposition: fixed}
  - {id: M3, severity: Medium, aim: deliverable, fix_induced: true, component: velocity-duplicate-copies, disposition: fixed}
  - {id: M4, severity: Medium, aim: deliverable, fix_induced: false, component: number-populations, disposition: fixed}
  - {id: M5, severity: Medium, aim: deliverable, fix_induced: false, component: pr-body-attribution, disposition: fixed}
  - {id: M6, severity: Medium, aim: deliverable, fix_induced: true, component: backlog-row-177, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: true, component: rule-3-restatement, disposition: fixed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: true, component: status-banner, disposition: fixed}
  - {id: L3, severity: Low, aim: deliverable, fix_induced: false, component: sweep-policy-tension, disposition: fixed}
  - {id: L4, severity: Low, aim: deliverable, fix_induced: true, component: rule-1-scope, disposition: fixed}
  - {id: L5, severity: Low, aim: deliverable, fix_induced: true, component: seam-signal-pointer, disposition: fixed}
```

**Subject:** `git diff origin/master...HEAD` on `velocity-177` (PR #345, backlog #177) — docs only.
**Scope:** `one-round`, from `scripts/check-review-decision.py` (prose-only diff).
**Halves:** `claude/velocity-177-r1-claude.md` (2H/6M/5L) · `codex/velocity-177-r1-codex.md` (0B/0H/1M/1L,
`gate_ran=true`, model `gpt-5.5`).

## The finding that matters: the change adopting rules against unverified claims contained three

Both Highs were mine, and both are the exact class §6 was written about.

**H1.** The only evidence offered for adopting the draft-PR practice was *"it caught backlog #176 r2's
Blocking on its first use."* **False, and the document it names says so** —
`docs/reviews/claude/review-identity-176-r2-claude.md:156-158` records `verify pending` at the time and
states the finding *"rests on the anchor measurement above, not on a CI verdict."* The claim was carried
from a session note and never checked against its own source. Removing it leaves the speed measurement,
which is now stated as the whole case. Corrected **in place** at both sites.

**H2.** Rule 4 shipped as *derive gate lists from `ci.yml`*. `scripts/check-merge-ready.py:52-55` already
carries that defect and its correction: *"EVERY WORKFLOW, NOT `ci.yml` ALONE … the FILE SCOPE was the
hand-written part."* Measured: `check-schema-gates` appears in `ci.yml` **only in comments** (`:267`,
`:286`), so an author following the rule literally omits all fifteen schema gates.

## ⭐ What the round changed about the rules themselves — rule 1b

Three defects in this change all answer **YES** to rule 1's question *did you measure it*:

| Written | Actually measured | The gap |
|---|---|---|
| "28 gates named" | distinct `scripts/check-*.py` in one workflow | regex excluded `.sh`; "gates" names steps (54) or scripts (34), neither of which is 28 |
| "caught the Blocking" | nothing — it named a cause the source disclaims | the claim had no measurement at all |
| "derive from `ci.yml`" | one of two required workflows | the scope was the hand-written part |

So rule 1 gained a clause it did not have: **say what you counted, not just that you counted.** A number
carries its population or it is not a measurement. This is the one finding that improved the deliverable
rather than repairing it.

## The instructive Medium (M3)

§6 and §7 of `development-velocity.md` still carried full copies of the rules under an ✅ ADOPTED banner
— and the copies had kept the **refuted** text: still *derive from `ci.yml`*, still the disputed survivor
count. **The copy nobody is looking at is the copy that preserves the version review threw out.** Replaced
with pointers.

## Half overlap, and what that says

Thirteen findings across both halves; the halves overlapped on **exactly one** (the stale roadmap
sentence — Codex `Low`, Claude `M2`). That is consistent with this repo's recorded measurement that the
two halves are not redundant. Codex's single Medium and the Claude half's M4 are the same subject
approached from opposite ends: Codex could not verify "28" from the repo, Claude found it disagreed with
the "thirty-three" in the rule the same PR shipped.

## ⚠ Caveats, stated rather than hidden

- **The Claude half disclosed compromised independence on M2.** A repo-wide grep incidentally surfaced
  the Codex file's first line before it read that section. It re-verified the finding by reading the file
  itself and said so in the review. Recorded because a reviewer that flags its own contamination is doing
  the job; silently absorbing it is the failure.
- **`--mutate .` and the Postgres gates were NOT RUN locally** — recorded as NOT CHECKED, not as passed.
  The diff is docs-only and CI is the runner; the draft PR was opened at slice start precisely so every
  push sweeps there.
- **No machine-readable header was added to either half.** The Codex half's final message IS its review,
  and editing filed testimony is the shape this repo records as *the review gate that wrote over its own
  evidence*. This coordinator document carries the header instead, which is where `rounds_for` reads it
  (`scripts/check-review-decision.py` globs `docs/reviews/coordinator/<subject>-r*-coordinator.md`).
