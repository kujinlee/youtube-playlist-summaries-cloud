<!-- codex-review: model=gpt-5.5 -->

**REVIEW GAP:** claude — not invoked for this round, by design. Rounds 2+ alternate
(`docs/review-method.md`, Round topology), and Codex authored round 7 — the round whose
repair this reviews.

VERDICT: CONVERGED

Head reviewed: `33f1b2b5`. Worktree was clean before and after review (`git status --short` printed nothing).

**New Findings**

Medium: valid YAML step shapes can false-red as “no pin found”.

Command run:
```text
python3 - <<'PY'
# Psych parse vs guard declared_pins/verdict for:
# - &py uses: ...
# with: &w
# "with":
# 'python-version':
# python-version :
PY
```

Real output excerpt:
```text
--- anchored_step_mapping
Psych:
[
  {
    "uses": "actions/setup-python@v5",
    "with": {
      "python-version": "3.12"
    }
  }
]
guard declared_pins []
guard verdict 2 CANNOT RUN — no `python-version:` was found in any workflow, so the interpreter
...
--- pin_space_before_colon
Psych:
[
  {
    "uses": "actions/setup-python@v5",
    "with": {
      "python-version": "3.12"
    }
  }
]
guard declared_pins []
guard verdict 2 CANNOT RUN — no `python-version:` was found in any workflow, so the interpreter
```

This is fail-closed, not a false green. I do not rate it Blocking/High for PR #331 because it cannot certify an unpinned job, and the live workflows do not use these shapes. It is a real reader boundary to consider for #155 or a follow-up if the project wants to accept all GitHub-supported YAML node-property/quoted-key spellings.

Low: one explanatory comment is stale about `_structural` having one call site.

Command:
```text
rg -n "_structural\\(" scripts/check-python-pin.py
```

Output:
```text
232:    structural = _structural(text.split("\n"))
408:def _structural(body: list[str]) -> list[str]:
605:    lines = _structural(text.split("\n"))
```

The behavior is still sound: both callers operate on whole-file/job-block text before derivation, not on already-split `Step.body`. But the “exactly one call site” prose is no longer literally true.

**Merge Judgement**

PR #331 should merge. I found no Blocking or High defect in the final tree. Compared with `master`, this branch removes the known false-green families from rounds 3–7 and refuses unreadable scalar/document shapes before deriving pins. Shipping with #160 open is acceptable because it is already named as the line-local boundary, and I found no new silent-green member beyond it.

**Checks Run**

```text
python3 scripts/check-python-pin.py --self-test
111/111 passed
```

```text
python3 scripts/check-python-pin.py
⚠ ADVISORY — this machine runs Python 3.14; CI runs 3.12.
...
```

```text
python3 scripts/check-plan-code.py --self-test
128/128 passed
```

```text
python3 scripts/check-plan-code.py --mutate .
OK — delivered scripts mutated: 52 file(s), 881 mutation(s), 881 killed, 881 attributed to the case each names, 0 survivor(s)
```

Counts re-derived:
```text
EXPECTED_MUTATIONS entries 52
EXPECTED_MUTATIONS check-python-pin 52
EXPECTED_MUTATIONS sum 881
check-python-pin manifest entries 52
```

Live workflow guard facts:
```text
workflow files ['ci.yml', 'schema-gates.yml']
job names {'ci.yml': ['verify'], 'schema-gates.yml': ['schema-gates', 'prod-drift']}
declared pins {'ci.yml': ['3.12'], 'schema-gates.yml': ['3.12', '3.12']}
unreadable openers {'ci.yml': [], 'schema-gates.yml': []}
unreadable jobs {'ci.yml': 0, 'schema-gates.yml': 0}
unpinned jobs []
```

Differential fuzz with `/usr/bin/ruby` Psych:
```text
cases 255 psych_valid 246
false_green_content_unrefused_excluding_160 0
refused_valid_structure 0
```

Refusal over-fire, excluding dependency directories:
```text
yaml files excluding deps 18
structural noncomment lines excluding deps 7546
refusals 0
```

Sound:
- r7 direct-child mutations 50–52 are not vacuous; the full mutation sweep killed them.
- The refusal precedes `pins` computation in `verdict`.
- `_DOC_MARKER` does not fire on repo YAML/workflows.
- `_BARE_INDICATOR` closes the keyless-indicator family without over-firing on the repo corpus.
- Multi-document GitHub acceptance remains honestly marked unverified.
- The inherited manifest pair around entries 43/46 remains present and measured; I did not “fix” it.
