Reviewed head: cce4c48c0638ee9b09e1e8d1bfa764d1469ff5f6

# dashboard-retire S2 (Tasks 7–12), PR #640 — review round 1, Claude half (adversarial)

Scope: `git diff origin/master...HEAD` (9 commits, 42 files), merge base f9979fa0. Worktree was not modified;
every mutation below was applied to a `git archive HEAD` copy under the scratchpad, never the worktree.

## What I tried to refute and could not

- **L1 pins vs bytes.** `git hash-object docs/dashboard-entries.md` = `befaa1cb…ebc27` = `LEGACY_STORE_BLOB`;
  `shasum -a 256` = `c6e110df…ef97f` = `LEGACY_STORE_SHA256`; `origin/master:docs/dashboard-entries.md` =
  `f9979fa0:…` = `a9553580…98f0` = `LEGACY_STORE_BASE_BLOB`. All three hold.
- **L1 fail-closed shapes.** Missing path, a tree/gitlink at the path (`_store_blob` returns None → "missing",
  refused), a symlink (type blob, bytes are the link target → SHA mismatch, refused), a blob absent from the clone
  (12.6). No pass without the exact pinned bytes: the verdict is `sha256(head_bytes) == LEGACY_STORE_SHA256` only.
- **`gh` failure in `--list-store-prs`.** Failed list, unparseable list, full page, failed per-PR diff are all err
  → rc 2 (12.13–12.16, each mutated).
- **C1** (`gen-dashboard.py --assert-no-open-asks`): missing / non-UTF-8 / unreadable store → rc 2; any parse
  error → rc 2, never "0 asks"; open ask → rc 1. CI step runs it under Actions' default `bash -e`, after the gate.
- **CI.** PR step: `check-ask-store.py --base origin/$GITHUB_BASE_REF` + C1; push step (master, `batch/**`):
  A1 + L1. `fetch-depth: 0` retained. No `continue-on-error` on either. No step reads a PR body any more except
  `check-review-recorded`, which writes its own body file.
- **Stale loaders.** No executable loader names `check-dashboard-entry.py`: gen-dashboard, goal-tree,
  compaction-state, check-review-recorded (`_load_declaration_parser`, and its call passes `NO_REVIEW`
  explicitly, so the default-marker change from `NO-ENTRY:` to `NO-REVIEW:` cannot flip it), check-merge-ready
  (`ASK_STORE_GATE`), check-plan-code, check-shipping-sets, check-fixture-variation all repointed. gen-dashboard's
  historical-waiver reader passes `"NO-ENTRY:"` explicitly (correct, since the default changed).
- **Task 10 readers read `docs/asks/`.** goal-tree's `NEEDS_SOURCES = ("asks", "ledger", "backlog")`;
  compaction-state's `pending_asks` reads only `read_asks(root/"docs"/"asks")` and a missing dir is CANNOT RUN.
- **Builder's notes, verified:** check-ask-store manifest = 69 entries = pin; every pin in
  `expected_mutations.py` equals the manifest count for its file (0 mismatches, 0 unpinned). Anchors moved onto
  `if ask_err or l1_err:` (manifest line 645). `ACCOUNTED_MENTIONS` `("ci.yml","if: github.event_name == 'push'")`
  count 1 = `grep -c` on ci.yml = 1. Shipping-sets pin 369 / fd17d2d55520b77c passes in the live self-test.
  `EXAMINED_KEYS` swap accepted by check-fixture-variation's own suite (67/67). Every mutation anchor in the six
  touched manifests occurs exactly once in its target; every `expect` of a mutation new in this PR names a case
  string that occurs exactly once in the target source (lists are pre-existing harness form).
- **Master refused, this lets through?** Master's gate ran `collect` (entry grammar + references of ADDED store
  entries) + R1 + A1/F1. With L1 freezing the store to pinned bytes, no added entry can exist, so the grammar and
  reference checks have no population. Nothing else master refused is lost.

## Findings

### F1 — MEDIUM — L1's git-failure path is fail-open under two surviving mutations (the admitted gap is wider than stated)

`scripts/check-ask-store.py:797-801` and `:1901`

```python
    try:
        blob = _store_blob(root, "HEAD")
        data = _ask_git(root, "cat-file", "blob", blob) if blob else None
    except _AskGitError as exc:
        return None, f"the frozen store could not be read — {exc}"
...
    if ask_err or l1_err:
```

No case drives `legacy_store_check`'s `except` branch, and no case drives `main` with a non-None `l1_err`
(the dispatch cases stub `legacy_store_check` to `(None, None)` at `:1615`). Measured on a `git archive HEAD` copy:

| Mutation | Self-test |
|---|---|
| `return None, f"the frozen store could not be read — {exc}"` → `return None, None` | 139/139 + 28/28 **pass** (survives) |
| `if ask_err or l1_err:` → `if ask_err:` | 139/139 + 28/28 **pass** (survives) |

