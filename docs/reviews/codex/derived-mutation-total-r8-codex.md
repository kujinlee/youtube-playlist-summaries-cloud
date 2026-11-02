<!-- codex-review: model=gpt-6.1-sol -->

**COUNTS — High: empty pin map hides a falling pin.** `scripts/check-merge-ready.py:534`, `:1015`. Concrete ordinary edit: `def pin_display(src): return {}`. With synthetic base pins `a=5, b=3` and head pins `a=4, b=3`, real `main()` returned **READY, rc 0**: both revisions became empty maps. This is the explicitly requested empty-dict ordinary-edit case, requiring no hostile objects. **Fix-induced: no; r7 retains it.**

**COUNTS — Medium: self-test calls a sibling outside `_cross`.** `scripts/check-merge-ready.py:2067`:
```python
_base_pins = _pins_reader(PINS_READER).pin_display(_real_src)
```
Both attribute lookup and invocation bypass `_cross`; the result also leaves unreduced. Concrete input: `pin_display` raises `SystemExit(0)` when given the real reader source. Driving `_self_test()` with that behavior escaped at line 2067 with `SystemExit(0)`, before the test summary. Its surrounding `except Exception` does not catch it. This counts under **(c)** independently of return-value attacks. **Fix-induced: no; omitted from r7’s routing.**

The whole-file audit found production sibling attribute reads only at `:1015` and `:1107`, both inside `_cross` lambdas. Cache keys are paths; the marker default argument captures a local string. `_exact_pins` returns a fresh exact dict; `_exact_reason` returns only `None` or exact strings. The import reducer at `:569` explicitly returns the original module, retained as a handle; its production attribute accesses are guarded, but the self-test access above is not.

Measured ordinary-edit outcomes through real `main()`:

| Input | Outcome |
|---|---|
| `pin_display` renamed, signature changed, tuple returned, ordinary `ValueError` | CANNOT RUN, rc 2 |
| Pin keys gain trailing slashes | HOLD, rc 3 |
| Empty dict returned | **READY, rc 0** |
| `exemption_reason` renamed or returns bytes | CANNOT RUN, rc 2 |
| Dashboard gate file missing | CANNOT RUN, rc 2 |
| Check-plan-code missing at HEAD, present at base | HOLD, rc 3 |

`failure_path_removals` against `origin/master...HEAD` reports the **same six lines**, five in merge-ready and one in check-plan-code. All remain **FALSE HOLDs**, for the documented replacement/coverage reasons.

Foreground checks passed: merge-ready **253/253**, check-plan-code **281/281**. No review file written; `.claude/plans/` was not accessed.

**NOT CONVERGED.**
