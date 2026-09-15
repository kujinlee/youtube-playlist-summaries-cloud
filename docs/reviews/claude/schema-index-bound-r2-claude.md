# `schema-index-bound-stale` (PR #296) — round 2, CLAUDE half

**VERDICT: CONVERGED. No Blocking, High or Medium. All four r1 findings are fixed and I verified
each by execution with a control. Two Low findings remain, neither of which blocks a merge** — both
are the same shape (a comment that claims slightly more reach than the code has), both are one- or
two-line fixes, and neither can produce a false green.

**The r2 change is strictly better than r1 against a genuinely broken gate**, which is the thing the
coordinator asked about and the thing I most feared. Measured below: same reds, four fewer false
greens.

**Disclosure.** The Codex r1 half is committed on this branch, so its grade reached me through
`git log` and the diff; I still have not opened it. I have not seen any Codex r2 output.

---

## The question that mattered: did NOT RUN trade a false red for a false silence?

**No. Measured on both harnesses against the same broken gate, and the red count is identical.**

I neutered `unexpected()` — `return set()` inserted at the head of its body, inside the function and
nowhere else (verified: the neutered copy's own `--self-test` drops **119/119 → 104/119**, so the
neuter genuinely bites) — and ran the r1 harness and the r2 harness against it.

| harness | ✓ | ✗ | exit | the four `…and undoing the X goes GREEN again` lines |
|---|---|---|---|---|
| r1 (`57fd9d17`) | 12 | **5** | 1 | four **✓** — greens earned over a gate that detects nothing |
| r2 (`dd7ebaba`) | 8 | **5** | 1 | four **NOT RUN** |

Same five reds, same exit code, four fewer false greens. The NOT RUN path removed *only* assertions
that were previously passing for no reason. Nothing that was red became quiet.

And it cannot launder a green one level up either: `check-schema-gates.sh:22-28` decides purely on
the child's exit status — it never parses `✓`/`✗`/`⚠` — while the harness's own `exit "$fail"` is
driven by `report` and by explicit `fail=1`, never by `$?` of the last command. Every NOT RUN path
either sets `fail=1` itself (`:324`) or is reached only after a `report` that already did.

---

## The other question: callers, `return 1`, and `pipefail`

**No behavioural change, and I checked rather than reasoned.**

* `set -uo pipefail` at `:61` — **no `-e`**. A non-zero return at statement level does not abort.
* All four call sites are bare commands: `:362` POLICY, `:366` CONSTRAINT, `:370` TRIGGER, `:394`
  INDEX. None is inside `if`/`&&`/`||`, none is in a pipeline, so `pipefail` never sees `probe_kind`
  and the return value is discarded at every site.
* The script's exit is `exit "$fail"` at the tail, not `$?` of the last statement, so `return 1`
  cannot reach the exit code.
* `residue` is a new, unique identifier — three sites only (`:354` write, `:356` init, `:419` read).
  It does not collide with the `m4_mut_residue` column, and `:356` precedes every reader.
* `mrc=$?` at `:321` reads the `db` call directly; `local out mrc seen` at `:317` is a bare
  declaration with no assignment, so it does not mask the status. (`local x=$(cmd)` would have.)
* **`residue=1 ⟹ fail=1` holds, and provably:** `:354` is the single writer and it runs immediately
  after the `report` at `:345`, which sets `fail=1` on exactly the condition that writes the flag. So
  the FOREIGN bound's NOT RUN branch is right not to set `fail` — see the note below about making
  that explicit.

---

## Findings

### LOW 1 — `residue` has one writer and one reader, so three other ways the clone gets dirty cannot set it. One of the three is single-fault and reachable today.

The comment at `:351-353` states the flag's contract:

> *"once a probe's undo fails, the clone is KNOWN DIRTY, and **a downstream expected-pass reports NOT
> RUN** instead of a red it did not earn."*

That is true of *the* downstream expected-pass it guards — the FOREIGN bound at `:419` — and not of
downstream expected-passes in general. Three measured cases:

**(i) SINGLE FAULT, reachable in the shipped file.** Desync the POLICY undo
(`d-policy-undo-desync.sh`) — one fault, no neutering, nothing else changed:

