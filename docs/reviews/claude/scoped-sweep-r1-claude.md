Reviewed head: f6c770741d9f31a5eb8beb8def79b3024e85296d

# PR #496 (backlog #330) — adversarial review r1, CLAUDE half

Mandate: refute that the diff-scoped selector, the full-sweep backstop and the `sweep-red` alert implement the
owner's 2026-11-02 decision soundly. Every finding below was reproduced against the real tree at the reviewed head
by calling `check-plan-code.select_manifests` with `sweep_sources(Path("."))`, which is what `main()` does. Where
the *consequence* (a mutation that would now survive) was not reproduced, that is labelled UNVERIFIED.

## Findings, by severity

### M1 (MEDIUM-HIGH) — the "import name" rule misses this repo's standard loader for hyphenated scripts, so a changed sibling does not select the manifests that import it

`scripts/check-plan-code.py:357-364` (`_names_of`) adds an import name only when the stem `isidentifier()`. Every
hyphenated script is loaded by its BARE STEM through a helper — `goal-tree.py:154 _sibling("session-state")`,
`record-review-verdict.py:696 _load("check-review-rounds")` / `import_module(stem)`, `codex-review.py:104
import_module("codex-frontier-model")`. None of those spells `session-state.py` or `scripts/session-state.py`,
so rule 6 does not see the importer, and because rule 6 found *some* namers, rule 7's fallback never fires.

Concrete inputs (real tree, `event=pull_request`, one changed path):

| changed path | selected | real importer NOT selected |
|---|---|---|
| `scripts/session-state.py` | 4 of 87 | `scripts/goal-tree.py` (module-level `_SS = _sibling("session-state")`, `goal-tree.py:162`) |
| `scripts/check-review-rounds.py` | 9 of 87 | `scripts/record-review-verdict.py` (`_load("check-review-rounds")`, `:365`) |
| `scripts/gen-backlog-page.py` | 15 of 87 | `scripts/goal-tree.py` (`_sibling("gen-backlog-page")`, `:495`, `:612`, `:1116`) |
| `scripts/gen-dashboard.py` | 17 of 87 | `scripts/goal-tree.py` (`:463`) |
| `scripts/gen-work-lines.py` | 7 of 87 | `scripts/goal-tree.py` (`:726`, `:1687`) |

The coupling is MEASURED, not inferred: on a scratch copy, changing only `session-state.waits_on_owner` to
`return True` reddens 6 of `goal-tree.py --self-test`'s 205 cases; `return False` reddens 4. So `goal-tree`'s
manifest verdicts depend on `session-state.py`, and a PR changing only `session-state.py` does not run that manifest.
⚠ What was NOT reproduced: a session-state edit that keeps `goal-tree`'s control green while letting one of its
mutations survive (the shape only the sweep sees — a control red is also caught by `verify`'s
`goal-tree.py --self-test`, `ci.yml:857`). UNVERIFIED, but the selector's own contract ("import name") is false
on these inputs regardless.

Observed: the importer is dropped. Expected (rule 6 as documented, "full path, file name, or import name"): selected.
Fix: in `_names_of`, also add the bare stem for every `scripts/*.py` (hyphenated included), matched QUOTED
(`["']stem["']`) so `session-state` does not match prose. Add a case per loader idiom (`_sibling`, `import_module`,
a `_load` wrapper) with an independent fixture, and a mutation dropping the hyphenated arm.

### M2 (MEDIUM) — rule 6 only looks at directories STRICTLY BELOW the staged root, and rule 7 runs only when rule 6 found nothing, so a reader that walks the root is dropped whenever anything else names the file

`scripts/check-plan-code.py:402-406`. `between` excludes the root itself; the root-quoting fallback is gated on
`if not hit`. So the header's boundary (`:314-316`, "a suite that reads a file without naming it **or any directory
above it**") is wrong: a reader that quotes the root — a directory above the file — is dropped too.

Concrete input: `docs/memory/MEMORY.md` selects 5 of 87 (`check-canonical-source`, `check-fixture-variation`,
`check-memory-index-budget`, `check-memory-link`, `recall-llm`). **46** targets quote `docs` and are not selected,
including the four whose subject IS "every document under `docs/`": `check-plan-file-tags`
(`DOCS = ROOT / "docs"`, `rglob("*.md")` at `:221`), `check-docs` (`base.rglob("*")` at `:78`), `check-anchors`,
`check-reference-namespace`. Delete the one coincidental namer and the same path selects all of them via rule 7 — so
whether a docs walker runs depends on whether an UNRELATED script happens to mention the file name, which is the
inverse of "unrecognised selects MORE".

Impact probe (UNVERIFIED as a survivor): on a scratch copy I deleted `docs/memory/MEMORY.md` and ran all 46 dropped
targets' `--self-test` — 46/46 green both before and after, so this particular edit flips no control. The finding is
the rule, reproduced on the real tree; a content edit that flips one of these suites was not constructed.
Fix: always union the root quoters for paths whose namers are a strict minority, or include the root in `between`
(over-selects for `docs/` — measure the fraction before choosing); at minimum correct the header's stated boundary.

### M3 (MEDIUM) — rule 4's premise ("outside every root — never staged, so no suite can read it") is false for `node_modules/typescript`, which is staged but changed through `package.json` / `package-lock.json`

