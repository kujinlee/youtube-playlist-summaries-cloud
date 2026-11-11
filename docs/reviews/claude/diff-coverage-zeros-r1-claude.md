# Round 1 — diff-coverage-zeros — claude

Subject: PR #415, branch `diff-coverage-zeros`, head `3d9ba10a`, `git diff origin/master...HEAD`.
Mandate: refute. Every claim below was executed, in copies under
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/a6abe358-4c0b-44cb-a058-5446372998ef/scratchpad/r371/`
(`copy/` is a `cp -R` of the worktree; `h.py` is the fixture harness, which imports the tool by path with
`sys.modules` registration and `copy/scripts` on `sys.path`; `mut.py` holds my own mutations). git 2.49.0, Python 3.14.

## The three r4 fixtures, rebuilt (attack 1) — all three hold

`python3 r371/h.py r371/copy r4_1_lone_cr r4_2_textconv r4_3_uncommitted_manifest control_plain`

| Fixture | Result |
|---|---|
| r4 #1 committed lone CR (`z = 0\rif bad:`) | rc=0, `NOT CHECKED scripts/g.py: it contains a lone carriage return …` |
| r4 #2 `*.py diff=blank`, `diff.blank.textconv=true` | rc=0, `WARN scripts/g.py:2: \`if bad:\`` |
| r4 #3 uncommitted manifest edit that would clear line 2 | rc=2, `CANNOT RUN — the mutation manifests in the working tree differ …` |
| control, no tampering | rc=0, `WARN scripts/g.py:2` |

`git show` not applying textconv to a blob by default is also true (measured: `git show HEAD:a.py` printed
`x = 1\n`; `git show --textconv` and `git cat-file --textconv` printed nothing).

## High

### H1. The new real-git fixtures are not isolated from `GIT_DIR`: the self-test commits into whatever repository the environment names, rewrites its `user.*` config, and still prints 52/52 — `scripts/check-diff-coverage.py:517-530` (`world()`)

`world()` runs `git init`, `git config user.email/user.name`, `git add -A` and `git commit` with the inherited
environment. Command:

```
V=r371/victim; git init -q $V; git -C $V commit --allow-empty -m victim-root
cd r371/copy && GIT_DIR=$V/.git python3 scripts/check-diff-coverage.py --self-test | tail -1
git -C $V log --oneline --all; git -C $V config -l --local | grep user; git -C $V ls-files
```

Printed: `52/52 self-test cases passed`, then the victim's log had grown from 1 commit to 7
(`a6d1909 head`, `f069238 base`, `8cbfbfe head`, `f145302 base`, `e9232fb head`, `7d56aa4 base`, `dee95fe victim-root`),
its local config gained `user.email=t@t` / `user.name=t`, and its index held `scripts/check-plan-code.py`,
`scripts/g.py`, `scripts/mutations/g.json`.

Two things are wrong at once. The suite writes into a repository it does not own. And the three backlog-#371
cases PASS while doing it: `run_check(w, base)` also inherits `GIT_DIR`, so it measures the victim, which by luck
holds the same commits. So they pass for an ambient reason, which is the failure mode attack 3 asked about.

This repo has already paid for this exact defect. `scripts/codex-review.py:2307-2328` documents it as "r11 High,
DEMONSTRATED": under an exported `GIT_DIR` the fixture's commit "moved a real branch ref off its pushed merge
commit". The fix there was `unredirected()` plus `GIT_CONFIG_GLOBAL=os.devnull` etc. The new fixture copies the
shape and skips the isolation. `GIT_DIR` is exported for real, not in theory: git exports it to hooks, and a
`--self-test` run from a pre-push hook is the natural way to "run it before pushing". The shared `.git/config`
of the main checkout also still holds `core.hookspath=/var/folders/.../tmpmk1hf4tg/no-hooks` (from
`git config --show-origin --show-scope core.hooksPath`), which is `codex-review.py`'s fixture value. That is
evidence a fixture has written into the live repository before.
**Fix:** build `world()`'s environment the way `codex-review.py` does (`unredirected()`, global/system config to
`os.devnull`, `commit.gpgsign=false`, a private `core.hooksPath`). Run the cases' `run_check` under the same env
(through the `run=` seam). Add a case that runs with a planted `GIT_DIR` and asserts the planted repository is
unchanged.

## Medium

### M1. "The manifests must match HEAD's, or the run refuses" is false. `git status` is a proxy that misses three working-tree states the loader still reads, and each gives the clean zero this PR exists to remove — `scripts/check-diff-coverage.py:262-263`

`load_manifests` reads every `scripts/mutations/*.json` file on disk. The guard asks `git status`, which does not
report (a) an ignored untracked file, (b) an `--assume-unchanged` tracked file, or (c) a `--skip-worktree` tracked
file (sparse checkout sets this one). Command: `python3 r371/h.py r371/copy gitignored_manifest skip_worktree_manifest ignored_new_manifest`
(`gitignored_manifest` is the misnamed function that does the `--assume-unchanged` case). Printed:

