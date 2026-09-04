# Code review round 3 — Claude half — scoped to round 2's fix

**Subject:** commit `11512f58` — `verdicts_are_trustworthy`, `check()`'s copy of the contract,
`evidence()`'s `NOT RUN` rendering, the plan-mode printer gate, and the two new self-test cases +
one new / one retargeted mutation in `scripts/mutations/check-plan-code.json`.
**Date:** 2026-09-03. **Verdict:** 2 Blocking, 2 High, 0 Medium, 1 Low.

Everything below was **executed**. Throwaway scripts live outside the repo, under
`…/566236fc-…/scratchpad/`; `git status --porcelain` is empty before and after.

---

## 🔴 B1 — `check()` reports `trustworthy: True` over a run whose control was RED before any mutation. The sibling producer refuses the identical situation.

`mutate_delivered` treats a red control as fatal and returns before a single mutation is applied
(`scripts/check-plan-code.py:673-677`):

```
        if report:
            return False, report, ev
```

with the message *"Every verdict below would be an artefact. Treat this as NOT CHECKED."*

`check()` runs the same control — each file's `--self-test`, `scripts/check-plan-code.py:872-884` —
records `rc`, appends a report line, sets `ok = False`, **and keeps going**. Round 2 then added
`ev["trustworthy"] = verdicts_are_trustworthy(...)` at `:890`, so the path that previously merely
printed an ungated tally now emits a **positive assertion** that the tally may be read as a coverage
verdict.

**Executed** (`t1_control_red.py`) — a plan whose assembled suite exits 1 before any mutation:

```
=== B. CONTROL RED — the plan's own suite is red BEFORE any mutation ===
ok: False declared: 1 TRUSTWORTHY: True
mutations: [{'name': 'the guard is deleted', 'caught': True, 'fails': ['the guard holds', 'two plus two'], 'measured': True}]
  ✗ scripts/x.py: --self-test exited 1
    [FAIL] two plus two: got 4 want 5
  mutations declared and run: 1, caught 1
    caught   the guard is deleted
FAILED — plan's copy only, NOT compared: 1 file(s), 1 mutation(s), 0 survivor(s)
```

**Stronger form** (`t2_noop_certified.py`) — the mutation edits a **comment**, changing no behaviour
at all, and the case its `expect` names is already red at control. It is certified end to end:

```
ok: False declared: 1 TRUSTWORTHY: True
mutations: [{'name': 'a mutation that changes NOTHING', 'caught': True, 'fails': ['the guard holds'], 'measured': True}] survivors: []
  mutations declared and run: 1, caught 1
    caught   a mutation that changes NOTHING
```

**The contrast, executed** (`t4_mutate_side.py`, `run_suite` stubbed to return rc 1 on the first
call, real repo as root):

```
=== mutate_delivered with a RED CONTROL (first run_suite -> rc 1) ===
ok: False declared: None trustworthy: False len(mutations): 0 run_suite calls: 7
report[0]: CANNOT RUN — control run of scripts/check-dashboard-entry.py exited 1 BEFORE any
mutation was applied. Every verdict below would be an artefact. Treat this as N…
```

**Why this is a defect in round 2's fix, not merely pre-existing.** The commit's own claim is *"ONE
contract, TWO producers."* The contract in `mutate_delivered` has **two** clauses — (a) every
declared mutation produced a real verdict, (b) the controls were green (`:673-677` before,
`:690-703` after, which sets `ev["trustworthy"] = False` explicitly). The extracted helper
`verdicts_are_trustworthy(m_muts, declared)` can only see clause (a); its signature has no access to
the control result. So the shared function holds half the contract, and the half it drops is the one
that stops an environmental red being read as a catch — which is the failure the *after*-control was
added to prevent in the other producer. This is the same shape as the finding round 2 existed to fix:
one producer holds the rule, its sibling does not.

The suite already has a case for this on the other side —
`'a RED control is refused, not reported as catches'` (`:1934-1936`), driven by `mutate_delivered`.
There is no counterpart for `check()`.

**Nothing pins the current behaviour.** Probe (`t10_fixprobe.py`): make `check()` AND the red
control, i.e. `ev["trustworthy"] = (not _control_red) and verdicts_are_trustworthy(...)` →
`164/164 passed`. So the repair breaks no existing case; it also earns no new one, which is B2.

---

## 🔴 B2 — every line round 2 added to `check()` and to the plan-mode printer can be deleted or inverted and the suite stays 164/164. CI runs both `--self-test` and `--mutate .`, so neither would catch a regression of this fix.

`EXPECTED_MUTATIONS["scripts/check-plan-code.py"]` rose 23 → 24. The one added mutation
(`'the evidence block calls a cannot-run SURVIVED again'`) covers `evidence()`. The retargeted one
covers the `measured` conjunct of the shared helper. **Nothing covers the rest of the fix.**

