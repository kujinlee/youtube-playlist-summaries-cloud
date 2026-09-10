<!-- codex-review: model=gpt-5.5 -->

Reviewed archived branch tip `c1bb6b1c99ef8555fdfe41b8d771184fccbbf323`, extracted with `git archive` into `/tmp/review-gate.QnLaxF`.

**Findings**

BLOCKING — `scripts/check-review-recorded.py:60`

Exact input: a PR diff whose only changed path is `middleware.ts`, empty PR body.

Observed by running the archived code in a throwaway git repo:

```text
git diff --name-only origin/master HEAD
middleware.ts

python3 scripts/check-review-recorded.py --base origin/master
ok — no guarded path changed — a review round is not required
rc=0
```

Expected: fail with rc=1, because root `middleware.ts` is executable Next.js request-path code and can change product/security behavior.

The miss is in the allowlist:

```python
GUARDED = (
    "lib/", "app/", "components/", "worker/", "supabase/", "scripts/", "tests/",
    ".github/", ".claude/hooks/", ".agents/",
)
GUARDED_FILES = ("package.json", "tsconfig.json", "next.config.js", "next.config.ts", "fly.toml")
```

Same class verified for `package-lock.json`:

```text
git diff --name-only origin/master HEAD
package-lock.json

python3 scripts/check-review-recorded.py --base origin/master
ok — no guarded path changed — a review round is not required
rc=0
```

Expected: fail, because `package-lock.json` controls the exact dependency graph used by CI/runtime. Other behavior-affecting root files also return unguarded through `verdict()`: `Dockerfile`, `jest.config.ts`, `playwright.config.ts`, `postcss.config.mjs`, `tsconfig.worker.json`, `.claude/settings.json`, `.claude/commands/clean_gone.md`.

MAJOR — `scripts/check-review-recorded.py:132`

Exact input: run the archived script outside git, as the docstring explicitly describes as a cannot-run case.

Observed:

```text
python3 scripts/check-review-recorded.py --base origin/master
RuntimeError: CANNOT RUN — no .git directory. Treat this as NOT CHECKED.
rc=1
```

Expected: rc=2, no traceback, because the file promises:

```python
* git is absent, the base cannot be resolved, or the clone is SHALLOW -> exit **2**, CANNOT RUN.
```

A real shallow clone shows the same bug:

```text
git rev-parse --is-shallow-repository
true

python3 scripts/check-review-recorded.py --base origin/master
RuntimeError: CANNOT RUN — shallow clone; the diff would be confidently short.
rc=1
```

The implementation raises `RuntimeError` but `main()` never catches it:

```python
changed = changed_paths(args.base)
added = added_paths(args.base)
```

That collapses infrastructure “not checked” into an ordinary Python crash and violates the gate’s stated exit-code contract.

**Checks Run**

`python3 scripts/check-review-recorded.py --self-test` passed `14/14`.

`python3 scripts/check-dashboard-entry.py --self-test` passed `146/146` plus `13/13` cannot-run cases.

Verified non-default `NO-REVIEW:` marker parsing at both dashboard scan points; no finding there.

`python3 scripts/check-plan-code.py --mutate .` could not run from the archive because `node_modules/typescript` is absent, so I did not count mutation results as checked.

NOT CONVERGED
