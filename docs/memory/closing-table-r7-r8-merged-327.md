---
name: closing-table-r7-r8-merged-327
description: "FIRES-WHEN: citing PR #327/#328 or the closing-table guard, or about to tighten a format check, waive a review, or write a quantifier in a docstring — a marker that enforced one EXAMPLE of a rule (96.7%→49.1% firing); check-review-recorded keys on CODEX VERDICTS"
metadata: 
  node_type: memory
  type: project
  originSessionId: b3d559c1-6b4c-49e1-81af-8ac588f0b7d8
  modified: 2026-09-21T14:47:21.326Z
---

**STATE (verified 2026-11-14):** both MERGED — PR #327 `fab6f655` (2026-09-21) and PR #328 `42038988`.
Rows: **#148** 🟡 does the banner guard carry the same split (measurement only) · **#149** 🟡 half done
(Tier 1 shipped, Tier 2 anti-nag journal deferred) · **#151** 🟡 five vacuous self-test cases · **#152** ✅.

**RULES it taught:**
- **A format check must enforce the rule's PROPERTIES, not one example of it.** `has_closing_table`
  required the example's `check`/`result` header cells; the rule is three properties (one row per claim,
  evidence in the row, every row could have come back ❌). The user chose to WIDEN (option A).
- **Measure the constraint before shipping the tighter rule that sounds safer.** *"Accept a table only
  when it ENDS the message"* was measured dead: of 304 warned-on tabled messages, **0** end with one.
- ⛔ **`check-review-recorded` keys on CODEX VERDICT FILES, not review markdown or commit order** — *"Only the
  Codex half leaves a verdict."* Read the gate's source before theorising about it. It wants a round's
  fixes held UNCOMMITTED so the reviewer sees the merging state (schema-2 verdicts carry `head`+`dirty`).
- **A `NO-REVIEW:` waiver is backed by a PROOF**: the changed file's AST byte-identical to the reviewed tree
  once docstrings are stripped, plus every mutation anchor still resolving (51 manifests, 829 entries → 0
  orphaned). State its limit in the waiver: same behaviour, NOT true prose.
- **A body edit does not reach a CI run in flight** (frozen payload; a rerun replays it) — an EMPTY commit
  fires a fresh `synchronize` without touching the reviewed tree.
- ⭐⭐ **Do not assert a quantifier one step beyond what was checked.** One docstring paragraph was wrong
  three times (r7 "reachable and load-bearing", r9 "unreachable" from 1,790 records, r11 "one of the five"
  from verifying ONE). Codex: *"the fix repaired one false sentence by writing a stronger false sentence."*
  What held: enumerate the five conditions individually, and pin the reachable one as a CASE.
- **Ask what tree a number was taken on**: r8 R8-2 reported emissions −0.6% at `04461e1e`, before the F1
  widening; re-measured −47% ([[a-check-result-is-not-the-claim]]).

## History
PR #327 remediated PR #325, which shipped `scripts/check-closing-table.py` on a `NO-REVIEW:` waiver with no
Claude half ever (r1–r6 all Codex). Reviews `docs/reviews/claude/closing-table-r{7,8}-claude.md` — 12
findings, both with `REVIEW GAP: codex`. Widening, measured `master` → `HEAD` over 767 transcripts:

| | before | after |
|---|---|---|
| closing turns warned | 744/769 = **96.7%** | 315/642 = **49.1%** |
| "closed with prose" over a message CONTAINING a table | **372 (50%)** | **0** |
| emissions a reader receives | 1,183 | **630 (−47%)** |

Fixed: F1 marker · F2 teammate fold (332 openers, 125 warned turns) · F4 self-test count was a literal
(three copies of `128`, nothing counting) · F5 · R8-3 · R8-4 · R8-5 (mitigation only). R8-2: the fold made
repeats worse (**37% → 50%** of emissions, worst turn **36× → 71×**).

**Three errors of mine, all caught by gates:** (1) an EQUIVALENT MUTANT — `.match` → `.search` under a
`^\s*`-anchored pattern can never go red; (2) my scoped verifier said **6/6 KILLED** on three mutations
re-targeted onto ONE anchor, which the real harness REFUSED — verbatim
[[a-second-implementation-of-one-rule-drifts]]; (3) a vacuous case in my own fix (R8-4) filtered out the
very dict it was named for.

**PR #328 (rounds 9–11, #149 Tier 1):** `log_line` gained a 4th field `turn_id_of(judged)`; 630 emissions →
**315** unique turn ids, verified three ways. Tier 2 deferred because the live log had **ZERO firings**
since merge — every repeat figure was REPLAYED history; replay confirmed the guard stayed quiet on SIX
commits/pushes that closed with a table. Five CI reds on one PR: two from misreading
`check-review-recorded`, one `check-fixture-variation`, two duplicate edit anchors (instances 14–15).

See also [[concurrent-agents-go-wrong]], [[a-mutation-loses-its-binding]], [[unit-coverage-does-not-compose]].
