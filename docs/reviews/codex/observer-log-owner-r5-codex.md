# Codex adversarial review — observer-log-owner, round 5

**Subject:** the FOLD — `27db82a8` (round 5's fold of its Claude half: 1 High, 4 Medium, 1 Low,
plus one pre-existing `check-fixture-variation` failure). Mandate: refute, not confirm.

**Verdict: NOT CONVERGED — 0 Blocking, 0 High, 1 Medium, 0 Low.**

⚠ **Captured from the final message — Codex writes no file** (`docs/plugins.md` output contract).
Verdict: `docs/reviews/verdicts/observer-log-owner-r5-codex.9511331e6df5f942.verdict.json`,
`gate_ran=true`, model `gpt-5.5`. ⭐ The 16-hex token in that filename is r5's widened allocator
working on its first live dispatch.

⭐ **ITS ONE FINDING WAS CORRECT AND IS FOLDED:** `SUITE_TIMEOUT` was the last self-agreeing
constant, in the OTHER touched file — the Claude half had already named it inside its M3 and the
fold took only the half living in `codex-review.py`. An instance fix of an instance fix.

---

<!-- codex-review: model=gpt-5.5 -->

Subject: measured branch `observer-log-owner` at `27db82a80a23c44f5a5ac81dfa8a29e8885b1203` against base `origin/master` `b493edccb5f4b6020f40710f828c3b2311319bf7`. Working tree remained clean.

**NOT CONVERGED** with `0 Blocking · 0 High · 1 Medium · 0 Low`.

**What I Verified GREEN**
Command:
```bash
git rev-parse HEAD && git rev-parse origin/master && git status --short --branch
```
Output:
```text
27db82a80a23c44f5a5ac81dfa8a29e8885b1203
b493edccb5f4b6020f40710f828c3b2311319bf7
## observer-log-owner...origin/observer-log-owner [ahead 2]
```

Command:
```bash
python3 scripts/codex-review.py --self-test
```
Output ended:
```text
125/125 passed
```

Command:
```bash
python3 scripts/check-plan-code.py --self-test
```
Output:
```text
130/130 passed
```

Command:
```bash
python3 scripts/check-fixture-variation.py
```
Output:
```text
fixture variation OK — 649 parameter(s) examined across 58 file(s); 120 known-unvaried ratcheted, 7 exempt with a written reason
```

Command:
```bash
python3 - <<'PY'
import ast, json, pathlib
root = pathlib.Path('.').resolve()
mod = ast.parse((root/'scripts/check-plan-code.py').read_text())
expected = next(ast.literal_eval(n.value) for n in mod.body
                if isinstance(n, ast.Assign)
                for t in n.targets
                if isinstance(t, ast.Name) and t.id == 'EXPECTED_MUTATIONS')
manifest_counts = {}
for p in sorted((root/'scripts/mutations').glob('*.json')):
    manifest_counts['scripts/' + p.name[:-5] + '.py'] = len(json.loads(p.read_text()))
print('declared sum', sum(expected.values()))
print('declared codex-review', expected.get('scripts/codex-review.py'))
print('manifest sum', sum(manifest_counts.values()))
print('manifest codex-review', manifest_counts.get('scripts/codex-review.py'))
print('declared files', len(expected))
print('manifest files', len(manifest_counts))
print('mismatches', [(k, expected.get(k), manifest_counts.get(k))
      for k in sorted(set(expected)|set(manifest_counts)) if expected.get(k) != manifest_counts.get(k)][:10])
PY
```
Output:
```text
declared sum 993
declared codex-review 28
manifest sum 993
manifest codex-review 28
declared files 53
manifest files 53
mismatches []
```

The 12 r4+r5 `codex-review` mutations were run through the harness path over green controls by monkey-patching only the manifest loader in memory. Output:
```text
subset count 12
[1/1] control scripts/codex-review.py
[1/12] r4 H1: the allocator is dropped...
...
[12/12] r5 L1: the rate limit stops counting as an account-level fault
[1/1] re-control scripts/codex-review.py
ok True
declared 12
mutations 12
survivors 0
```
The measured records show every entry had `caught=True`, `attributed=True`, `measured=True`.

I also verified M4 directly:
```text
run_token defaults 0 []
all run_token calls: posargs 3
same head/prompt clean vs none False
verdict dirty none present/value True None
verdict dirty empty present/value True {}
```

**Findings**

Medium, structural: `SUITE_TIMEOUT` is another surviving self-agreeing constant in `check-plan-code.py`, so M1’s “class is closed” claim is false.

Premise: the fold says this class was closed by literal outside observers for `VERDICT_DIR`, `MIN_REVIEW_CHARS`, and `ACCOUNT_FAULT_STATUSES`, and the brief explicitly asks for more survivors in both `codex-review.py` and `check-plan-code.py`.

Code:
```text
scripts/check-plan-code.py:97
SUITE_TIMEOUT = 120
```
```text
scripts/check-plan-code.py:500-505
r = subprocess.run([sys.executable, name, "--self-test"], cwd=d,
                   capture_output=True, text=True, timeout=SUITE_TIMEOUT,
                   env=child_env(d))
except subprocess.TimeoutExpired:
    return 2, "", (f"CANNOT RUN — {name} --self-test did not finish in "
                   f"{SUITE_TIMEOUT}s. NOT CHECKED.")
```

Measurement:
```bash
python3 - <<'PY'
import importlib.util, pathlib, sys, io, contextlib
root=pathlib.Path('.').resolve()
spec=importlib.util.spec_from_file_location('cpc', root/'scripts/check-plan-code.py')
cpc=importlib.util.module_from_spec(spec); sys.modules['cpc']=cpc; spec.loader.exec_module(cpc)
for val in [1, 5, 999]:
    cpc.SUITE_TIMEOUT = val
    out=io.StringIO(); err=io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc=cpc._self_test()
    print('SUITE_TIMEOUT=', val, 'rc=', rc)
    print((out.getvalue()+err.getvalue()).strip().split('\n')[-1])
PY
```
Output:
```text
SUITE_TIMEOUT= 1 rc= 0
130/130 passed
SUITE_TIMEOUT= 5 rc= 0
130/130 passed
SUITE_TIMEOUT= 999 rc= 0
130/130 passed
```

Why severity: Medium because the timeout still works mechanically, but the suite does not pin the actual budget. The class named by M1 remains open in the other touched file: a mutation changes the operational timeout and leaves the suite green.

Proposed fix, structural: add a literal outside observer for `SUITE_TIMEOUT`, for example a self-test that asserts `SUITE_TIMEOUT == 120`, or a more behavioral case that stubs `subprocess.run` and asserts the `timeout` kwarg is exactly `120`. Do not assert it against `SUITE_TIMEOUT`.

**What I Could Not Measure**

I did not run:
```bash
python3 scripts/check-plan-code.py --mutate .
```
Per the brief, that ~14 minute full sweep is forbidden here. Treat the claimed `53 files, 993 mutations, 993 killed, 993 attributed, 0 survivors` as **not independently verified by me**.

The expected review gates are still red because this Codex half is not on disk:
```text
check-review-recorded.py rc=1
FAILED — 3 round(s) ran and guarded code was committed after every one of them.
...
check-review-rounds.py rc=1
FAILED — 1 review round(s) with one half and no stated reason:
✗ observer-log-owner round 5: only claude
```
