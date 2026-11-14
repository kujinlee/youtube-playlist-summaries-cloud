---
name: backlog-154-dash-scalar-ready-331
description: "FIRES-WHEN: citing backlog #154 or PR #331, or a line-scanner keeps sprouting new spellings round after round — PR #331 MERGED (b7ec0c42). EIGHT rounds, each a NEW GRANULARITY; the fix changed KIND (refuse, don't widen). Filed #160–#163"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0cfd7079-9c4f-4f89-9a59-337f426f6311
  modified: 2026-09-22T15:28:16.057Z
---

**CURRENT STATE (verified 2026-11-14):** PR #331 MERGED as `b7ec0c42`; backlog #154 ✅. Filed from it:
#160 ✅ (since closed), **#161** 🟡 commit the differential-vs-libyaml harness (**12 members in one run** vs
reviewers' ~1 per round), **#162** 🟢 derive each guard's invocation from `ci.yml`, **#163** 🟢 valid shapes
false-RED (colon-adjacency, not nesting).

**RULES it taught:**
- **When each round finds the next family at a new GRANULARITY, the instrument is wrong — change KIND.**
  A line scanner has no notion of YAML's containers; the fix was one generic key rule **plus a REFUSAL**
  (`unreadable_scalar_openers`, same pattern as `unreadable_jobs` since PR #317). Improving fixes are not
  diminishing returns: the false-green rate went **100% (master) → 76.7% → 36.7%** over one 7,200-fixture
  space and was still the wrong instrument (YAML's explicit key puts key and indicator on different lines).
- **A fix is done when the FALSIFIERS still fail, not when the suite is green.** My class-fix silently
  made SIX existing mutations unkillable at 111/111 green; only the sweep saw it.
- **Read the gate's source before theorising about it.** `check-review-recorded` keys on CODEX VERDICTS
  and the FINAL TREE; a `NO-REVIEW:` waiver must be LINE-LEADING (a `## NO-REVIEW:` heading is invisible to
  `check-dashboard-entry.exemption_reason`); a comment-only change is still guarded — waive with an
  AST-identity proof. Editing a PR body does not reach a run in flight — add an empty commit.

## History — the eight rounds
| round | granularity | what was wrong |
|---|---|---|
| r1–r4 | line | `- run: \|` and 3 more spellings; the indent invariant had no falsifier |
| r5 | node | keyless indicator (`run:` newline `\|`) — 12 more spellings; the refusal was blind to it |
| r6 | document | a pin in a second YAML document credited to the first |
| r7 | key depth | `uses:` matched at ANY depth — r7 found one depth-blind key; a six-line sweep found **three** |

Three of eight rounds found defects in MY repairs. An inverted causal story (`Step.body` blanks the dash
"before" `_structural`) survived in **four copies**, including `CONTEXT.md`'s glossary. CI was red on 6
pushes unnoticed: `check-ci-watched.py` fired, but on a channel (`exit 1` → the absent human) — the gap
was ADDRESSING, see [[a-gates-channel-can-be-weaker-than-the-gate]]. ⚠ I ran `git stash -u` and swept a
LIVE AGENT's untracked file, one sentence after saying I would not.

Related: [[a-test-that-cannot-fail]], [[fixing-a-premise-is-not-covering-the-branch]],
[[an-inference-stated-as-measured]], [[arch-review-153-workflow-readers]],
[[after-fixing-search-for-the-class]], [[dual-review-what-it-catches]].
