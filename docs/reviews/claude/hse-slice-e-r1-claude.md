Reviewed head: d381972481b830c921199d150f091d5333f5f879

# Marketplace slice E, round 1 — Claude half

Subject: `git diff origin/master...HEAD` (3 commits, 50ac3e65..d3819724): `scripts/mkt_seed_repo.py` + manifest and
wiring, `docs/marketplace/experiment-tier-a.{md,json}`, `experiment-tier-b.md`, `spend-log.md`, the
`check-shipping-sets.py` Phase 6 re-pin. Plan Tasks 13-15 of `docs/superpowers/plans/2026-11-11-marketplace-inventory.md`,
graded against spec §6 (`docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md`).

## What I ran

- `python3 scripts/mkt_seed_repo.py --self-test` → `12/12 self-test cases passed` (2.4 s).
- `python3 scripts/check-shipping-sets.py --self-test` → `140/140 self-test cases passed` (1 m 57 s).
- Determinism, outside the repository (scratchpad): `--out s1`, sleep 2 s, `--out s2` → both HEAD
  `3492d62a20b2140ffd1bc9726910989a03c915b3`; `known-facts.json` identical after normalising the repo path; 5 commits
  with author/committer dates 2026-03-01..05 09:00 +0000. Matches the record's `3492d62` (tier-A md:105). Re-seeding a
  non-empty dir, and seeding onto a FILE, both rc 2 `CANNOT RUN`.
- Control, on copies of `mkt_seed_repo.py` + `fixture_git.py` outside the repository: all 5 manifest mutations go red
  on their named case. Of 5 extra mutations, 3 go red (a `.claude/` dir, a dirty tree, a drifted check-docs line) and
  **2 stay 12/12 green** — see M1.
- Edge re-pin: ran `exec_edges` over every tracked `.py` with origin/master's reader on an origin/master checkout
  (344, `2cfb6a85d091b861`) and with HEAD's reader on HEAD (347, `1c64fcc5c8bd9add`). The diff is exactly the three
  lines the comment names (`check-selftest-counts.py -> mkt_seed_repo.py`, `mkt_seed_repo.py -> check-docs.py`,
  `mkt_seed_repo.py -> fixture_git.py`); nothing lost. **The re-pin adds only this diff's edges.**
- Record/JSON agreement: parsed all 33 Markdown matrix rows and compared `exercised`, `scenario`, `operation_ok` and
  conditions 1-5 with the sidecar — **0 disagreements**; the 33 ids equal the 33 `components.json` rows with
  `package == "comprehensibility"`; every unexercised row is either a `library` role or one of the 5 hooks, as stated.
- Recounts: 14 exercised / 19 not ✓; 9 exercised scripts, 7 with `operation_ok: no` ✓; S1 "6 of the 9" ✓
  (regen-pages, goal-tree, gen-backlog/features/goals-page, gen-dashboard); `brief` items 12 = 8 non-empty + 4 empty ✓;
  supplementary marks 6/4/2/0 ✓; tier-A cost 0.068+0.276+0.076+0.220+0.054+0.115 = 0.809 → "0.81" ✓; tier-B
  0.130+0.329+0.216+0.360+0.067 = 1.102 → "1.10" ✓; spend-log rows agree with both.
- Diagnosed defects, by source:
  - **S1 holds.** `scripts/gen-backlog-page.py:82-83` (`REPO = pathlib.Path(__file__).resolve().parent.parent`;
    `BACKLOG = REPO / "docs/backlog.md"`); `scripts/regen-pages.py:122-123` (`ROOT = SCRIPTS.parent`) and `:423`
    (`--git-common-dir` run in `ROOT`); `scripts/goal-tree.py:108,113`; `scripts/gen-features-page.py:66`;
    `scripts/gen-goals-page.py:59`; `scripts/gen-dashboard.py:21`. Every one roots the project at the script's own
    parent, never the CWD.
  - **S2 holds.** `scripts/brief-compose.py:789-800` (`find_source`): no `~/explainers` → `SystemExit("… run
    /explain-diff once first")`; no page with all of `TRAY_MARKERS` (`:77`) → `SystemExit("… Run /explain-diff once to
    produce one …")`. The package carries no tray template: `id="tray"` occurs in `scripts/` only in self-test
    fixtures (`brief-compose.py:1697,2161,2771`, `ask_answerer.py:1422`), and the hand-build path in
    `.agents/skills/shared/explainer-delivery.md:216-219` ends "Lift the `<script>` block byte-for-byte from an existing
    page" — the same circularity. `/explain-diff` is the advised bootstrap, and it delegates to the same
    `brief-compose.py` (`explain-diff/SKILL.md:140`).

## Findings

