# Marketplace inventory — implementation plan (exploration milestone, phase 1 of D11)

> **Anchor:** `harness-ships-elsewhere` — **ADR:** 0015
> **Goal:** The harness this project built can be installed and used by someone who has never seen this repository.

**Status:** 📝 DRAFT, written 2026-11-11 from the approved spec at `2f5e3f3d` (spec approved by the owner
2026-11-11 05:53, merged as `d18167ce`). Phase 2: dual adversarial review to convergence or the round cap
(`docs/review-method.md` §0 Q4c) before any task is dispatched. Nothing is built.

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
  published marketplace repository, a marketplace listing, a `LICENSE`, naming the copyright holder, pushing to
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

Each slice is ONE pull request off fresh `origin/master`, with its own dual review. Slices A-C can merge without
the experiment; slice F cannot be final before Task 21's checkpoint is answered.

| Slice | Branch | Tasks | What merges | Outward-facing? |
|---|---|---|---|---|
| A | `mkt-d8-corrections` | 1 | the three `portable-practices.md` corrections (spec §7 item 8, D8) | no |
| B | `mkt-spike` | 2-4 | isolation tool, staging tool, spike record | no (local marketplace in a temp dir) |
| C | `mkt-shipping-sets` | 5-7 | component map, shipping-set declaration, closure guard | no |
| D | `mkt-scan` | 8-12 | `check-publishability.py` + CI | no |
| E | `mkt-experiment` | 13-16 | seeded repo builder, tier-A and tier-B records, scan fixes | no (read-only clone) |
| F | `mkt-inventory` | 17-22 | effort (1)/(2) readings, inventory guard, cost record, checkpoint, inventory | no; Task 21 may STOP for the owner |

**Ordering.** A is independent and goes first (spec §7 item 8: "its first commit and mergeable alone"). B before C
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
| `docs/marketplace/scan-<date>.json` | one scan report, dated, with the commit | Task 12 |
| `scripts/mkt_seed_repo.py` | builds the tier-A seeded stranger repo and its known-facts file | Task 13 |
| `docs/marketplace/experiment-tier-a.md`, `experiment-tier-b.md` | spec §7 items 3b and 4 | Tasks 14, 15 |
| `docs/marketplace/inventory.json` | the inventory rows (spec §7 items 4b, 5, 9b) | Tasks 17-20 |
| `scripts/check-inventory.py` | spec §9 falsifiers decidable from the inventory; the D1 checkpoint; renders `inventory.md` | Task 19 |
| `docs/marketplace/inventory.md` | generated view: verdict and grade in one cell | Task 22 |
| `docs/marketplace/spend-log.md` | the milestone's own cost, per slice | every slice |

---

## Slice A — the D8 corrections (spec §7 item 8)

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
- [ ] **Step 4: dashboard entry, commit, then** `python3 scripts/check-dashboard-entry.py` (must say an entry block
  was added).

**FAILS IF:** any of the three phrases still occurs, or slice A's PR is still open when slice B's PR opens (spec
§7 item 8's bound: the corrections are first and mergeable alone).

---

## Slice B — isolation and the packaging spike (spec §6, §7 items 0b and 0)

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
  `env: dict[str, str]`); `preflight(world: World) -> list[str]` (refusal reasons, empty = clear);
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
  fixture); `preflight refuses when the explainer port is already listening` (bind a socket in the case, then
  release it); `preflight refuses an allow-listed command that resolves inside the repository`;
  `audit hook records an open of a fixture file`; `a non-Python child is listed as unobservable, never as zero
  opens`; `an unreachable command is CANNOT RUN (rc 2)`.
- [ ] **Step 2: run** `python3 scripts/mkt_isolate.py --self-test`; expected: fails (no implementation).
- [ ] **Step 3: implement** the four functions above. The explainer port is read from `scripts/explainer-serve.py`'s
  own default (import its constant, never type it).
- [ ] **Step 4: write `isolation-baseline.md`**: interpreter (`python3 -V` of the run), stdlib-only package set,
  the allow-listed commands with versions (`git --version`, `claude --version`, `node -v` if allowed), network
  policy (allowed only for `claude` model calls and the tier-B clone; nothing else), and the unobservable list.
  Every version is the output of a command in this session.
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
  (`scripts/x.py` → `<plugin>/scripts/x.py`, `.agents/skills/brief` → `<plugin>/skills/brief`);
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