Four probes, each applied to a **copy** of the delivered file, each running the delivered
`--self-test` (`t5_uncovered.py`, `t8_more.py`):

| Probe (what a regression would look like) | Result |
|---|---|
| Delete `check()`'s `ev["declared"] = …` + `ev["trustworthy"] = …` entirely (`:889-890`) | `rc=0` **164/164 passed** |
| Hardcode `ev["trustworthy"] = True` after `run_mutations` in `check()` | `rc=0` **164/164 passed** |
| Flip `check()`'s default-deny init at `:845` to `"trustworthy": True` (fail **open**) | `rc=0` **164/164 passed** |
| Revert the plan-mode printer gate `:2227` to the pre-r2 unconditional `if True:` | `rc=0` **164/164 passed** |

The `--mutate` printer gate at `:2176` is in the same state (`if ev["trustworthy"]:` → `if True:`
→ `164/164 passed`); that one predates r2.

**Mechanical confirmation of the negative claim.** Every `trustworthy` read in `_self_test` —
`grep -n "trustworthy" scripts/check-plan-code.py` — is line `1928` (`_ev` from `mutate_delivered`),
`1996-1997` (`_ev6`, `mutate_delivered`), `2021` (`_ev8`, `mutate_delivered`), and `2030`/`2034`
(hand-built literal dicts passed straight to `evidence()`). An AST enumeration of `_self_test` finds
**40 calls to `check(...)`** and not one of them reads `declared` or `trustworthy`. Both the grep and
the mutation probes agree: `check()`'s contract has no falsifier.

The two new cases at `:2026-2036` build their dict by hand. They test the **renderer**. They never
execute the producer round 2 was fixing.

Per `docs/dev-process.md`, `--mutate .` **is what CI runs** and coverage "cannot shrink". A fix for a
defect that has recurred inside its own fix five rounds running has shipped with no red case standing
behind it.

---

## 🟠 B3 — `evidence()` is a consumer of `ev` that reads neither `declared` nor `trustworthy`. On a shortfall run the GENERATED block asserts full coverage.

AST enumeration of every read/write of the evidence dict (all 35 sites):

```
  896 evidence   READ  ev.get('tally', {})
  904 evidence   READ  ev['files']
  906 evidence   READ  ev['mutations']
  910 evidence   READ  ev.get('compared')
  919 evidence   READ  ev['mutations']
  920 evidence   READ  ev['mutations']
```

No `declared`. No `trustworthy`. Round 2 put both keys into `check()`'s dict and edited `evidence()`
in the same commit; the per-entry rendering was gated, the block-level count line was not.

**Executed** (`t3_shortfall.py`) — three declared mutations, one real, one with an anchor that is not
found (skip site 2), one with an empty `expect` (skip site 3):

```
ok: False declared: 3 trustworthy: False len(mutations): 1
  mutations declared and run: 1, caught 1
    caught   m1 real
```

console, correctly:

```
NOT MEASURED — plan's copy only, NOT compared: the mutation harness produced no coverage verdict
(1 of 3 declared mutation(s) produced a verdict). Treat this as NOT CHECKED.
```

Probes against the block text: `'3' in block: False`, `'m2' in block: False`, `'m3' in block: False`,
`'NOT' in block: False`, `'MEASURED' in block: False`.

The line reads **"mutations declared and run: 1"**. Three were declared. The word *declared* is
false, the two dropped entries are invisible, and `caught 1` of `1` reads as complete coverage. This
block carries the header `GENERATED by scripts/check-plan-code.py — do not edit by hand.`, is pasted
into the plan, and outlives the console line that carries the truth. `--verify-evidence` re-derives
the same block, so it certifies it as *fresh* without ever noticing it is wrong.

**High rather than Blocking:** on every shortfall path measured, `ok` is `False` and the final console
line says `NOT MEASURED`, so no gate reports a success it did not earn *at run time*. The damage is a
durable artifact that misstates coverage. Combined with B1 it is worse: there, the block prints
`caught` with `trustworthy: True`.

---

## 🟠 B4 — the cardinality conjunct, the half the comment says makes enumerating the skip sites unnecessary, has no red case.

`scripts/check-plan-code.py:610-613`:

> `run_mutations` skips without appending at three places — unknown target file, anchor not
> found, empty `expect` — so `len(ev["mutations"]) < declared` catches all three, **and any
> fourth skip added later, without anyone having to enumerate them again.**

Probe (`t8_more.py`) — delete that conjunct from the shared helper:

```
    return len(m_muts) == declared and all(...)   ->   return all(...)
[helper: drop the CARDINALITY half] rc=0 tail='164/164 passed'
```