The builder named only the second. Either one turns "git could not read the frozen store" into a green L1.

**Concrete failing input** (run, not inferred): a repo with `docs/asks/.gitkeep` and the pinned
`docs/dashboard-entries.md` committed, then the store's loose object deleted
(`rm .git/objects/be/faa1cb22cfb272bc803e23b4b990ae812ebc27`). A1 still reads (its blob exists); L1's
`git cat-file` exits 128.
- real code: `CANNOT RUN — the frozen store could not be read — git cat-file exited 128 …` rc **2** (correct)
- with `if ask_err:`: `ok — the ask store under docs/asks/ is well-formed …` rc **0** (fail-open, unseen by any case)

**Fix:** one impure case that builds exactly that repo (or stubs `_ask_git` to raise only for `cat-file` on the
store blob) and asserts `legacy_store_check` returns `(None, <err>)` AND `main([])` is rc 2 with "CANNOT RUN";
add both mutations above to `scripts/mutations/check-ask-store.json` (pin 69 → 71) naming that case.

### F2 — LOW — the C1 replay in check-merge-ready is untested; deleting it is invisible

`scripts/check-merge-ready.py:2188`

```python
        ("old store holds no open ask (C1)", ["python3", "scripts/gen-dashboard.py", "--assert-no-open-asks"]),
```

Plan Task 12 requires "the replayed step also runs C1". No case, and no mutation, references it (`grep
"assert-no-open-asks\|(C1)"` over the script and its manifest: only this line). Measured: deleting the line on a
`git archive` copy leaves `459/459 self-test cases passed`. LOW because CI's own `ask store (pull request)` step
still runs C1 and a red CI is still seen; the defect is that the "replays the PR-only steps" promise for this
step is unwitnessed. Also cosmetic: the name is 32 chars against the `{name:18s}` column, so the row misaligns.
**Fix:** a case asserting the replayed command list for the `ask store (pull request)` step contains both commands
that step's `run:` holds (ideally derived from ci.yml), plus a mutation dropping the C1 entry.

### F3 — LOW — stale references to the retired gate / skill in live code comments and the new skill

- `.github/workflows/ci.yml:1064` — "The durable fix is in the REFUSAL MESSAGE (`scripts/check-dashboard-entry.py`)":
  that file and that refusal message (R1's frozen-payload text) no longer exist.
- `scripts/gen-dashboard.py:3365` — "the exact promise `.agents/skills/dashboard/SKILL.md` makes about the exit
  code": that file is deleted in this PR.
- `docs/marketplace/components.json:245` — component `"id": "check-dashboard-entry"` now owns
  `scripts/check-ask-store.py` (passes the closure check, but the id names a file that is gone).
- `.agents/skills/needs-you/SKILL.md:23` — "there is no dashboard page to regenerate", while `gen-dashboard.py`,
  `.claude/hooks/regen-dashboard.sh` (whose `:4` still says "There IS a `dashboard` skill") and the page remain
  until S3. True after S3, false at this head.
**Fix:** reword the four comments/lines; rename the component id or note it is kept for continuity.

### F4 — LOW — an L1 refusal hides A1/F1 problems found in the same run

`scripts/check-ask-store.py:1904-1906` returns on `l1_problem` before printing `ask_problems`, so a branch that
both edits the frozen store and has a malformed ask learns about the second only after fixing the first (one more
CI round). Not a pass; a diagnosis gap. **Fix:** print both blocks, then `return 1`.

## Self-test results (run at cce4c48c, foreground)

| Script | Result |
|---|---|
| `check-ask-store.py --self-test` | 139/139 + 28/28 cannot-run, rc 0 |
| `gen-dashboard.py --self-test` | 331/331, rc 0 |
| `check-merge-ready.py --self-test` | 459/459, rc 0 |
| `goal-tree.py --self-test` | 606/606, rc 0 |
| `compaction-state.py --self-test` | 129/129, rc 0 |
| `check-fixture-variation.py --self-test` | 67/67, rc 0 |
| `check-shipping-sets.py --self-test` | 170/170, rc 0 |
| `check-review-recorded.py --self-test` | 285/285, rc 0 |
| `check-explainer-delivery.py --self-test` | 8/8, rc 0 |
| `check-fixture-git-isolation.py --self-test` | 141/141, rc 0 |
| `check-main-drivable.py --self-test` | 462/462, rc 0 |
| `check-docs.py` | "Documentation integrity OK", rc 0 |
| live `check-ask-store.py --base origin/master` | ok, rc 0 |
| live `check-ask-store.py` (push mode) | ok (A1 only), rc 0 |
| live `gen-dashboard.py --assert-no-open-asks` | ok — 0 open asks, rc 0 |
| mutation sweeps (`check-plan-code.py --mutate`) | **NOT RUN** — only the four hand mutations above |

Unverified: the full mutation sweeps for the touched manifests; CI behaviour on the real `pull_request` merge ref.

VERDICT: NOT CONVERGED
