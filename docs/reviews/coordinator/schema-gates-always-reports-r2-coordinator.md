# Round 2 — coordinator notes, `schema-gates-always-reports` (backlog #137)

Subject at review time: `99f4da56`. Fixes committed after: see below.

## Halves

| Half | File | Verdict | Findings |
|---|---|---|---|
| codex | `docs/reviews/codex/schema-gates-always-reports-r2-codex.md` | NOT CONVERGED | 1 Medium |
| claude | `docs/reviews/claude/schema-gates-always-reports-r2-claude.md` | see file | — |

Round 1: codex 1 High; claude 1 Blocking / 4 High / 6 Medium / 3 Low, both NOT CONVERGED.

## What r2 found, and what CI found that neither half did

**codex r2 Medium — a derived CHILD vouched for its declared parent.** `declared_not_derived`
matched a declared directory if any derived path was equal to it *or under it*, so
`…/stable-blob-addressing/schema` alone made `…/stable-blob-addressing` count as found — the
EXECUTED prong could stop deriving both mode-755 gate executables and the guard still returned `[]`.
⚠ A self-test case **blessed** this, so it was pinned as intended behaviour rather than merely
missed. Fixed: the match is EXACT, and that case is inverted.

**CI found a defect both halves missed, and it is the more interesting one.** On the *same commit*,
this machine reported `723 mutations, 723 killed, 723 attributed` and CI reported **722 attributed**,
with one mutation *"RED but printed no `[FAIL] <case>` line, so NOTHING COULD SEE THE KILL"*.

Cause, measured rather than guessed: a gate script **docstring** that merely mentions a `docs/` path
yields a multi-thousand-character blob, six of them with path components up to **1450 bytes**.
`Path.is_file()` raises `OSError` (ENAMETOOLONG) for those — **except on Python 3.13+, which widened
the errno set it swallows.** This machine runs 3.14 and returned `False`; the runner's older Python
raised, while the case list was still being *built*, so nothing printed at all.

⚠ The unmutated code was safe only by luck: the longest component a real gate script binds today is
**129 bytes**, 126 short of the limit.

Fixed by answering *is this a path* with SHAPE before the disk (`looks_like_path`): no whitespace,
every component ≤ 255 bytes. Verified structural — the longest string now reaching `is_file` is
**38 bytes**, mutated or not, so no python version can crash it.

## ⚠ Two self-inflicted repeats worth recording, because both were the round's own fix carrying the next defect

1. **Two new mutations shared one anchor** — the identical shape as r1's Blocking, which had just
   been fixed. Caught by the duplicate-anchor check *before* it reached CI. Both `looks_like_path`
   and `declared_not_derived` were restructured one-clause-per-line so each clause is separably
   anchored, and `COMPONENT_LIMIT` exists as a name for that reason alone.
2. **The case written to prove the shape guard used a RAISING fake reader**, so removing the guard
   crashed the suite and left *two* mutations unattributable — the same report-format defect CI had
   just caught one fix earlier, reintroduced by the case covering it. The fake reader now RECORDS
   and the case asserts on the record, so it FAILS instead of crashing.

## ⟳ THRASHING WATCH — stated explicitly, per the arming condition

The arming condition is *two consecutive rounds whose findings came from the previous round's own
fix, in one component*. Round 2 is the **first** such round: codex's Medium is a defect in r1's
`declared_not_derived` fix, and the ENAMETOOLONG crash is a defect in r1-codex's injected-`is_file`
fix. Both are in ONE component — the gate-code derivation.

⚠ **If round 3 finds another defect inside these same fixes, that is the second consecutive round
and the architecture review is ARMED.** The pre-committed retreat, written before round 3 rather
than after it: **revert the derivation to the declared-authority-plus-staleness-check shape**
(the option C considered and rejected at the r1 routing decision) and let backlog #138 carry the
whole completeness question. Recording it now because a retreat authored after the round that
triggers it is not a gate.

Note the asymmetry that makes this the right retreat: **the actual #137 change — the deleted
`paths:` filters — has produced ZERO findings across four review halves.** Every finding in both
rounds is in the collateral derivation that replaced the authority the filter had been serving.
