<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Medium, fix-induced** — `_drive_src` in the committed subject only counts `os.environ.get`, so the “exactly one env read” invariant can be bypassed by changing the second read form.  
File: `78100320:scripts/explainer-serve.py:1962`  
Evidence: I restored the exact committed file from `HEAD:scripts/explainer-serve.py`, inserted this in the `/src/` branch after `observed = src_root()`:

```python
if SRC_ROOT_ENV in os.environ:
    pass
```

Then `python3 scripts/explainer-serve.py --self-test` still printed `self-test: 133/133 passed`. That means the new caller harness does exercise `do_GET`, but the counter is too narrow for the invariant it claims.  
Falsifier: the same mutation reddens the suite, or `_Counting` counts membership/indexing/bulk reads as well as `get`. Note: the current worktree already has an uncommitted broadening of `_Counting`; this finding is against the requested commit `78100320`.

**Medium, fix-induced** — the `[FAIL]` format guard covers only the false-result print arm, not the exception print arm.  
File: [scripts/explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:2110) and [scripts/explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:2129)  
Evidence: mutating only the exception reporter from:

```python
print(f"  [FAIL] {name} — {type(exc).__name__}: {exc}")
```

to:

```python
print(f"  EXC: {name} — {type(exc).__name__}: {exc}")
```

still printed `self-test: 133/133 passed`. This matters because mutation kills commonly arrive through raised cases, and `check-plan-code.parse_fail_names` depends on `[FAIL] `.  
Falsifier: a mutation of either runner print prefix, including the `except` arm, reddens the self-test.

**Low, fix-induced** — H1’s “count is gone” replacement still carries a drifting exact count.  
File: [scripts/explainer-serve.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/explainer-serve.py:221)  
Evidence: the comment says “Measured in the main checkout: 11,506”; walking the current tree for `SERVABLE` suffixes printed `TOTAL 11507` with `node_modules 9528`, `docs 1295`, `.next 379`, `.superpowers 105`, `.remember 76`. The qualitative reach claim is true, and the security reasoning checked out, but the fix did not fully delete staleable counts.  
Falsifier: the servable walk returns 11,506 in this checkout, or the replacement text removes exact corpus counts from the live comment.

**Checks Run**

Green controls included:

- `python3 scripts/explainer-serve.py --self-test` → `133/133`
- `HOME=$(mktemp -d)/.home python3 scripts/explainer-serve.py --self-test` → `133/133`
- `python3 scripts/check-fixture-variation.py --self-test` → `67/67`
- `python3 scripts/check-fixture-variation.py` → population OK
- `python3 scripts/gen-dashboard.py --self-test` → `325/325`
- `python3 scripts/check-plan-code.py --self-test` → `128/128`
- `python3 scripts/check-docs.py` → OK
- `python3 scripts/check-selftest-counts.py` → 39 scripts verified
- `python3 scripts/check-ratchet-contract.py` → OK

I also confirmed the CORS claim against `_send`: it emits status, `Content-Type`, and `Content-Length`, with no `Access-Control-Allow-Origin`.

Extraction hygiene: no live restart route/symbol found in active explainer code; the grep hits were docs/history or unrelated `repo_root` parameters.

I did **not** reach **CONVERGED**.
