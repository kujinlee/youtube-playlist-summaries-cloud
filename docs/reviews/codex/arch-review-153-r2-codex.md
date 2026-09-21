<!-- codex-review: model=gpt-5.5 -->

**REVIEW GAP:** claude — not invoked for this round, by design. `docs/review-method.md`'s
Round topology makes rounds 2+ **alternating**: a concurrent pair never reviews the fixes, so one
half reviews what the other's findings produced. The Claude half reviewed this round's repairs as
round 3, and its own round-1 findings are re-graded in the table below.

VERDICT: NOT CONVERGED — 0 Blocking, 2 High

| r1 finding | Status | Evidence |
|---|---:|---|
| Codex Blocking: mutation transfer count 8 vs 12 | FIXED | §5 now says `39 -> 27` and `workflow_structure.py = 12`, entries `#26-#37`. I re-bound the manifest and got entries 27-38 in 1-based enumeration, twelve total: ten in `_steps`, plus `_STEPS_KEY`, `_BLOCK_SCALAR`, and `_structural`. |
| Codex High: `if: false` survives extraction | FIXED | §5 now states `if: false` remains satisfied after `_structural` and files #156. |
| Codex Medium / Claude B2: dash-opened block scalar | FIXED | §2 and #154 now name it as a false green with the two-job `pin_took_effect` path. I reproduced `rc=0`. |
| Codex Low: “stdlib-only” imprecision | FIXED | §4 now says “no third-party dependency” and explicitly allows local helper imports. I verified 17 files import 6 local modules and no third-party modules. |
| Claude B1: mutation transfer arithmetic | FIXED | Same as Codex Blocking. No shipped-manifest reading gave 8; the defensible transfer is 12. |
| Claude B2: dash-opened scalar is a false green | FIXED | Same as Codex Medium. |
| Claude H1: `if: false` omitted from bounds | FIXED | §5 names it and #156 carries it. |
| Claude H2: killing cases / count / `POPULATION` bookkeeping | FIXED | §5 now says killing cases move, `check-python-pin.py`’s declared count falls from 84, and `workflow_structure.py` joins `check-selftest-counts.py` `POPULATION` with bare-name/full-path warning. |
| Claude M1: only `_structural()` is shared | FIXED | §5 now says `_steps()`/`Step` move because of ownership, not reuse. |
| Claude M2: wrong discovery mechanism | FIXED | §5 now points at `check-plan-code.py:2687` and says the non-guard population is computed by `check-ratchet-contract.py:402-409`. |
| Claude M3: wrong reason not to migrate `check-merge-ready.py` | FIXED | §5 now uses the soundness-check reason. |
| Claude M4: zero-sweep has no owner | FIXED | §3 now says the zero is point-in-time and ownerless. |
| Claude M5: corpus divergence omitted | FIXED | Main table has a corpus column; #156 records `ci.yml` alone vs `*.yml`/`*.yaml`. |
| Claude L1: “three guards” concentration | FIXED | §5 says risk concentrates across two guards, not three. |
| Claude L2: stale `_structural` docstring | FIXED | §6 names it as a correction required by promotion. |
| Claude L3: 284/480 composition | FIXED | §3 now says 269 comments + 15 block-scalar lines, 94.7% comments. |
| Claude L4: over-citing architecture review #7 | FIXED | §3 says `invocation_re` cites the finding, not the review. |
| Claude L5: mask `ci.yml`, not joined blob | FIXED | §5 has an explicit implementation-trap row. |
| Claude L6: stale `CONTEXT.md` count | FIXED | `CONTEXT.md` removes the stale count and explains why. |

**NEW High — #155 omits the wiring coverage for the second guard.**

The recommendation’s bookkeeping covers transferred `check-python-pin.py` mutations, but not the new behavior in `check-ratchet-contract.py`: R3 must apply the structural reader to `ci.yml` before building `caller_blob`. Existing `check-ratchet-contract.py` self-tests do not cover comments/block scalars in `ci.yml`, and its manifest has no mutation for that wiring. A #155 implementation could forget the mask and keep the suite green.

Command:

```bash
python3 - <<'PY'
import json
from pathlib import Path
data=json.loads(Path('scripts/mutations/check-ratchet-contract.json').read_text())
print('count', len(data))
for i,e in enumerate(data,1):
    print(i, e['name'])
PY
```

Output:

