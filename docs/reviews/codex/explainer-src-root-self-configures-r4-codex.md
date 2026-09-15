<!-- codex-review: model=gpt-5.5 -->

## Verdict
FINDINGS

I believe the redesign removed the CLASS from the current production code, not merely relocated it: `src_root()` carries `reason`, `env_value`, `fallback`, and `fallback_ok`, and the live `/src/` 404 path renders from that observation without a second env read or `is_dir()` probe. The evidence is the caller at `scripts/explainer-serve.py:1112`: it branches on `observed.root` and only calls `src_root_help(observed)` on failure.

But the class falsifier does not fully prove that property.

## Findings

### [Medium] The class falsifier still permits other world re-reads
**Where:** `scripts/explainer-serve.py:1760`

**What:**
```python
class _Forbidden(dict):
    def __init__(self, what): super().__init__(); self._what = what
    def _raise(self, *_a, **_k):
        raise AssertionError(f"src_root_help read {self._what} — it must carry, "
                             f"not re-derive")
    get = __getitem__ = __contains__ = keys = items = values = _raise
```

and:

```python
pathlib.Path.is_dir = _boom
os.environ = _Forbidden("the environment")
return bool(src_root_help(observed))
```

**Why it matters:** the falsifier claims “NO environment and NO filesystem”, but it only forbids `Path.is_dir()` and a few env mapping methods. I mutated the renderer to re-derive through another filesystem API:

```python
if not observed.fallback.exists():
```

The suite went red, but not because the class falsifier failed. It failed later on narrower gone-checkout behavior cases:

```text
[FAIL] help: the gone-checkout arm does not advise unsetting
[FAIL] help: with the REAL repo, the arm emits no command under the missing checkout
...
self-test: 121/128 passed
```

So a world re-read via `Path.exists()` slips past the falsifier itself. Similar gaps remain for `Path.stat()`, `Path.is_file()`, `Path.open()`, `Path.read_text()`, `subprocess`, `os.environ.copy()`, `len(os.environ)`, and iteration over `os.environ`.

The two refusal cases are load-bearing: removing the unknown-reason refusal failed exactly its case, and removing the OK refusal failed exactly its case. Baseline self-test is green: `128/128 passed`.

**Suggested fix:** strengthen `_renders_without_the_world` so it forbids the class, not two instances. Patch a denylist of filesystem methods used for probing (`is_dir`, `exists`, `is_file`, `stat`, maybe `open/read_text/resolve`) and replace `os.environ` with a mapping object whose `copy`, `__iter__`, and `__len__` also raise. Even better, pass a poison `fallback` object into `SrcRoot` that only permits `str()` and `/ "scripts" / "explainer-serve.py"` if those are the renderer’s intended pure operations.
