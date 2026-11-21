# Install experiment, tier A — the comprehensibility package in the seeded stranger repository

Spec §6; marketplace-inventory plan Task 14. Measured **2026-11-19, 23:20–23:31 PST**, on branch `hse-e` at
`50ac3e65` (Task 13's commit; the package staged is that commit's `scripts/` and `.agents/skills/`). Machine: macOS
(Darwin 25.5.0), `Python 3.14.4`, `claude --version` → `2.1.323 (Claude Code)`, `git version 2.49.0`.
The sidecar `experiment-tier-a.json` is generated from the SAME dict as the coverage matrix below.

**Headline (population: the 33 components `components.json` assigns to package `comprehensibility`; 14 exercised,
19 not):** the package installs, and its server works. **Every page skill FAILS pass condition 1** — no exercised run
produced a page a reader can ask a question in. Of the 9 exercised scripts, **7 fail their useful operation**, 1
completes it (`explainer-serve`), and 1 is NOT MEASURED (`ask_answerer`: only `--status` ran; answering a question
was not run). Suite defects S1 and S2 (below) account for the 7 script failures and for both pages produced without
an Ask tray (`explain-diff`, `explain-topic`); the three page skills that produced no page failed earlier, on S3
(`brief`, `explain-findings`, `dashboard`) and, for `dashboard`, also S4.
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

Condition 4: **(a) does the component document how to recover from failure? — answered per component from the
driver's output (`results.jsonl`, world 2), not from the spec's premise.** Two do: `brief-compose` (`run
/explain-diff once first`) and `gen-dashboard` (`Run /explain-diff once to produce one, then re-run`). Following that
advice was observed to fail — `explain-diff` ran and produced a page with NO Ask tray, so the tray page both scripts
demand still does not exist (S2) — so **4(b) FAILS for both**. No other exercised component's output documents a
recovery: for those, 4(b) holds vacuously and is recorded `pass` on that ground, not on a run. (r3 Claude M1 regraded
the two from a vacuous `pass`.)
Condition 2 is scored against `known-facts.json` for `brief` only; for the other page skills it is `not scored — no
seeded facts`, hence `argued`. Unexercised components are `argued` throughout (spec §4b).

| Component | Exercised | Scenario | operation_ok | 1 | 2 | 3 | 4 | 5 | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| `skill-brief` | yes | A-skill-brief | no | fail | fail | fail | pass | pass | no page: the skill named `scripts/brief-compose.py` / `explainer-serve.py` CWD-relative and found neither in the seeded repo; answered in text only. Condition 2 FAILS (no page carries any item; text-answer scoring below, supplementary) |
| `skill-explain-diff` | yes | A-skill-explain-diff | yes | fail | argued | argued | pass | pass | page written by the model and served by the package's `explainer-serve.py` on 7391 (HTTP 200); NO Ask tray — no existing page had one to copy (bootstrap circularity). Condition 3 is `argued`, not `pass`: the server ran from the STAGED marketplace, not the installed paths the condition names (I2) |
| `skill-explain-findings` | yes | A-skill-explain-findings | no | fail | argued | fail | pass | pass | no page: `../shared/explainer-delivery.md` did not resolve from the skill's CWD; verdicts given in text |
| `skill-explain-topic` | yes | A-skill-explain-topic | no | fail | argued | fail | pass | pass | page file written by the model to ~/explainers, NOT served, no Ask tray: `brief-compose.py` refuses without a tray source page |
| `skill-dashboard` | yes | A-skill-dashboard | no | fail | argued | fail | pass | pass | no entry, no page: the skill expects the HOST repo's docs/dashboard-entries.md, scripts/regen-pages.py, .agents/skills/shared/…, docs/anchors.md |
| `brief-compose` | yes | A-script-brief-compose | no | fail | argued | fail | fail | pass | rc 1 `no explainer directory at <world>/home/explainers`; with the directory present it refuses: no page has an Ask tray |
| `explainer-serve` | yes | A-script-explainer-serve | yes | fail | argued | pass | pass | pass | all three serve conditions held (start `serving <world HOME>/explainers`, pidfile 44052 = listener 44052, GET / 200 with sentinel); GET page 200; POST /questions 200 and recorded in the world's questions.md. Condition 1 FAILS: the page served was the experiment's own sentinel, with no Ask tray, so no page a reader can ask a question INSIDE was served — the endpoint answering a POST is not that (S2) |
| `ask-answerer` | yes | A-script-ask-answerer-status | no | argued | argued | argued | pass | pass | `--status` rc 0 named the world's folder and caps; `--once` (answering a question = a model call) NOT run, so the useful operation is argued. `operation_ok` is `no` because the useful operation was NOT RUN, not because it failed (the sidecar's field is a bool) |
| `regen-pages` | yes | A-script-regen-pages-all | no | argued | argued | fail | pass | pass | rc 2 `CANNOT RUN — git cannot name this repository's common directory from <install dir>`: it locates the repo from its OWN install path, not the user's CWD |
| `gen-dashboard` | yes | A-script-gen-dashboard | no | argued | argued | fail | fail | pass | rc 1: reads <install dir>/docs/backlog.md (absent) through `gen-backlog-page` (`gen-dashboard.py:3495-3498` loads it and calls `publish_rows(ROOT)`; the finding is `gen-backlog-page:2:2`), then brief-compose refuses (no tray page) |
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
23:28:13, finished):

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

