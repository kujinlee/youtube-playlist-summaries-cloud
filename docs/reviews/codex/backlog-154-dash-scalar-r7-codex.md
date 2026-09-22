<!-- codex-review: model=gpt-5.5 -->

**REVIEW GAP:** claude — not invoked for this round, by design. Rounds 2+ alternate
(`docs/review-method.md`, Round topology), and the Claude half authored round 5; round 6 was
Codex and round 7 reviewed the tree round 6's repair produced.

VERDICT: NOT CONVERGED — 1 Blocking, 0 High

Reviewed head: `6a2ed15c`

**Blocking**
1. `declared_pins()` treats `with.uses` on an unrelated action as the step’s action declaration, so a job with no `actions/setup-python` step can pass.

At [scripts/check-python-pin.py:491](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-python-pin.py:491), the setup-python test scans every `uses:` line anywhere in the step body. Then [scripts/check-python-pin.py:496](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-python-pin.py:496) accepts the step’s `with:` block and reads `python-version`.

Command run:

```bash
python3 - <<'PY'
import importlib.util, subprocess, json
spec=importlib.util.spec_from_file_location('pin','scripts/check-python-pin.py')
pin=importlib.util.module_from_spec(spec); spec.loader.exec_module(pin)
wf = """jobs:
  build:
    steps:
      - uses: someone/other@v1
        with:
          uses: actions/setup-python@v5
          python-version: '9.9'
"""
ruby = r'''
require 'psych'; require 'json'
doc = Psych.load(STDIN.read)
step = doc.dig('jobs','build','steps',0)
puts JSON.generate({step: step, step_uses: step['uses'], input_uses: step.dig('with','uses'), input_pin: step.dig('with','python-version')})
'''
psych=subprocess.run(['ruby','-rpsych','-rjson','-e',ruby],input=wf,text=True,capture_output=True,check=True).stdout.strip()
print('psych', psych)
print('unreadable', pin.unreadable_scalar_openers(wf))
print('declared_pins', pin.declared_pins(wf))
print('unpinned_jobs', pin.unpinned_jobs({'w.yml':wf}, {}))
rc,msg=pin.verdict({'w.yml':wf}, '9.9', True, None, '/opt/hostedtoolcache/Python/9.9/x64/bin/python3', '/opt/hostedtoolcache/Python/9.9/x64')
print('verdict_rc', rc)
print('verdict_msg', msg)
PY
```

Real output:

```text
psych {"step":{"uses":"someone/other@v1","with":{"uses":"actions/setup-python@v5","python-version":"9.9"}},"step_uses":"someone/other@v1","input_uses":"actions/setup-python@v5","input_pin":"9.9"}
unreadable []
declared_pins ['9.9']
unpinned_jobs []
verdict_rc 0
verdict_msg python pin OK — every job pins 9.9, and this interpreter is 9.9, from /opt/hostedtoolcache/Python/9.9/x64
```

This is not #160 and not a seventh block-scalar opener spelling. It is a separate false green: libyaml/Psych says the step action is `someone/other@v1`; `actions/setup-python@v5` is only an input value. The guard reports the job pinned and returns rc 0. Fix required before merge: only count `uses: actions/setup-python...` when it is a direct step-level key for that list item, then add a self-test and mutation for this exact false-green family.

**Merge Judgement**
PR #331 should not merge as-is. Master is worse for the backlog #154 scalar families, but this final tree still has a blocking false green in the same guard’s core predicate. After fixing the direct-child `uses:` detection, I would still accept shipping with #160 open as a documented parser-vs-crude decision for #155; #160 is not the blocker I found.

**Checked And Sound**
`git rev-parse --short HEAD` -> `6a2ed15c`; `git status --short` was clean before and after.

Suite/counts:
```text
python3 scripts/check-python-pin.py --self-test
106/106 passed

python3 scripts/check-plan-code.py --self-test
128/128 passed

python3 scripts/check-plan-code.py --mutate .
OK — delivered scripts mutated: 52 file(s), 878 mutation(s), 878 killed, 878 attributed to the case each names, 0 survivor(s)
```

Real workflows:
```text
workflow_files ['ci.yml', 'schema-gates.yml']
ci.yml pins ['3.12'] jobs ['verify'] unreadable []
schema-gates.yml pins ['3.12', '3.12'] jobs ['schema-gates', 'prod-drift'] unreadable []
verdict 0
```

Counts re-derived:
```text
manifest 49
EXPECTED_MUTATIONS[check-python-pin] 49
declared_sum 878
```

Refusal over-fire:
```text
yaml_files_excluding_node_modules 18
structural_lines 7623
files_with_refusals 0
```

Load-bearing claims checked:
```text
rg -n "_structural\(" scripts/check-python-pin.py
232:    structural = _structural(text.split("\n"))
408:def _structural(body: list[str]) -> list[str]:
574:    lines = _structural(text.split("\n"))
```

So `_structural` has one masking call site plus the refusal call site; `verdict()` computes `unreadable_openers` before `pins`; `_DOC_MARKER` has zero repo-workflow and zero non-vendored repo YAML over-fire; the multi-document GitHub acceptance caveat is honestly marked unverified. The inherited 43/46 paired mutation area was left untouched, and the mutation runner accepted the manifest with full attribution.
