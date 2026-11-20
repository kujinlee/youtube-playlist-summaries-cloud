Reviewed head: be23de0d8636e844cfccfae6c2e07cff12d1a89c

# Round 3 — `hse-slice-e` — Claude half (adversarial)

Subject: `git diff origin/master...HEAD` at `be23de0d` (r2 fold `4873b4bd`), plan
`docs/superpowers/plans/2026-11-11-marketplace-inventory.md` Tasks 13-15. Every mutation below was built on a copy of
`scripts/mkt_seed_repo.py` (plus `fixture_git.py`) in the session scratchpad, outside the repository; the driver
results were read from `$(getconf DARWIN_USER_TEMP_DIR)/mktA.OPK4/results.jsonl` (tier A, world 2) and
`…/mktB.4EXn/results.jsonl` (tier B), the files the records name.

## Findings

- **MAJOR — docs/marketplace/experiment-tier-a.md:57-58 (and every exercised row's condition 4, sidecar
  `pass_conditions."4"`):** condition 4(a) is recorded "no, for every component", so 4(b) is graded `pass`
  vacuously — but the record's OWN driver output shows two components that DO document a recovery, and that the
  recovery fails. Input: the tier-A world 2 `results.jsonl`. Observed: `brief-compose.py` stderr
  `no explainer directory at …/explainers — run /explain-diff once first`; `gen-dashboard.py` stderr
  `no page in …/explainers contains an Ask tray. Run /explain-diff once to produce one, then re-run.` The record
  itself states the outcome of following that advice: `explain-diff` ran and produced a page with NO Ask tray
  (row `skill-explain-diff`), and brief-compose "with the directory present … refuses: no page has an Ask tray"
  (row `brief-compose`); line 145-146 says outright "its advice cannot work (S2)". Spec §6 4(b) is *"where a
  recovery procedure is documented, it succeeds under isolation"* — here one is documented and was observed to
  fail, so 4 for `brief-compose` and `gen-dashboard` is `fail`, not a vacuous `pass`. The "no" was taken from the
  spec's premise (§6 item 4: "the answer is **no**"), not from the run: an inference recorded as measured. It changes
  no SHIP verdict (both components already fail 3), but it is a pass grade the record's evidence refutes — the same
  class as round 1's CM1. Fix: answer 4(a) per component from the observed messages; grade 4 `fail` for the two;
  carry the same in tier B (whose scripted messages are identical). Fix-induced: no.

- **MINOR — scripts/mkt_seed_repo.py:261:** the r2 fold's source check is token membership
  (`parsed_from[k] in src[k].split() + [src[k]]`), so a source that names the right file among other words passes,
  whatever the other words say. Inputs (copies outside the repo, each a one-line change to `known_facts`):
  `roadmap-status` source → `"README.md, not docs/roadmap-to-launch.md"`; `ratchet-check-docs` source →
  `"cat scripts/check-docs.py"` (the answer is the rc and stdout of RUNNING it, not its text);
  `roadmap-deployed` source → `"grep Deployed: README.md docs/roadmap-to-launch.md"`. Observed: all three
  `13/13 self-test cases passed`. The r2 control (`README.md` alone) is the only false pairing it refuses. Fix:
  compare `src[k]` against an independently written literal of the WHOLE expected source (an exact map), which also
  pins the verb for the command item. Fix-induced: **yes** (r2 fold `4873b4bd`). ⚠ For the coordinator: r2's Xm1
  was itself induced by the r1 fold in this same component (`mkt-seed-repo`), so this is the second consecutive
  round whose finding came from the previous round's fix — the THRASHING shape that arms Phase 6
  (`docs/dev-process.md` → *The arming condition*).

- **MINOR — scripts/mkt_seed_repo.py:251-262:** the typed-fact case checks a hand-listed set of 5 ids, never the
  set of typed facts `known_facts` actually emits, so a NEW typed fact is silently unchecked — no `KeyError`, since
  both `held` and `parsed_from` iterate the same 5 literals. Input: add
  `_item("roadmap-steps", "README.md", "Milestone 9 — invented")` to `known_facts`. Observed:
  `13/13 self-test cases passed` — an invented, wrongly-sourced fact ships green. The docstring (line 24) claims
  "a self-test case re-reads EACH from the committed file it names". Fix: an identity case — every item that is
  neither git-derived nor `empty_is_correct` must appear in `parsed_from` (an independent literal of the git-derived
  ids makes the partition checkable). Fix-induced: yes (r1 fold `a0afc60d`, which introduced the case; r2 kept the
  same key set).

