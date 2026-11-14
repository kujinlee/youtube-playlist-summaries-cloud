---
name: a-harness-cannot-read-a-cause-from-a-childs-text
description: "FIRES-WHEN: a harness, probe or my own shell pipeline decides WHY a child went red by parsing its stdout/stderr, or counts [FAIL] lines to judge coverage — a stream the child controls can forge anything you grep for, and a CRASH prints no [FAIL]. Read rc + traceback; weaken a line before calling it unmutatable"
metadata:
  type: feedback
---

# A harness cannot read a CAUSE out of a child's text — it can only quote it

**The rule: a stream a child controls can forge anything the harness greps for.** Ask of every parse — *could the
subject under test produce this text deliberately?* If yes, the parse is a QUOTATION, not a measurement, and the
message must say so. Printing MORE evidence makes this worse, not better.

**How to apply:**
- Prefer narrowing over cleverer parsing: require a structural marker (`  File "`) before treating indented lines as a
  traceback; validate a type name with `str.isidentifier()`; report an observation (`0 bytes`) and state it is NOT
  evidence of execution; read failure names from **stdout only**. ⚠ These are the DIRECTION, not a proven outcome — round
  13 showed two of them still drop real exceptions and invent fake ones (backlog **#279**, **#280**).
- **In my own probes, read the EXIT CODE and whether a traceback appeared**, not just a `[FAIL]` count — a crash prints
  no `[FAIL]`, so `0` means "uncovered" and "crashed" identically:

```bash
out=$(python3 "$PROBE" --self-test 2>&1); rc=$?
printf 'rc=%s fails=%s traceback=%s last=%s\n' "$rc" \
  "$(echo "$out" | grep -cE '^  \[FAIL\]')" "$(echo "$out" | grep -c Traceback)" "$(echo "$out" | tail -1)"
```

- **"Unmutatable" is a claim about EVERY mutation of a line.** Before concluding it, WEAKEN the line (narrower expression,
  flipped operator, dropped operand) — a line that crashes when deleted usually fails cleanly when merely made wrong.
- `check-plan-code` already encodes *a mutation that crashes is a crash forging a `[FAIL]`* — reuse it, do not
  re-derive it in a shell pipeline ([[a-second-implementation-of-one-rule-drifts]]).
- *An architecture review ran* is not evidence *the thrashing stopped* — round 12 produced three Highs of this class
  after Phase 6 chose option A.

## History

⤳ **Provenance:** PR **#371**, branch `backlog-249-260-fixes`, rounds **11–13**
(`docs/reviews/{codex,claude}/backlog-249-260-r{11..13}-*.md`); architecture review
`docs/reviews/architecture-review-2026-10-13.md`. (An earlier version said rounds 9–13; rounds 9–10 were withdrawal and
parser problems — corrected by round 2 of the docs review. A "that worked" claim about the repairs was withdrawn by r5 M2.)

**Three consecutive rounds on `scripts/check-plan-code.py` (2026-10-13), one root cause:**

| the harness believed | the child actually did |
|---|---|
| *"stderr NAMES `ValueError: X`"* — two exceptions | raised **ONE**; the second was fabricated from an indented MESSAGE CONTINUATION |
| *"stderr is EMPTY, so the suite RAN and its PRINTER is the subject"* | `import os; os._exit(1)` — rc 1, stderr empty, **nothing ran** |
| *"killed, attributed to case `fabricated`"* | `raise RuntimeError("no cases ran\n[FAIL] fabricated: got 0 want 1")` — **zero cases executed**; the traceback FORGED the failure name |

Round 13 still: `type("bad-name", (Exception,), {})` prints `bad-name: ROOT_MARKER` and is reported as nothing; a
frame-shaped line inside an exception MESSAGE yields two headings for one exception.

**2026-10-16, `marketplace-inventory` round 3 — the same blindness in my hand-written probe**, four probes in an hour,
two wrong in OPPOSITE directions:

| probe | counting `[FAIL]` said | rc + traceback said |
|---|---|---|
| whitespace guard removed | 0 red → "uncovered" | `rc=0`, **79/79 green — genuinely uncovered** |
| `wanted \|= {DERIVED pages}` deleted | 0 red → "uncovered" | `rc=1`, **1 traceback, `FileNotFoundError`** — covered structurally |

⟳ I then called the second row "unmutatable"; **refuted 2026-10-17 by round 5's Codex half**: the substitution
`wanted |= {d["page"] for d in DERIVED}` fails cleanly —
`[FAIL] audit: an absent COMPOSED page reached only through DERIVED is CannotRun: got 'FileNotFoundError' want 'CannotRun'`
— and is now a live, KILLED manifest entry. The defect was there; declining to cover it would have been the error.

Related: [[printing-more-evidence-weakens-substring-cases]] *(⚠ no such memory file exists as of 2026-11-14 — the
link dangles)*, [[cannot-die-may-mean-a-second-clause]], [[gates-detect-defects-not-design]],
[[the-control-refuted-the-premise]], [[a-case-can-pass-for-an-ambient-reason]].
