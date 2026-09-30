---
name: selection-card-guard-built
description: "FIRES-WHEN: citing the selection-card hook or PR #287 — ⭐ A PreToolUse hook now REFUSES a malformed AskUserQuestion card (PR #287). Its own 2 rounds found 4 Blockings — a guard that blocks is judged on FALSE POSITIVES"
metadata: 
  node_type: memory
  type: project
  originSessionId: 24bed3bc-51b2-4b47-b1fe-a488b2d3db19
  modified: 2026-09-10T21:03:05.278Z
---

**Built 2026-09-10, MERGED as `050913f6` (PR #287).** `.claude/hooks/enforce-selection-card.sh` (PreToolUse on
`AskUserQuestion`) → `scripts/check-selection-card.py` (59 cases, 13 mutations, in
`EXPECTED_MUTATIONS`). It refuses a card that breaks the clauses of `portable-practices` §19 that
are exactly decidable. See [[print-selection-cards-in-chat]] for the pre-flight; §19 is the rule.

**Why it exists:** three cards in one session, ONE compliant, with §19 and two memory files all
saying the same thing. The rule was reconstructed from recall at the moment of use instead of read.
Recording was never the gap — see [[it-already-exists-under-a-name-i-didnt-search]].

## ⭐ A GUARD THAT BLOCKS IS JUDGED ON ITS FALSE POSITIVES, and that inverted several decisions

Two review rounds produced **four Blockings**. Every one was the guard being *clever*:

* **The advice must be POSSIBLE.** The block message said "add option E"; `AskUserQuestion` accepts
  2–4. Measured over 49 real questions: 29 already used all four slots. A guard that blocks correctly
  and then misdirects the repair is worse at the moment of use than the prose it replaced.
* **Parsing the `(Recommended)` parenthesis failed three times, each wrong in BOTH directions** —
  prose about the marker counted; §19's own "with its reason" did not. ⛔ The tell that the RULE was
  wrong rather than the regex: **every fix moved the false positive somewhere else.** Now it is the
  word, minus its negations, anywhere.
* **A "dense script" floor keyed on `len(desc.split()) > 1` measured SPACES, not information** — so
  no Korean description could ever reach it. One floor, every script.
* **The shell mutated the evidence.** `INPUT=$(cat)` strips NUL bytes (`direct=2 hook=0`), and a
  detector reporting through stdout was defeated by a `python3` that prints a banner. The payload
  now never enters a shell variable and the verdict travels by **exit code**.

⚠ **Absence is not a negative.** The hook required `tool_name == "AskUserQuestion"` and exited 0
otherwise, while the checker accepts a bare tool input — so it failed open on the exact shape it was
written for. Skip only on a POSITIVE identification of something else.

⚠ **Shell in a hook is the risky part**: it had no `--self-test`, was in no manifest, and both of
round 1's fixes lived there unguarded. There are now 8 cases that RUN the hook, including
chatty-interpreter and broken-interpreter shims — which is where the defects actually were.

See also [[a-report-format-is-a-contract]] and `portable-practices` §22.