- **MINOR — scripts/mkt_seed_repo.py:138 (`ratchets-absent`):** an item whose seeded fact is EMPTINESS is never
  checked against the tree, so the seed can contradict its own ground truth. Input: add
  `"scripts/check-test-counts.py": "print(1)\n"` to the last `HISTORY` commit. Observed: `13/13`; known-facts still
  says `ratchets-absent` is correctly empty while the repository now has one of them — a stranger's page naming it
  would be scored `wrong`. (By contrast `git-status` IS guarded: a dirtying write goes red at 12/13.) Fix: a case
  that each path in `ABSENT_RATCHETS` is absent from `git ls-tree -r HEAD`. Fix-induced: no.

- **MINOR — docs/marketplace/experiment-tier-a.md:103-104:** the chat answer scored is labelled
  "world 2 run, 23:26:59", but world 2's `skill brief` row reads `at 2026-11-19 23:28:13`, `secs 13`
  (`duration_ms 11103`), and world 2 was seeded at 23:27:42 — 23:26:59 precedes world 2's existence. The answer
  scored IS world 2's (its text matches every mark in the table: five commits, newest 3 subjects, no ahead count,
  `master`, clean, #2/#3, rc 0, the three ratchets absent, flyctl absent, TaskList disabled), so the marks hold;
  only the timestamp is wrong, and it points the reader at the discarded world. Fix: `23:28:13 (finished)`.
  Fix-induced: no.

- **MINOR — docs/marketplace/experiment-tier-b.md:49-50:** "Pass conditions match tier A's matrix for every
  component except `skill-explain-diff`" is contradicted by the next sentence, "Condition 2 is `argued` for every
  page skill": tier A grades `skill-brief` condition 2 `fail` (seeded facts), tier B `argued` (none). Two
  components differ, not one. Fix: name `skill-brief` condition 2 as the second difference. Fix-induced: no.

## Recounts that held (no finding)

- Tier A: 33 components = `components.json` package `comprehensibility` (33); matrix vs sidecar on `exercised`,
  `scenario`, `operation_ok`, conditions 1-5 — 0 disagreements over 33 rows; 14 exercised (5 skills + 9 scripts),
  19 not (5 hooks + 14 libraries); 7 scripts `operation_ok: no` besides `ask-answerer`; S1 names 6, S1+S2 = 7;
  8 non-empty items; chat marks 6 + 4 + 2 = 12; seeded HEAD `3492d62` re-derived by running the seed (identical
  SHA, 12 items, `ahead-count` `0`); install `n_files 34`; serve pid 44052 = listener 44052; world-2 costs
  0.068/0.276/0.076/0.220/0.054 from `total_cost_usd` (world 1's 0.115 not verifiable — its run dir is not named;
  the 0.81 total depends on it); `opened_outside_world_and_stdlib` lies under `…/mktA.OPK4/world` for every run.
- Tier B: 16 `RunRecord` rows (8 scripted + `--status`/start/`--stop` + 5 post-skill `--stop`); rc/time/turns/cost
  for all 5 skills match the table (25/97/43/86/12 s; 8/16/11/19/5 turns; total 1.101 → 1.10); the only
  `opened` path under `<world HOME>/project` is `gen-backlog-page.py`'s `<unknown>`, in both tiers.
- Plan Task 13's three named cases exist; its FAILS IF (two seeds → different HEAD) is exercised by a seed taken
  1.1 s later.

## Loosening answers

- **Condition 4 (spec §6 4(b)), tier A and B: LOOSENED in effect** — graded `pass` vacuously for `brief-compose`
  and `gen-dashboard`, whose documented recovery was observed to fail (MAJOR above). Not introduced by a fold; the
  condition text itself was not edited.
- **Task 14 Step 5 (scan prediction per failure):** recorded NOT RUN with its cause (`ScanReport`, slice D, PR #600,
  unmerged) and handed to Task 16 — stated, not passed; not loosening.
- **Task 13 FAILS IF, Task 14 FAILS IF (hollow page), Task 15 FAILS IF (full clone):** not loosened — `brief`
  condition 2 is `fail`, `operation_ok` regrades went toward `no`/`fail`, the clone is recorded non-shallow
  (`--is-shallow-repository false`, 6343 commits).
- **The r2 fold:** tightens (adds a source check); its weakness (MINOR above) is under-reach, not a loosening.

## Self-tests (at be23de0d)

- `python3 scripts/mkt_seed_repo.py --self-test` → `13/13 self-test cases passed` (rc 0)
- `python3 scripts/check-plan-code.py --self-test` → `506/506 passed` (rc 0)
- `python3 scripts/check-shipping-sets.py --self-test` → `140/140 self-test cases passed` (rc 0)

VERDICT: NOT CONVERGED
