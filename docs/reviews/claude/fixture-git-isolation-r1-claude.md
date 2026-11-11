# fixture-git-isolation — round 1, Claude half (adversarial)

**Subject:** PR #420, branch `fixture-git-isolation`, commit `1003add0` (backlog #373). Diff `origin/master...HEAD`.
**Mandate:** refute the claim that *no repository-building self-test fixture can write into, or read config from, a
repository or config the caller supplies through the environment*.
**Method:** I ran executed reproductions, not reasoning. I wrote an extended falsifier
(scratchpad `r1c/fals.sh`, plus `fals-idx.sh` which also hashes `.git/index`). Each run builds a victim repo
under `mktemp -d` and plants a hooks dir whose `pre-commit`, `post-commit`, `post-checkout`,
`reference-transaction` and `post-index-change` hooks append to a marker file. It also plants a `core.fsmonitor`
script that does the same, and a hostile `$HOME/.gitconfig` and `$XDG_CONFIG_HOME/git/config` that name both. It
runs one `--self-test` with ONE planted variable family: `GIT_DIR`, `GIT_DIR`+`GIT_WORK_TREE`, `GIT_INDEX_FILE`,
`GIT_OBJECT_DIRECTORY`, `GIT_CONFIG_COUNT/KEY/VALUE`, `GIT_CONFIG_PARAMETERS`, `HOME`, `XDG_CONFIG_HOME` or
`GIT_CONFIG_GLOBAL`. Then it hashes the victim and reads the marker. Population: the 8 migrated files, the 4
EXEMPT files that are not the helper, and the 14 other git-using scripts that have a `--self-test`. I also probed
the guard directly through `check_source`, and re-ran the mutation harness for both new files.

**What holds, measured:**
- `fixture_git.env()` is sound. Changing it from an allow-list to a deny-list reddens 3 cases, the
  command-scope-config case among them, so that case is not ambient.
- With `GIT_DIR` exported, all 8 migrated files leave the victim byte-identical, index included.
- Over master's tree the guard refuses exactly the 8 files.
- `--mutate . --only` gives 6/6 and 17/17, each mutant killed by the case it names. The implementer's
  `373-out/mut-fixture_git.txt` shows an earlier FAILED run (an unattributable kill), and at HEAD that run is OK.
- `check-selftest-counts`, `check-ratchet-contract` and `check-fixture-variation` are green.
- The three CI steps are in the `verify` job.

**What fails: the claim is refuted at two points.** One is an EXEMPT file that writes into the caller's
repository. The other is that every fixture which drives production readers runs commands that the caller's config
supplies.

---

## B1 — Blocking: `codex-review.py` is EXEMPT for a reason that is false. Its self-test writes into the caller's index and object store and runs the caller's hooks