So the property the comment leans on to *avoid* enumerating the skip sites is the one property the
suite cannot see. The two cases that do read `trustworthy` on a complete run both assert
`len(_ev["mutations"]) == _ev["declared"]` is **True** (`:1997`, `:2021`) — they exercise the
`measured` conjunct and the after-control override, never a shortfall.

Pre-existing: the conjunct arrived in `4c3d3390`; round 2 extracted it into the helper and retargeted
the mutation onto the helper's single return, which anchors on the whole line but reddens only via
the `measured` half. In scope because it is the load-bearing half of the function this round's fix
created.

---

## 🟢 B5 — the `is True` fail-closed clause is unguarded, and the comment credits the wrong construct for the property it names.

Probe: `m.get("measured") is True` → `m.get("measured")` (plain truthiness), in the helper **and** in
`evidence()`. Both `rc=0`, `164/164 passed`.

The docstring (`:379-381`, repeated at `:683-684`) justifies it: *"a future append site that forgets
the key yields None, which is not True, so the run is untrusted rather than trusted."* `None` is
falsy, so plain truthiness fails closed on exactly that case too — the fail-closed property for a
*forgotten key* is bought by `.get()`'s `None` default, not by `is True`. What `is True` actually
buys is rejection of a truthy non-`True` value (`1`, `"yes"`), which the comment does not mention and
no case exercises.

---

## Checked and correct

**The skip-site enumeration and the arithmetic that covers it.** AST walk of `run_mutations`
(lines 706-832, loop 720-831):

```
  CONTINUE 725   (unknown target file)          BREAK 742 (ambiguous anchor) -> src=None
  BREAK    748   (anchor not found) -> src=None CONTINUE 751 (src is None)
  CONTINUE 782   (after the rc==2 append)       CONTINUE 808 (empty `expect` list)
  APPEND ev_muts 776 (rc==2, measured False)    APPEND ev_muts 817 (the normal verdict)
```

Exactly three skip sites reach `continue` without appending — 725, 751 (reached from 742 or 748), and
808 — matching the comment. Every iteration appends to `ev_muts` **at most once** (776 is followed
unconditionally by the `continue` at 782). Therefore `len(m_muts) ≤ declared` with equality iff no
mutation was skipped, and both producers pass the *same* list to `run_mutations` and to `len(muts)`
(`:678`/`:682` and `:883`/`:889`). The arithmetic does catch all three, as claimed — it is only
untested (B5).

**The `declared is None` escape at `:2227` is not reachable with mutations attempted.** AST
enumeration of every `return` in both producers against the `ev['declared']` assignment:

```
check:            ev['declared'] assigned at [889]; run_mutations called at [883]
   return 891  declared-set-before=True   mutations-attempted-before=True
   return 848  declared-set-before=False  mutations-attempted-before=False   'return False, report, ev'
mutate_delivered: ev['declared'] assigned at [682]; run_mutations called at [678]
   return 617  False/False    return 657  False/False    return 677  False/False
   return 703  True/True
```

The single `declared is None` path out of `check()` is the `not files` early return. Executed
(`t9_escape.py`): `ok False, declared None, trustworthy False, mutations 0` →
`FAILED — plan's copy only, NOT compared: 0 file(s), 0 mutation(s), 0 survivor(s)`. A truthful zero.

**Both new self-test cases are non-vacuous.** Falsified on copies (`t7_falsify.py`):

| Break | Result |
|---|---|
| revert `evidence()` to `"caught  " if m["caught"] else "SURVIVED"` | `163/164` — RED: `a cannot-run renders as NOT RUN, never as SURVIVED` |
| render every uncaught entry as `NOT RUN` | `162/164` — RED: `...and a REAL survivor still renders as SURVIVED` **and** `the evidence block names a SURVIVOR as such` |

Each case goes red on its own property, with a legible message. The second case is load-bearing — it
is the one that stops the fix over-correcting.

**The new and the retargeted mutation each redden via exactly the case they name.** Applied by hand
to copies, delivered `--self-test` run, red case names parsed from `[FAIL]` lines (`apply_mut.py`):

```
[the evidence block calls a cannot-run SURVIVED again]                rc=1  163/164
    RED: 'a cannot-run renders as NOT RUN, never as SURVIVED'         -> 1 exact  OK
[a cannot-run mutation counts as a verdict again, …]                  rc=1  163/164
    RED: 'a TIMED-OUT mutation is counted but is NOT a verdict'       -> 1 exact  OK
[the after-control stops invalidating the run, …]                     rc=1  163/164
    RED: '...and it is NOT trustworthy, though every declared mutation ran'  -> 1 exact  OK
[the control BEFORE the sequence is not checked]                      rc=1  163/164
    RED: 'a RED control is refused, not reported as catches'          -> 1 exact  OK
```

**The three count bumps agree with reality.**