```
status: ''
--- assume-unchanged manifest edited: rc=0
    diff coverage: 0 changed decision line(s) no mutation edits, across 1 manifested script(s) … — every one is edited by a mutation
--- skip-worktree manifest edited: rc=0
    diff coverage: 0 changed decision line(s) … across 1 manifested script(s) … — every one is edited by a mutation
status: ''
--- ignored NEW manifest h.json: rc=0
    diff coverage: 0 changed decision line(s) … across 2 manifested script(s) … — every one is edited by a mutation
```

The untampered control for each prints `WARN scripts/g.py:2`, or leaves `h.py` uncounted. Case (c) is the r4 #3
fixture exactly, with one extra `git update-index` before the edit. Case (b) is the same with a different flag.
Case (a) counts `h.py` as manifested and "every one is edited" from a manifest HEAD does not have. The global
`core.excludesfile` widens (a) to any pattern in a user's personal ignore file.
**Fix:** compare what the loader will read with HEAD, not status with clean. That means: the set of
`scripts/mutations/*.json` on disk equals `git ls-tree HEAD scripts/mutations/`, and each file's
`git hash-object` equals its HEAD blob. Better still, materialise HEAD's manifests (`git show HEAD:…`) and load
those. That was the backlog row's first-listed fix, and it also removes the usability cost in L3.

### M2. The lone-CR class is only half closed: the DIFF is still read with `text=True`, and a lone CR in a DELETED line can drop a file's later hunks, giving "0 manifested script(s) … every one is edited" — `scripts/check-diff-coverage.py:242-246, 261` (with `parse_diff` at `:128`)

The fix moved `git show` to bytes. `git diff` still goes through `git()` with `text=True`, so universal newlines
still split a lone CR in the diff output. A deleted line is not in HEAD, so `measurable()` never sees it.
Fixture `cr_deleted_line_later_hunk`: base `x = 1\ns = '\rdiff --git zz'\na = 1\nb = 2\nc = 3\n`, head removes line 2
and appends `if bad:\n    pass`. Raw diff (bytes):
`@@ -2 +1,0 @@ x = 1\n-s = '\rdiff --git zz'\n@@ -5,0 +5,2 @@ c = 3\n+if bad:\n+    pass\n`. Read with
`text=True` it becomes `-s = '\ndiff --git zz'\n…`. `parse_diff` sees a `diff --git ` line, resets `new=None`, and
discards the `+5,2` hunk. Printed:

```
--- lone CR deleted line, decision in later hunk: rc=0
    diff coverage: 0 changed decision line(s) no mutation edits, across 0 manifested script(s) changed against f38d3fd0… — every one is edited by a mutation
```

The content is contrived (it needs `\rdiff --git ` on the base side). But this is the r4 #1 mechanism in the one
call the fix left alone, and the PR's commit subject says it "cannot report a clean zero through a lone CR". A
lone CR followed by `@@ -N +M @@` instead adds phantom lines (over-reports).
**Fix:** read the diff as bytes too and split on `b"\n"` only. Keep the `text=True` path for `status` alone, or
drop it. Add the fixture above as a real-git case.

### M3. The real-git fixtures are not isolated from host git config: `commit.gpgsign=true` or a global `core.hooksPath` crashes the whole suite with a traceback — `scripts/check-diff-coverage.py:517-530`

`GIT_CONFIG_GLOBAL=r371/gc-sign python3 scripts/check-diff-coverage.py --self-test` (gc-sign has
`commit.gpgsign=true`, `gpg.program=false`) printed
`subprocess.CalledProcessError: Command '['git', 'commit', '-qm', 'base']' returned non-zero exit status 128.`,
rc=1. With a global `core.hooksPath` whose `pre-commit` exits 1 it printed the same traceback, exit status 1.
`world()` is called outside `caught()`, so no case gets a name and every later case is lost. This is the
`codex-review.py` "r10 High" that the comment at `:2308-2311` describes: "A guard that goes red for the machine it
runs on gets switched off." Same fix as H1.

### M4. Two of my own mutations SURVIVE: nothing tests an UNTRACKED manifest, so the `--untracked-files=all` the fix depends on is unpinned — `scripts/check-diff-coverage.py:262`

`python3 r371/mut.py r371` printed:

```
M1 untracked-files=no: rc=0 52/52 self-test cases passed
M2 status pathspec narrowed … (drop untracked flag): rc=0 52/52 self-test cases passed
M3 show drops --no-textconv: rc=1 51/52   [FAIL] ⭐ both git reads pass --no-textconv …
M4 decode then strip CR (universal-newline equivalent): rc=1 51/52   [FAIL] ⭐ a committed lone CR, read by REAL git …
M5 skip the dirty check when the diff is empty: rc=1 51/52   [FAIL] ⭐ a `git status` that FAILS is CANNOT RUN …
M6 status counts only '??' lines: rc=1 51/52   [FAIL] ⭐ an UNCOMMITTED manifest edit is CANNOT RUN …
```