- **MAJOR — docs/marketplace/experiment-tier-a.md:67 (and experiment-tier-a.json `explainer-serve`):** pass condition 1
  is marked `pass` for `explainer-serve`, but spec §6 condition 1 is "the page is produced and served, **and the reader
  can ask a question inside it**". The page served was the experiment's own sentinel, and the record's own headline
  (md:9-10) says "no exercised run produced a page a reader can ask a question in", while S2 says no page can ever get
  a tray. `POST /questions` returning 200 proves the endpoint, not a page a reader can ask in. Input: the row's own
  evidence column. Observed: the only condition-1 `pass` in the matrix contradicts the headline. It should be `argued`
  (the server's half measured, the page half impossible) or `fail`; the same value is in the sidecar Task 19 reads.
- **MAJOR — docs/marketplace/experiment-tier-a.md:68, :9-10 (sidecar `ask-answerer.operation_ok: true`):** an
  inference stated as measured. The row says "`--once` … NOT run, so the useful operation is argued" and grades
  condition 3 `argued`, yet records `operation_ok: yes`; the headline then counts it as one of the 2 scripts that did
  NOT fail their useful operation ("all but `explainer-serve` and `ask_answerer --status`"). `--status` is not the
  useful operation by the row's own account. Observed: `operation_ok` true for an operation that was not run. Either
  `operation_ok: false` with the reason, or the schema needs a not-run value; the headline should read 7 fail, 1 pass,
  1 not run.
- **MAJOR — scripts/mkt_seed_repo.py:126-131 (`known_facts`) / :183 (`_self_test_body`):** the typed facts — the four
  that are not derived from git — are never checked against the files the seed writes, so the oracle can be wrong
  with the self-test green. Control input 1: `ROADMAP.splitlines()[2]` → `[3]` (a blank line). Observed: **12/12
  green**, and `roadmap-status` becomes `expected: ""`, `empty_is_correct: true` — a non-empty seeded fact silently
  re-graded as correctly empty, which is exactly the hollow-page loophole pass condition 2 exists to close. Control
  input 2: replace the `backlog-open` string with `"#1 x"`. Observed: 12/12 green. A case asserting each typed
  expected answer occurs in (or is parsed from) the committed file would kill both; the docstring's "Git items are
  DERIVED … never typed" is true and draws attention away from the four that are typed.
- **MAJOR — docs/marketplace/experiment-tier-a.md:153-158 (I1) and :148-149 (edge over-report):** both are found
  defects of THIS project's tooling, described only. The diff touches neither `docs/backlog.md` nor
  `docs/roadmap-to-launch.md` (`git diff --stat origin/master...HEAD -- docs/backlog.md docs/roadmap-to-launch.md` is
  empty), and no backlog row names `preflight`'s blindness to an ancestor `CLAUDE.md` (the only `mkt_isolate` row,
  #659, is about timeouts). I1 is a hole in the isolation instrument (Task 2's `build_world`/`preflight` passed `[]` on
  a world that loaded the author's global instructions) and no later plan task consumes it — Task 16 takes SCAN
  defects, Task 19 takes component verdicts. `dev-process.md` → *Roadmap & Task List*: a discovered step goes into the
  roadmap and the task list in the same turn. Same for the `exec_edges` string-as-edge over-report, which also widens
  closures (`check-docs.py` now reached from `mkt_seed_repo.py`). Observed: "recorded; not repaired" with no row.
  S1-S5 are experiment outputs the inventory consumes and need no row here.
- **MINOR — docs/marketplace/experiment-tier-a.md:62 (`skill-explain-diff`, condition 3 `pass`):** spec §6 condition 3
  is "one identified useful operation completes **through the installed paths**", but I2 (md:159-163) records that
  this run's `explainer-serve.py` came from `<run>/mkt/comprehensibility/scripts` — the staged marketplace, not the
  installed cache — and says path behaviour seen here "is the staging's, not a stranger's". The grade does not carry
  that caveat. Suggest `argued`, or a note in the row naming I2.
- **MINOR — scripts/mkt_seed_repo.py:15:** "one per command or file that step names" is false. `brief` Step 1
  (`.agents/skills/brief/SKILL.md`) also names `git diff --stat <boundary>..HEAD`, `docs/reviews/` and
  `docs/superpowers/`; none has an item (the seed has neither directory, so they would be two more correctly-empty
  items). The four ratchets are folded into two items. State the population as the 12 chosen items, or add the three.
- **MINOR — docs/marketplace/experiment-tier-b.md:56:** "all 11 scripted and serve runs" — a count with no enumerated
  population: the section above lists 8 scripted operations and one serve with start, GET page, POST, stop. Name the
  11.

## Checked and not a finding

- Task 13 FAILS-IF (two seeds, different HEAD): refuted by experiment, above. The plan's three named cases exist
  (`two seeds give identical trees`, `every ground-truth item has an expected answer`, `at least one item is
  correctly empty and one is non-empty`), plus 9 more; `fixture_git.isolated()` is used (`_self_test`).
- The determinism case cannot pass for the ambient reason: the 1.1 s sleep crosses git's one-second date resolution,
  and the date-removal mutation goes red on it.
- Task 14 FAILS-IF: no page skill has condition 2 `pass`; every `exercised: yes` row names a scenario; sidecar and
  Markdown agree. Task 15 FAILS-IF: `--is-shallow-repository` = `false` recorded (tier-b md:10) and no git-history item
  is cited as a suite defect (md:69-70).
- Condition 4 recorded `pass` vacuously with (a) = "no" for every component: matches spec §6 4(b) ("A condition over
  an empty set passes vacuously, and that is recorded rather than hidden"), and it is recorded.
- `brief` condition 2 FAILS on the page with the chat answer scored only as supplementary: matches plan Task 14's
  hollow-page rule.

## Loosening answers

- **Does the diff loosen a gate?** No gate is weakened. `check-shipping-sets.py`'s Phase 6 pin moves 344 → 347 with
  the gained lines listed by hand and reproduced here exactly (0 lost, 3 gained, all from this diff);
  `shipping-sets.json` `expected_count` 102 → 103 adds the one new manifest. `check-plan-code.py`,
  `check-selftest-counts.py`, `check-fixture-variation.py` and `expected_mutations.py` each ADD the new script to a
  population (more checking, not less); `ci.yml` adds a step.
- **Does a record loosen a pass condition?** Two grades do, in the permissive direction: `explainer-serve` condition 1
  `pass` without an askable page, and `ask-answerer.operation_ok: true` for an operation not run (MAJORs above);
  `explain-diff` condition 3 `pass` through a non-installed path (MINOR).
- **Is a check that cannot run reported as passing?** No: Step 5 (scan prediction) is stated NOT RUN with its reason
  (slice D unmerged), and the hooks and `ask_answerer --once` are stated not run.

VERDICT: NOT CONVERGED
