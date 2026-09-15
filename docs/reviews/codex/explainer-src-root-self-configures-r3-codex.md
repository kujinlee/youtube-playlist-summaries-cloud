<!-- codex-review: model=gpt-5.5 -->

## Verdict
FINDINGS

`src-root-help` is thrashing. The finding below is a defect introduced by round 2’s fix in `src_root_help`, so per `docs/review-method.md` Q5 the architecture review is armed. This should be answered with redesign, not another local patch.

I checked the ARGV slicing against `)` and `$(` in pidfile paths; those do not break the current helper because it uses the first `$(` and last `)`. I found no `page_chrome` regression from the non-raising `shlex.split` change; both self-tests pass (`122/122`, `76/76`).

## Findings

### [Medium] `src_root_help` can reclassify an unset-env missing-checkout failure as a bad env var
**Where:** scripts/explainer-serve.py:1099, scripts/explainer-serve.py:542, scripts/explainer-serve.py:552

**What:**
```python
root = src_root()
if root is None:
    body = src_root_help(os.environ.get(SRC_ROOT_ENV, "").strip(), REPO)
```

```python
if not repo.is_dir():
    return _gone_checkout_help(env_value, repo, pidfile)
```

```python
return (f"no source root — {SRC_ROOT_ENV} is set to {env_value!r}, which is not a "
        f"directory.\n\n"
```

**Why it matters:** `src_root()` can return `None` because `EXPLAINER_DOCS_ROOT` is unset and `REPO.is_dir()` was false. If the repo directory reappears between `src_root()` and `src_root_help()`, `env_value` is still empty but `repo.is_dir()` is now true, so the helper returns: `EXPLAINER_DOCS_ROOT is set to '', which is not a directory`, plus “unset it” advice. That state is reachable because the caller probes live filesystem state twice rather than carrying the reason `src_root()` observed.

This is round-2-fix-induced: the new `repo.is_dir()` branch plus removed fallthrough makes the helper infer the failure reason from a second filesystem read.

**Suggested fix:** Redesign the boundary so `src_root()` returns a structured result/reason from one observation, e.g. `ok(root)` vs `bad_env(value)` vs `missing_fallback(repo)`, and render help from that result instead of recomputing `repo.is_dir()` inside `src_root_help`.
