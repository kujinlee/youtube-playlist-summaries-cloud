# Round 3 — backlog-kinds — claude

Reviewed `e24da6df` (the redesign; `git diff bdf8f1a1..e24da6df` read first) in the `wt-394` worktree. I built every world below as a real git repository in scratchpad temp directories and ran it through the shipped `scan()`/`main()`. Nothing in the worktree was edited, staged or committed. I read no plan files and quote no plan text.

**THE BET, "no diff shape gets new prose past the exemption": REFUTED on two shapes.** (1) A path that git renders as **binary** produces no added lines, so the gate prints OK over a new bare `#77`. This predates the redesign, but it is a diff shape the brief names. (2) Under a repo-controlled `eol=crlf` attribute, the r2 **duplicate-line** rule is defeated. That one is caused by the r2 fix. The core redesign holds: reading the base per path, a counted budget, and `in_hunk` parsing of one-path diffs. I found no content-impersonation, rename, move-and-edit or marker trick that gets past it.

## Commands run (foreground)

| Command | Result |
|---|---|
| `python3 scripts/check-reference-namespace.py --self-test` | **46/46 passed**, rc 0 |
| `python3 scripts/check-plan-code.py --mutate . --only scripts/check-reference-namespace.py` | **20/20 killed, 20 attributed, 0 survivors** (diagnostic slice, 1m18s) |
| `python3 scripts/check-reference-namespace.py --base origin/master` (real repo; origin/master is an ancestor of HEAD) | **OK, 0 violations**, rc 0 |
| `python3 tools/plan_leak_scan.py wt-394 --base origin/master` (scratch leak scan, new API) | rc 0. Summary line: 673 plan strings, 1133 added tracked lines, **+356 marker-only not judged**, **hits: 0**. It loads `exemption_budget` and calls `changed_paths`/`path_diff`/`added_lines`/`file_lines`/`marker_only` without error |

## Findings

### F1 — Medium — `scripts/check-reference-namespace.py:290-293` (`path_diff`): a path git renders as binary is scanned as having no added lines, and the gate prints OK (fail-open)
- **Input:** any one of these, each with a new row `| 99 | new see #77 |` appended to `docs/backlog.md`:
  - (a) a NUL byte anywhere in the file;
  - (b) `.gitattributes` containing `docs/backlog.md -diff`;
  - (c) `.gitattributes` containing `*.md binary`.
- **Evidence (run):** in all three worlds `scan()` returns **0 violations**, and a sound gate reports at least 1. Git's one-path diff is only a header plus `Binary files a/docs/backlog.md and b/docs/backlog.md differ`. It has no `@@`, so `added_lines` returns `[]`. With `--text --no-textconv` added to the same command, git renders `+| 99 | new see #77 |` for (a), (b) and (c).
- **Fix-induced:** false. The `bdf8f1a1` code also returns rc 0 on the NUL and `-diff` worlds (run).
- **Component:** added-line fetch.
- **Fix:**
  - Pass `--text --no-textconv` in `path_diff`.
  - Belt and braces, per "cannot run is a failure": if an in-scope path changed but its diff has no hunk and no mode-only header, raise `RuntimeError`, so the result is CANNOT RUN.
  - Add a real-git case (`.gitattributes -diff`) and a manifest mutant that drops `--text`.

