<!-- codex-review: model=gpt-6.1-sol -->

**NOT CONVERGED**

1. **Major — malformed transcript paths still traceback.**  
   `scripts/check-transcript-references.py:135`, `scripts/check-banner-armed.py:1315`, `scripts/check-closing-table.py:907`.

   Concrete payload: `{"transcript_path":"x\u0000y"}`. All three real `--decide` entry points exit **1 with `ValueError: embedded null byte`**, rather than CANNOT RUN. Additionally, `{"transcript_path":123}` crashes transcript-references with `TypeError`.

   The registered `run-hook.sh block-idle-stop.sh` path surfaces these tracebacks as nonblocking rc 1. Validate path types and handle invalid path values.

2. **Major — object-shaped malformed check rows still become WARN.**  
   `scripts/check-ci-watched.py:538`.

   Replay GitHub output `[{"state":[]}]` with readable HEAD and no watcher: real `--decide` exits **1**, claiming CI is running. `[{}]` also WARNS. The new validation checks only that each row is a dictionary; it does not establish that the row carries a readable status.

   Reproduced through the registered Stop-hook launcher with controlled Git/`gh` boundaries. Malformed status fields need CANNOT RUN before watcher suppression or pending-check reporting.

3. **Minor — an unreadable-check test passes for an ambient reason; mutations survive.**  
   `scripts/check-ci-watched.py:851`, `scripts/check-transcript-references.py:130`.

   In a copied tree without Git metadata, mutate:

   ```python
   if raw is None:
       rows = []  # originally None
   ```

   The CI suite still passes **92/92**, including the case claiming to test unreadable PR checks. It receives CANNOT RUN because **HEAD is unreadable**, masking the broken checks refusal. Pin a readable HEAD in that case.

   Separately, narrowing the reference guard’s refusal to `if isinstance(data, list):` survives **22/22** cases, while payload `true` then crashes with `AttributeError`. Exercise additional non-object JSON types.

Validation completed:

- All changed self-tests passed: references **22**, banner **241**, closing-table **156**, handoff **22**, CI **92**, harness **246**.
- All five requested guard mutation slices passed: **9/9, 96/96, 50/50, 7/7, 44/44**, with every kill attributed. These results cover the declared manifests; the additional surviving mutations above remain uncovered.
- An additional harness-self mutation sweep did **NOT** complete; it was stopped.
- Read-only transcript probes covered a 50-file sample and the 12 largest transcripts. The latter produced identical branch/master outcomes. No new false refusal found. Sixteen real check rows from PR #439 were accepted.
- Invalid UTF-8, zero parsed records, an undecodable handoff file, and a genuinely unlistable arm directory produced the intended refusals through their applicable entry points.

**Hook blocking:** observer rc 2 maps to hook **rc 1**, so these CANNOT RUN outcomes do not trap Stop. Verified with `stop_hook_active` both false and true. Independently, the existing progress guard’s missing-plan refusal blocks repeatedly with **rc 2**, including continuations; pausing changes that to rc 1. Handoff’s receipt 2 blocks its **PreToolUse** hook until repaired.

No files under `.claude/plans/` were read or quoted. Working tree unchanged.
