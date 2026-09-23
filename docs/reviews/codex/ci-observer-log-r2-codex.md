# ci-observer-log — round 2, Codex half

REVIEW GAP: claude — rounds 2+ ALTERNATE by design; both halves ran concurrently as round 1,
and this round's subject is that round's FOLD

<!-- codex-review: model=gpt-5.5 -->

Subject: `23fb0d982a906866c8c4d6e9ee1516de100555a6` on `ci-observer-log`.

**Method.** Control first, then targeted probes only. I did not modify `scripts/` and did not run `check-plan-code.py --mutate .`.

```sh
$ git log --oneline origin/master..HEAD
23fb0d98 Round 1 folded: two of its findings were lessons already written in this file, and I wrote new code under them
6a8a2fbc The observer that catches unwatched CI kept no record of ever having spoken

$ python3 scripts/check-ci-watched.py --self-test
55/55 self-test cases passed

$ python3 scripts/check-fixture-variation.py
fixture variation OK — 628 parameter(s) examined across 57 file(s); 121 known-unvaried ratcheted, 7 exempt with a written reason
```

## Findings
| # | Severity | Finding | Introduced by round 1's fold? |
|---|---|---|---|
| 1 | Medium | `EXAMINED_KEYS` does not pin the new dispatch function’s parameters, so coverage can leave `main(argv, stream)` silently. The fold says this went 7 -> 15 “derived by running analyse()”, but the analyzer now reports 17 keys for this file, with `main.argv` and `main.stream` missing from the ratchet. That is exactly the new layer the fold exists to defend. | Yes |

Evidence:

```sh
$ python3 scripts/check-fixture-variation.py scripts/check-ci-watched.py
fixture variation OK — 17 parameter(s) examined across 1 file(s); 121 known-unvaried ratcheted, 7 exempt with a written reason
```

```sh
$ python3 - <<'PY'
import importlib.util, pathlib
p=pathlib.Path('scripts/check-fixture-variation.py')
spec=importlib.util.spec_from_file_location('cfv', p)
cfv=importlib.util.module_from_spec(spec); spec.loader.exec_module(cfv)
text=pathlib.Path('scripts/check-ci-watched.py').read_text()
findings, keys = cfv.analyse(text, 'check-ci-watched.py')
print('key_count', len(keys))
for k in sorted(keys): print(k)
print('pinned_count', len(cfv.EXAMINED_KEYS['check-ci-watched.py']))
print('missing_from_pin', sorted(set(keys)-set(cfv.EXAMINED_KEYS['check-ci-watched.py'])))
PY
key_count 17
decide.head_sha
decide.rows
decide.watching_sha
log_line.detail
log_line.reason
log_line.session
log_line.when
main.argv
main.stream
parse_sentinel.text
payload_from.stream
render_sentinel.sha
render_sentinel.when
run_decide.payload
unresolved_checks.rows
warn_reason.head_sha
warn_reason.watching_sha
pinned_count 15
missing_from_pin ['main.argv', 'main.stream']
```

Falsifier by construction: I renamed only `main` to `_main` in a temp copy, leaving runtime dispatch wired to `_main`. The guard still passed, proving the new dispatch parameters are not ratcheted. The contrasting `payload_from` rename fails, so the test is hitting the intended rule.

```sh
$ tmp=$(mktemp -d); cp -R scripts "$tmp/scripts"; python3 - <<'PY' "$tmp/scripts/check-ci-watched.py"
from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text()
s=s.replace('def main(argv: "list[str] | None" = None, stream=None) -> int:', 'def _main(argv: "list[str] | None" = None, stream=None) -> int:', 1)
s=s.replace('sys.exit(main(None, sys.stdin))', 'sys.exit(_main(None, sys.stdin))', 1)
p.write_text(s)
PY
$ HOME="$tmp/home" python3 "$tmp/scripts/check-fixture-variation.py" "$tmp/scripts/check-ci-watched.py"; echo rc=$?
fixture variation OK — 15 parameter(s) examined across 1 file(s); 121 known-unvaried ratcheted, 7 exempt with a written reason
rc=0
```

