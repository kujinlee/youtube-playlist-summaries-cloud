<!-- codex-review: model=gpt-5.5 -->

## Verdict
FINDINGS

No new Blocking or High. I found one Low. It is FIX-INDUCED in the r7 `start` readiness self-test, but I did not find a runtime fix-induced defect in `start`/`_restart`.

## Findings
### [Low] Readiness property test can be bypassed by compound statements
**Where:** `scripts/explainer-serve.py:2240`

**What:** 
```python
case("nothing that can fail happens after the readiness byte",
     lambda: all(s.startswith(("os.close(w_fd)", "with httpd", "except OSError",
                               "pass", "try:"))
                 for s in _after_the_byte()))
```

**Why it matters:** `_after_the_byte()` is line/string based and the allow-list uses `startswith`, so it catches a plain inserted failing line like `detach_streams()` after `K`, but it does not actually prove the property. I mutation-checked the predicate in-memory:

```text
os.close(w_fd); detach_streams()                  -> predicate: True
with httpd, open("/definitely/missing/path") as _x: -> predicate: True
```

Both add work after the readiness byte that can fail before `serve_forever`, while still passing this test. The current production code does not contain those shapes: AST enumeration shows only `os.close(w_fd)` and `with httpd:` between the `K` write and `serve_forever`. `BaseServer.__enter__` is just `return self`, so the present `with httpd:` enter is not a real failing step.

**Suggested fix:** Replace the string allow-list with an AST assertion over `start()` requiring the exact post-`K` statement sequence: `os.close(w_fd)`, then a `with` with exactly one context item whose expression is `httpd`, whose body immediately calls `httpd.serve_forever()`. This would reject semicolon compounds and extra context managers.
