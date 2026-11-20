# Install experiment, tier A — the comprehensibility package in the seeded stranger repository

Spec §6; marketplace-inventory plan Task 14. Measured **2026-11-19, 23:20–23:31 PST**, on branch `hse-e` at
`50ac3e65` (Task 13's commit; the package staged is that commit's `scripts/` and `.agents/skills/`). Machine: macOS
(Darwin 25.5.0), `Python 3.14.4`, `claude --version` → `2.1.323 (Claude Code)`, `git version 2.49.0`.
The sidecar `experiment-tier-a.json` is generated from the SAME dict as the coverage matrix below.

**Headline (population: the 33 components `components.json` assigns to package `comprehensibility`; 14 exercised,
19 not):** the package installs, and its server works. **Every page skill FAILS pass condition 1** — no exercised run
produced a page a reader can ask a question in — and **7 of the 9 exercised scripts fail their useful operation** (all but
`explainer-serve` and `ask_answerer --status`). Two causes explain all of it (suite defects S1 and S2 below).
`brief` FAILS pass condition 2: there is no page, so no seeded item reaches a page.

## How it was run

A driver in the session scratchpad (outside the repository) called the Task 2, 3 and 13 functions directly:
`mkt_seed_repo.seed(<run>/seed)` → `known-facts.json` stays at `<run>/seed/`, outside the world; `build_world(<run>/world,
["python3","git","claude"])`; the seeded repository copied (with `.git`) to `<world HOME>/project`;
`stage([spec_from_map(components.json, "comprehensibility", "0.1.0")], <run>/mkt)`; `preflight(world)` → `[]`;
`install(world, mkt, "comprehensibility")` → 34 files under `<world HOME>/.claude/plugins/cache/mkt-local/comprehensibility/0.1.0`.
Scripted half: `run_isolated(world, ["python3", <installed>/scripts/<x>.py, …], <world HOME>/project, 60)` per
operation. Skill half: `claude -p --permission-mode bypassPermissions --output-format json "/comprehensibility:<skill> …"`
with `cwd=<world HOME>/project`, one run at a time, 230 s cap each.

**The run that counts is world 2** (`$(getconf DARWIN_USER_TEMP_DIR)/mktA.OPK4`). World 1, under the session
scratchpad, was DISCARDED for the skill half — see isolation defect I1. Its scripted and serve results were identical
to world 2's (same rc and the same message for all 9 operations; serve conditions all held, pid 27658).