### F2 — Low — `scripts/check-reference-namespace.py:296-300` with `:316`: the head side is read as raw worktree bytes and the diff side through git's clean filter, so under `eol=crlf` a marked duplicate of a row that stays is exempt
- **Input:** the base has `docs/backlog.md` holding row `OLD`. The head adds `.gitattributes` with `docs/backlog.md text eol=crlf` (so the checkout is CRLF, on CI's Linux runner as well), keeps `OLD` unmarked, and appends `NEW` (the same row with `⟦kind: task⟧`).
- **Evidence (run):** `scan()` returns **0** violations. The control world without the attribute returns **2**.
  - `od -c` shows the diff line ending `|  \n` while the worktree line ends `|  \r  \n`.
  - `Counter(head)` therefore holds `OLD\r`, not `OLD`. The subtraction misses, and `budget[OLD]` stays at 1.
  - This defeats the r2 rule that the self-test case *"a base row that STAYS unmarked does not also exempt a marked copy of it"* pins on synthetic input.
- **Fix-induced:** true. The head subtraction is new in r2.
- **Component:** namespace-exemption.
- **Fix:** take the head's count from git's own view. Either:
  - (i) derive the unmarked-copies term from the same one-path diff, as `Counter(removed) − Counter(added unmarked)`. That is identical to `Counter(base) − Counter(head)` per line, and inside a one-path diff it is as impersonation-proof as `added_lines`, by the same `in_hunk` argument; or
  - (ii) read the worktree through the clean filter (`git hash-object -w --path=<p> <file>`, then `cat-file blob`).

  Add the `eol=crlf` real-git world as a case.

### F3 — Low — `scripts/check-reference-namespace.py:178` (`added_lines`): the `split("\n")` rule the docstring argues for is pinned by no case, and reverting it reopens a bypass
- **Input:** the mutant `one_path_diff.split("\n")` → `one_path_diff.splitlines()`, which is exactly the pre-r2 form (`bdf8f1a1:168`).
- **Evidence (run):**
  - The self-test stays **46/46**, so the mutant survives.
  - The real-git world adds `note\x1cthen see #77` to `docs/dev-process.md`. The shipped code reports **1** violation; the mutant reports **0**, because `splitlines()` breaks at `\x1c` and the second half loses its `+`.
  - The same mutant on `file_lines` (both sites) also survives 46/46. That one only fails toward false positives, so it is lower priority.
- **Fix-induced:** false. The r2 code fixed the split, but nothing pins it.
- **Component:** added-line fetch (instrument).
- **Fix:** add this world as a case and register the `added_lines` mutant in `scripts/mutations/check-reference-namespace.json` (manifest 20 → 21).

### F4 — Low — `scripts/check-reference-namespace.py:282-287` (scope): replacing an in-scope file with a symlink moves its prose out of scope
- **Input:** `docs/backlog.md` becomes a symlink to `real.md`. The new file `docs/real.md` (not in SCOPE) holds a new `| 99 | new see #77 |`.
- **Evidence (run):** **0** violations. The diff of `docs/backlog.md` adds only the link target text. The `bdf8f1a1` code also returns 0 (run).
- **Fix-induced:** false.
- **Component:** scope. This is not the exemption.
- **Fix:** treat an in-scope path whose head entry is mode `120000` as a violation, or as CANNOT RUN naming the target.

## Held (run, with the count each world returned)

| World | Result |
|---|---|
| Row moved within the file, marker only | 0 (correct) |
| Row moved within the file and edited (`#18`→`#19`) | 2 |
| Two markers on the line | 2 (judged) |
| Tab inside the marker | 0 (correct: `kind_mark` strips the field) |
| Trailing whitespace after the marker | 2 (a false positive, the safe direction) |
| Raw CRLF file with no attribute: marker-only edit | 0 |
| Raw CRLF file with no attribute: duplicate | 2 |
| Row moved out of a code fence into the table | 0. The text is pre-existing, not new prose |
| Merge commit as `head` (`scan(head="HEAD")` after `--no-ff`) | 1 (correct) |
| `base` as a sha, a tag, a branch name, or `branch~0` | 1 in every form, identical |

- **`./docs/backlog.md` as a path:** not applicable. Paths come only from git's `-z` name-only output, and the user never supplies one. `--literal-pathspecs` covers glob characters.
- **Submodule:** a gitlink's diff body is `+Subproject commit <sha>`, which carries no `#N` and no `⟦`, so `file_lines` is never reached for it.
- **Mode-only change:** no hunk, so no added lines. Correct.
- **Three-dot versus two-dot:** CI diffs `origin/$GITHUB_BASE_REF` against the merge checkout, which is exactly the PR's changes. Locally, a stale branch can only add base-side lines that the head lacks as removals, and a master-only row can only remove exemptions. That direction is false positives, never a bypass.

**Two surviving mutants I judge equivalent, not findings:**
- Dropping the `cells[0].strip()` check: the exempt line is still the base line plus a grammar-restricted marker, and a marker's only `#N` form is `part of: backlog #N`, which is qualified.
- Dropping the `name`/`blob` check in `file_lines`: it is only reachable for a path whose added lines contain `⟦`, and a gitlink diff cannot contain one.

## Counts

| Severity | Count | Findings |
|---|---|---|
| Blocking | 0 | — |
| High | 0 | — |
| Medium | 1 | F1 |
| Low | 3 | F2, F3, F4 |

1 finding caused by the r2 fix: F2.

**NOT CONVERGED.** F1 is a fail-open on a diff shape the bet names, and F2 defeats the r2 duplicate rule through a repo-controlled attribute. Both are small fixes in `path_diff`/`scan`, each with a real-git case.
