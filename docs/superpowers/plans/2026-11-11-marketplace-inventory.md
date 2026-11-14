# Marketplace inventory — implementation plan (exploration milestone, phase 1 of D11)

> **Anchor:** `harness-ships-elsewhere` — **ADR:** 0015
> **Goal:** The harness this project built can be installed and used by someone who has never seen this repository.

**Status:** 📝 DRAFT, written 2026-11-11 from the approved spec at `2f5e3f3d` (spec approved by the owner
2026-11-11 05:53, merged as `d18167ce`). Phase 2: dual adversarial review to convergence or the round cap
(`docs/review-method.md` §0 Q4c) before any task is dispatched. Nothing is built. ⟳ **r1 folded 2026-11-11**
(`docs/reviews/coordinator/marketplace-plan-r1-coordinator.md`): 1 BLOCKER (raised by both halves), 12 distinct MAJORs, 9 MINORs.
The header names ADR 0015 while the spec's reads `ADR: none`: the ADR was written after the spec, and
`docs/anchors.md` registers `harness-ships-elsewhere` with it.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** find out, with evidence and a measured price, how much of this repository's harness a stranger can
install and use; produce the phase-1 subset (comprehensibility, plus recall only if feasible) with its shipping
set, an inventory of every component, and a cost record, and stop for the owner at the D1 checkpoint. Publishing
is NOT part of this plan.

**Architecture:** three small Python tools and one guard, all stdlib-only, plus data under `docs/marketplace/`.
`scripts/mkt_isolate.py` builds the stranger's world (fresh `HOME`, allow-listed `PATH`, an audit-hook capture);
`scripts/mkt_stage.py` packages declared files into a throwaway local marketplace and derives the shipping set
from the INSTALLED tree; `scripts/check-shipping-sets.py` validates the component map and the dependency closure;
`scripts/check-publishability.py` is the seven-detector scan; `scripts/check-inventory.py` makes every falsifier of
spec §9 that is decidable from the inventory a machine check, including the D1 checkpoint. Three producers, so no
oracle checks its own output (spec §7 item 2).

**Tech Stack:** Python 3 stdlib (CI pins 3.12), bash, the `claude plugin` CLI (`validate`, `marketplace add`,
`install`), `git`, GitHub Actions (only for the effort (2) reading).

**Spec:** [`docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md`](../specs/2026-10-15-marketplace-inventory-design.md)
(the `marketplace-inventory` canon). Executors read the spec section each task cites; this plan does not restate
its rules, and where it names a decision symbol (D1-D11, C1-C5, the verdicts, the grades, the harvest field) the
spec is the definition.

## Owner context (recorded at the spec walkthrough; honoured by every task)

- The owner does **not** want this repository licensed or made public as a whole. The TOOLING is to be carved out
  as a general plugin repository, the way `mattpocock/skills` is (spec §2c, D7).
- Phase 1 = effort (3) comprehensibility, plus effort (1) recall **only if** it is useful with an empty corpus AND
  the owner's content review passes (spec §2c, D11). Effort (2) gets a scan and a first route estimate, read as a CI
  layer for any GitHub project with a mutation sweep (spec §3, Effort (2)).
- This is an EXPLORATION milestone: the output is the real cost. The D1 checkpoint (spec §2c) stops the work and
  asks the owner when the public bar costs ≥ 3× the "my next project" estimate for more than half of the phase-1
  components (Task 21).
- **Anything outward-facing is a HUMAN step** (section *Human steps*), never done by an agent: creating the
  published marketplace repository, a marketplace listing, a `LICENSE` (holder: `Kujin Lee`, H5, named 2026-11-13), pushing to
  any third-party repository.

## Global Constraints

- **Evaluate, never repair** (spec §7, *What PR 1 explicitly does NOT do*). No task edits a component under
  evaluation (`.agents/skills/{brief,explain-diff,explain-findings,explain-topic,dashboard}/`,
  `.agents/skills/shared/`, the effort (3)/(1)/(2) scripts and hooks). A defect found is RECORDED with its known
  fix. The staging step copies files; it never rewrites them (the CWD-relative paths stay CWD-relative in the
  staged package, because that IS the measurement).
- **Cannot run is a failure, never a pass.** Every tool here exits 2 with `CANNOT RUN: <why>` when it cannot reach
  its subject (empty file set, a declaration it cannot parse, a missing `claude` binary), never 0 with an empty
  report.
- **Every number is dated and carries its population** (`docs/process-checklists.md` → *Reduce defect INJECTION*,
  rules 1 and 1b). A count in a committed artifact names the commit it was measured at and the command.
- **Experiments run outside the repository**, under the session scratchpad or `mktemp -d`, never in the main
  checkout and never writing to a third-party clone (spec §6, tier-B criteria).
- **Stdlib only.** A new tool that imports a non-stdlib package is itself a detector-6 finding.
- **New self-tested scripts are wired per W1-W8** as written in
  `docs/superpowers/plans/2026-11-09-observed-reach-selection.md` → *Wiring a new self-tested script (W1-W8)*
  (declared count, mutation manifest, `expected_mutations.py`, the declared-counts case in `check-plan-code.py`,
  `check-selftest-counts.py` `POPULATION`, `check-fixture-variation.py` `EXAMINED_KEYS`, a `ci.yml` caller,
  `fixture_git.isolated()` if used). That section is the single source; it is cited, not restated.
- **Spend is recorded.** At the end of every slice the coordinator appends one row to
  `docs/marketplace/spend-log.md`: slice, date, agent runs, review rounds, weekly-usage % before and after (from the
  pace line). Exploring the cost of the milestone itself is part of the deliverable.

## Review Focus

1. **A component whose file set resolves to the wrong files and still scores** — a symlinked skill directory
   (`.claude/skills/*` → `.agents/skills/*`), a hook reached only through `.claude/hooks/run-hook.sh`, a file
   renamed since the map was written. Expected: CANNOT RUN naming the component, never a clean score. Owner:
   Task 8 (and Task 5 for the map).
2. **A hollow page reported as success** — the experiment's page renders but every ground-truth item returned
   nothing. Expected: a FAIL of pass condition 2 for each item whose seeded fact is non-empty. Owner: Task 14.
3. **The author's world leaking into the stranger's** — `~/explainers/` resolving into this repository, an
   already-running `explainer-serve.py` on its port, `gh` credentials, a `scripts/` directory on `PATH`. Expected:
   the isolation preflight refuses to start. Owner: Task 2.
4. **A mention counted as a dependency, or the reverse** — `supabase` inside a `page_markup.py` fixture string;
   an env read with a working default; a self-test that really contacts a service. Expected: the first two are
   mention candidates with no finding id; the third is a dependency finding. Owner: Tasks 9 and 12.
5. **A recall verdict computed over the author's corpus** — `recall-llm.py` finding `docs/memory/` through this
   repository's layout and looking useful. Expected: the empty-corpus probe runs with no corpus reachable and the
   verdict says what a stranger gets on day one. Owner: Task 18.

---

## Slice map

Each slice is ONE pull request off fresh `origin/master`, with its own dual review. Slices B-C can merge without
the experiment; slice F cannot be final before Task 21's checkpoint is answered.

**The spec's "PR 1" is delivered as five slice PRs (B-F); the D8 bound is applied to the FIRST of them.** The spec
names the milestone's deliverable "PR 1" and decides nothing about how many PRs carry it; it DOES decide where the
three corrections go, and that decision is kept as written (spec §7 item 8): *"⭐ **D8 — A CORRECTION LANDS WITH THE
WORK THAT FOUND IT, NOT IN A SEPARATE PR. Decided 2026-10-16 by the owner**, asked through the walkthrough page:
'yes, fix in here.'"* and *"All three repairs are docs-only and depend on nothing else in PR 1, so they go in as its
**first commit** and are mergeable alone. The observation that makes this bound FAIL: PR 1 open with ANY OF THE
THREE corrections not yet committed."* So Task 1 is **slice B's first commit**, not a PR of its own (⟳ r1 CLAUDE
M8: the r0 draft gave it a standalone slice A, which reversed D8). The spec names exactly one condition for a
separate PR — the stall risk going live — and this plan names its trigger: a Task 4 record of INCOMPLETE or NO-GO
splits Task 1's commit into its own PR (Task 4 Step 5; ⟳ r2 CLAUDE m4).

| Slice | Branch | Tasks | What merges | Outward-facing? |
|---|---|---|---|---|
| B | `mkt-spike` | 1-4 | **first commit:** the three `portable-practices.md` corrections (spec §7 item 8, D8); then the isolation tool, staging tool, spike record | no (local marketplace in a temp dir) |
| C | `mkt-shipping-sets` | 5-7 | component map, shipping-set declaration, closure guard | no |
| D | `mkt-scan` | 8-12 | `check-publishability.py` + CI | no |
| E | `mkt-experiment` | 13-16 | seeded repo builder, tier-A and tier-B records, scan fixes | no (read-only clone) |
| F | `mkt-inventory` | 17-22 | effort (1)/(2) readings, inventory guard, cost record, checkpoint, inventory | no; Task 21 may STOP for the owner |

