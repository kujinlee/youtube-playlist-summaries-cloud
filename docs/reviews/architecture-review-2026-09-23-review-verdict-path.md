# Architecture Review — the review-verdict path, 2026-09-23

**Convened by:** THRASHING in one component, per `docs/dev-process.md` Phase 6. Put to the user as
a selection card with per-finding evidence; the user chose to convene.

**Subject:** `scripts/codex-review.py` — the wrapper that dispatches an adversarial review and
writes **testimony** that the gate ran — together with its consumer `scripts/check-review-rounds.py`
and the convention in `docs/plugins.md` that joins them.

**Branch:** `observer-log-owner` (PR #342), HEAD `6cfae34a`.

---

## The arming condition, stated with its evidence

| Round | Finding | Caused by |
|---|---|---|
| r4 Claude, H1 | the allocator never allocated — a refusal, not an allocation | `c3ad7727`'s own verdict-path fix |
| r4 Codex, High | the allocator named the COMMIT and not the TREE | round 4's own fold |

⚠ **The literal trigger did not fire and the document says so.** `dev-process.md` writes the
condition as *two consecutive **ROUNDS***; these are two halves of **one** round (4). The SPIRIT
fired plainly: one component, defect-inside-its-own-fix twice running. The redesign test — *can a
redesign remove this class?* — answers **yes**, which is what decided it. This is the
*thrashing or prose floor?* question answered as **THRASHING**, on code findings rather than prose.

⛔ **Not a count.** Round totals were not consulted; the arming argument is the causal chain above.

---

## The root, and why four fixes missed it

`--out` is **deliberately a scratch path outside the repo**. `watched_dirs` snapshots it together
with `ARTIFACT_ROOTS = ("docs/reviews",)`, and `quarantine` moves agent-created files out of the
artifact tree — the reviewing agent runs under `-s danger-full-access` and has previously inferred
a committed review path from filenames in its brief. So `--out` being scratch is load-bearing, not
incidental.

The **review identity** — the durable `<subject>-r<N>-<writer>.md` a half is filed under — is
therefore assigned **after** the run, by whoever promotes the file.

⭐ **AND NO CODE IMPLEMENTS THE PROMOTION.** `docs/plugins.md:158` reads
`--out "$(mktemp -d)/r.md"  # then promote`, and that comment is the entire mechanism. The
coordinator does it by hand; I did it twice by shell redirect during this very session.

**Therefore no derivation from `--out` can be correct.** Both the testimony's filename
(`verdict_path`, `codex-review.py:306`) and the record's own `review` field
(`verdict_record`, `:470`) are derived from a basename that is never the durable name. Four
successive fixes — refuse-if-tracked, allocate-by-token, widen-the-token, add-the-tree — were each
attempts to *guess an identity assigned later by someone else*. Each was locally correct. None
could terminate, which is the signature of a wrong seam rather than a wrong line.

This is the shape `scripts/coverage_verdict.py` already recorded one module over, after **seven**
rounds: *"The rounds were not failing. They were ENUMERATING, one consumer per round, through a set
a real interface closes in one move."*

---

## Measurement

**The join, driven through the shipped `check-review-rounds.verdict_problems`:**

```
documented `--out "$(mktemp -d)/r.md"`  -> problems reported: 0
dispatched under the review's real name -> problems reported: 1
```

Same failed gate, same filed review. The first is invisible to the guard, because
`review_names = {p.name for p in paths}` (`:266`) is matched against a record field derived from a
scratch basename.

**The corpus:**

```
verdicts on disk                183
naming a review NOT filed        58   (32%)
  ...of which gate_ran=false      5
```

⚠ **NONE OF THE FIVE IS A LIVE MISS, and the review says so rather than inflating.** Four name
their real review with nothing filed — correct behaviour. One,
`plan-coverage-verdict-union-r1-codex.verdict.json`, records `"review": "r.md"` while its own
filename names the real review: the divergence in the wild, but not a miss. **A latent hole with a
demonstrated mechanism and one historical near-instance.**

**Depth of the module, by AST over the delivered file:**

```
lines 1795   module-level functions 27   reachable from main 17
named only by self_test 6    self_test body 627 lines    CLI flags 9
```

**Uniqueness of the mechanism** — ten scripts take an `--out`; every other one defaults to a
**constant** (`DEFAULT_OUT = ~/explainers/...`). Basename-derivation of a durable path occurs at
five sites, **all inside `codex-review.py`**. The fix is local; there is no cross-file sweep.

---

## The decision (settled with the user in the grilling loop)

1. **`--review-id` is REQUIRED; basename-derivation is DELETED.** An optional identity keeps both
   mechanisms alive for one concern, and the repo's recorded verdict is that a fallback everyone
   takes is the behaviour. Old invocations are owed a **refusal sentence**, not argparse's
   "unrecognized arguments" — the precedent is this file's own retired plan-mode flags.
2. **The wrapper performs the promotion**, so one module owns both artifacts of a run and the join
   is correct by construction. ⚠ Feasibility CHECKED, not assumed: the wrapper already writes into
   `docs/reviews/verdicts/`, and the intrusion snapshot of `docs/reviews` is **non-recursive**, so
   writing a subdirectory does not trip it.
3. **The 183 existing verdicts are left untouched** — they are committed testimony about runs
   nobody can re-observe, and `check-review-rounds` already refuses to back-fill history on the
   same grounds. The consumer must carry a written caveat that pre-cutover verdicts cannot be
   trusted to name a filed review, or the caveat becomes another undocumented thing.

**What this deletes:** `run_token`, `verdict_collision`, `path_is_tracked`, `refusal_verdict_path`
and their 9 mutation entries exist solely to manage a namespace that would no longer exist.

---

## What did we decide this milestone that isn't written down?

- **That `--out` must live outside the repo for the quarantine machinery.** Stated in scattered
  comments and in `docs/plugins.md`'s output contract, but never as a constraint on naming — which
  is exactly the fact that makes derivation impossible. Now recorded here and in `CONTEXT.md`.
- **That "verdict" names two concepts.** Added to `CONTEXT.md` this turn as **Testimony** and
  **Review identity**, resolving a collision no guard can see (backlog #167).
- **That promotion is a human step.** Believed to be part of the tooling by anyone reading
  `# then promote`; it is not.

---

## ADRs

No ADR covers the review-verdict path. None of the thirteen is re-litigated here.
⚠ Decision 2 (the wrapper writes committed review files) is a candidate for an ADR when it lands —
it changes who writes the repo, and a future architecture review would otherwise re-open it.

---

## Limits of this review — stated, not implied

- **The `Explore` agent dispatched for this review did not return within the session. Treat its
  contribution as NOT RUN.** Every claim above was verified by hand, with the command and output
  recorded; none rests on agent output. The Phase 6 rule that agent output is a *lead, not a
  finding* is satisfied vacuously here.
- **No implementation was attempted.** This review produces a decision and a backlog row; the work
  is a separate slice with its own review rounds.
- **`check-guard-coverage.py`, the schema gates, `test:integration` and `test:e2e` were not run** —
  outside this subject. Treat as NOT RUN rather than clean.