Population: 12 items; **6 correct, 4 correctly-empty, 2 missing-capability, 0 wrong.** The chat answer's ground
truth is partial — it omitted the ahead count and gave 3 of 5 commit subjects without SHAs — and there is no page
half at all.

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

**Scan defects (plan Task 16): S1 and S3 — both closed by a scan commit.** The experiment's failures were held
against the scan (Task 16, 2026-11-21). "Scan-clean" is read PER FAILURE: a component is scan-clean for a failure
when the scan held no dependency finding naming that failure's cause (read literally — no finding at all — only
`brief-compose` was clean, which would have hidden every other failure). Before: `scan-2026-11-17.json`; after:
`scan-2026-11-21.json` (measured at `2f4b59ce`, the round 2 fold commit: its scanner over its own tree).

| Failure | Components it hit | The scan before Task 16 | Now | Closed by |
|---|---|---|---|---|
| S1 (project located from the install path) | `regen-pages`, `goal-tree`, `gen-backlog-page`, `gen-features-page`, `gen-goals-page`, `gen-dashboard` | no finding naming the cause (`gen-backlog-page:4` named the `docs/backlog.md` path only as a doc-path) | detector 2 `install-root`: `regen-pages:2:1`, `goal-tree:2:3`, `gen-backlog-page:2:2`, `gen-features-page:2:7`, `gen-goals-page:2:3`, `gen-dashboard:2:2` and the rest of each component's `install-root` rows | **case added (red→green)**: three `S1:` self-test cases; round 1 added four more (the `..` climb, Python's scopes, the inert uses) |
| S3 (package files named CWD-relative) | `skill-brief`, `skill-explain-findings`, `skill-dashboard` | `skill-dashboard:2:1` (`scripts/regen-pages.py`) only; the `Follow ../shared/explainer-delivery.md` line was no finding on any skill | detector 2 `cwd-relative` with the plugin-root fix: `skill-brief:2:1`, `skill-explain-findings:2:1`, `skill-dashboard:2:2` (and `skill-explain-diff:2:1`, `skill-explain-topic:2:1`, which carry the same line) | **case added (red→green)**: one `S3:` self-test case |
| S2 (the Ask tray cannot be bootstrapped) | `brief-compose`, `gen-dashboard`, `skill-explain-diff`, `skill-explain-topic`, `explainer-serve` condition 1 | none | none | **limit recorded**: L1 below |
| S4 (the host's conventions assumed) | `skill-dashboard` | mentions only (`docs/dashboard-entries.md`, `docs/anchors.md`) | `skill-dashboard:4:1` (`docs/dashboard-entries.md` at `:28`, the path that opens the `## The store` section); `docs/anchors.md` (`:14`) still a mention | **case added (red→green)**: one `S4 (r1 M1):` case; the rest is limit L2 below |
| `brief-compose` refuses without `~/explainers` | `brief-compose` | none | `brief-compose:6:1` (detector 6 `home-path` `~/explainers`, at `:789`) | **case added (red→green)**: one `L3 (r1 B1):` case |
| S5 (hooks not registered) | the 5 `hook-regen-*` | `hook-regen-*:7:1` `needs-registration` | the same | not scan-clean: predicted |

RED, recorded: with the two new detector clauses disabled on a scratch copy and the four cases kept, the self-test
reported `95/98 self-test cases passed` — the three cases then present (two `S1:`, one `S3:`) each `[FAIL] … got []`.
GREEN after the fix: `109/109`. The fourth case (`S1: ...judged in INSTALLED coordinates`) was added after the fix;
its mutation (the depth taken from the source path) goes red against it. Round 1 fold (`3db9d353`): seven cases written
first, then the code — 100/105 red at the first run (the sixth, `S3 (r1 m6)`, passed on its first run: the shared
dedup already existed, so it is a regression lock); GREEN `116/116`. Against the previous scan, the fold removed
seven false findings (a comparison, a `print`, `relative_to` ×2, `REPO.is_dir()`, a file-wide name binding, the
`_sp.run = _real` restore) and added eight (among them `brief-compose:6:1`, `skill-dashboard:4:1`, and
`check-docs` reads that a disagreeing name had masked). Round 2 fold (`2f4b59ce`, both Codex r2 MAJORs caused by
the round 1 fold): five cases written first, four RED (`117/121`; the compared-and-printed negative passed and is
a lock); GREEN `121/121`. The live scan is unchanged: 365 findings, none gained or lost — no shipped file hands a
file-derived root through an f-string, `relpath`, `joinpath` or a multi-level `nonlocal`, so the fixture cases
are the only witnesses of the new rule.

**The scan defects list** — each entry closed by a scan commit or a named limit:

- S1 — closed by the scan commit of Task 16 (detector 2 `install-root`).
- S3 — closed by the scan commit of Task 16 (detector 2, Markdown read/follow references).
- `~/explainers` — closed by the round 1 fold (detector 6 `home-path`, `brief-compose:6:1`).
- S4 — `docs/dashboard-entries.md` closed by the round 1 fold (detector 4 section openers, `skill-dashboard:4:1`);
  the rest by limit L2. S2 — closed by limit L1.
- `check-shipping-sets.py`'s edge reader reports `scripts/mkt_seed_repo.py -> scripts/check-docs.py`, from the
  self-test's interpreter argv `[sys.executable, str(Path(a.repo) / "scripts/check-docs.py")]`, which runs the SEEDED
  repository's own file: the reader drops the base (`Path(a.repo)`) by design and resolves the rest from this
  repository's root — an over-report (found while re-pinning its Phase 6 case in this branch; cause located at the
  round 1 fold: removing that argv removes the edge, while rewording the `source` label does not). Filed as backlog #675.
  **Outside Task 16's population and still OPEN:** it is an over-report by the shipping-set reader, not an experiment
  failure on a scan-clean component, so it is neither closed by a scan commit nor a limit here.

