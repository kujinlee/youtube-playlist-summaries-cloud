# Round 2 — `ship-src-root-alone` — coordinator

```yaml
round: 2
fixes_nontrivial: true
subject: ship-src-root-alone
halves:
  codex: ran
  claude: ran
findings:
  - {id: H1, severity: High, aim: instrument, fix_induced: true, component: src-caller, disposition: redesigned}
  - {id: M1, severity: Medium, aim: instrument, fix_induced: true, component: src-caller, disposition: fixed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: true, component: report-format, disposition: fixed}
  - {id: M3, severity: Medium, aim: deliverable, fix_induced: false, component: review-evidence, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: true, component: src-root-reach, disposition: fixed}
  - {id: L2, severity: Low, aim: instrument, fix_induced: true, component: src-caller, disposition: fixed}
  - {id: L3, severity: Low, aim: instrument, fix_induced: true, component: src-caller, disposition: fixed}
  - {id: L4, severity: Low, aim: deliverable, fix_induced: false, component: src-root-reach, disposition: fixed}
  - {id: S3, severity: Low, aim: instrument, fix_induced: true, component: src-caller, disposition: fixed}
architecture_review: docs/reviews/architecture-review-2026-09-15-src-caller.md
```

## ⛔ THE THRASHING RULE ARMED, AND THIS ROUND STOPS PATCHING

Round 2's Claude half found that **round 1's fix caused round 2's Medium, and round 2's fix caused a
High — same component (`src-caller`), two consecutive rounds, code not prose.** That is
`dev-process.md`'s arming condition verbatim, and the branch this one forked from was parked by the
same rule eight rounds in.

**It was honoured rather than narrowed.** No fifth patch was applied to the interception design. The
component went to a Phase 6 architecture review —
[`docs/reviews/architecture-review-2026-09-15-src-caller.md`](../architecture-review-2026-09-15-src-caller.md)
— whose verdict is that four attempts failed for **one structural reason**: they tried to prove a
negative by intercepting an **open** set of runtime surfaces. The redesign asks the question a second
way, **statically**, over a bounded region of code, where the set is closed.

⚠ **Two process rules fired in opposite directions here, and the resolution is a judgement, not a
lookup.** `review-method.md`'s Q4 would have said *stop reviewing and go build* — every finding in
two rounds except one clause was aimed at the instrument, and the deliverable has taken nothing since
round 4 of PR #295. The thrashing rule said *stop patching and redesign*. The argument for letting
thrashing win is recorded in the architecture review, because the next person to hit the collision
deserves it: **"go build" on top of a guard that reports a pass it has not earned is how the four-day
outage happened** — a green suite over a dead subsystem.

## The halves, and what each was worth

**Codex (ran first, alternating):** 3 findings, **all fix-induced**, all confirmed and fixed — the
`get`-only counter (`SRC_ROOT_ENV in os.environ` passed 133/133), the `[FAIL] ` case covering one of
two report arms, and round 1's reach fix writing a **new** count three lines below the sentence
saying counts do not survive here. It re-walked the tree and got a different total than the comment
claimed, the difference being round 1's own review document. Did not converge.

