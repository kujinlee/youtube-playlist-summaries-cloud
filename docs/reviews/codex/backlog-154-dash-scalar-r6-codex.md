<!-- codex-review: model=gpt-5.5 -->

**REVIEW GAP:** claude — not invoked for this round, by design. Rounds 2+ alternate
(`docs/review-method.md`, Round topology), and the Claude half authored round 5 — the round
whose repair this reviews.

VERDICT: NOT CONVERGED — 0 Blocking, 1 High.

| r5 finding | status | review result |
|---|---:|---|
| F1 — refusal misses block scalar indicator on its own line | FIXED | `_BARE_INDICATOR` refuses `run:` / `|` and explicit-key `? run` / `:` / `|`; verdict returns `rc 2`, not green. |
| F2 — multi-line quoted scalar false green | FIXED AS DISPOSITION | Filed as backlog #160, not fixed here. Technical content checks out: unquoted multi-line is rejected by Psych; double/single quoted forms are valid strings and still false-green; quote-balance probe fires zero times in `.github/workflows/`. |
| F3 — file-vs-slice granularity bound | FIXED | The bound is in `unreadable_scalar_openers()`’s docstring, and it says the important consumer rule: callers that slice must call refusal on the same text. |
| F4 — #155 transfer obligation missing refusal/caller rule | FIXED | Backlog #155 now names `_LOOSE_SCALAR`, `_BARE_INDICATOR`, `unreadable_scalar_openers`, and the caller obligation to refuse before deriving from the mask. |
| F5 — mutation name was dishonest proxy | FIXED | The renamed mutation is honest enough: it names the keyless-indicator refusal, expects all three relevant cases, and was killed in the full mutation run. |

**New Findings**

High — a second YAML document can provide a fake pin while Psych’s first workflow document has no setup-python step.

Command run:

```text
python3 - <<'PY'
# imports scripts/check-python-pin.py, parses the same fixture with /usr/bin/ruby Psych.load_stream,
# then prints declared_pins(), unreadable_scalar_openers(), and verdict()
PY
```

Real output:

```text
psych_docs=2 first_doc_setup=false first_doc_run="python3 --version"
declared_pins= ['9.9']
unreadable_scalar_openers= []
rc= 0
first_line= python pin OK — every job pins 9.9, and this interpreter is 9.9
```

Fixture shape:

```yaml
jobs:
  build:
    steps:
      - name: real work
        run: python3 --version
---
jobs:
  other:
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: '9.9'
```

This is not the known #160 quoted-scalar family, and it is not fixed by `_BARE_INDICATOR`. It is the same line-scanner failure at document granularity: the guard reads all text as one workflow, while libyaml says there are two documents and the first workflow document has no setup-python step.

**Standing Question**

Not ready to merge as-is. I would have accepted shipping with #160 filed and measured: it is known, explicitly deferred to the #155 parse-or-refuse decision, and this branch is strictly better than master on the original block-scalar family. But the multi-document case is a newly found false green, not yet filed or bounded. The file’s standard is still right: false green is the direction the guard must not fail in. Branch-vs-master matters, but it does not make an unrecorded false green disappear.

**Checked Sound**

`python3 scripts/check-python-pin.py --self-test`:

```text
104/104 passed
```

Counts:

```text
manifest 48
EXPECTED_MUTATIONS check-python-pin 48
declared sum 877
```

Full mutation run:

```text
OK — delivered scripts mutated: 52 file(s), 877 mutation(s), 877 killed, 877 attributed to the case each names, 0 survivor(s)
```

`_BARE_INDICATOR` over-fire checks were sound. Indicators inside masked `run: |` bodies, markdown tables, shell pipes, and `>` redirects produced no refusals; a structural bare `|` did refuse. Current checkout measurements:

```text
tracked_yaml_files=2 structural_lines=282 refusals=0
workflow_structural_lines=282 workflow_refusals=0
yaml_files=61 structural_lines=8375 refusals=0
```

Other YAML-node probes did not produce new false greens:

```text
flow-map-run: OK docs=1 setup=false ... pins=[] refusals=[] rc=2
alias-to-block-scalar: OK docs=1 setup=false ... pins=[] refusals=[] rc=2
merge-step: OK docs=1 setup=true ... pins=[] refusals=[] rc=2
```

Duplicate anchor pair confirmed inherited: HEAD entries 43/46 share the old opener anchor; master entries 35/38 already shared that same old anchor. I did not fix it.
