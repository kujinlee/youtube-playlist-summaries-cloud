# Round 1 — 610-served-page — Claude half

Subject: branch `610-read-at-origin` (PR #561), `git diff origin/master...HEAD` at `717f9c73`. Mandate: refute that
only `regen-pages.py`'s fresh clone writes the served page `~/explainers/goal-tree.html` (`DEFAULT_OUT`).

## Evidence run

- `python3 scripts/goal-tree.py --self-test` → `481/481 self-test cases passed` (4.5 s).
- The three new mutations of `scripts/mutations/goal-tree.json`, each applied to a `git archive HEAD` copy in the
  scratchpad (never this worktree) and the self-test run there:
  - "the guard is gone" → 477/481; its named case `... a direct run (bare) never writes the SERVED page, and logs
    nothing` is RED (also `--page`, `--snapshot --page`, and the preview case).
  - "the guard ignores the clone marker" → 480/481; its named case (REGEN_MAIN_CHECKOUT set → served page IS
    written) is RED.
  - "the guard refuses an explicit --out preview too" → its named case `main wrote the page` is RED (the run then
    stops on a `FileNotFoundError` in a later case; the named case was already reported `[FAIL]`).
- Two extra mutations of my own:
  - the guard MOVED to after the snapshot/log write (just before `if a.page:`) → 478/481, the three
    "logs nothing" cases RED. So question 3 (refusal before any log write) is pinned, not just true today.
  - `a.out == DEFAULT_OUT` → `a.out.resolve() == DEFAULT_OUT.resolve()` → 481/481 (an equivalent; noted for F2).
- Real runs from this worktree with `HOME` pointed at a scratch dir (so `DEFAULT_OUT` is a scratch file, and
  `--page` only reads the main checkout's log), `REGEN_MAIN_CHECKOUT` unset:
  - bare `--page` → rc 2, `CANNOT RUN — the served page ...`, nothing written.
  - `--page --out $HOME/explainers/goal-tree.html` → rc 2, nothing written.
  - `--page --out $HOME/explainers/../explainers/goal-tree.html` → **rc 0, the served file WRITTEN** (F2).
- Callers (question 2): `explainer-serve.py` Refresh runs `[python, scripts/regen-pages.py, --page, <key>]`
  (`_regenerate`, line 1523); `.claude/commands/goal-tree.md` runs `regen-pages.py --page goal-tree` then
  `goal-tree.py --print` (`--print` alone is not `--page`, so unaffected); `check-page-links.py` `build` passes an
  explicit `--out` into a temp dir; CI runs only `--self-test`. `regen-pages.py launch` (line 536) sets
  `REGEN_MAIN_CHECKOUT` for a clone tree and `_env` (line 147) drops an inherited one, so the guard does not break
  any of them and an inherited value does not reach the generator through the runner. No legitimate caller broken.
- Env/global restoration (question 4): the new block's `try/finally` (goal-tree.py:5110-5133) restores
  `DEFAULT_OUT` and pops/restores `REGEN_MAIN_CHECKOUT` on every exit path; `argparse`'s default reads the patched
  global at `main()` call time, so the cases never touch the real `~/explainers`. Sound.

## Findings

### F1 — MAJOR — the served page, the docstring and a retirement message still tell the reader to run the command this PR refuses

- `scripts/goal-tree.py:2229` — the page itself says *"To refresh: `python3 scripts/goal-tree.py --snapshot --page`,
  or the Refresh button."* A self-test case pins that exact text (`scripts/goal-tree.py:3848`, *"⭐ Y7: the page
  says it REPLAYS a snapshot, when, and how to refresh it"*).
- `scripts/goal-tree.py:4-7` — the module usage block: `goal-tree.py` bare *"= --snapshot --page (the Refresh
  button)"* and `goal-tree.py --page` *"re-render from the log"*. Both are now CANNOT RUN outside the clone.
- `scripts/gen-work-lines.py:376` — the RETIRED message sends the reader to `python3 scripts/goal-tree.py --snapshot
  --page`; its own case at `:535` pins that string.

**Failure scenario:** the owner reads the refresh instruction on the very page this PR protects, pastes it, and gets
`CANNOT RUN`. The refusal names the right command, so nothing is damaged — but the page now advertises a command
the PR made refuse, and two self-test cases hold the wrong advice in place. This is the same instance-not-class
shape the repo memory warns about: the write path was closed, the instructions that route people to it were not.
**Fix:** say `python3 scripts/regen-pages.py --page goal-tree` (or the Refresh button) in all three, and update the
two pinning cases.

### F2 — MINOR — the guard compares paths lexically, so a differently spelled `--out` for the same file still writes the served page

`scripts/goal-tree.py:2465`, `a.out == DEFAULT_OUT`. `pathlib` equality is textual: it folds `//` and `.`, not
`..`, a symlinked directory, or a relative path. **Measured:** `--page --out $HOME/explainers/../explainers/goal-tree.html`
with `REGEN_MAIN_CHECKOUT` unset → rc 0 and the served file written. No caller does this today, and an explicit
`--out` is deliberately allowed, so this is not a live path. **Fix (cheap):** compare
`os.path.realpath(a.out) == os.path.realpath(DEFAULT_OUT)` — my resolve() variant kept 481/481 green; add a case
with a `..` spelling so the stronger form is pinned.

### F3 — MINOR — the env var is checked for PRESENCE, not that the run is inside the clone

`scripts/goal-tree.py:2465`, `not os.environ.get(_SS.MAIN_CHECKOUT_ENV)`. `session-state.main_checkout`
(session-state.py:616) honours `REGEN_MAIN_CHECKOUT` whenever it names THIS repository's main checkout — and a run
from the main checkout or a linked worktree satisfies that. So `REGEN_MAIN_CHECKOUT=<main> python3
scripts/goal-tree.py` from a stale checkout writes the served page. It needs a deliberate env var, so it is a
bypass, not an accident; but the backlog row's FAILS-IF ("a run with no `REGEN_MAIN_CHECKOUT` ... writes") is
narrower than the claim ("written ONLY by regen-pages.py"). **Fix options:** additionally require that `root` is
not `main_root` and not a linked worktree of it (in the clone, `root`'s common dir differs from `main_root`'s), or
restate the claim as "a direct run without the runner's marker".

### F4 — MINOR — the dashboard entry overstates: a stale checkout still writes the SHARED snapshot log

`docs/dashboard-entries.md` (last entry): *"Your local checkout lagging no longer matters to any page."* The guard
covers only `--page` to the default out. `--snapshot` alone (documented at `docs/goal-threads.md:5` as how states
are derived), `--record-agenda` and `--tick-agenda` still run from any checkout and write the main checkout's
`.claude/goal-tree-log.jsonl` / agenda log from that checkout's `docs/` (`collect(root, run)`, goal-tree.py:2487,
2496). The next clone build appends a fresh snapshot, so the tree is right, but the stale snapshot stays in the
history the page's timeline replays (a merged step "reverting" and returning). **Fix:** soften the sentence to
"no direct run can overwrite the page", or file the log path as its own row.

## Questions answered

1. Other write paths to `DEFAULT_OUT`: none in `.claude/hooks`, `.claude/commands`, `scripts/` or `explainer-serve.py`
   that bypass regen-pages; only the deliberate spellings in F2/F3.
2. Legitimate callers: none broken (evidence above).
3. Order: the refusal is after `main_checkout` (read-only `git rev-parse`) and before `log_path`, any
   `record_agenda`/`tick_agenda`/`append_if_changed`. Pinned (my moved-guard mutation went red).
4. The five cases and three mutations pin the property; each mutation reddens its named case; state is restored in
   `finally`.
5. Docs: backlog #610 row and the coordinator record match the code (rc 2, nothing logged, `--out` allowed, 5 cases,
   pin 364 → 367 — the manifest holds 367 entries). The dashboard entry overstates (F4).

VERDICT: NOT CONVERGED
