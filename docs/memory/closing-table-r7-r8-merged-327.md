---
name: closing-table-r7-r8-merged-327
description: "FIRES-WHEN: citing PR #327, PR #328, or the closing-table work — ⭐⭐ BOTH MERGED — #327 fab6f655 + #328 42038988, the independent read #325 shipped without. 16 findings over rounds 7–11. Marker enforced one EXAMPLE of the rule: firing 96.7%→49%, false-sentence firings 372→0. ⛔ check-review-recorded keys on CODEX VERDICTS, not commit order (2 of 5 CI reds). One docstring paragraph was WRONG THREE TIMES, same shape: a quantifier asserted one step beyond what was checked."
metadata: 
  node_type: memory
  type: project
  originSessionId: b3d559c1-6b4c-49e1-81af-8ac588f0b7d8
  modified: 2026-09-21T14:47:21.326Z
---

**MERGED 2026-09-21 as `fab6f655` (PR #327).** Remediates PR #325, which shipped
`scripts/check-closing-table.py` on a `NO-REVIEW:` waiver saying out loud it had never had a Claude
half — r1–r6 were all Codex, every "claude half" among them a coordinator self-review.

Reviews: `docs/reviews/claude/closing-table-r{7,8}-claude.md` (338 + 233 lines, 12 findings, both
carrying a `REVIEW GAP: codex` line — **the Codex half never ran for either round**).

## The finding that mattered, and the decision the user took

⭐ **THE MARKER ENFORCED ONE EXAMPLE OF THE RULE.** `docs/process-checklists.md` states the format as
three PROPERTIES (one row per claim, evidence in the row, every row could have come back ❌) and then
shows one example headed `check`/`result`. `has_closing_table` required those exact header cells.

**User chose to WIDEN (option A).** Measured `master` → `HEAD` over 767 transcripts:

| | before | after |
|---|---|---|
| turns closing a job that get warned | 744/769 = **96.7%** | 315/642 = **49.1%** |
| warnings saying "closed with prose" over a message CONTAINING a table | **372 (50%)** | **0** |
| emissions a reader actually receives | 1,183 | **630 (−47%)** |

⛔ **A NARROWER REPAIR WAS MEASURED DEAD FIRST** — *"accept a table only when it ENDS the message"*.
Of 304 warned-on tabled messages, **0** end with one; 100% are followed by a caveat or next step.
Recorded in the code so it is not re-proposed. **Measure the constraint before shipping the tighter
rule that sounds safer.**

## ⭐⭐ Three errors of mine, all caught by gates, none by me

1. **AN EQUIVALENT MUTANT.** I mutated `_INJECTED.match` → `.search` to simulate a substring fold.
   Under a `^\s*`-anchored pattern those are IDENTICAL — it could never go red. A mutation that
   proves nothing while looking like coverage, shipped in the same PR that files five such cases.
2. ⭐⭐ **MY STAND-IN PASSED A MANIFEST THE GATE REFUSED.** After CI rejected three mutations I
   re-targeted all three onto the SAME anchor text. The harness refused outright
   (*"repeats the edit anchors of an earlier entry — it measures nothing new"*), while my scoped
   verifier reported **6/6 KILLED**. That is verbatim
   [[a-second-implementation-of-one-rule-drifts]] — the recorded instance says a scoped verifier
   "checked that anchors RESOLVE and not that they are DISTINCT … 21/21 green on a manifest the real
   harness REFUSED". Same file, same guard, four weeks later. **I wrote the checker to answer "does
   each mutation kill?" and never asked "would the manifest be ACCEPTED?"**
3. **A VACUOUS CASE IN MY OWN FIX** (r8 R8-4). My case *"the teammate fragment's records join the
   interrupted turn"* filtered the opener out with `isinstance(x, str)` — the dict whose joining it
   is NAMED for. Deleting the behaviour left it green. Found because I explicitly asked the reviewer
   to hold my new cases to the standard its own F6 set.

## What was fixed vs filed

Fixed: F1 marker · F2 teammate fold (332 openers, 125 warned turns) · F4 self-test count was a
literal (`total = 128` vs a docstring `128` vs a printed `128` — three copies, nothing counting) ·
F5 docstring · R8-4 · R8-3 (stated bound) · R8-5 (mitigation only — a cross-reference, NOT a
falsifier; the literal is duplicated in two guards for OPPOSITE purposes and nothing observes it).

Open: **#149** 🟠 the log cannot answer the question it exists for — r8 R8-2 confirmed the fold made
repeats worse (**37% → 50%** of emissions, worst turn **36× → 71×**); `docs/dev-process.md` says
"read the log in a few weeks" and it is not yet readable. **#151** 🟡 five vacuous cases, only (b)
has a real MISS behind it. **#148** 🟡 whether the banner guard carries the same split — UNMEASURED
in both directions, measurement only.

⚠ **r8 R8-2 was HALF SUPERSEDED, and which commit it was measured at was the whole difference** — it
reported emissions falling 0.6%, taken at `04461e1e` before the F1 widening. Re-measured: −47%.
[[a-check-result-is-not-the-claim]]: ask what tree a number was taken on.

See also [[concurrent-agents-go-wrong]] (both costumes cost me this session),
[[a-mutation-loses-its-binding]] (the F2 edit orphaned a pre-existing anchor).

---

## ⭐ PR #328 ALSO MERGED — `42038988` (#149 Tier 1, rounds 9–11)

The log-turn-identity work. `log_line` gained a 4th field (`turn_id_of(judged)` = the judged
window's opener uuid), so `cut -f4 <log> | sort -u | wc -l` is a TURN count. Verified THREE
independent ways (coordinator replay, r9 Claude, r10 Codex): 630 emissions → **315** unique ids,
0 `-`, 0 unstable across consecutive stops.

**Tier 2 (the anti-nag journal) DEFERRED, and the reason is the one to remember:** the live log had
recorded **ZERO firings** since the guard merged. Every repeat figure was REPLAYED history, not
lived experience. ⭐ Verified that zero was correct behaviour and not a dead hook — replayed over
the session, the guard saw SIX commits/pushes and stayed QUIET because each closed with a table.

## ⛔ FIVE CI REDS ON ONE PR. The two that cost most were the same gate, misread twice

⭐⭐ **`check-review-recorded` KEYS ON CODEX VERDICT FILES, NOT ON REVIEW MARKDOWN OR COMMIT ORDER.**
Its own words: *"Only the Codex half leaves a verdict."* I spent two reds solving commit ORDER —
committing the review alone so a round was "genuinely last" — when no amount of ordering can help,
because the Claude half produces no verdict JSON at all. **Read the gate's source before theorising
about it a second time.** The documented practice it actually wants: hold a round's fixes
UNCOMMITTED so the reviewer sees the state that will merge (schema-2 verdicts carry `head`+`dirty`).

The other three: unvaried `when`/`session` params (`check-fixture-variation`, invisible until the
function HAD tests), and a duplicate edit anchor TWICE — see
[[a-second-implementation-of-one-rule-drifts]] instances 14–15.

## ⭐ THE LEGITIMATE WAIVER, AND HOW IT DIFFERED FROM #325'S

Cleared the final block with `NO-REVIEW:` **backed by a proof, not an assertion**: the AST of the
changed file was byte-identical between the reviewed tree and HEAD once docstrings were stripped —
every added line was docstring prose or a `#` comment. Also checked the one thing a comment edit
CAN break: text-matched mutation anchors (all 51 manifests, 829 entries → 0 orphaned, 0 ambiguous).

⚠ **The limit was stated in the waiver itself:** an identical AST means the BEHAVIOUR is unchanged.
It does NOT mean the new words are TRUE — which is exactly what r11 found wrong twice. The claim
waived was *"needs no further review"*, never *"this prose is correct"*.

⚠ **A body edit does NOT reach a CI run already in flight** (frozen event payload), and a rerun
replays the same payload. An EMPTY commit fires a fresh `synchronize` event without touching the
reviewed tree.

## ⭐⭐ THE PARAGRAPH THAT WAS WRONG THREE TIMES, SAME SHAPE, SHRINKING SCALE

One docstring paragraph about when a `-` can appear:

    r7   generalised from `windows()`'s docstring    -> "reachable and load-bearing"   WRONG
    r9   generalised from a corpus of 1,790 records  -> "unreachable"                  WRONG
    r11  generalised from having verified ONE        -> "one of the five"              WRONG

**A count or a quantifier asserted one step beyond what was checked**, three rounds running. Codex's
verdict on the middle one is the sentence to keep: *"the fix repaired one false sentence by writing
a stronger false sentence."* The repair that finally held was to **enumerate all five conditions
individually instead of quantifying over them** — and to pin the reachable one as a CASE, because
prose cannot fail. See [[unit-coverage-does-not-compose]], [[a-check-result-is-not-the-claim]].

**Still open:** #148 (measure the banner guard) · #149 Tier 2 · #151 (5 vacuous cases) · #152 (a
valid-JSON non-object transcript line raises UNCAUGHT and reports as exit 1 = a WARNING, when the
contract says CANNOT RUN 2).
