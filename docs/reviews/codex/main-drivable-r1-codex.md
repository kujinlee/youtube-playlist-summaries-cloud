<!-- codex-review: model=gpt-5.5 -->

**Findings**

Blocking: `suite_main_calls` credits calls that are not proven to be reached by `--self-test`. At `scripts/check-main-drivable.py:289-313`, the walker scans every non-skipped top-level subtree and calls that “SUITE”; `classify` then grants routes at `scripts/check-main-drivable.py:502-510`. I verified synthetically that this returns `argv` for:

```python
def unused():
    return main([str(tmp)])
def _self_test():
    case("literal only", main(["--flag"]), 0)
```

and also for `if False: main([str(tmp)])` inside `_self_test`. That violates the rule’s subject: “does its `--self-test` invoke `main()` over a world the case constructed?” A dead or unused call can make a guard look compliant while the suite cannot observe `main` wiring at all.

High: the PARAM route does not check that the “world parameter” is actually a parameter of `main`. `scripts/check-main-drivable.py:459-463` treats any second positional arg, or any keyword other than `argv`, as credit. I verified `def main(argv=None)` plus `main([], root=tmp)` classifies as `param`, even though the call is invalid and no `main` world parameter exists. That is a false-credit path against ADR-0014’s D1 shape.

High: the ARGV route equates “non-constant element” with “constructed world.” `scripts/check-main-drivable.py:466-479` credits any non-constant list element, so `flag = "--self-test"; main([flag])` classifies as `argv`. That is still just a flag vector over the live world, not a constructed path. This is the same dangerous direction as the literal-only discrimination, just hidden behind a local variable.

Medium: restore detection is not correct for tuple restores, causing live route over-reporting in today’s repo. At `scripts/check-main-drivable.py:413-416`, each target is checked against the full RHS name set; for `KNOWN_UNVARIED, EXAMINED_KEYS = _svK, _svF`, the RHS contains a sibling saved name, so neither target is recognized as restored. The live report consequence is visible at `scripts/check-fixture-variation.py:1880-1881`: `main(["/nonexistent/nope.py"])` is credited as `rebind` by the detector even though it is the unreadable-population case, not a constructed-world run. This does not falsely make that file compliant because earlier argv calls really do, but it makes the route accounting untrue and would falsely credit a file that only had this shape.

**Checks Run**

I ran:

`python3 scripts/check-main-drivable.py --self-test` -> 79/79 passed  
`python3 scripts/check-main-drivable.py --report` -> 8 compliant, 29 pinned, 37 in population  
`python3 ~/.claude/projects/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/tools/partial-sweep.py scripts/check-main-drivable.py` -> control green; all 18 mutations red via the named case

I also inspected the 8 reported compliant guards’ credited call sites. I did not find a live false-compliant guard among those 8; the dangerous false-credit paths above are rule holes demonstrated by classifier experiments, and one live over-credit affects route reporting.

CONVERGED: I executed against questions 1, 3, 4, 5, and 6. I sampled question 2 by hand across several pinned guards but did not exhaustively hand-prove all 29. I read question 7 claims against the implementation and found the tuple-restore/route-accounting mismatch above; I did not reproduce the 1.99s -> 0.076s timing claim independently. The working tree was not modified by me; `git status` only showed pre-existing untracked PDFs.
