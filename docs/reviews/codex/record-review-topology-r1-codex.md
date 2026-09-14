<!-- codex-review: model=gpt-5.5 -->

**Blocking**

`scripts/check-review-recorded.py:280-281` path-level `dirty` can certify code no reviewer saw.

```py
seen = {s for s in (rec.get("dirty") or []) if isinstance(s, str)}
tails[pathlib.PurePosixPath(rel).name] = sorted(set(after) - seen)
```

Concrete sequence I reproduced in a scratch repo:

1. Commit `lib/x.py` at `v1`.
2. Dispatch review with `head=<v1 commit>` and dirty `["lib/x.py"]`.
3. After review, change `lib/x.py` again to `v3`.
4. Commit final `lib/x.py`, review doc, and verdict.

The gate printed:

```text
ok — the final tree was reviewed by x-r1-codex.verdict.json
SCRATCH_RC=0
```

But the reviewer only saw “some dirty version of `lib/x.py`,” not the committed final contents. This is easy to hit accidentally when fixes after a review stay in the same file, and trivial to hit deliberately. Because the new rule’s whole job is “did any round see the code about to merge?”, path subtraction defeats the rule, not just its edge scope.

**High**

`.github/workflows/ci.yml:408-415` leaves a green CI path where the new rule never runs.

```yaml
- name: check-review-recorded (PR only)
  if: github.event_name == 'pull_request'
```

The workflow also runs on `push: branches: [master]` at `.github/workflows/ci.yml:17-18`, but this step is skipped there. A direct guarded-code push to `master` can have CI green while the review-recorded and final-tree questions are never asked. I cannot verify branch protection from the repo, so I cannot assert this is reachable through normal permissions, but the workflow itself has the green skip path.

**High**

`scripts/check-review-recorded.py:270-273` ignores a valid dirty review taken at the merge base.

```py
if _git("merge-base", "--is-ancestor", head, "HEAD").returncode != 0:
    continue
if _git("merge-base", "--is-ancestor", head, mb).returncode == 0:
    continue
```

I reproduced: branch from `master`, dispatch review before committing with `head == merge-base` and dirty `["lib/x.py"]`, then commit that reviewed dirty file plus artifacts. The script returned `0`:

```text
ok — final-tree rule NOT CHECKED — no Codex round was recorded on this branch
SCRATCH_RC=0
```

That round was this branch’s round: the branch code existed in `dirty`. The skip runs before `dirty` is considered, so a legitimate reviewed final tree is indistinguishable from no usable round, and CI still passes.

**High**

`scripts/check-review-recorded.py:211-214` makes “could not check” a pass.

```py
if not tails:
    why = ...
    return 0, f"final-tree rule NOT CHECKED — {why}"
```

This covers several “unknown” populations: pre-schema verdicts, deleted verdicts skipped at `:255-256`, unreachable/rebased heads skipped at `:270-271`, and the merge-base dirty case above. The wording is honest, but CI consumes the exit code. Under the project rule “CANNOT RUN is a failure, never a pass,” `NOT CHECKED` should not be `0` when guarded code and a review record made the second question applicable.

**Medium**

`scripts/check-review-recorded.py:189-197` uses changed verdict files, not added verdict files.

```py
def branch_verdicts(changed: list[str]) -> list[str]:
    return [p for p in changed if p.startswith(VERDICT_DIR) and p.endswith(".json")]
```

A modified historical verdict is treated as a round this branch wrote. Concrete bad case: a branch adds a normal review markdown file, changes guarded code, and modifies an old `docs/reviews/verdicts/*.json` so its `head`/`dirty` clears the tail. The first question passes via the added markdown; the second question can pass via the modified old verdict. Deleted verdicts are also included by `branch_verdicts()` and then silently skipped by `round_tails()` at `:255-256`, feeding the `NOT CHECKED` pass above. If the intended population is “rounds this branch recorded,” this should use added verdicts or status-aware filtering, not name-only changed paths.

**Medium**

`scripts/codex-review.py:293-296` parses porcelain status with newline/string slicing instead of `-z`.

```py
status = git("status", "--porcelain", "--untracked-files=no") or ""
dirty = {ln[3:].split(" -> ")[-1].strip() for ln in status.splitlines() if ln[3:].strip()}
```

Wrong parses mostly become false failures for quoted paths with spaces/non-ASCII (`core.quotePath`), renames, and paths containing newlines. There is also a false-pass shape: a dirty tracked file literally named `a -> b` parses as `b`; a later committed change to real file `b` is subtracted as “seen” even though the reviewer saw `a -> b`. Porcelain v1’s human-ish quoting is exactly what `--porcelain -z` avoids.

**Medium**

`docs/plugins.md:118-120` now contradicts `docs/review-method.md:240-258`.

```md
Both must complete before marking a task done. **Dispatch them CONCURRENTLY — measured safe.**
```

versus:

```md
1. **Round 1 concurrently**
...
4. **Rounds 2+ alternate**
```

The new section tries to distinguish interference safety from topology, but the canonical plugin governance quick path still commands concurrent dispatch for “Code Review (dual review per task)” without the r2+ exception. A reader following `docs/plugins.md` can violate the new topology while believing they followed the rule.

**Low**

`scripts/check-review-recorded.py:465-469` has a self-test whose name claims live wiring but does not exercise it.

```py
case("the tail rule and the review obligation share one idea of `guarded`",
     guarded_changes(["docs/reviews/codex/x-r1-codex.md", "lib/x.ts"]), ["lib/x.ts"])
```

I deleted the actual `guarded_changes()` call inside `round_tails()` in a scratch copy, replacing it with raw diff lines. `python3 scripts/check-review-recorded.py --self-test` still passed 45/45. So the guard whose removal is invisible is: `round_tails()` must call `guarded_changes()` before computing tails.

Mutation attribution note: the five new mutation entries all kill, but entry 7 is also killed by sibling case `...and the failure names the file no round saw`, and entry 8 is also killed by sibling case `pre-schema-2 verdicts are counted and named, not silently dropped`. The named expectations do fail, so this is not a survivor, just weaker one-case attribution than the prose implies.

Self-test execution: `check-review-recorded.py --self-test` passed 45/45; `codex-review.py --self-test` passed 68/68; `check-plan-code.py --self-test` failed locally because `node_modules/typescript` is missing, so I could not verify that premise in this worktree.

Verdict: NOT CONVERGED.
