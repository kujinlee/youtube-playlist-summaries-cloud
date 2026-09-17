<!-- codex-review: model=gpt-5.5 -->

LOW / `scripts/check-review-recorded.py:596` / ORIGIN: fix-induced by round-2 Fix 5 (`antidrift_verdict` extraction) / failure scenario: the extraction was intended to make the anti-drift ordering falsifiable without changing `main`’s externally visible answer, but the uncovered-directory diagnostic text changed. `HEAD~1` printed `— measured twice on this branch.`; current `antidrift_verdict()` prints `— measured twice.`. Return codes and all other anti-drift messages matched.

Executed evidence:
```text
$ tmp=$(mktemp -d /tmp/r3-compare.XXXXXX); git show HEAD~1:scripts/check-review-recorded.py > "$tmp/old.py"; cp scripts/check-review-recorded.py "$tmp/new.py"; python3 - "$tmp" ...
STATE empty        old rc 2  new rc 2  same msg True
STATE undiscovered old rc 2  new rc 2  same msg True
STATE uncovered    old rc 1  new rc 1  same msg False
OLD: ... owes no review round and skips the final-tree question — measured twice on this branch.
NEW: ... owes no review round and skips the final-tree question — measured twice.
STATE both         old rc 2  new rc 2  same msg True
STATE ok           old rc 0  new rc 0  same msg True
```

Observation proving fixed: restore the exact old suffix in the coverage-failure message, or add a self-test that pins the intended new wording so this is acknowledged as an intentional text change rather than an extraction drift.

LOW / `scripts/check-review-recorded.py:402` / ORIGIN: fix-induced by round-2 Fix 2 (`is_gate_data` deletion) / failure scenario: the code now accepts any existing non-`.md` bound `docs/` file as gate data, but the `gate_code_dirs()` docstring still says the GATE DATA prong is “a `docs/` path a gate binds whose suffix is in `GATE_DATA_SUFFIXES`.” There is no such active suffix allow-list any more. A future maintainer reading the local contract would think the deletion did not broaden the predicate.

Executed evidence:
```text
$ rg -n "GATE_DATA_SUFFIXES|def is_gate_data|return is_file" scripts/check-review-recorded.py
scripts/check-review-recorded.py:402:      2. GATE DATA — a `docs/` path a gate binds whose suffix is in `GATE_DATA_SUFFIXES`.
scripts/check-review-recorded.py:433:def is_gate_data(path: str, is_file: "Callable[[str], bool]") -> bool:
scripts/check-review-recorded.py:468:    return is_file(path)

$ python3 - <<'PY'
... import check-review-recorded.py ...
print(is_gate_data("docs/superpowers/specs/newgate/manifest", lambda p: True))
PY
True
```

Observation proving fixed: update the prong description to say the predicate is “existing non-`.md` file after shape filtering,” not a suffix allow-list.

Checks I ran that did not produce findings:
```text
$ python3 scripts/check-review-recorded.py --self-test
178/178 passed

$ python3 scripts/check-plan-code.py --self-test
128/128 passed

$ python3 scripts/check-plan-code.py --mutate .
OK — delivered scripts mutated: 47 file(s), 732 mutation(s), 732 killed, 732 attributed to the case each names, 0 survivor(s)
```

I also checked the specific attack surfaces:
```text
$ python3 ...  # derive real gate dirs and bound docs paths
derived real ['docs/superpowers/specs/2026-08-03-stable-blob-addressing',
              'docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema',
              'docs/superpowers/specs/m4']
bound existing non-md prose files classified as gate machinery? []

$ python3 ...  # manifest identity
entries 61 unique_names 61 unique_anchor_tuples 61
bad_anchor_occurrences []
declared_pin 61

$ python3 ...  # tracked docs path length
tracked docs files 1465
long offenders []
```

Verdict: NOT CONVERGED. Both findings are fix-induced by round-2 fixes in the same `check-review-recorded.py` derivation/anti-drift component; they are Low observability/prose defects, not wrong gate answers.