### Limits of the scan (what it cannot express — each a named limit, not a defect it could repair)

- **L1 — bootstrap circularity (S2).** A precondition on runtime state that only the package's own earlier output
  creates (a page that already has an Ask tray). The scan reads files, not the state a first run starts from; a
  refusal guarded by `if no page has a tray` is the same code whether a tray page exists or not.
- **L2 — host conventions cited in prose (S4).** `docs/anchors.md` (`.agents/skills/dashboard/SKILL.md:14`) is a
  citation: named in description, in none of the INSTRUCTS / REQUIRES shapes, and opening no section whose body acts,
  so it is a mention. Making every named `docs/` path a dependency would be positional matching (spec rule 1). (Round
  1 M1 narrowed this limit: `docs/dashboard-entries.md` opens a section that says to append to it, now a finding.)
- **L3 — dropped at the round 1 fold (B1).** It said the scan could not decide that `~/explainers`' absence is fatal;
  it can — the guard `if not ROOT.is_dir(): … sys.exit(1)` is the decision. Detector 6 `home-path` now reports a
  path below HOME whose absence a guard turns into a failure (`raise`, a non-zero exit or return) — spec rule 1's
  r2 CLAUDE M7 test (the component fails without it); a guard that exits 0 is a working default, not reported.
- **L4 — model adherence.** Whether a model follows a skill's delivery loop (tier B: `explain-diff` wrote its page and
  skipped serving it, where tier A's run served it) is not a property of the files.
- **L5 — what detector 2's `install-root` does NOT see** (Phase 6 rule, the MENTION WALK of
  `docs/reviews/architecture-review-2026-11-21-publishability-install-root.md` §4): every mention of a file-anchored
  value is walked upward through ONE decoder whose default is USE, so an unlisted use is reported, never hidden. It
  does NOT name the path a root reaches through a call of the program's own function (reported where it is passed or
  returned), or a part held in anything but a literal or a name bound to one string literal everywhere. **A name
  reused anywhere in its file is not followed** — a second function's local, a parameter, a `global`/`nonlocal`
  rebinding, a loop or `with` target: its root is reported AT THE BINDING, as `.`, and the paths built from it later
  are not named — coarser, never silent (e.g. `check-plan-code:2` at `:6355`). The only silencers are inert uses (a
  comparison, `print`, `relative_to`/`samefile`, a `relpath` start that is itself file-anchored, an existence test of
  the root itself), a part that leaves the tree, a level that is not the install depth, and a shipped target. It
  judges paths in a self-test's fixture strings like any other (e.g. `recall-llm:2:6`, `.claude/plans/p.md`, and
  `check-surface-recall:2` `.claude/hooks/does-not-exist.sh` at `:519`), an over-report, not a miss.
- **L6 — a package file named in descriptive prose (round 1 M2).** `scripts/check-dashboard-entry.py`
  (`.agents/skills/dashboard/SKILL.md:21`) and `.claude/hooks/regen-dashboard.sh` (`:88`) are shipped, named bare,
  and were reported absent by tier B's `dashboard` session. They sit in neither an invocation, a read/follow line, an
  INSTRUCTS nor a REQUIRES shape, so they are mentions under spec rule 1 (behavioural, not positional): judging
  every named package path would be the positional rule. The skill's other CWD-relative lines (`skill-dashboard:2:1`,
  `2:2`) are findings.

### Isolation and unobservable accesses

- **I1 — a world under the author's home directory inherits the author's global instructions.** World 1's root was
  under `/Users/<author>/…`; `claude` walks the working directory's ANCESTORS for `CLAUDE.md`, and loaded
  `/Users/<author>/.claude/CLAUDE.md` (its transcript: `Contents of /Users/<author>/.claude/CLAUDE.md`). The `brief` run
  there answered in the author's banner format and declined to build the page. **`preflight` passed** (`[]`) — it does
  not check this. World 2, under `DARWIN_USER_TEMP_DIR`, loaded none (`Contents of` absent in all 5 transcripts).
  A stated limit of `build_world`/`preflight`, recorded; not repaired here — filed as backlog #674.
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