```text
count 10
1 the widened population stops excluding guards, charging one file to two baselines
2 the widened population stops requiring a self-test, demanding manifests of everything
3 debt drift reports a NOT-EXAMINED pin as PAID, so an empty corpus reads as progress
4 the pin stops suppressing known debt, so the gate is red on day one
5 the widened rule is defined but never applied by evaluate()
6 the NO-MUTATIONS escape accepts prose again, so a guard documenting it exempts itself
7 R3's escape accepts prose again, so this guard exempts itself from the caller rule too
8 the debt-PAID arm is dropped, so paying debt down need never be recorded
9 R4's escape is read from the WHOLE FILE again, so a comment exempts a guard
10 R4's could-not-parse path fails OPEN again, so a BOM plus a comment exempts a file
```

And the behavior needing a committed consumer test:

```text
raw:        comment SATISFIED, named_block SATISFIED, dash_block SATISFIED
_structural comment VIOLATION, named_block VIOLATION, dash_block SATISFIED
```

Fix: #155 must explicitly add `check-ratchet-contract.py` self-test cases and mutation entries for “`ci.yml` comment/prose no longer satisfies R3” and the pre-join masking path. Library tests alone do not prove the consumer used the library.

**NEW High — the “no conditional guard invocation in real `ci.yml`” claim is false, so #156 is under-specified.**

`docs/reviews/architecture-review-2026-09-21-workflow-readers.md:268-270` and `docs/backlog.md:184` say no guard invocation in real `ci.yml` sits inside a conditional step. Two do: `check-dashboard-entry.py` and `check-review-recorded.py`, both under `if: github.event_name == 'pull_request'`.

Command:

```bash
python3 - <<'PY'
from pathlib import Path
import re
ci=Path('.github/workflows/ci.yml').read_text().splitlines()
print('job_level_if_lines', [(n,l.strip()) for n,l in enumerate(ci,1) if re.match(r'^    if:\s*', l)])
print('step_level_if_with_guard:')
for i,line in enumerate(ci):
    if re.match(r'^\s*-\s', line):
        indent=len(line)-len(line.lstrip())
        body=[(i+1,line)]
        for j in range(i+1,len(ci)):
            l=ci[j]; s=len(l)-len(l.lstrip())
            if l.strip() and s<=indent and re.match(r'^\s*-\s', l): break
            if l.strip() and s<indent: break
            body.append((j+1,l))
        text='\n'.join(l for _,l in body)
        if re.search(r'^\s*if:\s*', text, re.M) and 'check-' in text:
            print(i+1, [l.strip() for _,l in body if re.match(r'^\s*if:', l)],
                  [l.strip() for _,l in body if 'check-' in l and '.py' in l])
PY
```

Output:

```text
job_level_if_lines []
step_level_if_with_guard:
447 ["if: github.event_name == 'pull_request'"] ['python3 scripts/check-dashboard-entry.py \\']
472 ["if: github.event_name == 'pull_request'"] ['python3 scripts/check-review-recorded.py \\']
```

This is the standing-question defect: promoting a structure reader into R3 still does not answer “does this guard execute?” It answers “does this text survive workflow-content masking?” A later #156 that simply rejects invocations in conditional steps would red-line two real PR-only callers; a #156 that only rejects literal `if: false` still leaves event-scoped execution semantics unstated.

**Checked And Sound**

The two-job false green in #154 is real:

```text
verify        declared_pins -> ['3.12']
schema-gates  declared_pins -> ['3.12']
unpinned_jobs: []
VERDICT rc=0 'python pin OK — every job pins 3.12, and this interpreter is 3.12, from /opt/hostedtoolcache/Python/3.12.14/x64'
```

The flow-mapping transcript in #158 is real:

```text
declared_pins []
unpinned_jobs ['w.yml:verify']
verdict rc=2 CANNOT RUN — no `python-version:` was found...
```

The stdlib/dependency claim is now sound:

```text
scripts_py 63
local_import_files 17
local_modules ['coverage_verdict', 'm4_base_db', 'm4_catalog', 'page_chrome', 'page_markup', 'subject_status'] 6
third_party_like []
import yaml ModuleNotFoundError No module named 'yaml'
```

The roadmap section uses the requested `review-decides-itself` anchor and does not claim implementation of #154-#158. §8’s duplicate-finding note is fair: it compares concurrent review halves on the same artifact, and this round really did produce overlap that changed severity and framing.