**Claude (ran second, saw Codex's half and the working tree):** 1 High, 1 Medium, 3 Low. It
**re-ran both of Codex's mutations first and confirmed they now die**, then found that the repair for
one of them had retired coverage round 1 bought. It stated the arming condition, recommended against
its own sketched fix, and said so explicitly.

⭐ **Neither half was redundant, again.** Codex found the counter hole and the stale count; Claude
found that the *fix* for the counter hole was a regression, which is a thing only the second-running
half can see.

## H1 — HIGH, fix-induced — CONFIRMED, and answered by redesign rather than patch

Round 2's fix stubbed `src_root` so `_Forbidden` could forbid the environment outright. That made
calling the stub **free**, so the most natural spelling of a second observation was invisible:

| | `root = src_root().root` |
|---|---|
| working tree (attempt 4) | **142/142 SURVIVES** |
| commit `78100320` (attempt 2) | **KILLED**, by the two cases attempt 4 deleted |

Coordinator re-measured both. The shipped comment asserted the deleted cases were redundant; that
sentence was false, and the falsification is two lines.

**Not fixed by restoring the counter.** See the architecture review. The redesign adds a STATIC case
over the `/src/` branch's own source — `src_root()` appears exactly once, and no environment API is
named in the region — composed with the existing DYNAMIC `_Forbidden`. **Measured after: the second
`src_root()` call dies 148/150, and so does `os.environb`, which defeated every interception
attempt.**

## M3 — MEDIUM — I was destroying other people's review evidence, twice

`git status` showed ` D docs/reviews/verdicts/r2-codex.verdict.json`. Not a rename — the committed
file is schema 1 with no `head`; mine is schema 2 naming `78100320`. **Round 1 already committed the
same destruction**: `78100320` deletes `r1-codex.verdict.json`, whose `head` is `bb265c08` —
verified **not an ancestor of this branch**, i.e. an unrelated merged PR.

`docs/plugins.md` says those files exist so `check-review-rounds.py` can read **in CI** that a gate
ran. Deleting one erases the proof a merged round's gate ran, **and nothing noticed** —
`check-review-rounds.py` and `check-docs.py` were green over the deletion, measured.

**Both restored.** The cause is `codex-review.py` deriving the verdict path from the caller's `--out`
stem with no allocator — this project's *"a guard's evidence path is a namespace with no allocator"*,
**third occurrence**. Filed as backlog **#128** rather than fixed here: it needs a policy call about
who owns that namespace, which is not this branch's subject. The caller-side workaround
(branch-specific stems) is in use and is explicitly **not** the fix, because it only works for callers
who remember.

## M1, M2, L1 — Codex's three, all confirmed and fixed

- **M1** the counter overrode `get` only. Coordinator then found `setdefault`, `pop`, `repr()`, `==`
  and `len()` also escaped a broadened version — which is what sent the design to review.
- **M2** the `[FAIL] ` case asserted the truthy-result print arm, not the `except` arm that most
  mutations actually report through. Now asserts both prints.
- **L1** round 1's reach fix deleted one count and wrote another. Every exact count is now gone from
  that comment; the digits live only in round 1's coordinator document, where a measurement is dated
  and is not claiming to be current.

## L2, L3, L4 — Claude's three, all confirmed and fixed

- **L2** the surface list was hand-typed beside the class it mirrors. Derived now — **and deriving it
  alone introduced the opposite hole**: removing `__iter__` from `_Forbidden` removed its case too and
  the suite read **148/148 passed**. A derived population needs a **literal floor**, or the ratchet
  runs one way. Both directions measured (removed → 148/149; added-but-unexercisable → 149/151).
  Recorded below as **S3**, because it is a defect in this round's own fix.
- **L3** `_Forbidden`'s message hardcoded `src_root_help` while round 2 gave it a second caller, so
  failures from `do_GET` named the wrong function — *the reason for a failure inferred rather than
  carried*, inside the guard written for that rule. `by=` added; each site verified to name itself.
- **L4** the reach comment's CORS clause is true of the response **body** and silent about status.
  200-vs-404 by file existence is measured, and over the true reach that is a file-existence oracle.
  One clause added. Still not judged worth blocking on — paths, not contents, on a loopback server —
  but round 1's defect on this same paragraph was a security judgement resting on an unchecked claim,
  and shortening the sentence is how that happened.

## S3 — my own fix's defect, recorded rather than smoothed

Deriving `_SURFACES` from `_Forbidden` closed "added and unasserted" and opened "removed and
unnoticed". Caught by mutating in the *other* direction before committing, which is the habit the
whole round is about.

## ⚠ Process defects in the coordinator's own conduct, recorded because they nearly cost the round

1. **I edited the subject twice while the Claude half was reading it.** It noticed, snapshotted an
   md5, and asked for a freeze — correctly, and its note is in its review. The tree was frozen at
   `323bc2a4` and it re-based. *An instrument that edits the repo corrupts its peers* applies to the
   coordinator too, and the reviewer, not a mechanism, is what caught it.
2. **A fix of mine silently reverted** across a sequence of scripted rewrites — the two-arm `[FAIL] `
   case returned to its one-arm form and I did not notice for several steps. Found only because a
   mutation that had gone red earlier came back green.
3. **My mutation harness was unsound.** It counted red cases by grepping for `FAIL`-shaped tokens,
   which breaks when the mutation *is* that token: mangling `[FAIL] ` to `EXC: ` made my own grep
   miscount. Verdicts now read the `N/M passed` line only. ⭐ This is *a report format is a CONTRACT*
   rebuilt in my own scaffolding, while fixing a finding about that exact contract.

## Q4 / Q5

**Convergence: not reached at round 2.** A High, fix-induced, plus non-trivial fixes →
`fixes_nontrivial: true` → **round 3 owed**, alternating (Claude first this time, since Codex ran
first in round 2).

**Thrashing: ARMED and ACTED ON** — by redesigning, not by a fifth patch, and by writing down why.

⭐ **PRE-COMMITTED, BEFORE ROUND 3 RUNS, so the decision is not made after seeing the result:** if
round 3 finds **another fix-induced defect in `src-caller`** — i.e. caused by the static/dynamic
redesign — then the redesign has failed on the same axis as the four attempts before it, and the
answer is **not** a sixth attempt. It is to **delete the "consulted the world exactly once" property
from this suite entirely**, state in the comment that it is unguarded and why, and let the
behavioural cases stand alone. An honestly unguarded property is worth more than a fifth guard that
reports a pass it has not earned — which is the lesson of the whole branch, applied to itself.
