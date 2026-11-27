# Node tree slice S3 — round 1, Claude half (adversarial)

Subject: `git diff e316f96e bff26dbd` (branch `node-tree-s3-goals`, 7 commits, 13 files).
Plan: `docs/superpowers/plans/2026-11-24-goal-node-tree.md` Tasks 12–16. Spec: `docs/superpowers/specs/2026-11-23-goal-node-tree-design.md`.
Reviewed at HEAD `bff26dbd`. Reviewer did not edit tracked files, commit, push, or read `.claude/plans/`.

## What was run (all at `bff26dbd`)

| Check | Result |
|---|---|
| `check-features.py --self-test` | 113/113 |
| `goal-tree.py --self-test` | 636/636 |
| `session-state.py --self-test` | 183/183 |
| `batch-ci.py --self-test` | 184/184 |
| `check-features.py` (live) | rc 0, "45 nodes (30 built, 4 absent, 11 stateless)" |
| New/changed mutations, applied one at a time on a copy (`rsync` of the worktree, no `.git`), self-test run, the `expect` case looked for as `[FAIL]` | **38/38 KILLED**: check-features 10, session-state 12 (7 T15 + 5 re-anchored older ones), goal-tree 7, batch-ci 9 |
| Pins vs manifest lengths (`expected_mutations.py`) | equal: batch-ci 105, check-features 69, goal-tree 559, session-state 179 |
| Copy restored after the run | `cmp` equal for all four scripts |

## Plan FAILS IF lines, Tasks 12–16

