# local-sweep-guard — round 1 — Claude half

Reviewed range: `origin/master...6b86435c` (branch `local-sweep-guard`, draft PR #400).

Method: read the whole diff. Ran `check-plan-code.py --self-test` with `CI` unset and with
`CI=true`. Ran the real `--mutate .` locally (with and without `--only`). Applied each of the 11 new
manifest entries, plus 6 more I wrote myself, to an independent copy of the full `HARNESS_TREE`
under the scratchpad. Each was run under BOTH `CI` states, over a control that was green under both
(235/235). Ran CI shard 10/12 locally with `CI=true`. Timed `check-main-drivable.py --self-test` on
master, on the branch, and on master with only this branch's `check-plan-code.py` swapped in.
Resolved every manifest anchor in the repo against the branch tree. I made no git writes, and the
worktree was still clean at the end. Everything marked EXECUTED was run.

---

## H1 — High (Blocking) — the branch puts `check-main-drivable.py`'s suite past `SUITE_TIMEOUT`, so EVERY shard's control fails and the whole CI sweep is NOT MEASURED

**Where:** `scripts/check-plan-code.py` self-test block at `:3529-3538` (the three
`main(["--mutate", str(_r)…])` calls inside the `globals()["LOCAL_SWEEP_BUDGET"] = 0` rebind);
`SUITE_TIMEOUT = 120` at `:108`.

**EXECUTED, `CI=true python3 scripts/check-main-drivable.py --self-test` (all 438/438 pass):**

| tree | wall time |
|---|---|
| `origin/master` | **47.3 s** |
| branch | **2 m 28 s** (2 m 14 s with `CI` unset) |
| master + ONLY the branch's `check-plan-code.py` | **2 m 16 s** |
| that, with the three `main(["--mutate"…])` calls at `:3535-3538` replaced by constants | **49.1 s** |
| that, with only the `for _argv …: main(_argv)` loop neutralised instead | 2 m 13 s (no effect) |

So `check-main-drivable`'s call-site analysis spends about 85 s on those three call sites. A plausible
cause is its rebind route, because they sit inside a `globals()[…]` substitution. That mechanism is
my inference. The attribution to those three lines is measured.

**Consequence, EXECUTED:** `CI=true python3 scripts/check-plan-code.py --mutate . --shard0 9/12`
gives:

```
✗ CANNOT RUN — control run of scripts/check-main-drivable.py did not prove the suite works (exit 2) …
  CANNOT RUN — scripts/check-main-drivable.py --self-test did not finish in 120s. NOT CHECKED.
NOT MEASURED — … — measured over shard 10 of 12 (round-robin)
rc=1
```

`check-main-drivable.py` carries 183 entries, and round-robin spreads them over all 12 shards. Every
shard therefore pays that control and fails it. This matches PR #400's live checks:
`mutation-sweep (2,3,4,6,7,9,10,11,12)` were already `fail` at about 3 min each, with (1,5,8) still
pending. I could not read those logs because the run was still in progress, so the CI-side cause is
inferred from the local reproduction. The timing and the symptom agree.

**Fix direction:** keep the wiring cases, but do not make `check-main-drivable` pay for them. Two
options:
- drive them through a world that does not need the global rebind (for example, pass the budget
  through argv or a parameter);
- move them into a subprocess case.

Then re-time `check-main-drivable --self-test` against master. ⚠ Separately, its 47 s on master was
already 39 % of the 120 s timeout. Nothing warns as that margin shrinks.

## H2 — High — four EXISTING mutation entries are orphaned by this diff (anchor NOT FOUND)

**EXECUTED:** I resolved all 2,041 entries against the branch tree. Four anchors match 0 times,
and each matched once on master:

| entry (`scripts/mutations/check-plan-code.json`) | stale anchor | shard /12 |
|---|---|---|
| `:239` "the --mutate REFUSAL leaks a survivor count (r4 B1)" | `print(not_measured_line(verdict, shard))\n        return 0 if ok else 1` | 8 |
| `:514` "--mutate stops supplying the reporter…" | `mutate_delivered(mroot, progress=stderr_progress,\n …shard=shard)` | 7 |
| `:1082` "#217: the TALLY line stops naming its slice…" | `… + f" — measured over {shard_label(shard)}")` | 2 |
| `:1096` "#217: the NOT-MEASURED line stops naming its slice" | `return f"NOT MEASURED — {nm.reason} — measured over {shard_label(shard)}"` | 3 |

`run_mutations` reports each as "anchor NOT FOUND" and sets `ok=False`. The cardinality clause then
refuses a `Measured`, so shards 2, 3, 7 and 8 would be red even after H1 is fixed. H1 masks this
today.

These are not arbitrary entries. Two of them guard the exact property this branch extends: a verdict
line names its slice. The dashboard entry says the 11 new entries were verified "in memory — the full
128-entry run is itself past the budget, so it is CI's". That is the gap: the 117 existing entries
for this file were never re-resolved against the edited file. This anchor check needs no suite and
runs in under a second.

## M1 — Medium — the `--only` wiring in `main()` is unprotected; one deleted argument makes a narrowed run print "measured over the WHOLE manifest" with the suite green

**Where:** `scripts/check-plan-code.py:6160` (`only = frozenset(a.only) …`), `:6162`
(`only=only` passed to `mutate_delivered`), `:6199` (`print(tally_line(ok, verdict, shard, only))`),
`:6210` (`print(not_measured_line(verdict, shard, only))`).

**EXECUTED:** I applied each mutation to the independent copy and ran `--self-test`. All four
SURVIVE (235/235) under both `CI` states:

- G1: drop `only` from the `tally_line` call
- G2: drop `only` from the `not_measured_line` call
- G3: `only = None`
- G4: drop `only=only` from the `mutate_delivered` call

**G1 live, EXECUTED:** `--mutate . --only scripts/check-merge-ready.py` on the G1 copy prints:

```
OK — delivered scripts mutated: 1 file(s), 16 mutation(s), 16 killed, … 0 survivor(s) — measured over the WHOLE manifest
rc=0
```

That answers review question 2 with "yes": a one-token regression yields a whole-manifest-reading
green. HEAD's commit says "the --only label is asserted on both verdict printers". That is true of
`tally_line` and `not_measured_line` as functions (cases at the `:4708-4713` area), and false of the
call sites in `main`. This is the shape described by *unit coverage does not compose — mutate the
CALL SITE*.

G3 and G4 fail toward doing more work: a full run, which the budget then refuses locally. G1 and G2
fail toward a false whole-manifest reading. One case that drives
`main(["--mutate", fixture, "--only", X])` and asserts the stdout tail would kill all four. ⚠ Per H1,
do not add that case as another `main` call under a global rebind.

## L1 — Low — `CI` is a persistent environment-variable bypass, contrary to "never an environment variable … cannot persist"

**Where:** `:6159`, `budget = None if (os.environ.get("CI") or a.allow_long_local) …`; the comment
at `:110-117`; `dev-process.md` ("it cannot persist").

`export CI=1` in a shell profile, or a tool that sets `CI`, silently disables the guard for every
later run. `CI=false` and `CI=0` are truthy too. The claim is true of the flag and not of the guard.
The CI side is fine: the only `--mutate` caller is `ci.yml:1154`, on GitHub runners, which always set
`CI=true`. `child_env` inherits `os.environ`, so nested suites see the same value. Suggested fix:
state the `CI` escape in the prose, and consider `GITHUB_ACTIONS == "true"` as the CI test.

## L2 — Low — the budget is checked before control greenness, and "refusing here costs one suite" is unprotected

**Where:** `:2504-2508`. A slow, red control reports `REFUSED LOCALLY … NOTHING WAS MEASURED`
instead of `CANNOT RUN — control … did not prove the suite works`, so the more important fact is
hidden.

**EXECUTED:** G5 moves the check to after ALL controls, using `shard_muts`. It SURVIVES the suite
under both `CI` states. So the comment's "as soon as it is known to be blown … costs one suite, not
all" property is mechanism-only. The 12 s claim depends on it. The estimate also cannot see that a
mutated suite may run far longer than its control, up to 120 s each on timeout. It is a floor, not
a bound. That is acceptable for a cost guard, and the prose should not call it "the cost model the
harness actually has" without that caveat.

## L3 — Low — `--only` spelling and the diagnostic's leading word

`--only check-merge-ready.py` and `--only ./scripts/check-merge-ready.py` are refused with
"CANNOT RUN … which no manifest targets" (EXECUTED). That is correct and loud. But the help text
says `SCRIPT`, and the refusal hint says `--only <script>`. Neither says the manifest's
`scripts/…` form is required. The bad-name path also exits **1** while its text says CANNOT RUN.
That is consistent with the file's existing control-red path, so this is a note, not a defect.

A green `--only` run's line begins `OK —`, and the DIAGNOSTIC label is at the far end of a 190-char
line. A title is scanned, not read. Consider leading with the slice.

## L4 — Low — stale count in the dashboard entry

`docs/dashboard-entries.md:17537` says "233 cases". The suite reports **235/235** (EXECUTED), and
the docstring says 235.

---

## Verified true (EXECUTED)

- `--self-test`: 235/235, rc 0, with `CI` unset (6.3 s) and with `CI=true` (5.3 s).
- The unscoped local `--mutate .` is refused after **12.4 s**, rc 2, at target 12/68, naming
  `begin-plan.py: 60 mutation(s) x 4s`. Nothing is printed on stdout.
- `--only scripts/check-merge-ready.py`: **4.7 s**, 16/16 killed and attributed, rc 0, labelled
  DIAGNOSTIC. The backlog's "16" is correct.
- All **11** new entries die by the case(s) they name, under both `CI` states, over a 235/235
  control in an independent `HARNESS_TREE` copy. No new entry passed for an ambient reason: extra
  reds were only the sibling label cases of the same function.
- Self-test environment hygiene: `CI` and `LOCAL_SWEEP_BUDGET` are both restored in `finally`
  (`:3539-3543`). The `CI` pop happens before the `try` and cannot raise.
- Whole-manifest invariants (EXPECTED_MUTATIONS in both directions, duplicate names/anchors,
  home-escape scan over targets and replacements) all run before `--only` narrows anything
  (`:2407-2467`). The control runs over exactly the narrowed targets (`:2472`), so the green-control
  requirement holds for the slice.
- `--only` without `--mutate`, `--allow-long-local` without `--mutate`, and `--only` with a shard
  are each refused with rc 2 and the sentence asserted.

VERDICT: NOT CONVERGED