`scripts/check-fixture-git-isolation.py:61-62` exempts it because *"its fixture git goes through `unredirected()`,
which also isolates…"*. `unredirected()` strips only `REDIRECT_VARS = ("GIT_DIR", "GIT_WORK_TREE",
"GIT_COMMON_DIR")` (`scripts/codex-review.py:719`). Its own docstring says that it **deliberately keeps**
`GIT_INDEX_FILE` and `GIT_CONFIG_*` (`:738-741`). The fixture env is `dict(unredirected(), GIT_CONFIG_GLOBAL=…,
GIT_CONFIG_SYSTEM=…, GIT_CONFIG_NOSYSTEM="1", …)` (`:2319`). So `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`,
`GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_CONFIG_COUNT/KEY/VALUE` and `GIT_CONFIG_PARAMETERS` all reach the
fixture's `git init` and `git commit`.

**Reproduction (executed):**

```
victim index before: ce5d8fdb…   ls-files: v.txt
GIT_INDEX_FILE=$victim/.git/index python3 scripts/codex-review.py --self-test   → 168/168 passed
victim index after:  ca54a2e4…   ls-files: a.txt, gone.txt, unchanged.txt
victim `git status`: fatal: unable to read 5626abf0f72e58d7a153368ba57db4c673c0e171
```

The suite reports green. Meanwhile the victim's staging area is replaced with the fixture's entries, which point at
objects the victim does not have, so the victim repository no longer answers `git status`. The other modes:

| planted | codex-review result |
|---|---|
| `GIT_OBJECT_DIRECTORY=$victim/.git/objects` | victim `.git` **CHANGED**: fixture objects written into it |
| `GIT_CONFIG_COUNT` → `core.hooksPath` | caller-supplied hooks **RAN** in the fixture repo: 1 `post-commit`, 7 `reference-transaction`, 4 `post-index-change`, plus 10 `fsmonitor` executions |
| `GIT_CONFIG_PARAMETERS` | the same 10/1/4/7 |

The repo-local `core.hooksPath` that the fixture sets at `:2328` does not protect it, because command-scope config
outranks local config. This is the class of the original #373 incident, a caller's `core.hooksPath` acting inside
a fixture, and it still happens in a file this PR certifies as isolated. The same claim is in the backlog row
("`codex-review.py` already isolate") and in the commit's EXEMPT reasoning.

Realism: git exports `GIT_INDEX_FILE` to hooks during `git commit -a` and `git commit <paths>`. In that case it
points at the index being committed. Any hook that runs self-tests is therefore a caller of exactly this kind.

Why the PR's own falsifier missed it: `373-out/falsifier.sh` and the backlog row's FALSIFIER export **only
`GIT_DIR`**. The fixture_git self-test plants the full family, but the cross-file run does not.

**Fix:**
1. Delete the EXEMPT entry. Run the fixture's `_git` (`:2321`) under `env=fixture_git.env()`. The guard
   already sees `_git` as a fixture call: my scope audit lists only `reviewed_state/git` as unscoped. So
   removing the exemption alone turns the guard red here.
2. Widen the cross-file falsifier, and the backlog row's FALSIFIER, to the full planted family:
   `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`, `GIT_CONFIG_COUNT`, `GIT_CONFIG_PARAMETERS`, and a hostile HOME/XDG.
   Also add the hook marker, so that "byte-identical" is not the only observation.
3. Re-check the other four EXEMPT reasons against that wider run. I did: `check-run-hook` and
   `check-diff-coverage` stay clean in every mode, and `check-doc-citations` is M1.

## M1 — Major: the "read config" half is false for every fixture that drives a production reader. Caller-supplied config EXECUTES inside the fixture repos

The guard checks only the fixture's own `["git", …]` launches. Several self-tests then call production functions
over the fixture repository. Those functions inherit `os.environ`: `provenance` (page_chrome `:1288`),
`added_diff` (check-reference-namespace `:181`), `tree_at` (check-decision-scheme), `current_branch`
(check-plan-progress `:406`), `linked_worktree_main` (begin-plan `:2131`), and `changed_files`/`tracked_files`/`blob`
(check-doc-citations).

| self-test | under `HOME` / `XDG_CONFIG_HOME` / `GIT_CONFIG_COUNT` / `GIT_CONFIG_PARAMETERS` | under `GIT_DIR` (and `GIT_OBJECT_DIRECTORY`) |
|---|---|---|
| check-reference-namespace (migrated) | **8 fsmonitor runs in the fixture repos** `…/bad`, `…/hookworld`; suite green | 22/26 (objdir 22/26) |
| page_chrome (migrated) | **6 fsmonitor runs + 2–3 caller `post-index-change` hook runs** in the fixture tmp repo; suite green | 230/233 (objdir 231/233) |
| check-doc-citations (EXEMPT) | **182 fsmonitor runs** across its fixture repos; suite green | 66/78 (objdir 67/78) |
| codex-review (EXEMPT) | 4 fsmonitor runs under HOME, XDG or a hostile `GIT_CONFIG_GLOBAL` (from `reviewed_state`) | green |
| begin-plan / check-decision-scheme / check-plan-progress (migrated) | clean | 137/139, 271/274 (objdir 269/274), 64/66 |

The commit message discloses the `GIT_DIR` reds as *"a read, not a write"*. That label does not cover the left
column. A hook or `core.fsmonitor` that the caller's configuration names is **executed** in a repository the
fixture built, and every one of those suites still reports green. The claim says fixtures cannot *read config the
caller supplies*, and here they act on it. A common real setting, `core.fsmonitor=true`, would start a
fsmonitor daemon for each fixture repo.

The EXEMPT reason for `check-doc-citations` (`:63-64`, "its fixtures build an environment from scratch…") is true
only of the `run()` helpers. The production calls those fixtures drive inherit everything.

**Fix:** isolate the process, not only the call. Add `fixture_git.isolated()`, a context manager that replaces
`os.environ` with `env()` for its body and restores it on every path. The fixture_git self-test already writes
that restore logic. Wrap each self-test that drives a production reader over a fixture repo in it. This also
removes the 6 `GIT_DIR` reds, which makes those suites usable from a hook. The guard can then require that a
builder's self-test enters `isolated()` and stop matching calls one by one. The alternative is to thread an `env`
parameter through each production reader, which has more call sites.

## M2 — Major: the guard passes a builder whose inherited-env git sits beside one checked call. Its BOUNDS docstring says that case is refused

`check-fixture-git-isolation.py:31-34` says an argv built in a variable, or `env` passed through `**kwargs`,
*"makes a building file 'no checkable call', which is refused, not passed"*. That is true only when the file has no
other checkable call. `check_source` (`:148-166`) checks the calls it can see and passes everything else. I ran
these through `check_source`, each with one correctly isolated `["git","init",…]` call in `_self_test`:

| probe | rc |
|---|---|
| C — a helper `_make_repo(d)` that does `subprocess.run(["git","init",…])` and a commit with **no `env=`**, called from `_self_test` | **0** |
| D — `cmd = ["git","-C","a","commit",…]; subprocess.run(cmd)` | **0** |
| A — `env={**fixture_git.env(), **os.environ}`, which puts the whole caller env on top | **0** |
| B — `env=os.environ if fixture_git.env() else None` | **0** |

C is not hypothetical as a shape. `check-doc-citations` names its fixture functions `_rename_witness`,
`_nul_witness`, `_promotion_witness`, `_blob_witness`, `_rename_orientation_witness` and `_empty_tree_witness`.
None of those names contains the `test` word, so all six are outside the guard's scope today. Only EXEMPT hides
that.

**Fix:**
- C and D: in a builder file, require every `git` launch outside the fixture scope to be on a named `PRODUCTION`
  allow-list, so that the default is refusal. The alternative is to treat a builder file that contains any git
  launch the guard cannot attribute as refused. Then the docstring's sentence becomes true.
- A and B: refuse any `env=` expression that references `os.environ` at all, and require the helper call to
  be the value, or the first `**` of a dict with literal keys only.

## Minor

- **m1 — other false negatives, each rc=0:**
  - launcher aliased (`sp = subprocess.run; sp(["git",…])`);
  - git named by a variable (`[GIT, …]`, `shutil.which`);
  - a tuple argv to `check_output(("git",…))`;
  - a function named `selftest` (no underscore), which is outside `SELF_TEST_NAMES` and `TEST_WORD`;
  - `git clone` as the only builder, since clone is not a repository-build sign;
  - `subprocess.run("git init …", shell=True)` and `os.system("git init …")`, which are not detected as builders at
    all, so the file passes as a non-builder.

  None of these occurs in the tree today, but each one is a silent pass and not a refusal.
- **m2 — false positives:** `_builds_repo` (`:82`) treats *any* call with a positional `"init"` as a repository
  build. `sub.add_parser("init")` and `xs.count("init")` each make a file a "builder", which is then refused with
  the "no checkable fixture git call" message. Nothing in the tree trips this today, but the message would send
  the reader looking for git that does not exist. Fix: require a git context, for example the enclosing call's
  argv starting `"git"`, or `init` immediately after git's global options.
- **m3 — misleading refusal text:** the master-tree run refuses page_chrome `:1610/1612/1613` with *"inherits the
  caller's environment"*. Its env actually arrived through `**_q` (`env=_env` inside a dict). The finding is
  right but the diagnosis is wrong. Fix: when the call has a `**` keyword, say "env= not visible (passed through
  `**`)".
- **m4 — `REFUSED_EXTRA` is a deny-list with no coverage, and short.** `fixture_git.py:47-48` lists 8 names, but
  the self-test exercises only `GIT_DIR` and `GIT_CONFIG_COUNT`. Executed check: deleting `GIT_INDEX_FILE` and
  `GIT_OBJECT_DIRECTORY` from the tuple leaves the suite at **14/14**, and
  `env(GIT_INDEX_FILE=…, GIT_OBJECT_DIRECTORY=…)` then returns both. `GIT_SHALLOW_FILE`, `GIT_GRAFT_FILE`,
  `GIT_REPLACE_REF_BASE` and `GIT_EXEC_PATH` are accepted today. The module's own principle is "constructed, never
  filtered", so the extras should be an allow-list too. Callers pass only `HOME`, `GIT_AUTHOR_*`,
  `GIT_COMMITTER_*` and dates, so allow `HOME` plus `GIT_(AUTHOR|COMMITTER)_(NAME|EMAIL|DATE)`. Then iterate the
  refused-extra case over a sample that includes `GIT_INDEX_FILE`.
- **m5 — evidence scope:** "all eight leave it byte-identical" (commit, backlog row) is measured for `GIT_DIR`
  only. It is true, and I re-measured it including the index. But it is the narrowest of the families the claim
  covers, and B1 sits in the family it skipped. State the family in the row.

## Unrelated, noted

`scripts/subject_status.py --self-test` fails 16/17 with **no** planted variable at all, in my baseline run on
this tree. It reads the real repository and builds none, so it is out of scope for #373. It is red independently
of this PR.

VERDICT: NOT CONVERGED