```
  ✓ ⭐ backlog 65: an unexpected POLICY names DRIFT (not merely a red gate)
  ✗ …and undoing the POLICY goes GREEN again — MUTATION SURVIVED
  ✓ ⭐ backlog 65: an unexpected CONSTRAINT names DRIFT (not merely a red gate)
  ✗ …and undoing the CONSTRAINT goes GREEN again — MUTATION SURVIVED
  ✗ …and undoing the TRIGGER goes GREEN again — MUTATION SURVIVED
  ✗ …and undoing the INDEX goes GREEN again — MUTATION SURVIVED
  ⚠ BOUND: a new column on a FOREIGN relation (videos) — NOT RUN: a probe's undo failed above …
```

The flag protects the bound at the bottom and does nothing for the **three sibling probes in
between**, each of which is a downstream expected-pass reporting a red it did not earn — r1 LOW 1's
defect, one scope inward. `probe_kind` knows the clone is dirty at `:354` and the next probe never
asks.

**(ii) Path (b) cannot set the flag, and the leftover still bites.** `g-neutered-policy-desync.sh`
— gate neutered **and** the POLICY undo desynced. Path (b) fires for all four probes, `residue` stays
`0`, and the leftover policy breaks the *subset* test (not the drift report), so:

```
  ✗ BOUND: a new column on a FOREIGN relation (videos) still PASSES — MUTATION SURVIVED
```

exactly the red the flag exists to prevent. Two faults, so low reachability — but it is measured,
not argued, and it shows the flag is unreachable from path (b) rather than merely unnecessary there.
The undo at `:336-338` runs with its exit status discarded, and on this path there is no `gate` call
to substitute for it.

**(iii) Path (a) has the same gap.** `f-partial-land.sh` — mutate SQL that partially lands
(statement 1 creates the index, statement 2 errors) with a desynced undo. Guard (a) fires correctly,
its best-effort undo at `:325-327` runs without `ON_ERROR_STOP` and with its status discarded,
`residue` stays `0`, and the FOREIGN bound goes `✗ … MUTATION SURVIVED`. **Not reachable today** —
all four mutations are single statements, so a failure means nothing landed — but guard (a) is
explicitly sold at `:309-310` as *"generic, so it needs no hand-written predicate per kind"*, which
is an invitation to a future multi-statement mutation.

**Impact, stated honestly.** No false green in any of the three: the run is already red and exits 1.
The cost is misattribution — the reader is sent to CONSTRAINT/TRIGGER/INDEX or to the FOREIGN bound
when the defect is the POLICY undo. That is the same cost r1 LOW 1 carried and the same grade.

**Falsifier.** Re-run `d-policy-undo-desync.sh`. If the CONSTRAINT/TRIGGER/INDEX undo lines come back
as NOT RUN rather than MUTATION SURVIVED, (i) is closed.

**Fix — two lines, and they make the `:351-353` sentence true as written:**

* at the top of `probe_kind`, before the mutate: `[ "$residue" = 1 ] && { echo "  ⚠ $1 probe — NOT
  RUN: a previous undo failed, the clone is known dirty"; return 1; }`
* on the two early-return paths, capture the best-effort undo's exit status and `residue=1` when it
  is non-zero. ⚠ This does **not** close the desync case — `drop index if exists <wrong-name>`
  succeeds — so it is a partial closer and should be described as one. Only re-asserting the object
  is gone would close that, which is `landed` inverted and is the cost the generic guard bought out
  of.

---

### LOW 2 — the edit to the committed Codex review deletes the reviewer's own reasoning instead of quoting it, which is the opposite of what this branch did to backlog row 65.

`docs/reviews/codex/schema-index-bound-r1-codex.md:1-10` had its `REVIEW GAP:` paragraph replaced.
**Removing the line was mechanically necessary and I proved the gate is live for this round** rather
than assuming it: with my r1 file moved aside, `check-review-rounds.py` exits **1** with

```
  ✗ schema-index-bound round 1: only codex — claude neither ran nor recorded a `REVIEW GAP:` line
```

and passes with it restored (byte-identical after restore — verified with `diff -q`). So a stale gap
declaration would have been a real defect, and the replacement text says so clearly.