**Ordering.** Task 1 is slice B's first commit (spec §7 item 8: "its first commit and mergeable alone"). B before C
(C derives the declaration from B's installed tree). C before D (the scan reads C's data). D before E (the
experiment checks the scan's predictions). F needs D for effort (1)/(2) and E for effort (3). Task 4 is a
**go/no-go**: if the spike fails, spec §9's D3 falsifier has fired and the plan stops at Human step H3.

## Artifacts this plan creates (file map)

| Path | Responsibility | Produced by |
|---|---|---|
| `docs/marketplace/README.md` | what each file here is, and its producer | Task 2 |
| `docs/marketplace/isolation-baseline.md` | spec §7 item 0b: what a stranger is assumed to have, and what capture cannot see | Task 2 |
| `scripts/mkt_isolate.py` | builds the stranger world, preflight refusals, runs a command, writes the resource record | Task 2 |
| `scripts/mkt_stage.py` | stages declared files into a plugin + local marketplace; `--declare` lists the installed tree | Tasks 3, 6 |
| `docs/marketplace/spike-record.md` | spec §7 item 0 outcome | Task 4 |
| `docs/marketplace/components.json` | the component map: every component, effort, role, phase, package, files; and every exclusion with its reason | Task 5 |
| `docs/marketplace/shipping-sets.json` | per package: installed member files, symlinks resolved, expected count per component | Task 6 |
| `scripts/check-shipping-sets.py` | map completeness against disk; declaration closure against the installed tree | Tasks 5, 7 |
| `scripts/check-publishability.py` | the scan, detectors 1-7 (spec §5) | Tasks 8-12 |
| `docs/marketplace/harness-tools.txt` | the harness tool names detector 4 reports (hand-written, dated, with `claude --version`; a stated deviation from "derived") | Task 11 |
| `docs/marketplace/scan-<date>.json` | one scan report, dated, with the commit | Task 12 |
| `scripts/mkt_seed_repo.py` | builds the tier-A seeded stranger repo and its known-facts file | Task 13 |
| `docs/marketplace/experiment-tier-a.md`, `experiment-tier-b.md` | spec §7 items 3b and 4 | Tasks 14, 15 |
| `docs/marketplace/experiment-tier-a.json` | the tier-A coverage matrix as data (read by Task 19's SHIP-versus-experiment rule) | Task 14 |
| `docs/marketplace/inventory.json` | the inventory rows (spec §7 items 4b, 5, 9b) | Tasks 17-20 |
| `scripts/check-inventory.py` | spec §9 falsifiers decidable from the inventory; the D1 checkpoint; renders `inventory.md` | Task 19 |
| `docs/marketplace/inventory.md` | generated view: verdict and grade in one cell | Task 22 |
| `docs/marketplace/spend-log.md` | the milestone's own cost, per slice | every slice |

---

## Slice B, first commit — the D8 corrections (spec §7 item 8)

### Task 1: correct the three stale claims in `docs/portable-practices.md`

**Files:**
- Modify: `docs/portable-practices.md` (lines 13 and 24 at `2f5e3f3d`; find them by the phrases below, not by line)
- Modify: `docs/dashboard-entries.md` (append one entry)

**Interfaces:**
- Consumes: nothing.
- Produces: nothing other tasks read.

- [ ] **Step 1: the failing check.** Each phrase must occur zero times after the fix. Measured 2026-11-11 at
  `2f5e3f3d`: each occurs once — the first and third on line 13, the second on line 24 (its sentence runs
  on as *"...concentrated in / one file"*, so the probe matches the part that sits on one line).

```bash
for p in 'roughly 3x' 'The problem is concentrated in' '10,373 lines across six files'; do
  n=$(grep -o -- "$p" docs/portable-practices.md | wc -l | tr -d ' '); echo "$p: $n"
done
```

  Expected before: `1` each. After: `0` each.
- [ ] **Step 2: rewrite in place** (rule 2, *Fix the sentence IN PLACE*), per the three rows of spec §7 item 8's
  table: (a) the ratio is 1.82x against the nine enumerated files at `a4f6d4b5`, and the larger figure is a
  different set; (b) the C3 coupling is in `explainer-delivery.md` too, which scores 0 on vocabulary; (c) the
  headline's file set either includes the three shared contracts (11,624 at `a4f6d4b5`, spec §3) or says what it
  omits. Every figure keeps its commit. Cite the spec rather than restating its argument.
- [ ] **Step 3: run** the loop from Step 1 (all `0`), then `python3 scripts/check-docs.py`,
  `python3 scripts/check-canonical-source.py`, `python3 scripts/check-claim-propagation.py`. Each `rc=0`.
- [ ] **Step 4: dashboard entry, commit as the FIRST commit of slice B's branch `mkt-spike`, then**
  `python3 scripts/check-dashboard-entry.py` (must say an entry block was added). Nothing else goes in this commit,
  so it stays mergeable alone.

**FAILS IF:** any of the three phrases still occurs, or **slice B's PR (the first PR of the spec's "PR 1") is open
with any of the three corrections not yet committed** — D8's own FAILS IF, restated against the slices — or the
corrections commit is not the first commit on `mkt-spike` above `origin/master` (`git log --reverse
origin/master..mkt-spike | head` names it), or it touches any file besides `docs/portable-practices.md` and
`docs/dashboard-entries.md`.

---

## Slice B (continued) — isolation and the packaging spike (spec §6, §7 items 0b and 0)

### Task 2: the isolation baseline and `scripts/mkt_isolate.py`

**Files:**
- Create: `scripts/mkt_isolate.py`, `docs/marketplace/isolation-baseline.md`, `docs/marketplace/README.md`,
  `docs/marketplace/spend-log.md`
- Modify (W1-W8): `scripts/mutations/mkt_isolate.json` (create), `scripts/mutations/expected_mutations.py`,
  `scripts/check-plan-code.py`, `scripts/check-selftest-counts.py`, `scripts/check-fixture-variation.py`,
  `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: nothing.
- Produces: `build_world(root: Path, allow: list[str]) -> World` (a dataclass with `home`, `bindir`, `tmpdir`,
  `env: dict[str, str]`); `preflight(world: World, port: int = <explainer-serve's PORT>) -> list[str]` (refusal
  reasons, empty = clear; `port` is a parameter so the self-test can pass an ephemeral one);
  `run_isolated(world: World, argv: list[str], cwd: Path, timeout: int) -> RunRecord` (`rc`, `stdout`, `stderr`,
  `opened: list[str]`, `executed: list[str]`, `unobservable: list[str]`); CLI
  `python3 scripts/mkt_isolate.py --root DIR --allow CMD,... -- ARGV...` writing `RunRecord` as JSON to stdout.

The capture mechanism (decided here, spec §6 requires one to be named): **an allow-listed environment plus a Python
audit hook**. `env` is built from nothing (`HOME`, `TMPDIR` inside `root`; `PATH` = only `bindir`, which holds
symlinks to the absolute paths of the allow-listed commands; `LANG=C.UTF-8`). A `sitecustomize.py` placed in a
directory on `PYTHONPATH` installs `sys.addaudithook` and appends `open` and `subprocess.Popen`/`os.exec*` events to
a JSONL file. `fs_usage`/`dtruss` are rejected: both need `sudo` (measured present at `/usr/bin` on 2026-11-11, and
root is the owner's). What the hook cannot see, stated in the baseline and in every `RunRecord.unobservable`: file
access by non-Python children (`git`, `node`, `gh`), network access, and anything before the interpreter starts.

- [ ] **Step 1: write the self-test cases first** (in `_self_test()`, the repo's `--self-test` convention):
  `world env has no key outside the declared set`; `PATH holds only allow-listed commands` (`command -v gh` fails
  when `gh` is not allowed); `preflight refuses a HOME whose explainers dir resolves into the repo` (a symlink
  fixture); `preflight refuses when the explainer port is already listening` (the case binds port `0`, reads the
  port the OS assigned, passes THAT to `preflight(world, port=...)`, then releases it — never 7391, which the
  owner's own server holds; ⟳ r1 CLAUDE M1, measured listening 2026-11-11); `preflight refuses an allow-listed
  command that resolves inside the repository`;
  `audit hook records an open of a fixture file`; `a non-Python child is listed as unobservable, never as zero
  opens`; `an unreachable command is CANNOT RUN (rc 2)`.
- [ ] **Step 2: run** `python3 scripts/mkt_isolate.py --self-test`; expected: fails (no implementation).
- [ ] **Step 3: implement** the four functions above. The explainer port is read from `scripts/explainer-serve.py`'s
  own default (import its constant, never type it).
- [ ] **Step 4: write `isolation-baseline.md`**: interpreter (`python3 -V` of the run), stdlib-only package set,
  the allow-listed commands with versions (`git --version`, `claude --version`, `node -v` if allowed), network
  policy (allowed only for `claude` model calls and the tier-B clone; nothing else), and the unobservable list.
  Every version is the output of a command in this session. Two stated baseline deviations (r1 CLAUDE defaults
  table, m7): **(a)** the audit hook's `sitecustomize.py` on `PYTHONPATH` SHADOWS the interpreter's own (Homebrew
  Python ships one, measured `…/lib/python3.14/sitecustomize.py`; CI pins 3.12) — name the one shadowed, by path;
  **(b)** `claude -p` in the world runs with `--permission-mode bypassPermissions` (flag measured present in
  `claude --help` 2026-11-11), because a fresh `HOME` has no settings and would refuse Bash/Write — a stranger
  answers those prompts themselves, so a permission refusal is a baseline artifact, never a suite defect.
- [ ] **Step 5: run the self-test green; wire W1-W8; append the spend-log row; commit.**

**FAILS IF:** a self-test case passes with the hook removed (W2 mutation `drop audit hook` must go red), or the
baseline lists a command version that no command in the commit's session produced.

### Task 3: `scripts/mkt_stage.py` — package declared files into a throwaway local marketplace

**Files:**
- Create: `scripts/mkt_stage.py`
- Modify (W1-W8): as Task 2, for `mkt_stage.py`

**Interfaces:**
- Consumes: nothing from Task 2 (staging needs no isolation; installing does).
- Produces: `stage(packages: list[PackageSpec], out: Path) -> Path` (returns the marketplace root);
  `PackageSpec(name: str, version: str, skills: list[str], files: list[str])` where `skills` are skill directory
  paths and `files` repo-relative paths, each copied preserving its repo-relative path under the plugin root
  (`scripts/x.py` → `<plugin>/scripts/x.py`, `.agents/skills/brief` → `<plugin>/skills/brief`). **Every directory
  under `.agents/skills/` maps to `<plugin>/skills/<name>`, including `shared/`, which has no `SKILL.md`**
  (`corpus-search.md`, `explainer-delivery.md`, `handoff-path.md`): `.agents/skills/shared` →
  `<plugin>/skills/shared`, so the page skills' `../shared/explainer-delivery.md` (8 occurrences across the five
  skills) resolves from `<plugin>/skills/<skill>/` exactly as it does in the repository (⟳ r2 CLAUDE M5). Measured
  2026-11-11 (fold r2) with the Task 3 probe below plus a `skills/shared/contract.md` with no `SKILL.md` and a skill
  saying `Follow ../shared/contract.md`: `validate` rc 0 (two metadata warnings, none about `shared/`), `install`
  rc 0, the installed tree holds `skills/shared/contract.md`, and `skills/hello/../shared/contract.md` resolves.
  (Whether the harness also lists `shared` as a skill was not measured; it carries no frontmatter.)
  `install(world: World, mkt_root: Path, plugin: str) -> Path` (runs `claude plugin marketplace add` then
  `claude plugin install <plugin>@<mkt>` inside the world, returns the installed directory).

Measured 2026-11-11 under a fresh `HOME` in the scratchpad: `claude plugin validate <mkt>`,
`claude plugin marketplace add <path>` and `claude plugin install probe@probe-mkt` all succeed **with no login**,
and the installed tree lands at `$HOME/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`. So `install`
returns that path and fails (CANNOT RUN) if it does not exist after a zero exit. The probe, for reproduction:

```bash
S=$(mktemp -d); mkdir -p $S/mkt/.claude-plugin $S/mkt/p/.claude-plugin $S/mkt/p/skills/hello $S/home $S/work
printf '{"name":"probe-mkt","owner":{"name":"probe"},"plugins":[{"name":"probe","source":"./p","description":"x","version":"0.0.1"}]}' > $S/mkt/.claude-plugin/marketplace.json
printf '{"name":"probe","version":"0.0.1","description":"x"}' > $S/mkt/p/.claude-plugin/plugin.json
printf -- '---\nname: hello\ndescription: say hello\n---\nhello\n' > $S/mkt/p/skills/hello/SKILL.md
cd $S/work && HOME=$S/home claude plugin validate $S/mkt </dev/null && HOME=$S/home claude plugin marketplace add $S/mkt </dev/null && HOME=$S/home claude plugin install probe@probe-mkt </dev/null && ls $S/home/.claude/plugins/cache/probe-mkt/probe/0.0.1
```

- [ ] **Step 1: self-test cases**: `a declared file lands at its repo-relative path under the plugin`;
  `.agents/skills/shared lands at <plugin>/skills/shared, so ../shared/x.md resolves from an installed skill`;
  `a symlinked skill dir is copied as the contents its link points to, not as a link` (fixture: `a -> b`);
  `a declared path that does not exist is CANNOT RUN`; `the written marketplace.json passes claude plugin
  validate` (skipped with an explicit `NOT RUN: claude missing` line, counted as not run, when `claude` is absent;
  CI has no `claude`, so this case prints NOT RUN there and the declared count excludes it — state that in the
  docstring); `staging copies bytes unchanged` (sha256 of source = sha256 of staged, the no-repair rule).
- [ ] **Step 2: red; Step 3: implement; Step 4: green; W1-W8; commit.**

**FAILS IF:** a staged file's sha256 differs from its source (staging repaired something), or `install` returns a
path that does not exist.

### Task 4: the packaging spike (spec §7 item 0) — GO / NO-GO

**Files:**
- Create: `docs/marketplace/spike-record.md`

**Interfaces:**
- Consumes: `build_world`, `preflight`, `run_isolated` (Task 2); `stage`, `install`, `PackageSpec` (Task 3).
- Produces: `docs/marketplace/spike-record.md` (prose; no symbol).

- [ ] **Step 1:** stage ONE skill and ONE script **with the script's import closure**: `.agents/skills/explain-topic`,
  `scripts/explainer-serve.py`, and the two siblings it imports at module load, `scripts/page_chrome.py` and
  `scripts/page_markup.py` (`explainer-serve.py:101-102`), as package `spike` version `0.0.1`. (Choice:
  `explain-topic` is the smallest of the four page skills and `explainer-serve.py` is the script it ends in.)
  ⟳ r1 CLAUDE B1 / CODEX 1: the r0 payload omitted both siblings, and even `--help` died with
  `ModuleNotFoundError: No module named 'page_chrome'`. **Measured 2026-11-11 (fold r1):** those three files alone,
  copied to a scratch dir and run by absolute path from an unrelated directory under a fresh `HOME` with
  `python3 -I`, give `--help` rc 0. (⟳ r2 CLAUDE M1: the r1 fold also recorded `--status` rc 0 here; that was the
  owner's server answering on 7391, i.e. the very leak H7 exists for — on a free port `--status` exits **1**, see
  Step 3.) `fixture_git` is imported only inside the self-tests
  (`explainer-serve.py:1636`), so it is not in the closure of the operations below; a standing-page route
  (`/dashboard`, `/backlog-table`, …) shells out to `regen-pages.py` (`explainer-serve.py:1523`) and is likewise
  out of the spike's operation set.
- [ ] **Step 2:** build a world (allow: `python3`, `git`, `claude`), run `preflight` (must be empty), `install`.
  **The port.** `explainer-serve.py` has no port option: `PORT = 7391` is a module constant (`:104`) and `main()`
  takes only `--stop`, `--status`, `--self-test`. So the serve operation runs on 7391 or not at all, and preflight
  refuses while anything listens there. Measured 2026-11-11: the owner's own server listens on 7391, and the
  stranger's `--status` reported it (`listening : yes`) — a stranger's command observing the author's server, which
  is Review Focus 3's leak. If preflight refuses for the port, the serve operation waits on **Human step H7** (the
  owner stops their server for the experiment window); the agent never stops the owner's process. The hard-coded
  port itself is recorded as a **finding** on `explainer-serve.py` (one server per machine; any other user of
  7391 collides), not repaired (*Evaluate, never repair*).
- [ ] **Step 3:** from an unrelated directory inside the world, by the installed path:
  (a) `python3 <installed>/scripts/explainer-serve.py --help` — invocation from elsewhere, needs no port; expected
  rc 0. **`--status` is NOT the invocation check (⟳ r2 CLAUDE M1).** Measured 2026-11-11 (fold r2) on a scratch copy
  of the three files with only the `PORT` constant changed to a free port, fresh `HOME`, `python3 -I`: `--status`
  on a free port prints `listening : NO …` and exits **1** (`status()` returns `0 if running else 1`,
  `explainer-serve.py:1621-1629`); with a foreign listener on the port it prints `listening : yes` and exits **0**.
  So once H7 has freed 7391, `--status` is run for the record and its expected result is rc 1 with
  `listening : NO`; rc 0 there means something else holds the port, and the step stops as INCOMPLETE (H7 not in
  effect), never NO-GO. (b) the useful operation, ONLY once preflight has confirmed 7391 free:
  **seed** the world's `~/explainers` with a sentinel page whose name carries a fresh random token
  (`<date>-mkt-sentinel-<token>.html`), start it (no flag), `GET /`, then `--stop`. **The world's server answered
  only if ALL THREE hold (⟳ r2 CLAUDE M2 — the r1 check, "the response names no path outside the world", could not
  fail: `index_html` prints no root):** (i) start's stdout begins `serving <world HOME>/explainers`, not
  `already serving` — measured: `start()` prints `already serving on …` and **exits 0** when anything listens
  (`:1579-1585`), so rc alone cannot tell; (ii) the pid in the WORLD's pidfile (`<world HOME>/explainers/.serve.pid`,
  `:107`) is the pid `lsof -nP -t -iTCP:7391 -sTCP:LISTEN` reports; (iii) `GET /` is 200 and its body contains the
  sentinel's token. Measured on the same scratch copy: all three hold for the world's own server (start printed
  `serving <scratch HOME>/explainers`, pidfile pid = listener pid, body named the sentinel), and against a foreign
  listener (i) fails. **A failed condition is routed by WHOSE server failed (⟳ r3 CODEX M1)** — H7 can resolve
  only an isolation failure, never a broken component: **isolation failure → INCOMPLETE** (H7 not in effect),
  never GO and never NO-GO — 7391 held before start (`--status` rc 0), start printing `already serving`, or the
  world pidfile's pid differing from the listener's; **the world's VERIFIED own server failing → a recorded
  FAILURE of the component (the NO-GO route, H3)**, never INCOMPLETE — start exiting non-zero on a port preflight
  confirmed free, or start printing `serving <world HOME>/explainers` with the pidfile pid = listener pid and then
  `GET /` erroring, non-200, or lacking the sentinel token. Measured by r3 CODEX on a scratch copy with an injected
  `RuntimeError` in `index_html()`: port free before start, `serving …`, pid match, `GET /` →
  `RemoteDisconnected` — a component failure H7 cannot fix. The failure's evidence (start's rc and stdout, both
  pids, the `GET /` error or body) goes in the record. `--stop` is safe in both cases: it reads only the world's pidfile, so it can never signal the
  owner's process (measured: with the foreign listener up, the world's `--stop` printed `not running` and the
  listener survived). **No port flag is added** — the script has none and reads no port from the environment
  (`os.environ` is consulted only for `SRC_ROOT_ENV`, `:658`), and *Evaluate, never repair* forbids adding one
  here; 7391 plus H7 plus the three-part check is the least-invasive route. Record the `RunRecord`s.
- [ ] **Step 4:** also record what the skill's text tells the model to run, and whether that path resolves from the
  unrelated directory (expected, per spec §4: it does not, because the paths are CWD-relative; that is a finding,
  not a spike failure).
- [ ] **Step 5:** write the record: GO if the package installs, `--help` by the installed path exits 0, and (b)'s
  three conditions all hold; NO-GO if the install fails, `--help` by the installed path cannot run, or (b) records
  the world's verified own server failing (Step 3, ⟳ r3 CODEX M1); **INCOMPLETE (neither)** if (b) is waiting on
  H7 or one of (b)'s conditions fails as an isolation failure (Step 3) — an INCOMPLETE spike blocks slice C
  exactly as NO-GO does, but does not open H3. **On INCOMPLETE or NO-GO, split Task 1 off (⟳ r2 CLAUDE m4).**
  Spec §7 item 8 names this exact moment: *"The observation that makes this bound FAIL: PR 1 open with ANY OF THE
  THREE corrections not yet committed … At that point the stall risk the owner accepted is live and the corrections
  should be split into their own PR."* A stalled spike is that stall, so Task 1's commit is cherry-picked onto a
  fresh branch off `origin/master` (`mkt-d8-corrections`) and opened as its own PR, mergeable alone (it touches only
  `docs/portable-practices.md` and `docs/dashboard-entries.md`). Slice B's PR does not merge on an INCOMPLETE or
  NO-GO record: it stays open, holding the record, until H7 (re-run Steps 2-5) or H3 (the owner re-decides the
  method) resolves it.

**FAILS IF (and this is spec §9's D3 falsifier):** the package cannot be installed from the local marketplace, or
the installed script cannot be invoked from elsewhere. **And the spike's own check FAILS IF** GO is recorded with
start's stdout reading `already serving`, or with the world pidfile's pid differing from the 7391 listener's pid, or
with a `GET /` body that lacks the sentinel token. On NO-GO: stop the plan, file the record, and go to Human
step H3; do not proceed to slice C. **A NO-GO caused by the plan's own staging — a payload missing a member of the
script's import closure — is a PLAN defect, never the D3 falsifier:** fix the payload and re-run before recording
NO-GO. The observation that makes the staging FAIL: `--help` by the installed path exits non-zero with
`ModuleNotFoundError` naming a file that exists in this repository's `scripts/`.

---

## Slice C — the component map and the shipping-set declaration (spec §3 mapping step, §7 item 2)

### Task 5: the component map and its completeness check

**Files:**
- Create: `docs/marketplace/components.json`, `scripts/check-shipping-sets.py` (mode `--map`)
- Modify (W1-W8): as Task 2, for `check-shipping-sets.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (reads disk).
- Produces: `components.json` with `{"measured_at": "<sha>", "packages": {name: {"channel":
  "plugin"|"reusable-workflow"}}, "components": [Component], "exclusions": [{"path", "reason"}]}` (⟳ r2 CLAUDE m2:
  `channel` is a PACKAGE property, so it lives in `packages`, and every `Component.package` must be a key there —
  a refused case), where `Component = {"id", "effort": 1|2|3, "roles": ["entry-point"|"library"|"data"],
  "phase": "1"|"1-if-feasible"|"later", "package", "files": [repo-relative]}`;
  `load_map(path: Path) -> ComponentMap`; `candidates(root: Path) -> set[str]`; `map_gaps(m: ComponentMap,
  cands: set[str]) -> list[str]`.

`candidates()` derives from disk, not a list: every file under `.agents/skills/{brief,explain-diff,
explain-findings,explain-topic,dashboard}/` and `.agents/skills/shared/`; every `.claude/hooks/*.sh` that
`.claude/settings.json` registers (directly or through `run-hook.sh`, which is itself a candidate); every
`scripts/*.py` imported or invoked (`python3 scripts/X`) by an already-included candidate, transitively; the recall
trio and `docs/memory/`; the effort (2) set (`check-plan-code.py`, `scripts/mutations/`, the `mutation-sweep` jobs
of `ci.yml`, the velocity documents). Third-party vendored skills (the `mattpocock/skills` ones under
`.agents/skills/`) are not candidates; that rule is written in the map as an exclusion with its reason, so it is
visible. Measured 2026-11-11: the set has grown since spec §3 (a `dashboard` skill and a `regen-pages.sh` hook
exist; hooks are registered through `run-hook.sh`), which is why the map is derived and checked, not copied.

- [ ] **Step 1: self-test cases**: `a candidate in no component and no exclusion is a gap`; `an exclusion without a
  reason is refused`; `a component with no files is refused`; `a transitively invoked script is a candidate`
  (fixture: skill → `python3 scripts/a.py` → `import b`); `a hook reached through run-hook.sh is a candidate`;
  `the real repo map has zero gaps` (the identity case, run on the live tree).
- [ ] **Step 2: red. Step 3: implement `candidates`, `map_gaps`. Step 4: write `components.json` by hand from the
  candidates, assigning effort, role(s), phase and package per spec §3/§4 and D11; one package for phase 1
  (`comprehensibility`), one for recall (`recall`), one for the CI layer (`ci-layer`). Each package carries
  `"channel": "plugin"` or `"channel": "reusable-workflow"`; `ci-layer` is `reusable-workflow` (spec §2c, *Install
  channel for CI pieces*: installed as `uses: <owner>/<repo>/.github/workflows/…@<tag>`, "not through `/plugin
  marketplace add`"; ⟳ r1 CLAUDE M3).**
  **The standing cost of `--map` in CI is intended, and kept to one line (⟳ r1 CLAUDE m4).** The 27 registered
  hooks are mostly governance (`block-default-branch-push`, `check-plan-gate`, `usage-pace-*`); each becomes a
  candidate, so a future PR that adds a hook turns `--map` red until it is classified. That is the map doing its
  job (spec §3: every supporting artifact mapped or excluded), so an exclusion may be a glob with one reason
  (`.claude/hooks/*` reached from no package entry point → `"governance: not part of any shipped package"`), and a
  new governance hook then matches it with no edit. A glob exclusion that swallows a file some package component
  invokes is refused (case: `a glob exclusion never hides a file a package invokes`).
- [ ] **Step 5: green** `python3 scripts/check-shipping-sets.py --map docs/marketplace/components.json` → `0 gaps`;
  record the component count per effort with the commit in the map's `measured_at` and in the commit message
  (this count replaces spec §3's lower bound of 24).
- [ ] **Step 6: W1-W8, commit.**

**FAILS IF:** any file a page skill invokes, transitively, is neither in a component nor in a written exclusion
(the identity case on the live tree goes red).

### Task 6: derive the shipping-set declaration from the INSTALLED tree

**Files:**
- Modify: `scripts/mkt_stage.py` (add `--declare`; WM pins)
- Create: `docs/marketplace/shipping-sets.json`

**Interfaces:**
- Consumes: `stage`, `install` (Task 3); `build_world` (Task 2); `load_map` (Task 5).
- Produces: `declare(installed: Path, m: ComponentMap) -> dict` and `shipping-sets.json` =
  `{"measured_at", "packages": {name: {"installed_files": [...], "components": {id: {"files": [...],
  "expected_count": n}}}}}`.

`declare` walks the installed directory only. It never imports or reads `check-publishability.py` or its output
(spec §7 item 2: "a step that never reads the scan's output"). Self-test: `declare reads no file outside the
installed dir` (audit hook from Task 2), `a symlink in the installed tree is recorded by its resolved path`.

**Only the two `channel: plugin` packages are installed** (`comprehensibility`, `recall`). `ci-layer` is NOT
installed as a plugin (⟳ r1 CLAUDE M3; spec §2c says its channel is a reusable workflow, and C4 for it "stays
`argued` (no experiment this milestone)"). Its entry in `shipping-sets.json` is `{"channel": "reusable-workflow",
"declared_from": "components.json (no installed tree: spec §2c, C4 argued)", "components": {...}}` — the files a
reusable workflow would reference, listed from the map, with symlinks resolved and counts, and no
`installed_files`. Task 7's `--closure` skips it and says so (`ci-layer: SKIPPED — reusable-workflow channel, no
installed tree`), never a silent pass. Task 17 reads its routes against this entry.

- [ ] **Steps:** cases red → implement → stage and install the two plugin packages from `components.json` → write
  the JSON (plus the declared `ci-layer` entry) → green → WM pins → commit.

**FAILS IF:** `shipping-sets.json` lists a file under a `plugin` package that is not in its installed tree;
`declare` opens any path outside the installed dir it was given (audit record; the self-test case above — ⟳ r1
CLAUDE m5: the r0 gate named `scripts/check-publishability*`, which does not exist until Task 8, so it could not
fail); or `ci-layer` was passed to `install` (its entry carries `installed_files`).

### Task 7: the closure validator

**Files:**
- Modify: `scripts/check-shipping-sets.py` (mode `--closure`; WM pins)

**Interfaces:**
- Consumes: `shipping-sets.json` (Task 6); the installed tree from `install` (Task 3).
- Produces: `closure(installed: Path) -> set[str]` (every installed-relative path reached from the package's
  skills and entry-points by: Python `import` of a sibling module, `python3 <path>` / `bash <path>` in Markdown or
  shell, `source`, a `Read`-the-file or *Follow* instruction naming a path in a SKILL.md or in a member document it
  reaches); `closure_gaps(decl, reached) ->
  list[str]`.

**Every CWD-relative edge is ALSO resolved against the package root (⟳ r1 CLAUDE M2).** Measured 2026-11-11: every
skill→script edge in the page skills and shared contracts is CWD-relative (`dashboard/SKILL.md:76 python3
scripts/regen-pages.py`; `shared/explainer-delivery.md:165 … brief-compose.py`, `:223` and `:300 …
explainer-serve.py`), so a rule that called every CWD-relative path `external` could never turn red on the edge
that matters most. The rule, per reached path `p`:

| `p` is | and | result |
|---|---|---|
| an EXECUTABLE edge (`python3`/`bash`/`source`/import) | `<installed>/p` exists | member; ALSO `cwd-relative: p` handed to detector 2 (it resolves only from the plugin root) |
| an executable edge | not in the installed tree, but `p` exists in this repository | **gap** (the package omits a file its own text runs) |
| an executable edge | exists nowhere | **gap** (`dangling: p`) |
| a READ edge that resolves INSIDE the package's own source tree (a relative path from the citing file such as `../shared/explainer-delivery.md`, or a path under `.agents/skills/`) | `<installed>/p` exists | member — and its own edges are followed (this is how `brief-compose.py` is reached: its only inbound edge is `explainer-delivery.md:165`) |
| a read edge inside the package's source tree | not in the installed tree | **gap**, exactly like an executable edge (⟳ r2 CLAUDE M5: the r1 row filed every Read edge as `external`, so dropping `explainer-delivery.md` stayed green) |
| a READ of a project document (`docs/...`) | not in the installed tree | `external: p` — the stranger's own project file; handed to detector 4 (doc path), never a gap |

- [ ] **Steps:** cases (`omitted dependency with a count written to match is refused` — spec §5's third file-set
  mutation; **`brief-compose.py dropped from the declaration with its count lowered → closure red`** (the edge is
  CWD-relative in `explainer-delivery.md`; the r0 rule kept this green); `a CWD-relative invocation of a member is
  a member plus a cwd-relative hand-off, not a gap` (adjacent negative); `a docs/ read is external, not a gap`; **`explainer-delivery.md dropped from the declaration with its count
  lowered → closure red`** (a read edge inside the package's source tree, ⟳ r2 CLAUDE M5), beside `the same
  read with explainer-delivery.md present is a member` (adjacent negative);
  `an import cycle terminates`) red → implement →
  green on the real declaration → WM pins → add `python3 scripts/check-shipping-sets.py --closure` to `ci.yml`
  only if CI can build the installed tree without `claude` (it cannot; so CI runs `--self-test` and `--map`, and
  `--closure` is a recorded local gate in the slice's pre-push) → commit.

**FAILS IF:** removing a member from `shipping-sets.json` and lowering its `expected_count` leaves
`--closure` green — in particular `scripts/brief-compose.py`, whose only inbound edge is CWD-relative, and
`.agents/skills/shared/explainer-delivery.md`, reached only by `../shared/` read edges.

---

## Slice D — the scan, `scripts/check-publishability.py` (spec §5)

Every task in this slice adds cases to one `--self-test` and one manifest (WM pins after Task 8). Each detector's
known positive is a constructed fixture (spec §5: one mutation per detector; detector 6's positive is a fixture
component importing an absent package). Every finding has an id `<component>:<detector>:<n>`; a mention candidate
has NO id (spec §5 rule 1).

### Task 8: file-set resolution, identity comparison and CANNOT RUN

**Files:**
- Create: `scripts/check-publishability.py`
- Modify (W1-W8): as Task 2, for `check-publishability.py`

**Interfaces:**
- Consumes: `load_map` (Task 5); `shipping-sets.json` (Task 6).
- Produces: `resolve(component, decl) -> list[Path]` (symlinks resolved); `ScanReport = {"measured_at",
  "components": {id: {"findings": [Finding], "mentions": [Mention], "status": "scanned"|"CANNOT RUN", "why"}}}`;
  `Finding = {"id", "detector": 1..7, "file", "line", "text", "kind"}`; CLI
  `python3 scripts/check-publishability.py [--map P] [--sets P] [--out P]`, rc 0 scanned, 2 CANNOT RUN.

- [ ] **Step 1: cases** — the three file-set mutations of spec §5 as cases: `an emptied set is CANNOT RUN`;
  `a substituted member with equal cardinality is CANNOT RUN` (declared `coupled.py`, resolved `safe.py`);
  `a set walked through a symlinked directory finds the known positive` (fixture mirrors `.claude/skills` →
  `.agents/skills`; `grep -r` would find 0); `the report for a CANNOT RUN component carries no findings field
  that reads as zero`.
- [ ] **Steps 2-5:** red → implement → green → W1-W8 → commit.

**FAILS IF:** any of the three file-set mutations leaves the component `scanned`.

### Task 9: detector 1 (derived vocabulary) and the mention/dependency split

**Files:** Modify `scripts/check-publishability.py` (WM pins)

**Interfaces:**
- Consumes: `resolve`, `ScanReport` (Task 8).
- Produces: `derive_vocabulary(root: Path) -> set[str]`; `classify_match(file, line, token) -> "dependency" |
  "mention"`.

Vocabulary is derived, not hand-written (spec §5 item 1 names the terms it must reach: *"`supabase`, `gemini`,
`fly`, `youtube-playlist`, repo-rooted paths"*). Every source below is read from disk; none is a typed list
(⟳ r1 CLAUDE M6 — the r0 derivation could not produce `gemini`, and it hand-typed the directory list its own
structural case forbade):

| Source | Yields (measured 2026-11-11) |
|---|---|
| `git remote get-url origin`: the repository name AND the owner segment | `youtube-playlist-summaries-cloud`, and the owner handle (an identity term; intended — a published file naming the author's account is a C2 leak) |
| `package.json` `name` | `youtube-playlist-summaries` |
| top-level directories of `git ls-files` that hold a product-language file (`.ts`, `.tsx`, `.sql`) and contain NO Task 5 candidate | `app/`, `components/`, `lib/`, `supabase/`, `tests/`, `types/`, `worker/` (`docs/` and `scripts/` hold `.ts`/`.sql` files too, and are excluded because they hold candidates) |
| the module stems named in `docs/dev-process.md`'s *Mocking boundaries* paragraph (the project's own declaration of its external-service boundaries) | `gemini` (`lib/gemini.ts`), `youtube` (`lib/youtube.ts`) |
| the SCOPE of every scoped `package.json` `dependencies` key (`@<scope>/…`) — a vendor namespace, so no hand judgment of which keys "name a service" | `google`, `googleapis`, `supabase` (unscoped keys such as `next`, `react`, `zod` are generic words and are not taken) |
| the variable names in `.env.example` if present (measured absent) | — |
| `fly` if `fly.toml` exists | `fly` |

A match becomes a dependency only when it is an import, an invocation, a documented prerequisite, or a config read
without a working default (spec §5 rule 1, r2 CLAUDE M7); otherwise it is a mention with no id.

- [ ] **Cases**: `supabase inside a self-test fixture string is a mention` (the `page_markup.py` shape);
  `import of a project module is a dependency`; `an env read with a default that works is a mention`; `an env read
  whose absence raises is a dependency`; `a verdict cannot cite a mention` (no id is ever emitted for one);
  **`the derived vocabulary on the live tree contains an element EQUAL to supabase, gemini and fly, and an element
  that STARTS WITH youtube-playlist`** (each term spec §5 item 1 names; the derived names are
  `youtube-playlist-summaries[-cloud]`, so equality would be red on a correct derivation; an identity case on the
  live tree); **`a fixture repo with no Mocking boundaries paragraph and no
  lib/gemini.ts yields no gemini`** (the adjacent negative — the term comes from the source, not from the code);
  `the source of derive_vocabulary contains no string literal EQUAL to any of the four spec terms` (structural, and
  now satisfiable: the directory rule is a predicate, not a list; the `fly` rule's literal is `"fly.toml"`, which
  equals none of them). Red → implement → green → WM → commit.

**FAILS IF:** `page_markup.py`'s two `supabase` matches produce a dependency finding; or the live vocabulary lacks
any of `supabase`, `gemini`, `fly`, `youtube-playlist`; or `derive_vocabulary`'s source contains a string literal equal
to one of them.

### Task 10: detectors 2 (cross-repo invocation) and 3 (self-test and user docs)

**Files:** Modify `scripts/check-publishability.py` (WM pins)

**Interfaces:**
- Consumes: `resolve` (Task 8); `closure` external list (Task 7).
- Produces: findings with `detector: 2` (`kind: "cwd-relative"` or `"outside-set"`) and `detector: 3`
  (`kind: "no-self-test"`, `"no-user-doc"`).

Detector 2 judges against the INSTALLED layout: a `python3 scripts/X` in a SKILL.md or contract is `cwd-relative`
even when `X` is in the package, and the finding records the known fix `${CLAUDE_PLUGIN_ROOT}/scripts/X` (spec §4).

- [ ] **Cases**: `explainer-delivery.md's three invocations are three cwd-relative findings with the plugin-root
  fix named` (the real file); `an invocation of a file outside every package is outside-set`; `a script with
  --self-test and a usage block has no detector-3 finding`; `page_chrome.py with no CLI is not a detector-3 finding
  when its role is library`. Red → implement → green → WM → commit.

**FAILS IF:** `explainer-delivery.md` scores zero detector-2 findings.

### Task 11: detectors 4 (bare names) and 5 (prose skill dependencies)

**Files:** Modify `scripts/check-publishability.py` (WM pins)

**Interfaces:**
- Consumes: `resolve` (Task 8); `derive_vocabulary` (Task 9).
- Produces: findings `detector: 4` (`kind: "guard-name"|"doc-path"|"tool-name"`) and `detector: 5`
  (`kind: "requires-skill"`).

Bare guard names are derived from `ls scripts/check-*.py` stems; doc paths are repo-relative paths under `docs/`
that the package does not ship. Detector 5 matches an instruction to load or use another skill (`load the X
skill`, `use /X`, `X skill` in a prerequisite sentence) whose skill is not in the same package.

**Tool names come from a hand-written, dated list (⟳ r1 CLAUDE M5 / CODEX 5).**
The r0 rule confirmed candidates against `docs/available-skills.md`, which lists skills and commands and contains
none of `TaskList`, `TaskCreate`, `PushNotification`, `AskUserQuestion` (measured: `grep -c` → `0`), so it
confirmed nothing; and the camel-case pattern also matches `JavaScript`, `SessionStart`, `PreToolUse`, …. No file
in this repository lists the harness's tools (`.claude/settings.json`'s hook `matcher`s name only the tools a hook
watches — measured: `Agent`, `Skill`, `AskUserQuestion`, `Bash`, `Edit`, `Write`, `Read`, `SendMessage`; no
`TaskList`). So Task 11 commits `docs/marketplace/harness-tools.txt`: one tool name per line, headed by the date,
`claude --version` (2.1.322 on 2026-11-11), and its source. **The source is the COORDINATOR's tool list, written
by the coordinator, not by the implementing subagent (⟳ r2 CLAUDE m3):** a subagent's harness may expose fewer
tools (the r2 reviewer, a subagent, had no `TaskList`/`TaskCreate`), so "the writing session's list" would vary
with who wrote it. **Provenance limit, stated:** the list is one session's view of one harness version; nothing
in the repository can check it is complete, so the calibration's tool-name item is a MEMBERSHIP check (`TaskList`
is on the list and is found), not evidence the list is right. Spec §5 item 4 does not require tool names to be
derived (only detector 1's vocabulary is, item 1), so this is a choice within the spec, **not a deviation**, and
no owner decision is needed (the r1 fold's "STATED deviation" label is withdrawn). The detector reports a camel-case word as `tool-name` only if it is on that
list. The list is data the scan reads, so it can be stale; the case below makes a stale list visible rather than
silent.

**The calibration population is the ground-truth passage of `brief/SKILL.md`, not the whole file (⟳ r1 CLAUDE
M4).** Spec §4's nine are counted over `brief`'s *Step 1* reading list — at `2f5e3f3d`, the lines from *"Then read,
in this order"* through the ratchet names (`check-docs`, `check-roadmap-consistency`, `check-test-counts`,
`check-producer-enumeration`). The detector run over the WHOLE file finds more, correctly — **measured by the
detector's own rule, not by a regex (⟳ r2 CLAUDE M4: the r1 fold counted `check-[a-z-]+` matches and so listed
`check-deploy-freshness`, which is not a guard):** each `check-*` match is kept only if `scripts/<stem>.py`
exists. Over the file (fold r2, `2f5e3f3d`..HEAD `git diff --stat` empty): `check-docs`,
`check-producer-enumeration`, `check-roadmap-consistency`, `check-selftest-counts`, `check-test-counts` exist;
`check-deploy-freshness` does **not** (`ls scripts/check-deploy-freshness.py`: no such file; line 78 says the gate
*"was nearly built as `check-deploy-freshness.py`"*). Doc paths: the four of the nine plus `docs/dev-process.md`
(line 31, before the passage; the passage's own `dev-process.md` is bare). So the whole file yields the nine plus
**exactly two** extras: `check-selftest-counts` (line 167) and `docs/dev-process.md`. **A historical mention is
not a dependency** — spec §5 (line 842): *"a historical comment naming a guard is **not** an invocation"*, and
§5 rule 1: *"A match is a MENTION CANDIDATE until something makes it a dependency … Mention candidates are
**reported separately** from dependency findings."* So line 78 is excluded twice over: its name is not a guard
(no file), and a historical sentence naming a real guard would be a mention candidate, never a dependency finding.
The whole-file case asserts the NAMES detector 4 reports in either list; which list each lands in is §5 rule 1's
business, not this case's. The extras are reported separately with their names, never asserted away and never
counted into the nine.

- [ ] **Cases**: **calibration** `the ground-truth passage of brief/SKILL.md (fixture copy committed with the case,
  taken at 2f5e3f3d) yields exactly the 9 items of spec §4: 4 guard names (check-docs, check-producer-enumeration,
  check-roadmap-consistency, check-test-counts), 4 doc paths (docs/backlog.md, docs/reviews/,
  docs/roadmap-to-launch.md, docs/superpowers/), 1 tool name (TaskList)`; `the whole fixture file yields those 9
  plus exactly check-selftest-counts and docs/dev-process.md` (the extras named, so a detector that silently
  narrows to the passage goes red); `check-deploy-freshness (line 78: a check-* name with no scripts/ file, in a
  historical sentence) is not a guard-name item` beside `check-selftest-counts (file exists) is` (adjacent
  negative, ⟳ r2 CLAUDE M4); `a camel-case word absent from harness-tools.txt (JavaScript,
  SessionStart) is not a tool-name finding` (adjacent negative); `a harness-tools.txt with no date or version
  header is CANNOT RUN`; `brief and explain-findings require artifact-design` (detector 5); `a skill required from
  inside the same package is not a finding`. If the live `brief/SKILL.md` differs from the fixture, the
  difference is reported, never absorbed. Red → implement → green → WM → commit.

**FAILS IF:** the calibration case on the passage finds any count other than exactly 9 (fewer: an item missed;
more: the population leaked) — or the whole-file case does not name both extras, or names
`check-deploy-freshness`.

### Task 12: detectors 6 (runtime prerequisites) and 7 (inbound registration); CI; the first report

**Files:**
- Modify: `scripts/check-publishability.py` (WM pins), `.github/workflows/ci.yml`
- Create: `docs/marketplace/scan-<YYYY-MM-DD>.json`

**Interfaces:**
- Consumes: everything above.
- Produces: findings `detector: 6` (`kind: "import"|"executable"|"config"`) and `detector: 7`
  (`kind: "needs-registration"`, or the exemption `invoked-by: user`); the dated report file.

Detector 6: an `import` not in `sys.stdlib_module_names` and not a module in the same package; an executable
reached by `subprocess`/`shutil.which`/a shell line (`gh`, `git`, `node`, `npx`); a config read per Task 9's rule.
Detector 7 per spec §5 item 7: a component that needs a host registration to do anything must declare it; the
exemption is a literal `invoked-by: user` in its usage block or skill front matter; a test-only invoker does not
discharge it.

- [ ] **Cases**: `a fixture importing an absent package is a detector-6 finding` (the constructed positive);
  `gen-dashboard.py's gh call is an executable finding`; `a regen hook with a settings.json stanza and no
  declaration is needs-registration`; `a CLI declaring invoked-by: user is exempt`; `a hook invoked only by its
  self-test is needs-registration`. Red → implement → green → WM.
- [ ] **CI:** `python3 scripts/check-publishability.py --self-test` in `ci.yml`'s verify job (W7). The full scan
  needs `shipping-sets.json`, which is committed, so CI also runs the scan with `--out /dev/null` and fails on
  CANNOT RUN (a scan that cannot reach its subject in CI is red, not skipped).
- [ ] **Report:** run the scan on the live tree; commit `scan-<date>.json` with `measured_at` = the commit.

**FAILS IF:** any detector 3-7 has no mutation that goes red (`python3 scripts/check-plan-code.py --mutate .
--only scripts/check-publishability.py`), or CI's scan step exits 0 on an emptied `shipping-sets.json`.

---

## Slice E — the install experiment on effort (3) (spec §6, §7 items 3b and 4)

### Task 13: the seeded stranger repository

**Files:**
- Create: `scripts/mkt_seed_repo.py` (W1-W8)

**Interfaces:**
- Consumes: nothing.
- Produces: `seed(out: Path) -> KnownFacts` and `known-facts.json` beside the repo: for each of `brief`'s
  ground-truth items, the expected answer, including `"expected": ""` with `"empty_is_correct": true` where the
  seeded fact is emptiness (for example a clean `git status --short`).

The repo has a fixed commit history (fixed author, fixed dates via `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE`), its
own `docs/roadmap-to-launch.md` and `docs/backlog.md` with known rows, one `scripts/check-docs.py` that prints a
known line, and no `.claude/`. It must use `fixture_git.isolated()` (W8).

- [ ] **Cases**: `two seeds give identical trees` (determinism); `every ground-truth item has an expected answer`;
  `at least one item is correctly empty and one is non-empty` (so pass condition 2 can fail both ways). Red →
  implement → green → W1-W8 → commit.

**FAILS IF:** two runs of `seed` produce different `git rev-parse HEAD`.

### Task 14: tier A — install the comprehensibility package and run it in the seeded repo

**Files:**
- Create: `docs/marketplace/experiment-tier-a.md` (record, coverage matrix, pass conditions)

**Interfaces:**
- Consumes: `build_world`, `preflight`, `run_isolated` (Task 2); `stage`, `install` (Task 3); `seed`,
  `known-facts.json` (Task 13); `ScanReport` (Task 8).
- Produces: the record's three lists — suite defects, scan defects, unobservable accesses — and the coverage
  matrix (entry-point × exercised? × scenario name).

Two halves, because a model call needs a login (measured 2026-11-11: `claude -p` under a fresh `HOME` prints
`Not logged in · Please run /login`):

- **Scripted half (autonomous):** for each entry-point script of the package, by its installed path, from inside
  the seeded repo: one useful operation each (compose a page with `brief-compose.py`, serve it with
  `explainer-serve.py` (on 7391 only, once preflight confirms it free; else CANNOT RUN waiting on H7, Task 4
  Step 2; the serve counts as `operation_ok` only under Task 4 Step 3 (b)'s three conditions — start says
  `serving <world HOME>/explainers`, world pidfile pid = listener pid, `GET /` names a seeded sentinel — else, routed as
  Task 4 Step 3 (⟳ r3 CODEX M1): an isolation failure is CANNOT RUN waiting on H7, and the world's verified own
  server failing is a recorded component failure (a suite defect) with its evidence, never CANNOT RUN and never pass), `GET` the page and its Ask endpoint, run each generator's documented command). Record a
  `RunRecord` per operation.
- **Skill half (needs Human step H2's token):** with `CLAUDE_CODE_OAUTH_TOKEN` from the file H2 produced (never
  committed, never echoed), `claude -p --permission-mode bypassPermissions "/comprehensibility:<skill> …"` invokes
  each of the four page skills in the seeded repo (a plugin skill is invoked under `-p` by its namespaced slash
  name; the first run records the exact form that worked, and a form that does not resolve the skill is a
  baseline defect to fix, never a suite defect — ⟳ r1 CLAUDE m7). The token and the permission mode are recorded
  baseline deviations (Task 2 Step 4): a stranger has their own login and answers their own prompts. If H2 has not happened, the skill half is
  **CANNOT RUN**, recorded with that reason, and every skill entry-point is `argued` (spec §4: CANNOT RUN is not a
  component failure).

- [ ] **Step 1:** seed, build the world (allow: `python3`, `git`, `claude`; NOT `gh`), preflight empty, install.
- [ ] **Step 2:** scripted half; Step 3: skill half or its CANNOT RUN line.
- [ ] **Step 4:** score the five pass conditions of spec §6 per entry-point; for pass condition 2 compare every
  ground-truth answer with `known-facts.json` and mark `correct`, `correctly-empty`, `missing-capability`, or
  `wrong`; condition 4(a) answered for each component (does it document recovery?). **Ground truth exists only
  for `brief`** (`known-facts.json` seeds `brief`'s items; ⟳ r1 CLAUDE m9): pass condition 2 is scored against it
  for `brief` alone, and for `explain-diff`, `explain-findings`, `explain-topic` and `dashboard` it is recorded
  `not scored — no seeded facts`, which makes their condition 2 `argued` (their other conditions keep whatever
  grade their own scenario earns).
- [ ] **Step 5:** for every failure, record whether the scan predicted it (a finding id) — feeds Task 16.
- [ ] **Step 6:** write the record, AND its machine-readable sidecar `docs/marketplace/experiment-tier-a.json`:
  `{"measured_at", "components": {id: {"exercised": bool, "scenario": str|null, "operation_ok": bool,
  "pass_conditions": {"1".."5": "pass"|"fail"|"argued"|"CANNOT RUN"}}}}` — the coverage matrix as data, which
  Task 19's SHIP-versus-experiment rule reads (⟳ r1 CLAUDE M7). Spend-log row; commit.

**A hollow page is a FAILED measurement, not an unmeasured one (⟳ r1 CODEX 3).** Spec §4b defines `measured` as
exercised with a named scenario, and a measured run may fail. A page whose `missing-capability` items are non-empty
keeps its `measured` grade and FAILS pass condition 2, which supports `NEEDS-WORK` and forbids `SHIP`.

**FAILS IF:** the record marks pass condition 2 `pass` — or the component `SHIP` — for a page skill whose page
carried `missing-capability` or `wrong` on any item whose seeded fact is non-empty (the hollow-page case, spec §6);
or a `measured` grade names no scenario; or the sidecar and the Markdown record disagree on any component's
`exercised` or pass-condition value.

### Task 15: tier B — a real third-party harness repository

**Files:** Create `docs/marketplace/experiment-tier-b.md`

**Interfaces:**
- Consumes: as Task 14 (no `seed`).
- Produces: the tier-B record with the third list: resources reached that belong to the host repo.

Repository choice (spec §6 criteria): `Yeachan-Heo/oh-my-claudecode`, MIT, FULL clone (`git clone` without
`--depth`) into the scratchpad; the copy under `~/.claude/plugins/marketplaces/omc` is shallow and is NOT used.
Nothing is ever pushed or written back (a remote-less clone: `git remote remove origin` after cloning).

- [ ] **Steps:** clone → record its commit → world + install → scripted half and (if H2) skill half → list every
  `RunRecord.opened` path inside the host repo → record → commit.

**FAILS IF:** the record cites a git-history item as a suite defect without having confirmed the clone is full
(`git rev-parse --is-shallow-repository` = `false`).

### Task 16: reconcile the experiment with the scan (spec §5's falsifier)

**Files:** Modify `scripts/check-publishability.py` (WM pins) as needed; modify both experiment records.

**Interfaces:**
- Consumes: Tasks 12, 14, 15.
- Produces: a `scan defects` list in each record that is empty or every entry closed by a scan commit.

- [ ] For each blocker or degraded result the experiment hit on a component the scan scored clean: add a case that
  reproduces it as a fixture (red), fix the detector (green), re-run the scan, commit a new `scan-<date>.json`. A
  finding that the scan cannot express is recorded as a stated limit of the scan, never as a footnote.

**FAILS IF:** a tier-A or tier-B record lists an experiment failure on a scan-clean component with no
corresponding scan case.

---

## Slice F — the inventory, the cost record and the checkpoint (spec §2b, §2c, §4b, §4c, §7 items 4b-11)

### Task 17: effort (2) — scan, cost record and first route, as a CI layer

**Files:** Create rows in `docs/marketplace/inventory.json` for every effort (2) component.

**Interfaces:**
- Consumes: `ScanReport` (Task 12); `components.json` (Task 5); the `ci-layer` entry of `shipping-sets.json`
  (Task 6 — declared from the map, `channel: reusable-workflow`, no installed tree).
- Produces: inventory rows (schema in Task 19).

For the three pieces of spec §3 Effort (2) — (a) matrix sharding, (b) selection by closure / observed reach,
(c) the scheduled full sweep with a `sweep-red` issue — record: the scan's findings read against GitHub Actions plus
an arbitrary mutation engine (a dependency on `check-plan-code.py` is a C3 finding), the cheapest route (D10: a
reusable workflow `uses: <owner>/<repo>/.github/workflows/<file>@<tag>` in the marketplace repo, spec §2c), and an
estimate of each cost. Compare each piece with the incremental/shard modes of Stryker, mutmut, PIT and
cargo-mutants **from each project's own documentation, fetched in this task**; any comparison not fetched is
written `unverified`. The mutation engine itself is expected `DON'T-SHIP` with `harvest: practice` candidates.
Grade: `argued` for all (spec §2b).

- [ ] **Steps:** read scan → fetch the four engines' docs → write rows → `python3 scripts/check-inventory.py`
  (after Task 19 exists; until then, validate the rows parse) → commit.

**FAILS IF:** a row's comparison sentence names an engine capability with no fetched source and is not marked
`unverified`.

### Task 18: effort (1) — scan, and the empty-corpus probe (D11 condition (a))

**Files:** Create rows in `inventory.json` for the four effort (1) components; a section in
`docs/marketplace/experiment-tier-a.md` named *Recall with an empty corpus*.

**Interfaces:**
- Consumes: `build_world`, `run_isolated` (Task 2); `ScanReport` (Task 12); Human step H2's token.
- Produces: the inventory's top-level `"recall": {"a": true|false|"CANNOT RUN", "b": "pass"|"fail"|"unanswered"}`
  with its evidence in the corpus row's notes and in the record, and the recall rows' `phase` resolved from it.

The probe: stage the `recall` package, run `.claude/hooks/surface-recall.sh` and `scripts/recall-llm.py` in the
seeded repo with NO memory corpus reachable (spec §3: `recall-llm.memory_dir()` returns `None` in a clone). The
world's allow-list is `python3`, `git`, `bash` and `claude` (⟳ r1 CLAUDE m8: `surface-recall.sh` starts
`#!/usr/bin/env bash`, and `recall-llm.py` shells out to `claude -p` at `recall-llm.py:924`), and the model half
needs H2's token. Without H2 — or with `bash`/`claude` unreachable — the probe is **CANNOT RUN** and `a` is
recorded `"CANNOT RUN"`, never `false`: a probe that could not run says nothing about usefulness and must not
decide D11 (a). Record what happens: an error, a silent no-op, or a useful behaviour (for example, telling the user
how to start a corpus). Condition (a) is met only if a stranger with an empty corpus gets something useful on day
one; a silent no-op is NOT useful. Condition (b) is Human step H1 and is never decided here. The corpus row carries
`C5: unanswered — blocked on the content review` until H1 lands, and its verdict cannot be the ship verdict.

**The phase is written, and it has TWO values, not three (⟳ r1 CODEX 2, CLAUDE m3; ⟳ r2 CLAUDE M3).** Spec §2c,
D11 (spec line 145): *"Recall is in phase 1 **only if** (a) it is useful to a stranger whose memory corpus starts
**empty**, and (b) our own corpus passes the owner's **content review** (C5's corpus half). Either one failing moves
(1) to 'later'."* "Only if" makes phase 1 conditional on BOTH conditions being established, so Task 18 rewrites
every recall row's `phase`: `a` is `true` AND `b` is `"pass"` → `"1"`; **anything else → `"later"`** — including
H1 unanswered and `a` CANNOT RUN, whose reason goes in the row's notes (`later — pending H1`,
`later — probe CANNOT RUN (H2)`), as a note, never as a phase. Spec line 1205 expects the corpus row to end this
milestone at *"`C5: unanswered — blocked on the content review`"*, so `"later"` is the expected outcome, not an
edge. The r1 fold kept a third, UNRESOLVED value (`"1-if-feasible"`) and a checkpoint branch that refused over it
with rc 2; nothing downstream (Tasks 20, 21, 22, the CI caller) had an exit for that state, so it is **removed**,
not routed. `"1-if-feasible"` survives only as the map's label in `components.json` (Task 5, the spec's own
word); an inventory row never carries it (Task 19 refuses it). **If H1 (or H2) lands later**, Task 18's phase step
is re-run, then `check-inventory.py` and Task 21 — a recall row moving to `"1"` changes the checkpoint's
population, and the checkpoint is answered over the new one.

**Build the shipped corpus (step added 2026-11-13, from the owner's answers to walkthrough decision 5).** The shipped
memory corpus is built from `docs/memory/`, never edited in place there. Per `docs/marketplace/decision-5-suspect-files.md`
→ *Answered*: **group A** (6 files) is **redacted**: the Supabase project ref, the Fly URL and the role names are
replaced with placeholders; **groups B and C** (10 files) are **excluded**; **group D** (6 files) has the owner's quotes
**paraphrased** into neutral wording with every rule kept; the ~170 other files are copied as they are. Each of the
two transforms has its own check, and **each check reads the BUILT OUTPUT**, not the transform's code: it greps the
output tree for the original ref, URL, role names (redaction) and for the quote text (paraphrase), and **fails if
any is found**. The originals are DERIVED at check time from the source files, never typed into the check, so the
check neither goes stale nor itself publishes the ref. A check that finds no originals to look for in the SOURCE is a
failure (CANNOT RUN), not a pass. The corpus row's C5 moves off `unanswered` only when the build and both checks pass.

**FAILS IF:** the probe ran with any path under this repository's `docs/memory/` in its `RunRecord.opened`; or a
recall row has `phase: "1"` while `recall.a` is not `true` or `recall.b` is not `"pass"`; or any inventory row has
`phase: "1-if-feasible"` (Task 19 refuses both); or `recall.a` is `false` on a record whose probe was CANNOT RUN.

### Task 19: `scripts/check-inventory.py` — the falsifiers as a guard, and the checkpoint

**Files:**
- Create: `scripts/check-inventory.py` (W1-W8)

**Interfaces:**
- Consumes: `inventory.json` rows written by Tasks 17-18 (and 20); `components.json` (Task 5);
  `shipping-sets.json` (Task 6); the latest `scan-<date>.json` (Task 12); `experiment-tier-a.json` (Task 14).
- Produces: `checkpoint_fires(rows: list[dict]) -> bool`; `row_errors(row: dict, scan: dict) -> list[str]`;
  `render(rows) -> str` (Markdown, verdict and grade in ONE table cell); CLI rc 0 clean, 1 row errors,
  2 CANNOT RUN, **3 CHECKPOINT** (the D1 checkpoint fired: stop and go to Human step H4).

Row schema (one per component in `components.json`; a missing component is an error):

```json
{"id": "brief", "effort": 3, "roles": ["entry-point"], "phase": "1",
 "verdict": "NEEDS-WORK", "grade": "measured", "scenario": "tier-A scripted: brief-compose page",
 "cites": ["brief:4:1", "brief:2:1"], "harvest": "none", "practice_entry": null,
 "criteria": {"C1": "pass", "C2": "pass", "C3": "fail", "C4": "fail", "C5": "pass"},
 "cost": {"public_bar_hours": 6.0, "next_project_hours": 2.0, "grade": "argued"},
 "route": {"kind": "decouple-config", "cost_hours": 4.0, "grade": "argued"}}
```

`row_errors` refuses, each a spec falsifier: **ANY row whose grade is missing** (§4b: *"Every component in the
inventory carries both fields. A verdict without a grade is an incomplete row"* — ⟳ r1 CLAUDE M7, the r0 rule
checked SHIP rows only); **a `SHIP` row in a `plugin`-channel package that the experiment does not back** (§9: *"a component marked `SHIP`
that the install experiment cannot run"*), applied BY ROLE because spec §4's role table assesses C4 differently per
role (⟳ r2 CLAUDE m1 — the r1 rule read every row's own sidecar entry, which barred SHIP for every library): an
**`entry-point`** row needs its own `experiment-tier-a.json` entry with `exercised: true`, `operation_ok: true`
and no pass condition `fail` or `CANNOT RUN` — a MISSING entry means the experiment did not run it, so SHIP is
refused (this is why recall's entry-points, which tier A does not run, cannot be `SHIP` this milestone); a
**`library`** row is held to the same test on the entry-point its `scenario` names (§4: C4 is *inherited*), not on
an entry of its own — a SHIP library whose `scenario` names no entry-point component id is refused; a **`data`** row is outside the rule (§4: its C4 is *struck*). `ci-layer` rows are outside it
too, because the spec gives effort (2) no experiment this milestone (§2c); **a phase-1 row
whose component is absent from its package's `components` in `shipping-sets.json`** (§9 D11's "named subset that
has no shipping set", per component, not only per package); **a row whose `phase` is neither `"1"` nor `"later"`, or a recall
row at `"1"` unless the inventory's `recall.a` is `true` and `recall.b` is `"pass"`** (§2c D11's "only if"; Task
18 resolves the map's `"1-if-feasible"`, ⟳ r2 CLAUDE M3);
**`next_project_hours` ≤ 0** (the ratio is undefined; ⟳ r1 CLAUDE m2); an `inherited` grade with no
`scenario` (§4b); a non-ship verdict with no `cites`, or citing an id the scan did not emit (§5 rule 1); a non-ship
row with no `route` (§9 D10); a `practice` harvest with no `practice_entry` naming a heading that exists in
`docs/portable-practices.md` (§4c); a `data` row with a C4 value other than `"struck"` (§4); the memory-corpus row
with a ship verdict while its `C5` is `unanswered` (§7 item 11); a `measured` grade on an effort (1) or (2) row
(§2b); a cost with either estimate missing (§2b). And at the inventory level: no phase-1 package named, or a phase-1
package with no entry in `shipping-sets.json` (§9 D11).

The checkpoint, exactly as spec §2c states it (embedded because the threshold arithmetic is what the owner decided;
it is run as written below). ⟳ r1 CODEX 2 / CLAUDE m3: the r0 function counted every `"1-if-feasible"` row, so
recall rows D11 had already excluded could suppress the owner's checkpoint (Codex measured: three comprehensibility
rows with two at 3× fire alone; four added recall rows flipped it to False). Phase is resolved before counting
(Task 18 writes `"1"` or `"later"`), so the checkpoint counts phase `"1"` and nothing else. ⟳ r2 CLAUDE M3: the r1
fold's with-and-without branch for unresolved rows is **deleted** with the state it served. Extracted and run under
`python3 -I` at the r2 fold: every assert passes; the mutation that restores r0's population
(`== "1"` → `in ("1", "1-if-feasible")`) fails an assert.

```python
def _fires(pop):
    """public_bar >= 3 x next_project for MORE THAN HALF of `pop`."""
    if not pop:
        raise ValueError("CANNOT RUN: no phase-1 rows")
    for r in pop:
        if not r["cost"]["next_project_hours"] > 0:
            raise ValueError(f"CANNOT RUN: {r.get('id', '?')} has next_project_hours <= 0 "
                             "(a row error; row_errors must have refused it first)")
    over = [r for r in pop
            if r["cost"]["public_bar_hours"] >= 3 * r["cost"]["next_project_hours"]]
    return 2 * len(over) > len(pop)


def checkpoint_fires(rows):
    """D1 checkpoint (spec §2c) over the phase-1 population: phase "1" rows, and nothing else.
    Task 18 resolves recall to "1" or "later" (D11's "only if"); a row still carrying the map's
    "1-if-feasible" label is a row error refused before this runs (rc 1 outranks), and is not counted."""
    return _fires([r for r in rows if r["phase"] == "1"])


def _row(phase, pub, nxt):
    return {"phase": phase, "cost": {"public_bar_hours": pub, "next_project_hours": nxt}}


def _raises(rows):
    try:
        checkpoint_fires(rows)
    except ValueError:
        return True
    return False


C3 = [_row("1", 3, 1), _row("1", 3, 1), _row("1", 1, 1)]                          # 2 of 3 at exactly 3x
assert checkpoint_fires(C3)
assert not checkpoint_fires([_row("1", 3, 1), _row("1", 1, 1)])                    # 1 of 2 is not MORE than half
assert not checkpoint_fires([_row("1", 2.9, 1), _row("1", 2.9, 1)])                # below 3x
assert checkpoint_fires([_row("1", 9, 1), _row("later", 1, 1), _row("later", 1, 1)])  # later rows do not count
assert _raises([_row("later", 9, 1)])                                              # empty phase 1 is not "did not fire"
# r1 CODEX 2: recall moved to "later" (D11 failed) cannot suppress the checkpoint.
assert checkpoint_fires(C3 + [_row("later", 1, 1)] * 4)
# r2 CLAUDE M3: a stray "1-if-feasible" row is never counted (row_errors refuses it first), so it cannot
# suppress the checkpoint either — and it never makes the checkpoint refuse.
assert checkpoint_fires(C3 + [_row("1-if-feasible", 1, 1)] * 4)
# r1 CLAUDE m2: next_project_hours = 0 never fires automatically.
assert _raises([_row("1", 1, 0)])
assert _raises([_row("1", 0, 0)])
```

A `next_project_hours` of 0 is a row error (the ratio is undefined), never an automatic fire; the function also
refuses it, so the order of the two checks cannot turn it into a fire.

**Exit codes rank, and the order is the rule (⟳ r1 CLAUDE m2):** inputs unreadable or absent → **2**; else any
row error → **1**, and the checkpoint is NOT computed (a fire over rows with errors is not evidence); else
`checkpoint_fires` raising (no phase-1 rows — the only way left; inventory-level `row_errors` already refuses "no
phase-1 package named") → **2**; else fired → **3**; else
**0**. So rc 1 outranks rc 3.

- [ ] **Cases**: one per `row_errors` rule (each with an ADJACENT negative: the same row with the field fixed is
  clean — including `a NEEDS-WORK row with no grade is an error` beside the same row graded, and `a SHIP row whose
  tier-A entry is exercised: false is an error` beside `exercised: true, operation_ok: true`, and `a SHIP library
  row with no sidecar entry of its own, whose scenario names a passing entry-point, is clean` beside the same row
  naming a failing one), the checkpoint
  asserts above, `rows with an error AND a crossed threshold exit 1, not 3`, `render puts verdict and grade in one
  cell`, `a component in the map with no row is an error`. Red → implement → green → W1-W8 → commit.
- [ ] **CI caller — `--self-test` ONLY in this task (⟳ r1 CODEX 6).** The live inventory is necessarily incomplete
  here (Tasks 17-18 wrote effort (2)/(1) rows; effort (3) rows come in Task 20), and a missing component is rc 1,
  so enabling the live run now would put CI red by construction. The live caller is added in **Task 20**, in the
  same commit that completes the rows.

**FAILS IF:** the live inventory has a ship row with its grade in a different cell of `inventory.md`; or the
checkpoint fires on the live inventory and `check-inventory.py` exits 0; or this task's commit adds a `ci.yml`
step that runs `check-inventory.py` without `--self-test`.

### Task 20: the cost record and the cheapest routes for effort (3)

**Files:** Create/modify rows in `inventory.json` for every effort (3) component.

**Interfaces:**
- Consumes: Tasks 12, 14, 15, 16, 19.
- Produces: complete rows.

For each component: verdict from the evidence (scan findings + experiment), grade per §4b and §4's inheritance
table (a `library` is `inherited` only via a named measured scenario that exercised it; CANNOT RUN importers
contribute nothing), the two cost estimates, and for every non-ship row the cheapest of D10's routes with its cost.
Estimates are in hours of agent-implemented work including review to convergence under the round cap (at least
r1 with BOTH halves, then alternating halves; `docs/review-method.md` §0 Q4c — ⟳ r1 CLAUDE defaults table: "one
review round" understated it), graded `argued` unless something was
run (for example, a route whose fix was tried in the experiment's scratch copy, never in the repository, is
`measured`). Each estimate names its basis in one line (which findings it removes).

- [ ] **Steps (order matters — ⟳ r1 CODEX 4):** write rows → **write one `docs/portable-practices.md` entry per
  `harvest: practice` row across ALL efforts (the first is the `${CLAUDE_PLUGIN_ROOT}` practice of spec §4, item
  9b), so every `practice_entry` heading exists BEFORE the guard first reads the live inventory** (measured
  2026-11-11: no heading in `portable-practices.md` contains `CLAUDE_PLUGIN_ROOT`, so the r0 order — headings in
  Task 22, guard here — returned rc 1 on a valid row) → `python3 scripts/check-inventory.py` rc 0 or 3 → **add
  the live caller to `ci.yml`** (`python3 scripts/check-inventory.py`; rc 3 is printed and is NOT a CI failure,
  only rc 1 and 2 fail — Task 19 deferred it here, ⟳ r1 CODEX 6) → commit rows, practice entries and the caller
  together.

**FAILS IF:** `check-inventory.py` exits 1 on the committed inventory; or a `practice_entry` names a heading that
the commit's `portable-practices.md` does not contain; or the live `ci.yml` caller lands in a commit whose
inventory lacks a row for any component in `components.json`.

### Task 21: the D1 checkpoint (spec §2c) — STOP POINT

**Files:** none unless it fires (then the dashboard entry of Task 22 carries `[needs-you]`).

**Interfaces:**
- Consumes: `checkpoint_fires` via `python3 scripts/check-inventory.py` (Task 19).
- Produces: either "did not fire" recorded in `inventory.md`'s header, or Human step H4 opened.

- [ ] Run `python3 scripts/check-inventory.py; rc=$?; echo "rc=$rc"`. **Every exit has a path (⟳ r2 CLAUDE M3):**
  rc 0 → write "did not fire" in `inventory.md`'s header; rc 1 or 2 → the checkpoint was NOT computed: the
  inventory is **not final**, slice F stops here, and the row errors or unreadable inputs are fixed and this step
  re-run (never read as "did not fire"); rc 3 → write the selection card (A: keep D1, the
  public bar; B: drop to "my next project"; recommendation stated with the ratio per phase-1 component), send the
  notification, mark the inventory **not final**, and stop slice F at this task. The coordinator does not continue
  past this point on its own (spec §2b).

**FAILS IF:** rc 3 and Task 22 is marked final without a recorded owner answer (spec §2c's FAILS IF); or rc 1 or
2 and `inventory.md`'s header says "did not fire".

### Task 22: finish the inventory — render, harvest, rubric, backlog, roadmap, dashboard

**Files:**
- Create: `docs/marketplace/inventory.md` (generated by `python3 scripts/check-inventory.py --render`)
- Modify: `docs/portable-practices.md` (the rubric entry, spec §7 item 9; the item 9b `harvest: practice` entries
  were already written in Task 20, before the guard read them), `docs/backlog.md` (one row per
  `NEEDS-WORK` component with its named defect and nothing else, item 6; area `(process / deliverable #2)`, already
  claimed in `docs/features.md`), `docs/roadmap-to-launch.md` (the milestone's status line and ticks under the
  existing `harness-ships-elsewhere` section), `docs/dashboard-entries.md`.

**Interfaces:**
- Consumes: Tasks 19-21.
- Produces: the phase-1 subset named with its package and shipping set; the inventory marked final only if
  `check-inventory.py` exits **0**, or exits **3** and the owner's H4 answer is recorded — never on rc 1 or 2.

Spec §7 item 7 (register the anchor, close backlog row 290) is **already done** on master at `2f5e3f3d`:
`docs/anchors.md` registers `harness-ships-elsewhere` and row 290 is ✅. This task only verifies it
(`python3 scripts/check-anchors.py` rc 0).

- [ ] **Steps:** rubric entry → render → backlog rows (`python3 scripts/gen-backlog-page.py --self-test`
  after editing `backlog.md`) → roadmap → dashboard entry → all document guards → commit →
  `python3 scripts/check-dashboard-entry.py`.

**FAILS IF:** a backlog row is filed for a component whose verdict is not `NEEDS-WORK`, or `inventory.md` differs
from `--render`'s output (the page is derived, never hand-edited), or the inventory is marked final while
`check-inventory.py` exits 1 or 2.

---

## Human steps (never done by an agent)

| # | Step | Needed by | If it does not happen |
|---|---|---|---|
| **H1** | ✅ **ANSWERED 2026-11-13 11:25 (walkthrough decision 5)** — **C5 content review of the memory corpus** (`docs/memory/`): A ship redacted, B exclude, C exclude, D ship with quotes paraphrased, the rest as they are (`docs/marketplace/decision-5-suspect-files.md` → *Answered*). The answer takes effect only when Task 18's *Build the shipped corpus* step and its checks pass. Spec §7 item 11. | the recall phase decision (D11 (b)) | the corpus row stays `C5: unanswered`; recall rows are `"later"` (D11's "only if"; Task 18). If H1 lands later and passes with `recall.a` true, Task 18's phase step, `check-inventory.py` and Task 21 re-run |
| **H2** | **A login token for the skill half of the experiment**: run `claude setup-token` and save the token to a file outside the repository (path told to the coordinator, never pasted into chat or committed). | Task 14/15 skill half | the skill half is CANNOT RUN; the four page skills stay `argued` |
| **H3** | **Re-decide the method if the spike fails** (spec §9: D4 is unachievable; never silently downgrade to paper scoring). | Task 4 NO-GO | the plan stops after slice B |
| **H7** | **Free port 7391 for the experiment window**: stop your own explainer server (`python3 scripts/explainer-serve.py --stop` in your checkout) and say when; restart it afterwards. The port is a constant, so the stranger's server can only run there (Task 4 Step 2). | Task 4 (b), Task 14/15 serve operations | the serve operations stay CANNOT RUN; the spike is INCOMPLETE, slice C waits, and Task 1 splits into its own PR (Task 4 Step 5) |
| **H4** | **Answer the D1 checkpoint card** (keep the public bar, or drop to "my next project"). | Task 21 rc 3 | the inventory stays not final |
| **H5** | ✅ **DONE 2026-11-13 03:48 — the copyright holder is `Kujin Lee`** (walkthrough decision 7). The MIT `LICENSE` that H6 adds reads `Copyright (c) <year> Kujin Lee`. | the NEXT milestone | nothing in this plan blocks |
| **H6** | **Create the published marketplace repository, add its `LICENSE`, any listing, the first tag and `CHANGELOG`** (spec §10, D9). | the NEXT milestone | out of scope here |

## Before every push (all slices)

Run in the slice's worktree; read each `rc` on its own line (`cmd; rc=$?; echo "rc=$rc"`), never after a pipe. The
list is the `python3 scripts/check-*` steps of `.github/workflows/ci.yml` (`docs/CLAUDE.md` rule 1), taken from the
workflow at push time, plus for slices that add a script: `python3 scripts/check-selftest-counts.py --changed`,
`python3 scripts/check-fixture-variation.py`, `python3 scripts/check-ratchet-contract.py`, and
`python3 scripts/check-plan-code.py --mutate . --only <each new or changed script>`. Slice C also runs
`python3 scripts/check-shipping-sets.py --closure` locally (CI cannot; Task 7). Open each slice's PR as a DRAFT at
slice start so CI's selected sweep runs early.

## Self-review notes (coverage of the spec)

| Spec item | Task |
|---|---|
| §7 item 0b, isolation baseline + capture mechanism and its limits | 2 |
| §7 item 0, packaging spike; §9 D3 falsifier | 3, 4, H3, H7 |
| §3 mapping step (map first, then count; every supporting artifact mapped or excluded) | 5 |
| §7 item 2, declaration from the installed tree; three producers | 6, 7 |
| §5 file-set rules (symlinks, identity, independent declaration, three mutations) | 8, 7 |
| §5 detectors 1-7, mention vs dependency, ids | 9-12 |
| §7 item 3, scan + self-test + manifest + CI | 8-12 |
| §6 / §7 item 3b, seeded repo, tier B, coverage matrix | 13-15 |
| §7 item 4, experiment record with what capture cannot see | 14, 15 |
| §5 falsifier: experiment failure on a scan-clean component | 16 |
| §2c effort (2) as a CI layer; engines compared from their docs | 17 |
| §2c D11 condition (a) empty corpus; (b) content review | 18, H1 |
| §4b two axes and its checkable falsifier; §4 roles and inheritance; §4c harvest; §9 D10, D11 | 19, 20 |
| §7 item 4b cost record and routes | 20 |
| §2c / §7 item 4c D1 checkpoint | 19, 21, H4 |
| §7 items 5, 6, 9, 9b, 10 | 22 |
| §7 item 7 (anchor, row 290) | already on master; verified in 22 |
| §7 item 8 (D8 corrections: slice B's FIRST commit, not a separate PR) | 1 |
| §7 item 11 (C5 corpus review) | H1, 18, 19 |
| §4d D9, §10 publication | H5, H6 (next milestone) |
