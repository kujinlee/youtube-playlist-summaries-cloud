# Backlog 65 — round 3: an INDEPENDENT review of round 2's fixes

**Date** 2026-08-27 · **Subject** `fix/backlog-65-live-schema-drift` @ `d3ffd84`
**Reviewer** a FRESH subagent — deliberately not the round-2 reviewer, which had proposed the
direction (the allow-list) and so had a stake in the implementation being right. Run alone; the
coordinator stayed read-only for the duration.
**Verdict: NOT CONVERGED — 0 Blocking, 1 High, 3 Medium, 5 Low.** All fixed below except two
pre-existing items, recorded not carried.

---

## ⭐ THE META-FINDING: THREE OF NINE ARE MY FIX BEING INSTANCE-NOT-CLASS

This is the round's real result and it is about method, not code:

| Round 2 fix | What round 3 found |
|---|---|
| corrected *"27 foreign objects, 12 indexes"* → 15/0 | **`27` still live four sentences later, in the SAME backlog row** |
| gave the drift report a conditional `AND` joiner | **the identical dangling `AND` 26 lines up, untouched, in the same function** |
| gave the drift failure a reachable remedy (r2 HIGH 1) | **the ambiguity refusal next to it still prints NO remedy at all** |

Each time I fixed the instance in front of me and not the class — the exact defect this repo has
named twice (`a-convention-catches-what-you-read`, `a-shim-can-fail-in-both-directions`). Landing one
day after `7c95059` made *"qualify every number in prose"* a standing rule.

---

## HIGH 1 ✅ FIXED — the POLICY probe could not fail for the reason it was added

Round 2 added `probe_kind` for POLICY/CONSTRAINT/TRIGGER and claimed each *"sabotages a REAL database
and requires RED."* For POLICY that was false. `_policies()` is spliced into the **`table:`** digest
(`m4_catalog.py:330`), so a new policy makes `table:video_artifacts` REDEFINED and breaks the subset
test — which mutation 27 already covers. The tick was earned by pre-existing coverage.

The reviewer proved it by neutering `unexpected()` to `return set()` on a temp copy: POLICY stayed
red **1 → 1**, discriminating nothing, while the other three went 1 → 0.

This is r8 B1's shape verbatim, against a rule this same file states: *a token is only a
discriminator if the control cannot contain it.*

**Fix** — the probes stop reading the exit code and match the drift SENTENCE
(`EXIST ON A RELATION M4 OWNS`), which only `unexpected()` can emit, plus a control asserting the
unmutated clone does **not** contain it. Captured first and matched second, never piped into
`grep -q` under `pipefail` — a trap this file measured before.

**COORDINATOR-VERIFIED by re-running the experiment:** neutered → **COLUMN, POLICY, CONSTRAINT and
TRIGGER all MUTATION SURVIVED** (4 of 4 now discriminate; POLICY previously did not), harness exit 1.
Restored → 55/55, exit 0.

## MEDIUM 1 ✅ FIXED — the corrected number was still live in the row announcing its correction
`docs/backlog.md:93` still read *"The **27** manifest objects on the 4 FOREIGN relations …"*.
Re-derived: **15** (7 trg · 5 con · 3 col). Also *"1 of 48 assertions red"* was stale — re-measured
against this build: **4 of 55**, and the row now records which build it was verified against.

## MEDIUM 2 ✅ FIXED — the dangling `⛔ AND` fixed for one branch, not the class
`check-live-schema.py:854` printed `⛔ AND N object(s) EXIST BUT DO NOT MATCH…` as the first line
whenever `redefined` is non-empty and `missing` is empty — most of the mutation suite. Pre-existing
on `master`, but 26 lines from the one round 2 fixed, in the same function. Now conditional.
Verified by execution: first line is now `⛔ 1 object(s) EXIST BUT DO NOT MATCH THEIR DEFINITION —`.

