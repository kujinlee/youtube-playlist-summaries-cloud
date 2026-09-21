# closing-table — round 5, Claude half

**REVIEW GAP: the independent Claude half could not be dispatched (fifth round running).** Same
constraint throughout. Coordinator self-review only.

## r5's verdict: NOT CONVERGED — three live defects, all MISSES

| # | Grade | Finding | Status |
|---|---|---|---|
| r5-H1 | High | a quoted or commented `<<EOF` opened a fake heredoc and swallowed a later real close | **already fixed** at `c0efd8fe`, which landed while r5 was reviewing `998b1999`. Verified against both of r5's repros |
| r5-H2 | High | **the veto is paired to the CALL, but the act's unit is a SEGMENT.** `cat old-push.log` (containing a stale `error: failed to push`) followed by a successful `git push` in the same call = a MISS | fixed by ADJUDICATION, not attribution — see below |
| r5-M1 | Medium | `paired_outputs` paired by dictionary overwrite: a duplicate `tool_use_id` let a later result replace a success, and a result appearing BEFORE its use was accepted | fixed — pairing now respects order and uniqueness; a violated invariant yields no output, hence no veto, hence no miss |
| r5-C1 | — | the corpus claim "229 calls, 11 fires, 0 FP, 0 misses" could not be independently reproduced | **conceded and corrected** — see *On the corpus claim* |

## r5-H2 and why the fix is adjudication rather than attribution

A Bash call produces ONE combined output; there is no way to attribute an output line to a segment
within it. So "pair the veto to the segment" is not available. What is available is a tie-breaker:

> If the same output ALSO carries the act's SUCCESS signature, the failure phrase did not come from
> the act that matters, and the veto stands down.

This reuses the effect signatures measured during the redesign — the ones **rejected as a detector**
because `| tail` truncates them. As a tie-breaker their truncation is harmless: no signature simply
means the veto behaves as it did before. A mechanism that was wrong for one job is right for another,
and the measurement that rejected it is what made the second use safe.

⚠ **This fix made one of my own mutations survivable**, which is worth recording. The whole-window
mutation had been killed by "a failed push does not cancel a later successful one" — but with
adjudication, joining all outputs pulls in call 2's success signature and rescues the act, so the
mutation went unnoticed. The new case truncates call 2's output to empty, so **only pairing** can
save the push. A fix that silently disarms an existing mutation is the *removing a signal hollows
out its falsifier* shape, caught here only because the verifier reports survivors.

## On the corpus claim — r5 is right and I overstated it

I reported "229 Bash calls → 11 fires, 0 false positives, 0 misses". r5 could not reproduce it and
named the reason precisely: **that is not the guard's judged-turn unit.**

What I actually measured is a **component-level** property: for each Bash `tool_use` paired with its
own result, does `closing_acts_of` agree with a hand-written ground-truth rule? That is a real and
useful measure of the TRIGGER, and it is what justified the veto and the heredoc masking. It is
**not** an end-to-end measure of the guard's verdicts, which operate on judged turns — of which this
session has five, not 229.

Both numbers are true of different things; only one was labelled. That is this project's recorded
*a measurement needs its CONTEXT, not just its value* defect, and the count itself also drifted
(211 → 219 → 229 → 238) because the transcript grows while the session runs. The claim now reads:

> per-Bash-call trigger agreement against a stated ground-truth rule — not per-judged-turn verdicts.

## Verification

| check | result |
|---|---|
| Self-test | ✅ **124/124** |
| Mutations kill via the case each NAMES | ✅ **36/36** — 0 survivors, 0 unattributable, 0 orphaned |
| r5-H1 repros (quoted / commented `<<EOF`) | ✅ `['a push']` both |
| r5-H2 repro (stale error + real success, one call) | ✅ `['a push']` — was `[]` |
| r5-M1 repros (duplicate id; result-before-use) | ✅ `['a push']` both — were `[]` |
| Veto still does its job (refused tick, failed push, nothing to commit) | ✅ `[]` all three |
| r4's fix not regressed (failed call then separate success) | ✅ `['a push']` |
| All repo gates | ✅ rc=0 |
| An independent Claude reviewer ran | ❌ **NO** — five rounds, never available |

---

## ⭐ ADDENDUM — generalisation against SIX UNSEEN transcripts (measured after r5 was filed)

Every measurement up to this point used **the session that built the guard**, which is the corpus
most likely to flatter it. Re-run against six other sessions from this project — none of which were
looked at while writing any of the code:

| transcript | Bash calls | fires | apparent false + | apparent misses |
|---|---|---|---|---|
| `a00a513a` | 1,646 | 169 | 1 | 0 |
| `92595a72` | 1,602 | 107 | 0 | 0 |
| `9a5869f4` | 585 | 38 | 0 | 0 |
| `d573bf68` | 660 | 72 | 0 | 0 |
| `dca6fb13` | 509 | 56 | 0 | 1 |
| `d5a719c9` | 285 | 14 | 0 | 0 |
| **total** | **5,287** | **456** | **1** | **1** |

**Both discrepancies were adjudicated by hand, and BOTH were defects in the ground-truth rule, not
in the guard:**

* the "false positive" was `gh pr merge $p --squash --delete-branch` inside a `for` loop. The merges
  **really ran** — the ground-truth regex required the command at line start, and a loop body is
  indented. The guard was right.
* the "miss" was `git commit -F /tmp/t-script-msg.txt`, whose output ends
  `no changes added to commit (use "git add" and/or "git commit -a")`. The commit **genuinely did
  not happen**; the veto caught it correctly. The guard was right, and this is the veto doing
  exactly the job it was added for, on data it had never seen.

So: **0 confirmed guard errors over 5,287 unseen calls.**

⚠ **This is the THIRD time on this branch that the thing that was wrong was the MEASUREMENT.** The
sha fixtures that only passed because a bad pattern carried them; the corpus claim labelled as
end-to-end when it measured per-call agreement; and now two "errors" that were ground-truth bugs.
When a measurement disagrees with the code, the measurement is about as likely to be the defect —
and adjudicating each disagreement by hand is the only thing that separates them. A number nobody
interrogates is the same hazard as a green check over the wrong subject.