- [ ] **Step 1:** stage ONE skill and ONE script: `.agents/skills/explain-topic` and `scripts/explainer-serve.py`,
  as package `spike` version `0.0.1`. (Choice: `explain-topic` is the smallest of the four page skills and
  `explainer-serve.py` is the script it ends in.)
- [ ] **Step 2:** build a world (allow: `python3`, `git`, `claude`), run `preflight` (must be empty), `install`.
- [ ] **Step 3:** from an unrelated directory inside the world, run the installed script by its installed path
  (`python3 <installed>/scripts/explainer-serve.py --help`) and one useful operation (start it on a free port,
  `GET /` returns 200, stop it). Record the `RunRecord`s.
- [ ] **Step 4:** also record what the skill's text tells the model to run, and whether that path resolves from the
  unrelated directory (expected, per spec §4: it does not, because the paths are CWD-relative; that is a finding,
  not a spike failure).
- [ ] **Step 5:** write the record: GO if the package installs and the installed script performs the operation by
  its installed path; NO-GO otherwise, with the failure.

**FAILS IF (and this is spec §9's D3 falsifier):** the package cannot be installed from the local marketplace, or
the installed script cannot be invoked from elsewhere. On NO-GO: stop the plan, file the record, and go to Human
step H3; do not proceed to slice C.

---

## Slice C — the component map and the shipping-set declaration (spec §3 mapping step, §7 item 2)

### Task 5: the component map and its completeness check

**Files:**
- Create: `docs/marketplace/components.json`, `scripts/check-shipping-sets.py` (mode `--map`)
- Modify (W1-W8): as Task 2, for `check-shipping-sets.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (reads disk).
- Produces: `components.json` with `{"measured_at": "<sha>", "components": [Component], "exclusions":
  [{"path", "reason"}]}`, where `Component = {"id", "effort": 1|2|3, "roles": ["entry-point"|"library"|"data"],
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
  (`comprehensibility`), one for recall (`recall`), one for the CI layer (`ci-layer`).**
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

- [ ] **Steps:** cases red → implement → stage and install all three packages from `components.json` → write the
  JSON → green → WM pins → commit.

**FAILS IF:** `shipping-sets.json` lists a file that is not in the installed tree, or `declare` opens any path
under `scripts/check-publishability*` (audit record).

### Task 7: the closure validator

**Files:**
- Modify: `scripts/check-shipping-sets.py` (mode `--closure`; WM pins)

**Interfaces:**
- Consumes: `shipping-sets.json` (Task 6); the installed tree from `install` (Task 3).
- Produces: `closure(installed: Path) -> set[str]` (every installed-relative path reached from the package's
  skills and entry-points by: Python `import` of a sibling module, `python3 <path>` / `bash <path>` in Markdown or
  shell, `source`, a `Read`-the-file instruction naming a path in a SKILL.md); `closure_gaps(decl, reached) ->
  list[str]`.

A reached path that resolves OUTSIDE the installed tree (CWD-relative, `docs/...`) is not a gap in the declaration:
it is reported as `external: <path>` and handed to the scan (detector 2). Only a reached path that exists in the
repository's version of the package but is missing from the declaration is a gap.

- [ ] **Steps:** cases (`omitted dependency with a count written to match is refused` — spec §5's third file-set
  mutation; `a CWD-relative invocation is external, not a gap`; `an import cycle terminates`) red → implement →
  green on the real declaration → WM pins → add `python3 scripts/check-shipping-sets.py --closure` to `ci.yml`
  only if CI can build the installed tree without `claude` (it cannot; so CI runs `--self-test` and `--map`, and
  `--closure` is a recorded local gate in the slice's pre-push) → commit.

**FAILS IF:** removing a member from `shipping-sets.json` and lowering its `expected_count` leaves
`--closure` green.

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

Vocabulary is derived, not hand-written: the repository name from `git remote get-url origin`, top-level
directories that exist only for the product (`supabase/`, `worker/`, `app/`, `lib/`, `components/`), the
`dependencies` keys of `package.json` that name a service SDK, the variable names in `.env.example` if present, and
`fly` if `fly.toml` exists. A match becomes a dependency only when it is an import, an invocation, a documented
prerequisite, or a config read without a working default (spec §5 rule 1, r2 CLAUDE M7); otherwise it is a
mention with no id.

- [ ] **Cases**: `supabase inside a self-test fixture string is a mention` (the `page_markup.py` shape);
  `import of a project module is a dependency`; `an env read with a default that works is a mention`; `an env read
  whose absence raises is a dependency`; `a verdict cannot cite a mention` (no id is ever emitted for one);
  `vocabulary contains no hand-typed literal` (the source of `derive_vocabulary` has no service-name string
  literal — a structural case). Red → implement → green → WM → commit.

**FAILS IF:** `page_markup.py`'s two `supabase` matches produce a dependency finding.

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

Bare guard names are derived from `ls scripts/check-*.py` stems; tool names from the set of tool names the harness
exposes that a stranger's install may lack (`TaskList`, `TaskCreate`, `PushNotification`, `AskUserQuestion`,
derived by grepping skills for `\b[A-Z][a-z]+[A-Z]\w+\b` and confirming each against `docs/available-skills.md`);
doc paths are repo-relative paths under `docs/` that the package does not ship. Detector 5 matches an instruction
to load or use another skill (`load the X skill`, `use /X`, `X skill` in a prerequisite sentence) whose skill is not
in the same package.

- [ ] **Cases**: **calibration** `brief/SKILL.md yields exactly the 9 items of spec §4: 4 guard names
  (check-docs, check-producer-enumeration, check-roadmap-consistency, check-test-counts), 4 doc paths
  (docs/backlog.md, docs/reviews/, docs/roadmap-to-launch.md, docs/superpowers/), 1 tool name (TaskList)` — if the
  live file has changed since `2f5e3f3d`, the case re-derives the expectation from a fixture copy committed with
  the case, and the live difference is reported, never absorbed; `brief and explain-findings require
  artifact-design` (detector 5); `a skill required from inside the same package is not a finding`. Red → implement
  → green → WM → commit.

**FAILS IF:** the calibration case finds fewer than 9 on the fixture copy.

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
  `explainer-serve.py`, `GET` the page and its Ask endpoint, run each generator's documented command). Record a
  `RunRecord` per operation.
- **Skill half (needs Human step H2's token):** with `CLAUDE_CODE_OAUTH_TOKEN` from the file H2 produced (never
  committed, never echoed), `claude -p` invokes each of the four page skills in the seeded repo. The token is a
  recorded baseline deviation: a stranger has their own login. If H2 has not happened, the skill half is
  **CANNOT RUN**, recorded with that reason, and every skill entry-point is `argued` (spec §4: CANNOT RUN is not a
  component failure).

- [ ] **Step 1:** seed, build the world (allow: `python3`, `git`, `claude`; NOT `gh`), preflight empty, install.
- [ ] **Step 2:** scripted half; Step 3: skill half or its CANNOT RUN line.
- [ ] **Step 4:** score the five pass conditions of spec §6 per entry-point; for pass condition 2 compare every
  ground-truth answer with `known-facts.json` and mark `correct`, `correctly-empty`, `missing-capability`, or
  `wrong`; condition 4(a) answered for each component (does it document recovery?).
- [ ] **Step 5:** for every failure, record whether the scan predicted it (a finding id) — feeds Task 16.
- [ ] **Step 6:** write the record; spend-log row; commit.

**FAILS IF:** the record marks a page skill `measured` while its page carried `missing-capability` on any item
whose seeded fact is non-empty (the hollow-page case, spec §6), or a `measured` grade names no scenario.

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
- Consumes: `ScanReport` (Task 12); `components.json` (Task 5).
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
- Consumes: `build_world`, `run_isolated` (Task 2); `ScanReport` (Task 12).
- Produces: `recall_feasible_a: true|false` with its evidence, in the corpus row's notes and in the record.

The probe: stage the `recall` package, run `.claude/hooks/surface-recall.sh` and `scripts/recall-llm.py` in the
seeded repo with NO memory corpus reachable (spec §3: `recall-llm.memory_dir()` returns `None` in a clone). Record
what happens: an error, a silent no-op, or a useful behaviour (for example, telling the user how to start a
corpus). Condition (a) is met only if a stranger with an empty corpus gets something useful on day one; a silent
no-op is NOT useful. Condition (b) is Human step H1 and is never decided here. The corpus row carries
`C5: unanswered — blocked on the content review` until H1 lands, and its verdict cannot be the ship verdict.

**FAILS IF:** the probe ran with any path under this repository's `docs/memory/` in its `RunRecord.opened`.

### Task 19: `scripts/check-inventory.py` — the falsifiers as a guard, and the checkpoint

**Files:**
- Create: `scripts/check-inventory.py` (W1-W8)

**Interfaces:**
- Consumes: `inventory.json` rows written by Tasks 17-18 (and 20); `components.json` (Task 5);
  `shipping-sets.json` (Task 6); the latest `scan-<date>.json` (Task 12).
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

`row_errors` refuses, each a spec falsifier: a ship row whose grade is missing (§4b); an `inherited` grade with no
`scenario` (§4b); a non-ship verdict with no `cites`, or citing an id the scan did not emit (§5 rule 1); a non-ship
row with no `route` (§9 D10); a `practice` harvest with no `practice_entry` naming a heading that exists in
`docs/portable-practices.md` (§4c); a `data` row with a C4 value other than `"struck"` (§4); the memory-corpus row
with a ship verdict while its `C5` is `unanswered` (§7 item 11); a `measured` grade on an effort (1) or (2) row
(§2b); a cost with either estimate missing (§2b). And at the inventory level: no phase-1 package named, or a phase-1
package with no entry in `shipping-sets.json` (§9 D11).

The checkpoint, exactly as spec §2c states it (embedded because the threshold arithmetic is what the owner decided;
it is run as written below):

```python
def checkpoint_fires(rows):
    """D1 checkpoint (spec §2c): fires when public_bar >= 3 x next_project
    for MORE THAN HALF of the phase-1 components (phase "1" and "1-if-feasible")."""
    phase1 = [r for r in rows if r["phase"] in ("1", "1-if-feasible")]
    if not phase1:
        raise ValueError("CANNOT RUN: no phase-1 rows")
    over = [r for r in phase1
            if r["cost"]["public_bar_hours"] >= 3 * r["cost"]["next_project_hours"]]
    return 2 * len(over) > len(phase1)


def _row(phase, pub, nxt):
    return {"phase": phase, "cost": {"public_bar_hours": pub, "next_project_hours": nxt}}


assert checkpoint_fires([_row("1", 3, 1), _row("1", 3, 1), _row("1", 1, 1)])        # 2 of 3 at exactly 3x
assert not checkpoint_fires([_row("1", 3, 1), _row("1", 1, 1)])                     # 1 of 2 is not MORE than half
assert not checkpoint_fires([_row("1", 2.9, 1), _row("1", 2.9, 1)])                 # below 3x
assert checkpoint_fires([_row("1", 9, 1), _row("later", 1, 1), _row("later", 1, 1)])  # later rows do not count
try:
    checkpoint_fires([_row("later", 9, 1)])
    raise AssertionError("an empty phase-1 set must not read as 'did not fire'")
except ValueError:
    pass
```

A `next_project_hours` of 0 is a row error (the ratio is undefined), never an automatic fire.

- [ ] **Cases**: one per `row_errors` rule (each with an ADJACENT negative: the same row with the field fixed is
  clean), the five checkpoint asserts above, `render puts verdict and grade in one cell`, `a component in the map
  with no row is an error`. Red → implement → green → W1-W8 (the `ci.yml` caller runs both `--self-test` and the
  live inventory once it exists; rc 3 on the live inventory is NOT a CI failure — CI prints it; only rc 1 and 2
  fail) → commit.

**FAILS IF:** the live inventory has a ship row with its grade in a different cell of `inventory.md`, or the
checkpoint fires on the live inventory and `check-inventory.py` exits 0.

### Task 20: the cost record and the cheapest routes for effort (3)

**Files:** Create/modify rows in `inventory.json` for every effort (3) component.

**Interfaces:**
- Consumes: Tasks 12, 14, 15, 16, 19.
- Produces: complete rows.

For each component: verdict from the evidence (scan findings + experiment), grade per §4b and §4's inheritance
table (a `library` is `inherited` only via a named measured scenario that exercised it; CANNOT RUN importers
contribute nothing), the two cost estimates, and for every non-ship row the cheapest of D10's routes with its cost.
Estimates are in hours of agent-implemented work including one review round, graded `argued` unless something was
run (for example, a route whose fix was tried in the experiment's scratch copy, never in the repository, is
`measured`). Each estimate names its basis in one line (which findings it removes).

- [ ] **Steps:** write rows → `python3 scripts/check-inventory.py` rc 0 or 3 → commit.

**FAILS IF:** `check-inventory.py` exits 1 on the committed inventory.

### Task 21: the D1 checkpoint (spec §2c) — STOP POINT

**Files:** none unless it fires (then the dashboard entry of Task 22 carries `[needs-you]`).

**Interfaces:**
- Consumes: `checkpoint_fires` via `python3 scripts/check-inventory.py` (Task 19).
- Produces: either "did not fire" recorded in `inventory.md`'s header, or Human step H4 opened.

- [ ] Run `python3 scripts/check-inventory.py; echo rc=$?`. rc 3 → write the selection card (A: keep D1, the
  public bar; B: drop to "my next project"; recommendation stated with the ratio per phase-1 component), send the
  notification, mark the inventory **not final**, and stop slice F at this task. The coordinator does not continue
  past this point on its own (spec §2b).

**FAILS IF:** rc 3 and Task 22 is marked final without a recorded owner answer (spec §2c's FAILS IF).

### Task 22: finish the inventory — render, harvest, rubric, backlog, roadmap, dashboard

**Files:**
- Create: `docs/marketplace/inventory.md` (generated by `python3 scripts/check-inventory.py --render`)
- Modify: `docs/portable-practices.md` (the rubric entry, spec §7 item 9; one entry per `harvest: practice`, item
  9b — the first is the `${CLAUDE_PLUGIN_ROOT}` practice of spec §4), `docs/backlog.md` (one row per
  `NEEDS-WORK` component with its named defect and nothing else, item 6; area `(process / deliverable #2)`, already
  claimed in `docs/features.md`), `docs/roadmap-to-launch.md` (the milestone's status line and ticks under the
  existing `harness-ships-elsewhere` section), `docs/dashboard-entries.md`.

**Interfaces:**
- Consumes: Tasks 19-21.
- Produces: the phase-1 subset named with its package and shipping set; the inventory marked final only if Task 21
  did not fire or the owner answered.

Spec §7 item 7 (register the anchor, close backlog row 290) is **already done** on master at `2f5e3f3d`:
`docs/anchors.md` registers `harness-ships-elsewhere` and row 290 is ✅. This task only verifies it
(`python3 scripts/check-anchors.py` rc 0).

- [ ] **Steps:** render → write practice entries → backlog rows (`python3 scripts/gen-backlog-page.py --self-test`
  after editing `backlog.md`) → roadmap → dashboard entry → all document guards → commit →
  `python3 scripts/check-dashboard-entry.py`.

**FAILS IF:** a backlog row is filed for a component whose verdict is not `NEEDS-WORK`, or `inventory.md` differs
from `--render`'s output (the page is derived, never hand-edited).

---

## Human steps (never done by an agent)

| # | Step | Needed by | If it does not happen |
|---|---|---|---|
| **H1** | **C5 content review of the memory corpus** (`docs/memory/`): does any file hold private content, credentials or third-party material that may not be redistributed? Spec §7 item 11. | the recall phase decision (D11 (b)) | the corpus row stays `C5: unanswered`; recall moves to "later" |
| **H2** | **A login token for the skill half of the experiment**: run `claude setup-token` and save the token to a file outside the repository (path told to the coordinator, never pasted into chat or committed). | Task 14/15 skill half | the skill half is CANNOT RUN; the four page skills stay `argued` |
| **H3** | **Re-decide the method if the spike fails** (spec §9: D4 is unachievable; never silently downgrade to paper scoring). | Task 4 NO-GO | the plan stops after slice B |
| **H4** | **Answer the D1 checkpoint card** (keep the public bar, or drop to "my next project"). | Task 21 rc 3 | the inventory stays not final |
| **H5** | **Name the copyright holder** for the MIT `LICENSE` (spec §4: the git identity is a placeholder). | the NEXT milestone | nothing in this plan blocks |
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
| §7 item 0, packaging spike; §9 D3 falsifier | 3, 4, H3 |
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
| §7 item 8 (D8 corrections, first and alone) | 1 |
| §7 item 11 (C5 corpus review) | H1, 18, 19 |
| §4d D9, §10 publication | H5, H6 (next milestone) |