What went with it is a substantive claim of Codex's own: *"The change is a 44-line assertion
inversion whose subject is itself a test harness, and it is verified by the full fifteen-gate schema
suite plus an independent Codex run that re-executed the harness on the clone path."* That was the
reviewer's justification for tolerating the gap, and it is now unrecoverable from the file. This
branch's own convention for exactly this situation is three lines away in `docs/backlog.md:93` —
*"the sentence it replaces is kept below … It read: `…`"* — and in the dashboard store's append-only
rule. Applying it here costs one sentence.

**Falsifier.** The deleted paragraph contained no claim beyond the gap declaration itself.

**Fix.** Quote the removed paragraph inline, as row 65 does.

---

## r1 findings — each re-measured, with a control

| r1 finding | status | evidence |
|---|---|---|
| **MEDIUM 1** — the undo half is an expected-pass earned by SQL that never ran | **FIXED at the mechanism** | `a-unlandable.sh` (`create index … (no_such_column)`): `✗ the INDEX mutation DID NOT LAND (psql exit 3) — treat this probe as NOT RUN`, `fail=1`, **and no second assertion is emitted at all**. The r1 code printed `✓ …and undoing the INDEX goes GREEN again` here. The accusation is also back on the SQL rather than on `check-live-schema.py`, which is the half `landed` used to carry |
| **LOW 1** — a failed undo reds an unrelated downstream bound | **FIXED for the bound it names** | `c-index-undo-desync.sh`: **exactly 1 ✗** (was 2 on r1) plus `⚠ BOUND … NOT RUN`. See r2 LOW 1 for the scopes the flag does not reach |
| **LOW 2** — nested `**` in backlog row 65 | **FIXED** | three-way control through `page_markup.render_inline`: master **0** stray `**`, r1 **1**, r2 **0**. The only change to row 65 since r1 is that character pair (`--word-diff`: `-**PAID` → `+PAID`) |
| **LOW 3(a)** — enumeration short by one | **FIXED** | `docs/dashboard-entries.md:8084` now names `backlog-65-live-schema-drift-claude.md:54-57` and classifies it correctly as a dated record |
| **LOW 3(b)** — the append/renumber justification | **FIXED by recording, not rewriting** | entry 2026-09-12/6 states the correction; entry /5 is untouched. 6 blocks now carry that date, so /5 kept its id — which is the append-only rule behaving as advertised |

**Author's own falsifiers, independently reproduced:**

| claim | my measurement |
|---|---|
| control `56 ✓ / 0 ✗` exit 0, unchanged | **56 ✓ / 0 ✗, exit 0** |
| (a) unlandable → DID NOT LAND / NOT RUN, no second assertion | **reproduced**, and the FOREIGN bound correctly still passes (nothing landed, clone clean) |
| (b) lands but no drift → MUTATION SURVIVED + undo NOT RUN | **reproduced** with `create index m4_mut_idx on public.videos (position)`; the undo still executes, so the clone is clean and the FOREIGN bound passes ✓ afterwards |
| (c) undo desynced → 1 ✗ + downstream NOT RUN | **reproduced exactly** |
| suite `73 ✓ / 0 ✗`, 15/15, exit 0 | **73 ✓ / 0 ✗, exit 0, "✅ all schema gates green"** |

**Counts are undisturbed:** static `report` call sites **50 on both r1 and r2** (the new lines are
`echo`, not `report`), so the dynamic total stays 56; `mutation N` labels unchanged, so
`check-schema-gates.sh:130`'s "29 mutations" and `check-catalog-coverage.MOVED_COVERAGE`'s citations
still resolve.

---

## Smaller notes — not findings, but worth one line each

* **`probe_kind`'s return value is 1 on "could not run" and 0 on "ran and failed"** — `:354`'s
  `[ "$r" = pass ] || residue=1` returns 0 even when the undo assertion went red. Nothing reads it
  today, so this costs nothing; a future `probe_kind … || handle_failure` would read it backwards.
  One comment naming the convention would close it.
* **The FOREIGN bound's NOT RUN branch (`:419-425`) depends on an invariant established 65 lines
  away.** It holds (verified above), and the comment says *"`fail` is already 1"* — but it names the
  fact, not the guarantor. An idempotent `fail=1` in the branch would make it self-evident.
