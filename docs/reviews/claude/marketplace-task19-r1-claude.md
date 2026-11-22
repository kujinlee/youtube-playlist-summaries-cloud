# marketplace-task19 — round 1, Claude half

Subject: branch `marketplace-task19`, HEAD `19ce4ac2` (PR #618), plan Task 19 of
`docs/superpowers/plans/2026-11-11-marketplace-inventory.md`; `scripts/check-inventory.py`.

How I worked: the probes import `scripts/check-inventory.py` and call `row_errors` against the LIVE context
(`load()` of this worktree: the live map, scan-2026-11-17, sidecar, spec, practices), changing one field per row
(`scratchpad/task19/r1-claude-work/probe.py`, `probe2.py`). End-to-end exit codes come from fixture worlds run through
the CLI with `--root` (`world.py`, worlds under `r1-claude-work/w/`). Mutations were run in a FULL `git clone` of the
branch (`r1-claude-work/clone`, `node_modules` symlinked in).

## What I tried to refute and could NOT (no finding)

- **Every listed refusal fires.** I ran each one against a live-context row: a borrowed id
  (`ask-answerer:4:1` on brief-compose → `[ground-finding]`); empty `ids`, empty section, empty decision, `heading: null`
  (`[ground-empty]`); decision `D12` and `D` refused, `D1`, `D10`, `D11` resolve, `D1 becomes a working target…` and
  `D10. Every` refused (the match is exact, not a substring); heading `Effort (2)` refused (no substring match), and the
  right heading under the wrong section refused; section `11` refused; `9b / 9c`, `2`, `2b` resolve; an experiment
  ground naming another component's scenario refused, one with no `fail` refused (`A-script-ask-answerer-status`); a `c5`
  ground with C5 `pass` refused; empty and absent `rests_on` refused; kind `Finding` refused; route kind `plugin` and a
  route given as a bare string refused; practice_entry with no number, with the `## ` prefix, and with a doubled
  space refused, and the exact heading accepted; phase `1-if-feasible` refused; recall at `"1"` refused while
  `recall.a` is false and while it is the string `"true"`, accepted at `a: true, b: "pass"`; SHIP entry-point with
  `exercised: false` (hook-regen-backlog-page; and explainer-serve patched to `false` or `"true"`) refused, clean when
  patched to fully pass; SHIP library naming a failing entry-point, naming nothing, naming a library, with no scenario:
  all refused; `next_project_hours` 0, NaN and `True` refused; `inherited` with no scenario, measured C3 fail with no
  finding ground, memory-corpus SHIP with C5 `unanswered`, a data row with C4 `pass`, measured on effort (2): all
  refused.
- **Over-refusal.** I found none beyond C4 below. Only the spec's own §5 table ("no decision `D<n>` in §2 or §2b")
  explains why `D5`/`D7` are refused, and that is the spec's rule, not the guard's. The 12 live rows are clean
  (`check-inventory.py` on the live tree: 34 `[missing]` errors and nothing else, rc 1, which is what the plan says
  this task's live state must be).
- **Checkpoint and rank.** The plan's asserts are embedded verbatim (`_plan_asserts`). Fixture worlds: clean + fired →
  rc 3; clean + not fired → 0; row error + crossed threshold → 1 ("checkpoint was NOT computed"); missing scan + row
  errors → 2; newer scan beside the named one → 1 `[scan]`; practices file absent → 2; sidecar `components` a list → 2.
- **Tests and mutations.** `--self-test`: 149/149, rc 0. In the full clone,
  `check-plan-code.py --mutate . --only scripts/check-inventory.py`: `61 mutation(s), 61 killed, 61 attributed to the
  case each names, 0 survivor(s)`. `expected_mutations.py` pins 61 = the manifest's 61 entries.
  `check-shipping-sets.py --self-test` 140/140 (it holds the 360 pin) and `--closure` 0 gaps; `check-selftest-counts.py`
  rc 0 over 97 scripts; `check-fixture-variation.py` OK.
- **CI.** The one added `ci.yml` step runs `python3 scripts/check-inventory.py --self-test` and nothing else.

## C1 — MAJOR — a non-finite or negative cost estimate passes every rule and silently suppresses the D1 checkpoint

fix_induced: false

**Input.** A three-component fixture world (all plugin, phase 1, entry-points, NEEDS-WORK rows otherwise clean),
`inventory.json` written with the JSON literals Python's `json.loads` accepts:
`rows c0, c1 public_bar_hours: NaN, c2 public_bar_hours: 1` (all next_project_hours 1); a second world with
`next_project_hours: Infinity` on c0 and c1 (public 9); a third with c0 `public_bar_hours: -9`, c1 9, c2 1.

**Observed.**
```
--- nan-suppresses: rc=0   OK: 3 rows, 0 errors; the D1 checkpoint did not fire
--- inf-suppresses: rc=0   OK: 3 rows, 0 errors; the D1 checkpoint did not fire
--- neg-pub: rc=0          OK: 3 rows, 0 errors; the D1 checkpoint did not fire
```
Row-level: `row_errors` returns `[]` for `public_bar_hours` NaN, `-5`, and `next_project_hours` `inf`
(`_num` accepts any float; the only value test is `nxt > 0`, which NaN fails but `inf` passes, and `pub` has none).

**Expected.** A cost that is not a finite, non-negative number is not an estimate (§2b: "a cost with either estimate
missing"), so it is a `[cost]` row error and rc 1. Instead each such row counts as "not over 3×" (`nan >= 3` and
`9 >= inf` are False), so the owner's checkpoint reports "did not fire" with rc 0 on an inventory that never gave it a
number. That is the fail-open the mandate's item 4 names: a malformed row producing rc 0.

**Proposed fix.** In `row_errors`, replace `_num(pub) and _num(nxt)` with a test that also requires
`math.isfinite(v) and v >= 0` for both (keep `nxt > 0` as `[next-project]`). Add the NaN-public and Infinity-next
cases beside a finite control, and a mutation that drops the finiteness test.

## C2 — MAJOR — a row missing a whole field, or with an out-of-vocabulary `harvest`, passes; `harvest: "Practice"` escapes the backlog #696 (c) rule

fix_induced: false

**Input.** Same fixture world, rows otherwise clean and not firing:
(a) row c2 with the `criteria` key deleted; (b) row c2 with `harvest` and `practice_entry` deleted;
(c) row c2 with `harvest: "Practice"`, `practice_entry: "nonsense"`. Live-context row probes: brief-compose with
`harvest: "bogus"`; brief-compose with `criteria: {"C1": "bogus"}`; memory-corpus SHIP, C4 `struck`, **C5 key absent**.

**Observed.**
```
--- rows-missing-field: rc=0         OK: 3 rows, 0 errors; the D1 checkpoint did not fire
--- no-harvest: rc=0                 OK: 3 rows, 0 errors; the D1 checkpoint did not fire
--- harvest-Practice-bad-entry: rc=0 OK: 3 rows, 0 errors; the D1 checkpoint did not fire
harvest bogus: []      criteria bogus: []      corpus ship C5 missing: []
```

**Expected.** Spec §4c fixes the harvest axis to `practice · none`, and §7 item 9b requires "for every component, a
`harvest` field". The guard validates `verdict`, `grade`, `phase` and (for #696 a) route `kind` against their
vocabularies, but not `harvest`, so the practice rule (`row.get("harvest") == "practice"`) is bypassed by any spelling
that is not exactly `practice` — the same hole #696 (a) closed for routes. A row with no `criteria` at all carries a
verdict over five criteria it never states, and passes; with no C5 key, memory-corpus can SHIP although its content
review was never answered (§7 item 11's rule tests `== "unanswered"`, so absence passes). Mandate item 4: a row
missing a whole field must never produce rc 0.

**Proposed fix.** Add `[harvest]`: harvest must be one of `("practice", "none")`; add `[criteria]`: `criteria` must be a
dict holding C1–C5, each from the spec §4 value set (`pass`/`fail`/`unanswered`/`struck`, whichever §4 enumerates);
make `[corpus-c5]` refuse a SHIP whose C5 is anything but an answered value (or rely on the new `[criteria]` rule). One
case each with an adjacent clean row, and a mutation per rule.

## C3 — MINOR — a non-dict row, or an unhashable field value, crashes with a traceback instead of a named error

fix_induced: false

**Input.** Fixture world with `rows: [<three clean rows>, 42]`; live-context probes with `route: {"kind": ["x"]}`,
`practice_entry: ["x"]` (with `harvest: "practice"`), `rests_on: [{"kind": "finding", "ids": [{"a": 1}]}]`.

**Observed.** `row-not-dict: rc=1` with `AttributeError: 'int' object has no attribute 'get'` at
`inventory_errors` (`ids = [r.get("id") for r in rows]`); the three probes raise
`TypeError: cannot use 'list' as a dict key` / `… as a set element` / `cannot use 'dict' as a set element`.

**Expected.** Not fail-open (rc is 1 by Python's uncaught-exception exit), but it is rc 1 by accident rather than by the
ranking, it prints no `<id>: [<rule>]` line, and the crash stops every other row's errors from being reported. The
module promises "Every error is printed as `<row id>: [<rule>] <why>`".

**Proposed fix.** Refuse a non-dict row as `[shape]` before the other rules, and guard the three membership tests with
`isinstance(..., str)` (route kind, practice_entry, each finding id), reporting them under their existing rule tags.

## C4 — MINOR — "the entry-point its scenario names" is the text before the first `:`, which both under- and over-refuses

fix_induced: false

**Input.** Live context with the sidecar patched so explainer-serve fully passes (`pass_conditions["1"] = "pass"`),
SHIP library rows:
(a) page-chrome, scenario `explainer-serve: also brief-compose (failing)`;
(b) page-chrome, scenario `tier-A scripted: explainer-serve page` (the plan's own scenario wording style);
(c) check-rc-contract (recall package), scenario `explainer-serve: x`.

**Observed.** (a) `[]`; (b) `[ship-experiment] … names no entry-point component id`; (c) `[]`.

**Expected.** The plan refuses "a library whose `scenario` names a failing entry-point" and one that "names no
entry-point component id". (a) names a failing entry-point and is accepted; (b) names a passing one and is refused;
(c) accepts a recall library backed by a comprehensibility entry-point from a different package, which cannot
exercise it (§4: C4 is inherited from the entry-point that uses the library). The prefix convention is documented
in the module docstring but not in the plan, so the row author has no way to know it. The guard checks resolution,
not bearing, so this is MINOR.

**Proposed fix.** Either state the `<entry-point id>: <description>` convention in the plan, the spec §4 role table, or
both, or match every component id the scenario contains and refuse if any named entry-point fails. In either case,
require the named entry-point's package to equal the library's.

## C5 — MINOR — the sweep-costs provenance note gives the wrong case count

fix_induced: false

**Input.** `grep -n "144\|149" scripts/sweep-costs.json scripts/check-inventory.py`.

**Observed.** `sweep-costs.json:16 … self-test 0.13 s locally over 144 cases`; `check-inventory.py:7 … --self-test  # 149 cases`;
the self-test prints `149/149`.

**Expected.** The note's count matches the suite as committed: 149 cases.

**Proposed fix.** Change the note to 149, or drop the number from it.

VERDICT: NOT CONVERGED