| Task | FAILS IF | Observed |
|---|---|---|
| 12 | parent diff outside the list; node count ≠ 45; a NEW `for:` differs from the spec; `^state:` ≠ 34 | parent diff = trunk re-parenting + the 6 new nodes + the level moves; 45 nodes; all 8 NEW purpose sentences found verbatim in the spec (goal-tree's is 4.39 "unchanged, minus its URL", not NEW); `grep -c '^state:'` = 34; parser problems `[]` |
| 13 | thread count changes; a `> ` request line touched | `^- ` count 155→157 is the preamble (−1 +3 bullets), thread lines unchanged; `git diff … -- docs/goal-threads.md \| grep -E '^[-+]> '` prints nothing |
| 14 | a snapshot over a pre-rename log reports a slug as unknown | not run live (needs gh); covered by the cases `history: a pre-rename snapshot resolves` and `⛔ history: the page draws a pre-rename log under the node's current slug`, whose mutations (pure helper and the `main` call site) are both KILLED |
| 15 | `--add x … --goal dev-speed-first …` exits 0 | run against a scratch root (`scripts/` + `docs/features.md`, no git): `REFUSED — --goal \`dev-speed-first\` is a former slug …`, **rc 1**; `--also token-usage-first` rc 1; missing features.md rc 2 CANNOT RUN; empty features.md rc 2 CANNOT RUN |
| 16 | the retired-slug search prints a line outside the four classes | every hit is a `was:` entry, a quoted request, a self-test fixture (incl. the `check-features.py:1282` comment over a fixture), or ADR-0016 |

## Refutation attempts that held

- **Former slug** as heading, `also`, PRIORITY slug, answer key, `--goal`, `--also`, ledger goal: each refused (G2, G5) or resolved for history only (`resolve_snapshot`, `resolve_ledger`).
- **A slug that is a prefix of another** (`a` / `ab`, `## GOAL a-`): `resolve` compares whole strings and `was` is a tuple; no prefix match.
- **`also` naming its own heading, or its heading's former slug**: both refused by G2 (`… is the heading this thread sits under`, `… is a former slug`); `--also` = `--goal` refused by G5.
- **`also` after `waits on`**: `parse_thread_line` refuses it; G2 also reports the slug.
- **Empty `also` entry / trailing comma**: G2 refuses the empty slug.
- **Heading that matches a `was:` line but no node** (`## GOAL old-a`): refused as a former slug, naming the current one.
- **Empty or missing features.md**: session-state CANNOT RUN (rc 2), goal-tree `TreeUnreadable` CANNOT RUN (rc 2); G2 with no nodes refuses every heading, not silently passes.
- **batch-ci tree union**: re-parent on one side, move on both, slug met twice, unparseable result — each is a P8 violation, judged with `parse_features`, the tree's one parser.

## Gate loosening

**None found.** The dropped "a goal quotes a request" rule in `goal-tree.py parse_threads` is required by spec §2.2 (a heading no longer allocates a name; `goal_numbers` now places goals with no request last, and that is tested). G5 accepts any current node, a `proposed:` one included, which is the spec's rule. Before this slice nothing checked `--goal`. The self-test worlds (`_write_world`, `_tree_world`) add fixtures. They do not relax any check. The page-trigger gap (goal-tree now reads `docs/features.md`, but `regen-pages.pages_for` and `explainer-serve.PAGE_SOURCES["goal-tree"]` do not list it) is what spec §5.1.1 says to expect ("no hook, `pages_for` route or `PAGE_SOURCES` entry is added"; backlog #710). It is not a finding.

## Findings

### F1 — MINOR — a preamble prose line that begins `PRIORITY` is refused as a malformed PRIORITY line
`scripts/check-features.py:569` (`if line.startswith("PRIORITY"):`)
Failing input: `docs/goal-threads.md` with the preamble line `PRIORITY is decided by the owner.` above the first `## GOAL`. G2 prints `a PRIORITY line is written ONCE, above the first \`## GOAL\`, as \`PRIORITY YYYY-MM-DD …\``. That is a false refusal, and the message is wrong about what was written. The live file has no such line, and the failure is loud, so the damage is limited to confusing an author.
Fix: count a line as a PRIORITY line only when it starts with `"PRIORITY "` followed by a date (`^PRIORITY \d{4}-`). Report a line that starts that way but fails `PRIORITY_LINE` as malformed, and leave other lines to the preamble. Add an adjacent negative case.

### F2 — MINOR — the plan's "resolve-before-diff ordering" mutation names a different case than the plan says it reddens, and `--snapshot` still diffs against the raw log
Plan Step 5 of Task 14 (`plan:894`) asks for a mutation of "the resolve-before-diff ordering (reddens the rename-alone case)". The manifest's call-site mutation (`goal-tree.json`, "the page reads the log raw … (call site)") instead expects `⛔ history: the page draws a pre-rename log under the node's current slug`. The case `history: a rename alone logs no thread move` (`goal-tree.py:4495`) calls `changes(resolve_snapshot(...))` directly, so it cannot see `main`'s ordering. Separately, `main` (`goal-tree.py:3489–3496`) runs `append_if_changed` on the RAW log. The first `--snapshot` after a rename therefore logs a snapshot the reader would call unchanged.
Failing input: a log whose newest snapshot carries `token-usage-first`, the threads unchanged, and the heading renamed to `token-usage`. `--snapshot` prints "snapshot logged". The page shows no move, so this is harmless to readers, but the log grows by one.
Fix: either resolve the newest logged snapshot before `append_if_changed` compares it, or record the deviation in the plan with its reason. Rename the mutation, or add an `expect`, so the plan's claim and the manifest agree.

### F3 — MINOR — two new branches have no mutation
`goal-tree.py parse_threads(text, nodes)`: the heading check through `_name_problem` (case "nodes: a heading that is not a node is refused"). Also `goal-tree.py read_tree`: the "declares no node" CANNOT RUN. Deleting either branch is not covered by any manifest entry. Neither is listed in the plan's Step 5, so this is a gap, not a deviation. check-features G2 refuses the same headings in CI, which limits the risk.
Failing input: replace `_name_problem(...)` in `parse_threads` with `None`. Nothing in the manifest reddens.
Fix: add one mutation per branch, each expecting its existing case.

### F4 — NIT — a repeated slug is accepted in `also`, `--also` and PRIORITY
`check-features.py:518` (`also_slugs`), `:571` (PRIORITY), `session-state.py:534` (`ledger_add`'s `also`).
Failing inputs: `- fix · PR #1 · x · also b, b` (G2 `[]`); `PRIORITY 2026-11-27 "x" · a > a` (G2 `[]`); `--add z … --goal dev-speed --also token-usage --also token-usage` exits 0 and stores `"also": ["token-usage", "token-usage"]` (observed on a scratch root). The owner's rule is "counted once", and S4 is the slice that draws `also`, so nothing is miscounted yet.
Fix: refuse a repeated slug in each of the three. Each fix is one line plus one case.

### F5 — NIT — session-state's EXIT CODES docstring omits the new rc 1
`scripts/session-state.py:68–69` says "2 for a ledger command that cannot write". `--add` now exits 1 with `REFUSED — …` (G5).
Fix: add "1 for a ledger command refused (G5)".

### F6 — NIT — `_check_features()` re-executes check-features.py on every call
`scripts/session-state.py:390`: it runs once in `read_tree` and once per `goal_refusal`, so `--goal` plus two `--also` load the module four times. This is only a cost.
Fix: cache the module, as `batch-ci._features` does in `sys.modules`.

### F7 — NIT (S4) — `resolve_ledger` maps a ledger entry's `goal` but not its `also`
`scripts/goal-tree.py:286`. An entry written before a rename with `also: ["harness-speed"]` keeps the former slug. No view reads ledger `also` yet.
Fix: resolve `also` the same way when S4 draws it.

## Plan steps

Tasks 12–16 are done as written, except for F2's mutation naming. Every FAILS IF above was observed not to fire, Task 14's by a killed case rather than a live run.

**Verdict: CONVERGED** — no BLOCKER or MAJOR. F1–F3 are MINOR, and F4–F7 are NITs, to be fixed or filed.