* **`psql exit $mrc` at `:323` would misname a Docker failure.** `db` returns `docker exec`'s status,
  so a dead container reports as a psql exit code. Cosmetic; `landed`'s message had the same flavour.
* **Pre-existing and out of this branch's scope:**
  `docs/reviews/backlog-65-live-schema-drift-r3-codex.md:51` already filed stale claims in
  `backlog-65-live-schema-drift-claude.md` (lines 31, 33 and a `54/54` harness count at 94) in an
  earlier round, and they are still there. My r1 LOW 3(a) was a rediscovery of the same file by a
  different line. If anyone wants that closed, it is a separate change — a finding whose only
  closer is a reply.
* **Structural point the branch already records, and I agree with it:** the Codex half being
  committed on the branch under review makes the second half's independence unprovable. The
  dashboard entry states this. Dispatching both halves before either is committed is the fix.

---

## What I executed

Same constraints as r1: never changed the branch, wrote no tracked file but this review. Variants ran
against a symlink farm at `…/scratchpad/claude-half-r2/fakeroot/` — every repo entry symlinked except
`scripts/`, a real directory of symlinks with one or two files swapped. `git status --porcelain` was
clean before and after, and is clean now apart from this file.

| # | run | result |
|---|---|---|
| 1 | `r2-harness.sh` (control, full) | 56 ✓ / 0 ✗, exit 0 |
| 2 | `a-unlandable.sh` | `DID NOT LAND (psql exit 3) … NOT RUN`, no second assertion → **r1 MEDIUM 1 closed** |
| 3 | `b-lands-no-drift.sh` | drift half ✗, undo `NOT RUN`, clone still cleaned |
| 4 | `c-index-undo-desync.sh` | 1 ✗ + FOREIGN bound `NOT RUN` → **r1 LOW 1 closed** |
| 5 | `d-policy-undo-desync.sh` | 4 ✗, three of them misattributed siblings → **r2 LOW 1 (i)** |
| 6 | `f-partial-land.sh` | path (a) leaves the clone dirty, `residue` unset → **r2 LOW 1 (iii)** |
| 7 | `e1-r1-neutered.sh` + neutered `unexpected()` | 12 ✓ / **5 ✗**, exit 1 — four false greens |
| 8 | `e-r2-neutered.sh` + neutered `unexpected()` | 8 ✓ / **5 ✗**, exit 1 — the four became NOT RUN |
| 9 | `g-neutered-policy-desync.sh` | FOREIGN bound `✗ MUTATION SURVIVED` with `residue=0` → **r2 LOW 1 (ii)** |
| 10 | `M4_PHASE=post bash scripts/check-schema-gates.sh` | 73 ✓ / 0 ✗, exit 0, 15/15 green |
| 11 | neutered copy `--self-test` | 104/119 — proof the neuter bites before trusting runs 7–9 |
| 12 | `check-review-rounds.py` with my r1 file moved aside, then restored | rc **1** with the exact missing-half message, then rc 0; `diff -q` confirms byte-identical restore |
| 13 | `check-docs.py`, `check-backlog-closure.py`, `check-dashboard-entry.py`, `check-review-rounds.py` | all rc=0 |
| 14 | `gen-dashboard.py`, `page_markup.render_inline` three-way | rc=0; stray `**` 0 / 1 / 0 |

**NOT RUN, stated rather than implied:** I did not re-run master's full `check-schema-gates.sh` (it
would require a checkout, which the brief forbids), and I did not sabotage the live `postgres`
database — every mutation ran on PID-scoped scratch clones.

---

## Recommendation

**Merge.** The four r1 findings are closed at the mechanism, the control is unmoved, and the change
is measurably better than r1 against a broken gate rather than merely quieter.

r2 LOW 1 is worth the two lines before merge if the coordinator wants the `:351-353` sentence to be
true as written — this branch's whole subject is a comment that outlived its premise, and (i) is a
single-fault case that reproduces on the shipped file. r2 LOW 2 is one sentence. Neither is a reason
to hold the branch, and neither makes anything green that should be red.

---

# Coordinator response — CONVERGED accepted; both Lows fixed anyway, and all THREE scopes close