M1 changes behaviour. The real code refuses a new untracked `scripts/mutations/h.json` (rc=2,
`?? scripts/mutations/h.json`), while the M1 mutant prints `rc=0 … across 2 manifested script(s) … — every one is
edited by a mutation` (`python3 r371/untracked.py r371/copy` and `… r371/m1`). The td5 case covers only an edit
(`M`) and a delete-then-checkout. **Fix:** add an untracked-new-manifest case and a mutation entry for it.

The project harness itself is green for what it pins:
`python3 scripts/check-plan-code.py --mutate . --only scripts/check-diff-coverage.py` (in `copy/`) printed
`OK — … 30 mutation(s), 30 killed, 30 attributed to the case each names, 0 survivor(s)` (47s). The suite printed
`52/52 self-test cases passed`.

## Low

### L1. The refusal message says "`git status` failed: M scripts/mutations/g.json" when git status SUCCEEDED — `scripts/check-diff-coverage.py:264-266`

The parenthetical always says "or `git status` failed:" and then prints `stderr or stdout`. On the ordinary dirty
path that is the porcelain listing. Printed in r4 #3 above:
`(or \`git status\` failed: M scripts/mutations/g.json)`. Split the two messages.

### L2. A manifest staged and then reverted is refused with a false reason — same lines

Fixture `staged_then_reverted`: the working tree is byte-identical to HEAD, `status: 'MM scripts/mutations/g.json\n'`,
and the tool printed rc=2 "the mutation manifests in the working tree differ from HEAD's". The refusal is
conservative, which is fine. The sentence is not true. A content comparison (M1's fix) would run here.

### L3. Usability (attack 4): CANNOT RUN on a dirty `scripts/mutations/` is defensible before a push, and costly in the edit loop

Argument for: before a push, everything being pushed is committed. A dirty manifest is not part of what gets
pushed, so measuring it would describe a tree nobody pushes. Refusing is loud and says what to do ("Commit or
stash it"). No caller treats exit 2 as blocking (`grep -rln check-diff-coverage` finds only docs and reviews, no
hook or workflow), and nothing in this repo dirties `scripts/mutations/` on its own (the main checkout's
`git status` lists none).

Argument against: the tool's natural loop is: it warns, you add a mutation entry, you rerun to see the warning
clear. That loop now needs a commit on every iteration. A stash makes the tool measure without the new entry,
which is the opposite of what you want. Reading HEAD's manifests (M1's fix) gives the same safety, keeps a dirty
tree runnable, and closes M1 too. So the refusal is not a correctness defect, but it is the weaker of the two
fixes the backlog row offered.

### L4. A zero over zero files still says "every one is edited by a mutation" — `scripts/check-diff-coverage.py:310-313` (pre-existing)

Both M2's fixture and `GIT_DIR` pointed at another repository (`git_dir_env`: rc=0,
`across 1 manifested script(s) … every one is edited`) end in the vacuous sentence. When `n_files == 0`,
"no manifested script changed" would be the true statement.

## Prose (attack 5)

- **Module docstring `:19-20`** says "the manifests must match HEAD's, or the run refuses". **`:30`** says "an
  uncommitted change under `scripts/mutations/` is CANNOT RUN". The exit-code paragraph says the same. All are
  false for the three states in M1.
- **Backlog #371 row**, FIXED cell: "(3) an uncommitted change under `scripts/mutations/` is CANNOT RUN" is false
  per M1. "52 cases; 30 mutations (6 new, 3 rebound), each killed by its named case" is true (the harness run
  above). "The falsifier is three cases over REAL repositories" is true, but those cases pass ambiently under
  `GIT_DIR` (H1).
- **Dashboard entry** (`docs/dashboard-entries.md:17816-17824`): "can no longer say 'every one is edited' … [for]
  an uncommitted change to the planted-fault lists" is false per M1 (skip-worktree, assume-unchanged, ignored).
  "a lone CR is NOT CHECKED" is true for HEAD's source and false for a deleted line (M2).
- **PR body**: "No mutation was added for `show`'s `--no-textconv`, because it would be equivalent on git 2.49"
  overstates. It is equivalent in behaviour, but my M3 deleting it was KILLED by the fake-run case "⭐ both git
  reads pass --no-textconv" (51/52). So a manifest entry would be killed, not survive as an equivalent. Item 1's
  "universal-newline translation turned a lone `\r` into `\n` before `measurable()` could refuse it" is true, and
  the same translation still applies to the diff (M2).

VERDICT: NOT CONVERGED