## MEDIUM 3 ✅ FIXED — the ambiguity refusal had no exit, which is round 2's HIGH one branch over
Exit 2 with no remedy, and `check-schema-gates.sh` treats it as `fail=1`. The accept-list cannot
express a two-dot name (`load_accepted` refuses it) and the manifest is derived, so an operator had
nothing to do. Now prints the only two real actions — rename the object, or quote the separator in
`CATALOG_SQL` as its own slice — and states explicitly that the accept-list cannot clear it.

## LOW 1 ✅ FIXED — a comment the round-2 narrowing made false in both directions.
## LOW 2 ✅ FIXED — a malformed accept-list took `--expect-absent` to exit 2, a mode that never reads
it. Now loaded only in present mode. Verified: absent + malformed → exit 1; present + malformed → 2.
## LOW 3 ✅ FIXED — `partition("#")` accepted `col:workspaces.a` from `col:workspaces.a#b # reason`,
silencing a different object than the line named. The marker must now be whitespace-preceded.
Verified: the same input now yields `col:workspaces.a#b`.
## LOW 4 ✅ FIXED — `accepted-additions.txt` claimed the printed count meant the list "cannot grow
unnoticed"; it printed a bare number, on the pass path only. It now prints the NAMES.
## LOW 5 — NOT FIXED, recorded. The harness assertion count is a runtime tally with no ratchet; a
skipped block would shrink it silently. Every skip path sets `fail=1` today, so it is not a false
green — but the number quoted in these docs is unguarded.

## ⛔ THE CODEX HALF OF ROUND 3 FOUND A SECOND HIGH — THE SAME CLASS AGAIN

`name_of` splits at the FIRST `@`, so a live column literally named `"retention_class@shadow"`
renders `col:workspaces.retention_class@shadow@<digest>` and `name_of` returns
`col:workspaces.retention_class` — the name of a **different** column. MEASURED: with only
`col:workspaces.retention_class` on the accept-list, `verdict` returned **True** while the shadow
column sat unaccepted on an M4-owned relation. That is the one thing an allow-list must never do,
and it is the direct answer to the question I put to the Claude half.

**This is the FOURTH instance-not-class in this slice, and the second in the same commit** — I had
just fixed `#` inside an identifier (LOW 3) and did not carry the reasoning to `@`.

**Fix** — `ambiguous()` now flags any attributable object whose raw string does not have exactly one
`@` (scoped, as with the dot, to objects that could land on an owned relation), and `load_accepted`
refuses an entry containing `@`. Verified: the shadow object is flagged, `main` refuses before the
verdict, an `@`-bearing accept entry is REFUSED, and both real subjects still measure 0 ambiguous /
0 unexpected across 391 objects.

## What round 3 attacked and could NOT break — reported because it is evidence, not filler
- **The allow-list cannot suppress more than the object it names.** 17 crafted inputs executed: 6
  refused, 11 parse, 1 mis-parse (LOW 3, fixed). Malformed input fails CLOSED (exit 2). An ADR-0011
  object on the list changes nothing — `forbidden()` runs before `unexpected` and matches by symbol.
  The list cannot clear either refusal; neither reads `accepted`.
- **`ambiguous()`'s narrowing is sound**, with a proof rather than an assertion: the true relation is
  always `".".join(parts[:k])` for some k, and the code tests every such prefix.
- **No path returns non-zero printing nothing, or zero checking nothing.** All four failure
  combinations traced.
- `probe_kind`'s unquoted heredoc does not expand `$$` to the PID — checked because the file has a
  rule about that class.

---

## Verification (coordinator, after the fixes)

self-test **110/110** · harness **55/55**, exit 0 · neutered-`unexpected()` falsification: **4 of 4
kinds go red** · all 15 schema gates green · 5 doc ratchets green · `--prod --expect-present` exit 0
over 161 objects. Production read-only throughout.

⚠ **THREE ROUNDS, NONE CONVERGED.** `docs/dev-process.md` fires Phase 6 on **four**. If a round 4
does not converge, that trigger is met — and on this evidence the subject would be the *method*
(fixes that address the instance and not the class), not the drift logic, which round 3 tried hard
to break and could not.