```sh
$ tmp=$(mktemp -d); cp -R scripts "$tmp/scripts"; python3 - <<'PY' "$tmp/scripts/check-ci-watched.py"
from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text()
s=s.replace('def payload_from(stream) -> str:', 'def _payload_from(stream) -> str:', 1)
s=s.replace('return run_decide(payload_from(stream))', 'return run_decide(_payload_from(stream))', 1)
p.write_text(s)
PY
$ HOME="$tmp/home" python3 "$tmp/scripts/check-fixture-variation.py" "$tmp/scripts/check-ci-watched.py"; echo rc=$?
FAILED — 1 parameter(s) never varied by any case:
  ✗ check-ci-watched.py: `payload_from.stream` was examined and is NOT any more — its function was renamed, made private, or lost its last call site. Restore it, or update EXAMINED_KEYS deliberately and say why in the commit.
rc=1
```

## Attacked, and found sound

The new `main` dispatch behavior is covered by self-test and mutation attribution, even though its fixture-variation ratchet is missing. I verified the manifest population by enumerating the 27 JSON entries and counting each edit anchor in the current source:

```sh
$ python3 - <<'PY'
import json, pathlib
data=json.loads(pathlib.Path('scripts/mutations/check-ci-watched.json').read_text())
text=pathlib.Path('scripts/check-ci-watched.py').read_text()
print('manifest entries', len(data))
for i,m in enumerate(data,1):
    print(i, 'anchor_counts=', [text.count(old) for old,_ in m['edits']], 'name=', m['name'])
PY
manifest entries 27
1 anchor_counts= [1] name= the unknown-state fallback is dropped, so a state GitHub adds later reads as finished and the warning goes silent on exactly the case it was not designed for
...
27 anchor_counts= [1] name= warn_reason stops comparing the two shas, so a watcher armed for the CURRENT head reads as stale
```

I also drove the 27 entries through `run_mutations` on a temporary copy of `scripts/`, not through the forbidden full `--mutate .` run:

```sh
control rc 0
control tail 55/55 self-test cases passed
ok True
mutations 27
survivors []
unattributed []
report_lines 0
```

`_col` removes the separators it claims, including Python’s broader `splitlines()` set. Its falsey non-string behavior is odd but not live on this path because the production callers pass strings.

```sh
_col samples:
'a\x0bb' -> 'a b'
'a\x0cb' -> 'a b'
'a\x1cb' -> 'a b'
'a\x1db' -> 'a b'
'a\x1eb' -> 'a b'
'a\x85b' -> 'a b'
'a\u2028b' -> 'a b'
'a\u2029b' -> 'a b'
0 -> ''
False -> ''
None -> ''
True -> 'True'
17 -> '17'
```

`argparse` still accepts multiple flags by priority, but that is pre-existing CLI looseness rather than a fold regression:

```sh
main argv samples:
[] rc= 2 stdout_head= ['usage: - [-h] [--decide] [--watching] [--clear] [--self-test]', ''] stderr_head= []
['--bogus'] SystemExit 2 stdout_head= [] stderr_head= ['usage: - [-h] [--decide] [--watching] [--clear] [--self-test]', '-: error: unrecognized arguments: --bogus']
['--self-test', '--decide'] rc= 0 stdout_head= ['  PASS  pending + nothing armed -> WARN', '  PASS  pending + armed for THIS sha -> quiet'] stderr_head= []
['--clear', '--decide'] rc= 0 stdout_head= ['cleared .claude/ci-watching'] stderr_head= []
```

The unfixed sibling is real: `check-banner-armed.py` still has the raw four-column `log_line`. I do not file it against this fold because it was explicitly left as a separate family slice, and this fold’s stricter producer does not create a cross-file reader break.

```sh
scripts/check-ci-watched.py [(151, 'return (f"{_col(when)}\\t{_col(session) or \'-\'}\\t{_col(reason)}\\t{_col(detail)}\\n")')]
scripts/check-banner-armed.py [(626, 'return f"{when}\\t{session or \'-\'}\\t{reason}\\t{detail}\\n"')]
```

**VERDICT: NOT CONVERGED**