r2 graded its LOW 1 as non-blocking and it was right about the impact — no false green in any of the
three cases. It was fixed regardless, for the reason r2 itself named: **this branch's entire subject
is a comment that outlived its premise, and the r1 flag shipped a sentence claiming more reach than
the code had.** Merging that would have been the defect committed by its own fix.

## LOW 1 — fixed for all three scopes, not just the single-fault one

The fix is **one rule, applied at three sites**: *observe whether the clone is still clean; credit
nothing.* Both NOT-RUN paths now read the gate without asserting, so the flag learns about residue on
paths that emit no assertion at all — which is what made (ii) and (iii) invisible to r1's writer. Plus
the guard r2 specified at the top of `probe_kind`.

⚠ **r2's own fix sketch would have closed only (i).** Its second bullet — capture the best-effort
undo's exit status — it correctly labelled a partial closer, because `drop … if exists <wrong-name>`
*succeeds*. Reading the **gate** instead of the **exit status** is what closes the desync cases, and
it costs nothing on the happy path since neither branch is reached in a green run.

| case | before | after |
|---|---|---|
| **(i)** POLICY undo desynced, single fault | 4 ✗ — POLICY plus three siblings red for a leftover policy | **1 ✗** + CONSTRAINT/TRIGGER/INDEX and the FOREIGN bound all `NOT RUN` |
| **(ii)** gate neutered **and** POLICY undo desynced | `✗ BOUND: a new column on a FOREIGN relation — MUTATION SURVIVED`, `residue=0` | **`⚠ BOUND … NOT RUN`** — the gate read on the never-observed-as-drift path sets the flag |
| **(iii)** partial land (`create index …; select 1/0;`) + desynced undo | FOREIGN bound `✗ MUTATION SURVIVED`, `residue=0` | `✗ the INDEX mutation DID NOT LAND (psql exit 3) — NOT RUN` + **`⚠ BOUND … NOT RUN`** |

**The neuter was validated before being trusted**, independently of r2: the neutered copy's own
`--self-test` goes **119/119 → 104/119**, reproducing r2's number exactly.

## LOW 2 — accepted, with one correction to the finding

The deleted paragraph is now quoted inline in the Codex doc, exactly as row 65 quotes what it
replaced. ⚠ r2 calls it *"a substantive claim of Codex's own"* — it is not; that paragraph is the
**coordinator's** filing header, written by me. Codex authored nothing about the gap. The fix stands
for the same reason either way.

## The smaller notes, dispositions

* **`probe_kind` returns 1 on "could not run" and 0 on "ran and failed"** — real inversion risk, and
  now a third early-return joins it. Left as-is: nothing reads the value at any of the four call
  sites (verified again after this change), and inventing a convention no caller honours is the kind
  of unfalsifiable guard this repo files findings about. Recorded here rather than in a comment that
  would claim an invariant nothing enforces.
* **FOREIGN bound's NOT RUN branch depends on `fail=1` set 65 lines away** — the invariant still
  holds and now has more writers, all of which set `fail` via `report` or explicitly. Not changed.
* **`psql exit $mrc` would misname a Docker failure** — accepted as cosmetic; `db` returns
  `docker exec`'s status. Unchanged, and a dead container is already a CANNOT-RUN one layer up.
* **Pre-existing stale claims in `backlog-65-live-schema-drift-claude.md`** (lines 31, 33, and a
  `54/54` count at 94, already filed by an earlier round's Codex half) — agreed, out of scope, and
  agreed that only a reply closes it. Not touched by this branch.

## What I executed after fixing

    ./scripts/mutate-live-schema-check.sh                   56 ✓ / 0 ✗, exit 0 (control, unmoved)
    (d) POLICY undo desynced                                1 ✗, three siblings + bound NOT RUN
    (g) neutered gate + POLICY undo desynced                bound NOT RUN (was MUTATION SURVIVED)
    (f) partial land + desynced undo                        DID NOT LAND + bound NOT RUN
    neutered copy --self-test                               104/119 — the neuter bites
    M4_PHASE=post bash scripts/check-schema-gates.sh        73 ✓ / 0 ✗, exit 0, 15/15 green