**Skill invocation form that resolved:** `/comprehensibility:<skill> <request>` under `claude -p`: all 5 runs resolved
the skill (each session's transcript names `Base directory for this skill: …/comprehensibility/skills/<skill>`).

### Port 7391

The owner's explainer server (pid 50846, 92 explainers) was **stopped 2026-11-19 23:26:11** (`explainer-serve.py
--stop` from the main checkout) and **restarted 23:31:53** (`python3 scripts/explainer-serve.py` from the main checkout
→ pid 72980, 92 explainers). Each skill run was followed by the WORLD's own `--stop`; no listener remained before the
restart. ⚠ While the world's server held 7391, the owner's open browser tab polled it (`GET /_stale?p=/2026-11-17-brief-marketplace-plan.html`
in the world's `.serve.log`): the port is shared state with the author's desktop, not only with the author's server.

### Stated deviations from a stranger's machine

- **The token bypasses `run_isolated`.** `world.env` carries only `ENV_KEYS` and `boundary()` refuses any other key,
  so `run_isolated` has no channel for `CLAUDE_CODE_OAUTH_TOKEN`. The skill half ran `subprocess.run` directly with
  `world.env` plus the token (read from its file inside the driver; never printed, logged or written). Consequence:
  **no `RunRecord` exists for the skill half** — `claude` is a non-Python process, and its file access is unobservable
  either way (list U below). A tool limit, recorded; not repaired.
- `--permission-mode bypassPermissions` and the stranger's login (plan baseline deviations).
- **PATH is harsher than a stranger's.** The allow-list holds `python3`, `git`, `claude` only; the skill sessions
  reported `ls`, `cat`, `tail`, `date` as `command not found` and fell back to `/bin/…` paths. A real stranger has them.
- No `bash` on the allow-list (the plan's list), so the 5 hook scripts were not run.

## Coverage matrix and pass conditions (spec §6)

Condition 4: **(a) does the component document how to recover from failure? — no, for every component** (spec §6 4(a));
so 4(b) holds vacuously for every exercised component and is recorded `pass` on that ground, not on a run.
Condition 2 is scored against `known-facts.json` for `brief` only; for the other page skills it is `not scored — no
seeded facts`, hence `argued`. Unexercised components are `argued` throughout (spec §4b).

| Component | Exercised | Scenario | operation_ok | 1 | 2 | 3 | 4 | 5 | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| `skill-brief` | yes | A-skill-brief | no | fail | fail | fail | pass | pass | no page: the skill named `scripts/brief-compose.py` / `explainer-serve.py` CWD-relative and found neither in the seeded repo; answered in text only. Condition 2 FAILS (no page carries any item; text-answer scoring below, supplementary) |
| `skill-explain-diff` | yes | A-skill-explain-diff | yes | fail | argued | pass | pass | pass | page written by the model and served by the package's `explainer-serve.py` on 7391 (HTTP 200); NO Ask tray — no existing page had one to copy (bootstrap circularity) |
| `skill-explain-findings` | yes | A-skill-explain-findings | no | fail | argued | fail | pass | pass | no page: `../shared/explainer-delivery.md` did not resolve from the skill's CWD; verdicts given in text |
| `skill-explain-topic` | yes | A-skill-explain-topic | no | fail | argued | fail | pass | pass | page file written by the model to ~/explainers, NOT served, no Ask tray: `brief-compose.py` refuses without a tray source page |
| `skill-dashboard` | yes | A-skill-dashboard | no | fail | argued | fail | pass | pass | no entry, no page: the skill expects the HOST repo's docs/dashboard-entries.md, scripts/regen-pages.py, .agents/skills/shared/…, docs/anchors.md |
| `brief-compose` | yes | A-script-brief-compose | no | fail | argued | fail | pass | pass | rc 1 `no explainer directory at <world>/home/explainers`; with the directory present it refuses: no page has an Ask tray |
| `explainer-serve` | yes | A-script-explainer-serve | yes | pass | argued | pass | pass | pass | all three serve conditions held (start `serving <world HOME>/explainers`, pidfile 44052 = listener 44052, GET / 200 with sentinel); GET page 200; POST /questions 200 and recorded in the world's questions.md |
| `ask-answerer` | yes | A-script-ask-answerer-status | yes | argued | argued | argued | pass | pass | `--status` rc 0 named the world's folder and caps; `--once` (answering a question = a model call) NOT run, so the useful operation is argued |
| `regen-pages` | yes | A-script-regen-pages-all | no | argued | argued | fail | pass | pass | rc 2 `CANNOT RUN — git cannot name this repository's common directory from <install dir>`: it locates the repo from its OWN install path, not the user's CWD |
| `gen-dashboard` | yes | A-script-gen-dashboard | no | argued | argued | fail | pass | pass | rc 1: reads <install dir>/docs/backlog.md (absent), then brief-compose refuses (no tray page) |
| `gen-goals-page` | yes | A-script-gen-goals-page | no | argued | argued | fail | pass | pass | rc 2 `CANNOT RUN — docs/anchors.md or scripts/gen-backlog-page.py is missing` (looked up beside the install, not in the repo) |
| `gen-features-page` | yes | A-script-gen-features-page | no | argued | argued | fail | pass | pass | rc 2 `CANNOT RUN — <install dir>/docs/features.md is missing` |
| `gen-backlog-page` | yes | A-script-gen-backlog-page | no | argued | argued | fail | pass | pass | rc 1 traceback FileNotFoundError <install dir>/docs/backlog.md — the seeded repo HAS docs/backlog.md; the script reads beside itself |
| `goal-tree` | yes | A-script-goal-tree-print | no | argued | argued | fail | pass | pass | rc 2 `CANNOT RUN — … git rev-parse --git-common-dir gave no usable path` (run from the install dir's repo, which is none) |
| `hook-regen-backlog-page` | no | — | no | argued | argued | argued | argued | argued | NOT exercised: `bash` is not on the allow-list, and the installed package carries no hooks/hooks.json, so Claude Code would never invoke it |
| `hook-regen-dashboard` | no | — | no | argued | argued | argued | argued | argued | NOT exercised: `bash` is not on the allow-list, and the installed package carries no hooks/hooks.json, so Claude Code would never invoke it |
| `hook-regen-features-page` | no | — | no | argued | argued | argued | argued | argued | NOT exercised: `bash` is not on the allow-list, and the installed package carries no hooks/hooks.json, so Claude Code would never invoke it |
| `hook-regen-goals-page` | no | — | no | argued | argued | argued | argued | argued | NOT exercised: `bash` is not on the allow-list, and the installed package carries no hooks/hooks.json, so Claude Code would never invoke it |
| `hook-regen-pages` | no | — | no | argued | argued | argued | argued | argued | NOT exercised: `bash` is not on the allow-list, and the installed package carries no hooks/hooks.json, so Claude Code would never invoke it |
| `contract-explainer-delivery` | no | — | no | argued | argued | argued | argued | argued | library: not an entry point; loaded only indirectly by the runs above |
| `contract-handoff-path` | no | — | no | argued | argued | argued | argued | argued | library: not an entry point; loaded only indirectly by the runs above |
| `contract-corpus-search` | no | — | no | argued | argued | argued | argued | argued | library: not an entry point; loaded only indirectly by the runs above |
| `page-chrome` | no | — | no | argued | argued | argued | argued | argued | library: not an entry point; loaded only indirectly by the runs above |
| `page-markup` | no | — | no | argued | argued | argued | argued | argued | library: not an entry point; loaded only indirectly by the runs above |
| `session-state` | no | — | no | argued | argued | argued | argued | argued | library: not an entry point; loaded only indirectly by the runs above |
| `gen-work-lines` | no | — | no | argued | argued | argued | argued | argued | library: not an entry point; loaded only indirectly by the runs above |
| `check-dashboard-entry` | no | — | no | argued | argued | argued | argued | argued | library: not an entry point; loaded only indirectly by the runs above |
| `check-goal-status` | no | — | no | argued | argued | argued | argued | argued | library: not an entry point; loaded only indirectly by the runs above |
| `check-features` | no | — | no | argued | argued | argued | argued | argued | library: not an entry point; loaded only indirectly by the runs above |
| `check-docs` | no | — | no | argued | argued | argued | argued | argued | library: not an entry point; loaded only indirectly by the runs above |
| `check-anchors` | no | — | no | argued | argued | argued | argued | argued | library: not an entry point; loaded only indirectly by the runs above |
| `fixture-git` | no | — | no | argued | argued | argued | argued | argued | library: not an entry point; loaded only indirectly by the runs above |
| `hook-dispatcher` | no | — | no | argued | argued | argued | argued | argued | library: not an entry point; loaded only indirectly by the runs above |

### `brief`, condition 2 — item by item

**The page: none was produced, so every one of the 8 non-empty items is `missing-capability` ON THE PAGE, and
condition 2 FAILS** (the hollow-page rule: a measured run that fails; it forbids SHIP).

Supplementary, NOT the pass condition — the skill's chat answer scored against the same 12 items (world 2 run,
23:26:59):

| Item | Expected (seeded) | Chat answer | Mark |
|---|---|---|---|
| git-log | 5 commits, `3492d62 Add the docs ratchet` … `Initial commit` | "five commits", the newest 3 subjects | missing-capability (partial: 3 of 5 subjects, no SHAs) |
| git-status | empty | "working tree clean" | correctly-empty |
| branch | `master` | `master` | correct |
| ahead-count | `0` | not stated | missing-capability |
| roadmap-status | milestone 2 of 3, import pipeline half built | M1 done, M2 in progress, M3 not started | correct |
| roadmap-deployed | `Deployed: release v4 (2026-03-02)` | same, quoted | correct |
| decision-waiting | storage backend — A: SQLite, B: Postgres | same | correct |
| backlog-open | #2, #3 | #2, #3 (and #1 fixed) | correct |
| ratchet-check-docs | rc 0, `check-docs: 2 documents checked, 0 problems` | exits 0 (2 documents, 0 problems) | correct |
| ratchets-absent | empty | the three named, "don't exist" | correctly-empty |
| live-release | empty | `flyctl` not installed, v4 unconfirmed | correctly-empty |
| task-list | empty | `TaskList` disabled | correctly-empty |

Population: 12 items; **6 correct, 4 correctly-empty, 2 missing-capability, 0 wrong.** The ground-truth half of
`brief` works for a stranger; the page half does not.

## The three lists

### Suite defects (the package's own)

- **S1 — scripts locate the project from their OWN install path, not the user's working directory.** `regen-pages.py`,
  `goal-tree.py` (`git rev-parse --git-common-dir` from the install dir → exit 128), `gen-backlog-page.py`,
  `gen-features-page.py`, `gen-goals-page.py`, `gen-dashboard.py` (each reads `<install dir>/docs/…`). Run from inside
  the seeded repository, which HAS `docs/backlog.md`, `gen-backlog-page.py` still raised `FileNotFoundError` on
  `<install dir>/docs/backlog.md`. 6 of the 9 scripts exercised.
- **S2 — the Ask tray cannot be bootstrapped.** `brief-compose.py` copies the tray from an existing page and refuses
  without one; a stranger starts with none, so no page can ever get one. Hit by `brief-compose` (scripted),
  `gen-dashboard`, `explain-diff` (page served, no tray), `explain-topic` (page written, no tray, not served). This
  alone fails condition 1 for every page skill.
- **S3 — the skills name package files CWD-relative** (spike-record finding, now measured end to end): `brief`
  looked for `scripts/brief-compose.py` in the seeded repo; `explain-findings` could not resolve
  `../shared/explainer-delivery.md`; `dashboard` looked for `scripts/regen-pages.py`, `.agents/skills/shared/…`.
- **S4 — `dashboard` assumes the host repository's conventions** (`docs/dashboard-entries.md`, `docs/anchors.md`)
  and stops rather than creating them.
- **S5 — the 5 hooks are not registered.** The installed package has no `hooks/hooks.json`; Claude Code would never
  invoke `regen-*.sh`. (Not exercised: no `bash` on the allow-list.)
- `brief-compose.py` with no `~/explainers`: rc 1, `run /explain-diff once first` — a correct, loud refusal, but its
  advice cannot work (S2).

### Scan defects (the scan or its readers)

- **Scan prediction for each failure (plan Step 5): NOT RUN.** `ScanReport` (Task 8, slice D, PR #600) is not merged,
  so no finding id can be named. Feeds Task 16, which needs slice D.
- `check-shipping-sets.py`'s edge reader reports `scripts/mkt_seed_repo.py -> scripts/check-docs.py`, from a STRING
  naming the seeded repository's own file — an over-report (found while re-pinning its Phase 6 case in this branch).

### Isolation and unobservable accesses

- **I1 — a world under the author's home directory inherits the author's global instructions.** World 1's root was
  under `/Users/<author>/…`; `claude` walks the working directory's ANCESTORS for `CLAUDE.md`, and loaded
  `/Users/<author>/.claude/CLAUDE.md` (its transcript: `Contents of /Users/<author>/.claude/CLAUDE.md`). The `brief` run
  there answered in the author's banner format and declined to build the page. **`preflight` passed** (`[]`) — it does
  not check this. World 2, under `DARWIN_USER_TEMP_DIR`, loaded none (`Contents of` absent in all 5 transcripts).
  A stated limit of `build_world`/`preflight`, recorded; not repaired.
- **I2 — skills ran from the STAGED marketplace, outside the world.** Every skill's base directory was
  `<run>/mkt/comprehensibility/skills/<skill>` — the local-directory marketplace source, a sibling of the world — not
  the installed cache; `explain-diff` ran `explainer-serve.py` from `<run>/mkt/comprehensibility/scripts`. The staged
  copy is the package, not the author's repo, so no author resource was reached; but a git-hosted marketplace would
  resolve elsewhere, so path behaviour seen here is the staging's, not a stranger's.
- **U — unobservable by construction:** all file access by the 5 `claude` sessions (no `RunRecord`: see the token
  deviation), and by `git` in every scripted run (non-Python); network; the keychain (isolation-baseline bound (e)).
  `run_isolated` captured the Python opens of every scripted and serve run in world 2: none fell outside the world root other than the
  stdlib (world 2 paths appear as `/private/var/…`, the same directory through the `/var` symlink).

## Cost

Stranger account, `total_cost_usd` as `claude -p --output-format json` reported it, 2026-11-19, population: 6 skill
runs. World 2: `brief` 0.068 (13 s), `explain-diff` 0.276 (85 s), `explain-findings` 0.076 (23 s), `explain-topic`
0.220 (49 s), `dashboard` 0.054 (13 s); world 1 (discarded) `brief` 0.115 (24 s). **Total 0.81 USD.** The scripted
half made no model call.
