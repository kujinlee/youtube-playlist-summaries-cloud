# Round 9, coordinator — hand-verification of the Codex half, and the thrashing determination

**This is not a third review.** It records (a) which of the Codex half's findings survive
independent reproduction, (b) one of my own measurements that was INVALID and how, and (c) the
Phase 6 arming determination that ends this review loop.

Subject: the uncommitted working tree on `semantic-recall-replication`, dispatch fingerprint
`b61218a85d1ebd7f833d672c8750c1bd472bd20a51f825ee2a5cbacd02969c33`.

The Codex half verified the freeze itself — it reported the same fingerprint at start and at end,
which is the first round in this fold where the reviewer could do that AND the gate agreed with it.

## The gate and the reviewer saw the same tree, and that is new

| claim | evidence |
|---|---|
| Gate green | 57 files, 1177 mutations, 1177 killed, 1177 attributed, 0 survivors, rc=0; 0 `[FAIL]` lines |
| Gate's tree == dispatch tree | fingerprint `7d54599b…` identical before and after the run |
| Only delta since the gate | `docs/backlog.md` (the #214 amendment). All 57 MUTATED scripts byte-identical — `shasum -c`, **0 mismatches** |
| Reviewer's own freeze check | start == end == `b61218a8…`, reported by the reviewer unprompted |

⚠ **One inference was attempted and NOT confirmed:** that a docs-only edit cannot reach the gate.
**20 of the 57 mutated scripts reference the `docs/` tree.** That does not show the edit matters —
it shows the clean argument does not hold, so it is recorded as unconfirmed rather than assumed.
The Codex half was told this and also declined to confirm it.

## Findings reproduced by hand

Isolated copy (`HARNESS_TREE`: `scripts`, `supabase`, `docs`, `node_modules/typescript`,
`.claude/hooks`, `.github`), `$HOME` redirected — **`~/explainers` is a symlink INTO this repo**, so
a suite resolving it would write into the subject. Control green before, after-control green after;
without both the run is void.

| # | severity | sever | suite | live | verdict |
|---|---|---|---|---|---|
| B1 | **BLOCKING** | `violations = assess(ROOT, ci_path, texts, ratchets)` → `[]` | **52/52** | rc=0 | ⛔ **SURVIVES** |
| H1a | HIGH | `defined = _defined_codes()` → its exact current value | **58/58** | rc=0 | ⛔ **SURVIVES** |
| H1b | HIGH | `defined = defined_codes(_read_or_refuse(MATCHER))` → same | **55/55** | rc=0 | ⛔ **SURVIVES** |
| H2 | HIGH | `_env` scrub → `dict(os.environ)` | **55/55** | rc=0 | ⛔ **SURVIVES** |

**B1's known-positive, because a sever that hides nothing is not a defect:** with the two CI callers
for `check-surface-recall.py` removed, the live guard exits **1** with `[R3_no_caller]`. That is the
violation `violations = []` conceals while `main()` prints `ratchet contract OK`.

H3 (the live diagnostic names `DECLARED_RENDER` when the failing rule is `DECLARED_WITH_DETAIL`) and
L1 (the `$1` seam is unreachable from `settings.json` by construction — not a defect) are taken from
the Codex half's measurements and not independently reproduced. Recorded as such.

## ⛔ MY FIRST H1 MEASUREMENT WAS INVALID, AND IT WOULD HAVE CLEARED A LIVE DEFECT

The first sever replaced `_defined_codes()` with a six-code dict I composed from memory:
`{'OK': 0, 'NO_MATCH': 1, 'STALE': 2, 'PAUSED': 3, 'NO_PLAN': 4, 'REFUSED': 5}`.
The suite went **red, 4 named `[FAIL]`s**, and the obvious reading was *"the wiring is tested; the
Codex half is wrong."*

The real value is `{'OK': 0, 'CANNOT_RUN': 2, 'STALE_CACHE': 3, 'BAD_RESPONSE': 4,
'UNREADABLE_PLAN': 5, 'UNANSWERABLE': 6}` — **every name wrong and four of six values wrong.** The
red was my literal being incorrect, which the guard is supposed to catch. Substituting the value the
function actually returns today, the suite is **58/58 green and the live run rc=0**.

⭐ **The rule this yields: a sever tests WIRING only if the substituted value is what the callee
returns right now.** Any other value tests correctness, which was never in question — and it fails
in the direction that looks like good news. Four named `[FAIL]`s read as a passing guard.

## Q4(a) — is another round owed? CONTINUE, on all three grounds

A Blocking; findings in the deliverable; fixes that would be non-trivial. Not converged.

## Q5 — thrashing: YES, and the Phase 6 condition is MET

Per finding, *did the previous round's fix cause this?*

| finding | caused by a previous fix? | evidence |
|---|---|---|
| B1 | **YES** | round 8's B1 fix extracted `assess()` to make its internals testable; the extraction created the new, untested call site at `main()`. The reviewer names this. |
| H1a/H1b | no — **unfixed carry-over** | this IS round 8's H4, which the handoff recorded as addressed. It was not. |
| H2 | **YES** | round 8's H1 fix added the allowlist and a reconciler; the reconciler works, the CONSUMPTION was never wired |
| H3 | **YES** | round 8's H3 fix closed the behaviour and left the diagnostic naming the other table |

**Two consecutive rounds, one component:**

- Round 8's Blocking was in `check-surface-recall.py` — a file **round 7's fold created**.
- Round 9's Blocking is in the call site **round 8's fix created**.

That is the shape `dev-process.md` describes: one component producing Blocking/High in consecutive
rounds, instances introduced by the previous fix, while every other part of this fold converged.
**Nine rounds; the class is at eleven instances.** Each fix extracts a function to make its internals
testable and leaves the new call site unexercised.

## Disposition — the loop STOPS here

Put to the human as a selection card (axis: step back to the DESIGN / go to the MECHANISM / keep
patching INSTANCES). **Chosen: a scoped Phase 6 architecture review**, on one question — *why does
each fix create the next instance?*

The four findings above are **NOT folded per-instance.** They are the architecture review's evidence.
Folding them would produce a twelfth instance, which is the prediction this determination rests on.

> ### REVIEW GAP: claude — round 9's Claude half was not run as a per-instance review.
> Not because it could not run — it could, and spawning it is pre-authorised. The per-instance
> instrument is what this round determined to be the wrong one. The independent Claude reading moved
> to the architecture review, with a DESIGN mandate instead of an instance-hunting one; it is filed
> as that review's document. This gap is a redirection of the second reader, not the loss of one.
