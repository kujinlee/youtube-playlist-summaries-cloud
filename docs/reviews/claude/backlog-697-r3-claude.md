Reviewed head: 36a031129191c414a9ba452f58775601b7712159

# Round 3 — `backlog-697` — Claude half — the r2 fold (every shipped file is quote-checked; an exact success contract)

**Scope:** `git diff a6efb56a..HEAD` (45847ecf, 36a03112). I reviewed adversarially: every claim below comes from an input I built and ran. The fixture worlds are synthetic (the self-test's `d5_src` shape), so no corpus quote appears here.

**Bet (the pending `redesign` row):** the bet is **WON**. I found no path, package or file type by which a group-D quote ships past `--closure`. No builder output reads as `0 gaps` unless it has the builder's exact clean shape. Both findings in closure-guard fail CLOSED (red or CANNOT RUN, never `0 gaps`), and both predate this fold. **No fix-induced finding is in closure-guard, so this round is not thrashing.**

## Attacks, with what was observed

### 1. Can a group-D quote ship past `--closure`?

Each world below holds a D source (one owner quote) plus one extra shipped file. Results are from the `--closure` CLI.

| Input | Observed |
|---|---|
| quote in `notes/.hidden` (a dotfile; `rglob("*")` must see it) | rc 1, gap `QUOTE FROM d1.md` |
| quote after a binary prefix `\xff\xfe\x00` in `n/x.bin` | rc 1, gap |
| `n/l.md`, a symlink to a quote-bearing file | rc 1, gap |
| quote in a reusable-workflow package's `wf/ok.yml` | rc 1, gap |
| a reusable-workflow package that declares a missing `wf/missing.yml` (the fold now SKIPS it in `decision5_quotes`) | rc 1, `REFUSED: component 'job': file 'wf/missing.yml' does not exist`. The fold's comment ("its absence is the other clauses' gap") holds. A plugin's missing file is `materialize`'s CANNOT RUN, as the r1 cases already pin. |
| quote UTF-16-encoded in `n/x.txt` | rc 0, `0 gaps`. **This is the builder's documented bound** ("a form the normaliser does not undo"), not this fold's. It is not a finding. |
| a repo file at `.claude-plugin/plugin.json` carrying the quote | rc 0, `0 gaps` (PLUGIN_META is excluded from both clauses). **Not a path:** `materialize` never sources it, and `mkt_stage.py:_description` writes it from a fixed template, so no owner text can reach it. It is not a finding. |

### 2. The exact contract (`_not_clean`, `CLEAN_SOURCE_RE`, `CLEAN_COUNT_RE`, `PASS_LINE`)

**Does a genuine clean run read as CANNOT RUN?**
- `_not_clean` returns `''` (clean) for:
  - zero group-D source lines;
  - a count of 10^9 files and 10^6 fragments;
  - a D source name containing spaces;
  - stderr that is only whitespace.
- Over the CLI, these clean worlds give rc 0, `0 gaps`:
  - shipped paths with spaces (`my notes/a b.md`);
  - a DUPLICATE basename (`x/a b.md`).

  So the count equality holds with a `dup-i/` copy, because the builder's `rglob` counts nested files.
- The real tree runs the builder on Python 3.14 with empty stderr: `--closure` gives rc 0.

**Does a non-clean run read as PASS?**
- The fold's six X5 cases each wrap the REAL builder and differ by one thing, and I ran them.
- Each FAIL hit line starts with a non-space character, so it cannot match `CLEAN_SOURCE_RE` (which needs two leading spaces).
- Every rc other than 0 or 1, and every rc-1 run without a parseable `FAIL: n hit(s)` line, is CANNOT RUN.

**The bound, which is inherent and not a finding:** a fabricated output that reproduces the WHOLE clean shape is accepted. That shape is the per-source lines, a count line with the right file count, and the exact PASS line. Parsing output cannot rule it out. The contract also does not pin the number of source lines to the group-D size. The real builder cannot emit a clean run without six of them, because `groups` refuses any other size and an unread D source is rc 2.

### 3. The paraphrase in `scripts/gen-backlog-page.py:838`

- **The meaning is carried.** The original asked to keep the wording unchanged and only lay it out for human reading with line breaks and indentation. The paraphrase says exactly that.
- `grep` for both distinctive phrases of the original finds no hit anywhere in the worktree.
- The real `--closure` gives rc 0, `0 gaps` (8.6 s).
- **Other owner quotes:**
  - A quote-shaped scan of all 334 shipped files found one other owner-attributed quote, in `docs/memory/a-usage-limit-stop-needs-a-wake-at-reset.md`.
  - That file is in no decision-5 group, so decision 5 does not govern it. It is not a finding here.

### 4. Mutations, verified in a full `git clone` outside the repository

- **Setup:** 4 clones checked out at 36a03112 (`--is-shallow-repository` false). Each clone had one mutation applied by its manifest edit, after an assertion that the anchor appears exactly once. Each then ran the full `--self-test`.

| Mutation | Result | Named case red |
|---|---|---|
| X4: the corpus-directory filter comes back | 165/170 | yes |
| X5: stderr on a PASS is ignored | 169/170 | yes |
| X5: a count line naming a different number of files is read as clean | 169/170 | yes |
| X5: a stdout line a clean run never prints is accepted | 169/170 | yes |

- **The manifest count:** it holds 215 entries for the file, which matches `expected_mutations.py` (209 − 1 + 7).

### 5. The gates

- **Self-tests:**
  - `check-shipping-sets.py --self-test` gives **170/170** (86.7 s).
  - `gen-backlog-page.py --self-test` gives **250/250**.
  - `build-shipped-corpus.py --self-test` gives **31/31**.
- **Non-self-test `check-*` steps from `ci.yml`:** all rc 0, except the two noted below. The steps run were:
  - `python-pin`, `docs`, `backlog-closure` (warn), `hook-commands`;
  - `fixture-git-isolation`, `arch-findings`, `gate-falsifiability`, `roadmap-consistency`;
  - `review-rounds`, `decision-scheme`, `anchors`, `goal-status`, `memory-link`;
  - `memory-index-budget`, `memory-shape`, `rc-contract`, `surface-recall`, `features`;
  - `ratchet-contract`, `explainer-delivery`, `claim-propagation`, `canonical-source`, `plan-task-order`;
  - `plan-file-tags`, `theme-token-coverage`, `fixture-variation`, `main-drivable`;
  - `storage-independence`, `group-claims`, `producer-enumeration`, `storage-grant-pin`, `function-revokes`;
  - `shipping-sets --map` and `--closure` (both `0 gaps`), `publishability`;
  - `page-links --sources`, `page-links --build --ci`;
  - `reference-namespace --base origin/master`, `doc-citations --base origin/master`.
- **The exceptions:**
  - `check-inventory` gives **rc 3**, the documented D1 owner-stop. CI treats it as a warning.
  - `check-selftest-counts --jobs 4` (full) **timed out at 255 s, so treat it as NOT RUN.**
    - The `--changed --base origin/master` form ran (218 s). It reported one disagreement: `check-plan-code.py --self-test` exits 1.
    - I re-ran that suite alone: **503/506**. All 3 failures are `node_modules/typescript is missing`, because this worktree has no `node_modules`.
    - That is the environment, not this branch, which does not touch `check-plan-code.py`. **The cause is environmental; the step is NOT RUN here.**
  - `check-test-counts` needs Jest results: **NOT RUN.**
  - The steps that need a PR body (`dashboard-entry`, `review-recorded`) were **NOT RUN.**

## Findings

### F1 — MINOR — fix_induced: false — closure-guard — `scripts/check-shipping-sets.py:1101`

- **Input:** shipped files `a/dup-2` (clean), `b/z.md` (clean) and `c/z.md` (a D quote), in a plugin `recall`.
  - The scratch copy writes `a/dup-2` as the FILE `dup-2`.
  - `c/z.md` (i=2) collides on basename, so it is routed to `dup-2/z.md`.
  - `mkdir(parents=True, exist_ok=True)` then raises `FileExistsError`, because the parent exists as a file.
  - That `mkdir` sits OUTSIDE the `try` that guards the copy.
- **Observed:** an uncaught `FileExistsError` traceback out of `--closure`, whose process rc is 1. That is the same rc as "gaps", which round 1's M2 called a defect. The opposite order (the dup directory created first, then a FILE named `dup-N`) is caught as `CannotRun: cannot copy`.
- **Expected:** CANNOT RUN (rc 2), or no collision at all.
- **Why MINOR:** it fails CLOSED (red, never `0 gaps`), and no shipped basename in the real declaration matches `dup-\d+`. I checked all three packages: 0.
- **Why not fix-induced:** the copy loop and its `dup-{i}` scheme are round 1's. That code is reachable in r1 too, by a corpus-directory file named `dup-N`. The r2 fold widened the input set to every shipped file, but it did not write the defect.
- **Fix (either):**
  - copy each file into its own index directory (`f"{i}/{name}"`), so no name can collide with a generated one; or
  - move the `mkdir` inside the `try`.

  Add a case with the input above.

### F2 — NIT — fix_induced: false — closure-guard — `scripts/check-shipping-sets.py:1051` (`HIT_RES[0]`)

- **Input:** a shipped file named `n/a: b.md` that carries a D quote.
- **Observed:** rc 2, `CANNOT RUN: ... it names 'a', which was not copied`. The lazy `(.+?): ` splits the builder's hit line at the first `: ` inside the file name.
- **Expected:** a gap on `n/a: b.md`.
- **Why NIT:**
  - It fails closed.
  - When a copied file named exactly `a` exists, the hit is attributed to the wrong file, but the count still matches and the result is still red.
  - The regex is round 1's.
- **Fix:** match the hit line's name against the known `where` keys, or anchor on the builder's `!r` fragment (`: '…'$`). Alternatively, give F1's index-directory copy names that contain no `: `.

### F3 — NIT — fix_induced: true — docs — `docs/dashboard-entries.md:21401`

- **Input:** the dashboard entry says the contract requires "one `<source>: <n> quotes` line per group-D source".
- **Observed:** `_not_clean` accepts ANY number of lines matching `CLEAN_SOURCE_RE`, including zero. The code comment at `:1053–1055` describes the builder's report correctly; only the dashboard prose overclaims.
- **Expected:** the prose matches the check.
- **Fix (either):**
  - reword to "each line before the count line is a `<source>: <n> quotes` line"; or
  - make it true by comparing the source-line count to the D-group size. That size is available from `decision5`'s table, but it is not passed into `decision5_quotes` today.

VERDICT: CONVERGED
