<!-- codex-review: model=gpt-5.5 -->

HIGH / `scripts/check-python-pin.py:106` / A `python-version:` under `env:` inside an `actions/setup-python` step is counted as a real pin, even though it is not `with.python-version` and is not an input to the action. That leaves a false green: the checker reports “every job pins 3.12” for a job whose setup-python step did not declare the pin in the only place the action reads as an input. This is the same class as the r1 false-positive fix, just one level narrower: the new span is “inside setup-python step,” but the predicate still is not “inside that step’s `with:` block.”

Executed evidence:

```bash
python3 - <<'PY'
import importlib.util, pathlib
p=pathlib.Path('scripts/check-python-pin.py')
s=importlib.util.spec_from_file_location('cpp', p)
m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
wf="""jobs:
  verify:
    steps:
      - uses: actions/setup-python@v5
        env:
          python-version: '3.12'
"""
print('declared_pins', m.declared_pins(wf))
print('unpinned_jobs', m.unpinned_jobs({'w.yml': wf}, {}))
print('verdict', m.verdict(
    {'w.yml': wf}, '3.12', True, None,
    '/opt/hostedtoolcache/Python/3.12.14/x64/bin/python3',
    '/opt/hostedtoolcache/Python/3.12.14/x64',
))
PY
```

Output:

```text
declared_pins ['3.12']
unpinned_jobs []
verdict (0, 'python pin OK — every job pins 3.12, and this interpreter is 3.12')
```

Other verification run:

```bash
rm -rf /tmp/pin-python-review-r2
git clone --quiet . /tmp/pin-python-review-r2
cd /tmp/pin-python-review-r2
git checkout --quiet c65e4f29
python3 scripts/check-python-pin.py --self-test
```

Output: `45/45 passed`.

```bash
python3 scripts/check-plan-code.py --mutate .
```

First attempt refused because `/tmp` clone lacked `node_modules/typescript`. Then:

```bash
ln -s /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/node_modules /tmp/pin-python-review-r2/node_modules
python3 scripts/check-plan-code.py --mutate .
```

Output: `OK — delivered scripts mutated: 48 file(s), 755 mutation(s), 755 killed, 755 attributed to the case each names, 0 survivor(s)`.

Attacks that failed: provenance rejects missing `pythonLocation`, ambient `/usr/bin/python3`, sibling-prefix paths, relative executables, and trailing-slash `pythonLocation` works. The refusal order did not produce a merge-blocking wrong result in the states I tested. The loosened job tail handled comments/anchors and did not match top-level keys after `jobs:`. Jobless workflows correctly refused; I did not find a legitimate GitHub workflow with no jobs.

Verdict: not clean. This diff is not safe to merge until `declared_pins` requires the `python-version` to belong to the setup-python step’s `with:` mapping, not merely anywhere inside the step.