`scripts/check-plan-code.py:385-388`. `node_modules/` is not tracked (`git ls-files | grep -c ^node_modules/` = 0),
so no PR diff ever contains a `node_modules/typescript/...` path; the staged content changes when `package.json:63`
(`"typescript": "^5"`) or the lockfile changes. Concrete input: changed = `["package.json"]` (or
`package-lock.json`) → `diff-scoped: 0 of 87 manifest(s) selected … 1 outside the staged tree`. Yet
`check-paid-caller-arrival`'s suite shells to `scripts/ts-comment-spans.mjs`, which imports typescript, and 20 of its
32 cases depend on it (`HARNESS_TREE` comment, `:240-243`). A TypeScript bump that changes comment-span parsing
selects nothing on the PR.
Fix: map the dependency manifests (`package.json`, `package-lock.json`) to the readers of `node_modules/typescript`
(or to FULL); a case pinning it.

### M4 (MEDIUM) — nothing in this repository reads the `sweep-red` issue, so "visible" rests entirely on GitHub notification settings

`ci.yml` alert step (`:1297-1321`). `grep -rl sweep-red` finds only `ci.yml`, `check-merge-ready.py` (an accounting
entry), `docs/dev-process.md`, `docs/dashboard-entries.md`, `docs/goal-threads.md`. No script lists issues
(`grep -ln 'gh issue list\|"issue", "list"' scripts/*.py .claude/hooks/*` → nothing): not `session-state.py`, not
the dashboard, not the SessionStart path — and the owner's session-opening rule derives state from `git log` and
`gh pr list`, never issues. The issue is authored by `github-actions[bot]`, so the owner is notified only if they
watch the repository with issue notifications on; whether they do is UNVERIFIED. The owner's approval was
conditional on the red being seen by someone who was away; today that is an assumption about an account setting.
A related LOW: a red that later goes green leaves the issue open, and the next red becomes a comment on a stale
issue rather than a new one.
Fix: surface open `sweep-red` issues where the owner already looks (`session-state.py` / the dashboard "needs you"
count), with a CANNOT-READ arm when `gh` fails; optionally close the issue from a green full run.

### L1 (LOW) — transitive imports are not followed

`select_manifests` tests direct naming only. AST-only import graph, real tree: `scripts/m4_base_db.py` changed →
7 selected; `check-live-schema` and `check-catalog-coverage` import `m4_catalog`, which does
`from m4_base_db import CONTAINER` (`m4_catalog.py:92`), and neither names `m4_base_db` — both dropped. With the
hyphenated loaders of M1 included, the closure misses grow (e.g. `codex-frontier-model.py` → `record-review-verdict`
via `codex-review`). Not acknowledged in the header's "WHAT THIS DOES NOT SEE". Fix: close the namer set over the
import graph, or document it as part of the accepted residual.

### L2 (LOW, UNVERIFIED) — a manually cancelled master/schedule run raises no alert

The alert is `if: failure() && …`; on a cancelled run `failure()` is false, so a cancelled full sweep leaves no
evidence and no issue. Concurrency never cancels a master run in progress, and a PENDING run replaced by a newer
one (backlog #482) is covered by the newer run's full sweep over a superset tree, so the exposure is manual
cancellation only. Not exercised on Actions.

### Checked and NOT a finding
- **Undetermined → FULL**: diff fails → file removed → `raw None` → FULL (`:423-425`); no `--changed` → FULL;
  non-NUL list → `changed_from_nul` None → FULL (`"a"` → None, `""` → `[]`, `"a\0b\0"` → `['a','b']`); non-PR event →
  FULL; harness file (`check-plan-code.py`, `coverage_verdict.py`, `ci.yml`) → FULL; manifest with no target → FULL.
- **Whole-manifest invariants under a subset**: `manifest_counts`/`pin_drift`, the home-escape scan over every
  target and REPLACEMENT, and `anchor_problems` all run before `pool` is narrowed (`:3132-3169` vs `:3178`).
- **Required check on an empty/scoped selection**: an empty slice returns `Measured(declared=0)` → rc 0, "nothing to
  do", and `mutation-sweep-complete` reads the matrix aggregate — reports on every PR.
- **Docs-only master push now running the full sweep** and **the schedule also running `verify`**: both strictly
  stronger (more runs), not weaker; `verify`'s PR-only steps are `if: github.event_name == 'pull_request'`.
- **`issues: write`** at job level is sufficient for `gh label create` / `issue list|create|comment`; no checkout in
  that job, so no `contents` scope needed.

## What I ran
- `python3 scripts/check-plan-code.py --self-test` → `291/291 passed`, rc 0 (in the worktree).
- `python3 scripts/check-merge-ready.py --self-test` → `256/256 self-test cases passed`, rc 0.
- `select_manifests` over the real tree for every `scripts/*.py`, compared against (a) quoted-stem importers and
  (b) an AST import graph's transitive closure; and for `docs/memory/MEMORY.md`, `package.json`,
  `scripts/session-state.py`, `scripts/check-review-rounds.py`, `scripts/m4_base_db.py`, and others.
- Scratch copy (`git archive HEAD`): `goal-tree.py --self-test` 205/205 baseline; the manifest mutation
  "an owner-wait in the ledger…" killed (204/205); `session-state.waits_on_owner` → `True` reddens 6 control cases,
  → `False` reddens 4.
- Scratch copies with/without `docs/memory/MEMORY.md`: 46 dropped docs-root readers' `--self-test`, 46/46 green both.
- Not run: any GitHub Actions run (alert, cancellation, notification delivery).

VERDICT: NOT CONVERGED
