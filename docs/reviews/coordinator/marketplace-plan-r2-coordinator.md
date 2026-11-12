# Round 2 — `marketplace-plan` (the marketplace-inventory implementation plan, PR #562) — coordinator — NOT CONVERGED (Claude half), all folded

```yaml
round: 2
fixes_nontrivial: true
subject: marketplace-plan
halves:
  codex: gap
  claude: ran
findings:
  - {id: M1, severity: High, aim: deliverable, fix_induced: true, component: task-4-spike, disposition: fixed}
  - {id: M2, severity: High, aim: deliverable, fix_induced: true, component: task-4-spike, disposition: fixed}
  - {id: M3, severity: High, aim: deliverable, fix_induced: true, component: task-19-inventory-guard, disposition: fixed}
  - {id: M4, severity: High, aim: deliverable, fix_induced: true, component: task-11-detector-4, disposition: fixed}
  - {id: M5, severity: High, aim: deliverable, fix_induced: true, component: task-7-closure, disposition: fixed}
  - {id: m1, severity: Low, aim: deliverable, fix_induced: true, component: task-19-inventory-guard, disposition: fixed}
  - {id: m2, severity: Low, aim: deliverable, fix_induced: true, component: task-5-map, disposition: fixed}
  - {id: m3, severity: Low, aim: deliverable, fix_induced: true, component: task-11-detector-4, disposition: fixed}
  - {id: m4, severity: Low, aim: deliverable, fix_induced: true, component: slice-map, disposition: fixed}
```

REVIEW GAP: codex — alternation

Plan at `c316d97a`; the Claude half (`docs/reviews/claude/marketplace-plan-r2-claude.md`) filed in `65b0246a`:
0 BLOCKER, 5 MAJOR, 4 MINOR, **every one caused by the r1 fold**. Severity map as r1: MAJOR → High, MINOR → Low.

**Thrashing watch.** This is the first round whose findings came from the previous round's fix. If r3 again finds
fold-caused findings in one of the same components (`task-4-spike`, `task-19-inventory-guard`, `task-7-closure`,
`task-11-detector-4`), Phase 6 arms (`docs/dev-process.md`, *the arming condition is thrashing*). So this fold fixed
CAUSES and, where the spec allowed, REMOVED machinery rather than adding it: the unresolved recall phase and the
checkpoint's with-and-without branch are deleted (M3), and `--status` is dropped as the invocation check (M1).

**No `OWNER DECISION NEEDED`.** M3 follows spec D11's "only if" as written (quoted below). m3's "STATED deviation"
label is withdrawn because the spec never required tool names to be derived. m4 names the trigger the spec itself
gives (spec §7 item 8).

## Findings

- **M1 (High, FIXED; Task 4 Steps 1, 3, 5):** `--status` exits 1 on a free port, so the r1 step (a) would have
  produced a false NO-GO once H7 worked, and the r1 evidence "`--status` rc 0" was the owner's server answering.
  **Measured at fold** on a scratch copy of the three files (only `PORT` changed to a free port, fresh `HOME`,
  `python3 -I`): free port → `listening : NO`, rc 1; foreign listener → `listening : yes`, rc 0; `--help` rc 0.
  Step (a) is now `--help` alone. `--status` is run for the record, with an expected rc 1 on the freed port; rc 0
  there means H7 is not in effect, so the result is INCOMPLETE, never NO-GO. The Step 1 evidence line is corrected.
  **FAILS IF:** GO or NO-GO is decided by `--status`'s exit code.
- **M2 (High, FIXED; Task 4 Step 3 (b), Step 5, FAILS IF; Task 14 scripted half):** the leak check could not fail,
  and `start()` exits 0 when another server holds the port. **Measured at fold:** with a foreign listener up,
  `start()` printed `already serving on …` with rc 0. With the port free and a sentinel page seeded, it printed
  `serving <scratch HOME>/explainers`, the world pidfile's pid equalled `lsof -t` for the listener, and `GET /`
  (200) named the sentinel. With the foreign listener up, the world's `--stop` printed `not running` and the
  listener survived, so `--stop` can never signal the owner's process. GO now requires all three conditions:
  (i) start says `serving <world HOME>/explainers`; (ii) the world pidfile pid is the 7391 listener; (iii) `GET /`
  names a seeded sentinel token. Any one failing gives INCOMPLETE. Task 14's serve counts as `operation_ok` only
  under the same three. **Port route:** the script has no port flag and reads no port from the environment
  (`os.environ` is consulted only for `SRC_ROOT_ENV`, `explainer-serve.py:658`). *Evaluate, never repair* forbids
  adding one, so 7391 plus H7 plus the three-part check is the least-invasive route, and it is stated in the plan.
  **FAILS IF:** GO is recorded with `already serving` in start's stdout, a pidfile/listener pid mismatch, or a
  `GET /` body without the sentinel.