```
python3 scripts/check-plan-code.py --self-test        -> 164/164 passed
grep -n "self-test .* cases" scripts/check-plan-code.py -> ":8  # 164 cases"
python3 -c "json … len" scripts/mutations/check-plan-code.json -> 24 entries, all
        scripts/check-plan-code.py, no duplicate names   (EXPECTED_MUTATIONS says 24)
python3 scripts/check-plan-code.py --mutate .
        -> OK — delivered scripts mutated: 7 file(s), 165 mutation(s), 0 survivor(s)   exit 0  (4m15s)
grep -rn "164\|165" docs/dev-process.md                -> no hits; the spine quotes neither
check-selftest-counts / check-docs / check-guard-coverage / check-ratchet-contract /
check-review-rounds                                    -> all OK
```

**`--mutate .` does not touch the repo.** `git status --porcelain` empty immediately after the
4-minute run.

**F2-S3 holds for plan mode — byte-identical, executed.** `pre_r2.py` = `git show
7166921f:scripts/check-plan-code.py`; both modules imported side by side and `main()` captured on the
same clean plan (`t6_f2s3.py`):

```
BARE identical: True
EVIDENCE identical: True
OK — plan's copy only, NOT compared: 1 file(s), 1 mutation(s), 0 survivor(s)
```

**No false-alarm path found.** `trustworthy` can go `False` only via: a cardinality shortfall (a
genuine skip at one of the three enumerated sites), a `measured is not True` entry (a genuine
`run_suite` rc 2), the `mutate_delivered` after-control override at `:697` (a genuine tree change), or
the default on an early return where `run_mutations` was never called — and that last one is exactly
the `declared is None` set, escaped by the plan printer and printed truthfully as `NOT MEASURED` by
the `--mutate` printer. A plan declaring zero mutations gives `verdicts_are_trustworthy([], 0) ==
True`, which is correct: nothing was skipped. I found no run that measured everything and was
reported untrustworthy.

**No consumer of the evidence dict outside this file.** `grep -rn "check-plan-code\|check_plan_code"`
over `scripts/ .github/ docs/dev-process.md`: `check-selftest-counts.py` imports `count_drift` and
`child_env` only; `ci.yml` invokes `--mutate .` and `--self-test` as processes; the rest are prose
references. The dict never leaves the module.

---

## Not checked

Severity is **unpriced** for everything here — I did not run it.

- **`--mutate` mode byte-comparison against pre-r2.** The current run prints
  `OK — delivered scripts mutated: 7 file(s), 165 mutation(s), 0 survivor(s)`, and `git show
  11512f58` shows no change to the `--mutate` printer (`:2172-2194`), so F2-S3 holds there by
  **diff inspection, not execution**. A pre-r2 `--mutate .` run is another ~4 minutes.
- **A real (non-stubbed) suite timeout.** Every `measured: False` path I exercised used a stubbed
  `run_suite` returning rc 2, as the suite itself does. `SUITE_TIMEOUT` was never allowed to elapse.
- **`--verify-evidence` against a plan carrying a stale block from an untrustworthy run.** I
  established that `verify_evidence` reads only `ev["compared"]` and re-derives via `evidence()`, so
  it cannot distinguish; I did not build the two-run staleness scenario end to end.
- **Whether the B1 repair I probed is the right shape.** I showed only that adding a control clause to
  `check()`'s `trustworthy` leaves the suite at 164/164 — i.e. nothing pins the current behaviour.
  Whether `check()` should refuse *outright* like `mutate_delivered`, or merely withhold trust, is a
  design call I did not make.
- **`check-vocabulary-collisions.py`, `check-anchors.py`, `check-dashboard-entry.py`.** Not run; the
  r2 commit message reports them green and I had no reason from this scope to re-measure.

---

## Verdict

Round 2 fixed the instance it was given — `evidence()` no longer prints `SURVIVED` over a cannot-run,
and `check()` now carries a `trustworthy` key — and both of those are real, both are covered by a
mutation, and both were verified here. But the round repeated its own diagnosis in a new place:

- the extracted "one contract" holds **one of the contract's two clauses**, and the clause it drops is
  the one that stops an environmental red reading as a catch — so `check()` now *asserts*
  trustworthiness over a run whose control was red, which is a positive false claim where there was
  previously only an ungated print (**B1**);
- the fix itself has **no falsifier**: four separate ways to delete or invert round 2's new code all
  leave `--self-test` at 164/164, and CI runs exactly that suite plus `--mutate .` (**B2**);
- `evidence()` was edited for this class and gated **per entry but not per block** (**B3**);
- and the conjunct the design leans on to avoid re-enumerating the skip sites is the one nothing
  measures (**B4**).

The positional-vs-semantic pattern the brief describes has not recurred — the arithmetic is genuinely
position-independent and I could not break it. What recurred instead is the *scope* pattern: the
named instance fixed, the sibling left, and the new rule shipped without a red case.

NOT CONVERGED
