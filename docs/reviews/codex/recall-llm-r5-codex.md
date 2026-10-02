<!-- codex-review: model=gpt-5.5 -->

## HIGH

### H1 · `dead_arms` only probes through 15, so executable dead arms above 15 pass as clean

[file](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:294)

> `def dead_arms(hook_src: str, defined: set[int], probe_max: int = 15) -> list[int]:`

[file](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:302)

> `return [rc for rc in range(probe_max + 1)`

This violates R2’s stated contract: “Every `case` arm in the hook names a code the matcher can actually emit.” The redesign no longer parses arms, so black-box probing is the only dead-arm detector. But it only probes `0..15`, while bash/Python exit statuses are observable through at least `0..255`, and a hook arm at `16)` is real executable code.

Reproduction, no file writes:

```bash
python3 - <<'PY'
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("crc", Path("scripts/check-rc-contract.py"))
crc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crc)

hook = '''#!/usr/bin/env bash
set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$(python3 "$REPO_ROOT/scripts/recall-llm.py" --fire 2>&1)"; RC=$?
PAYLOAD=""
case "$RC" in
  0) [ -n "$OUT" ] && PAYLOAD="$OUT" ;;
  3) [ -n "$OUT" ] && PAYLOAD="stale. Detail: $OUT" ;;
  5) PAYLOAD="unreadable."
     [ -n "$OUT" ] && PAYLOAD="$PAYLOAD Detail: $OUT" ;;
  6) PAYLOAD="no corpus."
     [ -n "$OUT" ] && PAYLOAD="$PAYLOAD Detail: $OUT" ;;
  16) PAYLOAD="dead arm for undefined code" ;;
  *) : ;;
esac
[ -n "$PAYLOAD" ] || exit 0
python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":sys.stdin.read()}}))' <<<"$PAYLOAD"
exit 0
'''

D = {"OK":0, "CANNOT_RUN":2, "STALE_CACHE":3, "BAD_RESPONSE":4, "UNREADABLE_PLAN":5, "UNANSWERABLE":6}
handled = crc.handled_codes(hook, set(D.values()))
dangling = crc.dangling_detail(hook, set(D.values()))
dead = crc.dead_arms(hook, set(D.values()))
print("handled=", handled)
print("dangling=", dangling)
print("dead=", dead)
print("verdict=", crc.verdict(D, handled, dangling, dead))
print("observe16=", repr(crc.observe(hook, 16, "PROBE-DETAIL-TEXT")))
PY
```

Observed:

```text
handled= {0, 3, 5, 6}
dangling= []
dead= []
verdict= []
observe16= 'dead arm for undefined code\n'
```

So the guard reports agreement while a real, reachable, undefined `case` arm exists.

What would prove this wrong: `dead_arms()` either probes the full shell-observable exit-status range, e.g. `0..255`, or otherwise proves from bash semantics that `16)` cannot be reached. The reproduction would then need to return `dead=[16]` and `verdict` would need to contain the dead-arm finding.

## MEDIUM

None.

## LOW

None.

## Redesign Soundness

The redesign is sounder than the deleted lexer on the exact failure class that caused rounds 3 and 4: it asks bash what the hook does instead of hand-reading bash syntax. I reproduced the hostile payload checks for braces/JSON-looking fragments, trailing newline, large payloads, and silence; the envelope survived and silence stayed distinct from malformed output.

The repository-touch concern also came back clean. I snapshotted tracked file hashes plus `.claude/`, ran:

```bash
python3 scripts/check-rc-contract.py
python3 scripts/check-rc-contract.py --self-test
```

Then snapshotted again. Both diffs were empty.

But the redesign is not fully sound; it traded lexer unsoundness for bounded black-box sampling. That is a better failure mode, but H1 shows it is still a fail-open for real hook behavior outside the sample window.

## Could Not Establish

I did not complete the full repo-wide mutation sweep. It passed controls and reached mutation `431/1147` before I stopped it for time; no survivor had been reported by then. I did verify these claimed gates:

```text
recall-llm.py --self-test: 201/201
check-rc-contract.py: rc=0
check-rc-contract.py --self-test: 40/40
check-ratchet-contract.py: rc=0
check-fixture-variation.py: rc=0
check-selftest-counts.py: rc=0
check-docs.py: rc=0
check-features.py: rc=0
check-plan-code.py --self-test: 131/131
```

The retired `check-rc-contract` mutation entries I checked all named anchors that no longer exist in the redesigned file, so I did not find a ratchet fall there.

NOT CONVERGED.