- **M3 (High, FIXED by REMOVAL; Tasks 18, 19, 21, 22, H1):** the r1 fold's unresolved `"1-if-feasible"` phase made
  the checkpoint exit rc 2 with no downstream exit. Spec line 145 (D11): *"Recall is in phase 1 **only if** (a) it
  is useful to a stranger whose memory corpus starts **empty**, and (b) our own corpus passes the owner's
  **content review** (C5's corpus half). Either one failing moves (1) to 'later'."* Spec line 1205 expects the
  corpus row to end at *"`C5: unanswered — blocked on the content review`"*. So under "only if", the phase is `"1"`
  exactly when `a` is true AND `b` is `"pass"`, and `"later"` otherwise, with the reason (`pending H1`,
  `probe CANNOT RUN (H2)`) kept as a note. The third state, the with-and-without branch and its CANNOT RUN are
  deleted, and `checkpoint_fires` is now one line over phase `"1"`. `row_errors` refuses any phase other than
  `"1"`/`"later"`, and a recall row at `"1"` unless `a` is true and `b` is `"pass"`. The H1 row and Task 18 now
  agree. If H1 or H2 lands later, Task 18's phase step, `check-inventory.py` and Task 21 re-run. The remaining
  rc 2 (no phase-1 rows, or unreadable inputs) has an explicit path:
  - Task 21: rc 1 or 2 means not final, slice F stops, fix and re-run, never "did not fire".
  - Task 22: final only on rc 0, or on rc 3 with H4 answered.
  - CI: rc 2 legitimately fails.
  **Extracted and run at fold** (scratch, `python3 -I`): all asserts pass. The stated mutation
  (`== "1"` → `in ("1","1-if-feasible")`) fails an assert (mutant rc 1). The reviewer's realistic population
  (11 of 20 at ≥3×, 4 recall rows at `"later"`) now fires instead of raising. **FAILS IF:** Task 22 marks the
  inventory final while `check-inventory.py` exits 1 or 2 (now in Task 22's FAILS IF).
- **M4 (High, FIXED; Task 11):** `check-deploy-freshness` is not a guard. **Measured at fold:** `scripts/<stem>.py`
  exists for `check-docs`, `check-producer-enumeration`, `check-roadmap-consistency`, `check-selftest-counts` and
  `check-test-counts`, and is ABSENT for `check-deploy-freshness`. `brief/SKILL.md` is unchanged since
  `2f5e3f3d`. The whole-file extras are now exactly `check-selftest-counts` and `docs/dev-process.md`. Spec line
  842 is quoted: *"a historical comment naming a guard is **not** an invocation"*. So is §5 rule 1: a mention
  candidate is reported separately. Line 78 is therefore excluded twice: its name has no file, and a historical
  sentence naming a real guard would be a mention candidate. New adjacent negative:
  `check-deploy-freshness … is not a guard-name item` beside `check-selftest-counts … is`. **FAILS IF:** the
  whole-file case names `check-deploy-freshness`, or omits either extra.
- **M5 (High, FIXED; Task 3 staging, Task 7 closure table):** a missing shared contract was filed `external`.
  - The closure table now splits read edges. A read edge that resolves inside the package's own source tree (a
    relative `../shared/…` path, or a path under `.agents/skills/`) is a member, or a **gap** when absent, exactly
    like an executable edge. Only a `docs/…` read is `external`.
  - Task 3 now states that every `.agents/skills/<name>` directory, `shared/` included, maps to
    `<plugin>/skills/<name>`.
  - **Measured at fold** with the Task 3 probe plus a `skills/shared/contract.md` with no `SKILL.md`: `validate`
    rc 0 (two metadata warnings, none about `shared/`), `install` rc 0, and `skills/hello/../shared/contract.md`
    resolves in the installed tree.
  - **Re-measured:** `../shared/explainer-delivery.md` occurs 8 times across the five skills, and
    `explainer-delivery.md:165` is `brief-compose.py`'s only executable inbound edge.
  - New cases: `explainer-delivery.md dropped → closure red` beside its present-is-member negative, and a Task 3
    case that `shared/` lands at `<plugin>/skills/shared`.
  - **FAILS IF:** dropping `explainer-delivery.md` (count lowered) leaves `--closure` green.
- **m1 (Low, FIXED; Task 19):** the SHIP-versus-experiment rule is now applied by role, following spec §4's role
  table. An `entry-point` needs its own passing sidecar entry, and a missing entry refuses SHIP (so recall's
  entry-points, which tier A does not run, cannot be SHIP this milestone). A `library` is judged on the entry-point
  its `scenario` names (inherited C4); a library whose scenario names no entry-point id is refused. `data` is
  outside the rule (C4 struck). A library adjacent-negative case was added.
- **m2 (Low, FIXED; Task 5):** `components.json` gains `"packages": {name: {"channel": …}}`, and every
  `Component.package` must be a key there.
- **m3 (Low, FIXED; Task 11):** the source of `harness-tools.txt` is the COORDINATOR's tool list. The provenance
  limit is stated: it is a one-session view, and the calibration's tool item is a membership check. The "STATED
  deviation" label is withdrawn, because spec §5 item 4 does not require tool names to be derived. No owner
  decision is needed.
- **m4 (Low, FIXED; slice map, Task 4 Step 5, H7):** a Task 4 record of INCOMPLETE or NO-GO now splits Task 1 into
  its own PR, cherry-picked onto `mkt-d8-corrections` off `origin/master`. Spec §7 item 8 (lines 1180-1183):
  *"The observation that makes this bound FAIL: PR 1 open with ANY OF THE THREE corrections not yet committed …
  At that point the stall risk the owner accepted is live and the corrections should be split into their own
  PR."* Slice B does not merge on INCOMPLETE or NO-GO; it stays open until H7 or H3 resolves.
- **Wording note (no finding id; Task 9), fixed:** the vocabulary case now reads "an element EQUAL to
  supabase/gemini/fly, and one that STARTS WITH youtube-playlist". The structural case reads "no string literal
  EQUAL to a spec term", so `"fly.toml"` equals none of them.

**Backlog rows filed:** none.

Round 3 alternates: ONE half (Codex).
