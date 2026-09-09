# Post-Plan Gate round 4 — coordinator half — backlog #91 coverage-verdict union

Scope: **round 3's own fixes**, plus the anchor-split written mid-round in response to CI.

Partner halves — round 4 has **two** independent reviewers, the first time in this series:

* [`../claude/plan-coverage-verdict-union-r4-claude.md`](../claude/plan-coverage-verdict-union-r4-claude.md)
  — **NOT CONVERGED**, 0 Blocking, 1 High, 2 Medium, 2 Low.
* [`plan-coverage-verdict-union-r4-codex.md`](plan-coverage-verdict-union-r4-codex.md) — **CONVERGED**,
  0/0/0/1, `gate_ran=true` on `gpt-5.5` after three HTTP 400s.

⭐ **THE TWO HALVES DISAGREED, AND THE FINDING-REVIEWER WAS RIGHT.** Codex reported CONVERGED with a
measured route enumeration; the Claude half found a High that Codex's enumeration could not have
reached, because Codex asked *"can `mut_readable` be True with entries lost?"* (correctly: no) and the
defect is in the **census**, not the parser. This is the fourth recorded instance of this project's
*dual review halves are not redundant* rule, and the argument for never taking a single CONVERGED as
proof. Had I merged on Codex's half — which arrived first and was clean — the High would have shipped.

---

## r4 H1 — `assembled` still had two owners. ACCEPTED, and the overclaim was mine.

A file tagged with a **non-python** fence is reported *and assembled anyway* (`extract()` appends the
problem, then appends the block). The census incremented inside the `is_py` branch, so `files` held a
name it never counted, and the shipped CLI printed `0 assembled` two lines above
`a.py 1 blocks assembled`. Row E of the reviewer's table is the second half: a tagged-then-DROPPED
non-python block decremented zero and announced nothing, so the drop was invisible — which fails r3's
*other* stated rationale, the one about exclusions nobody can see.

**Measured on `master` and every branch revision: identical. This is NOT a regression from r3's fix.**
It is r3 fixing the instance it was shown and then writing, in a comment I authored,
*"ONE OWNER FOR THE WORD 'assembled', and it is `files`."* That sentence was false when written. The
recorded shape is *instance-not-class*, and the aggravating factor is that the comment asserted the
class was closed — which is worse than silence, because it tells the next reader not to look.

**Fixed** by counting where the block enters `files` rather than where a python fence is seen. Both
lines are asserted in one case on a non-python fixture, and the invisible-drop half has its own case.
⚠ `assembled` can now exceed `python fences`; that is honest — they count different things — and the
comment says so.

## r4 M1 — three refusal causes, one identical durable sentence. ACCEPTED.

`check()` constructed a precise `VerdictContractError` and caught it bare, so the only place the cause
was named got discarded. A reader holding the pasted block could not tell *"your suite was already
failing"* from *"your mutations JSON has a trailing comma"*.

**Fixed** by naming the exception and threading `cause` through `NotMeasured.from_counts` into
`not_measured_reason`, where the arithmetic already lives — so cause and counts are baked in together
at construction and no consumer can re-render either. Cased as an **inequality** plus each naming its
own cause, because asserting a substring of one would pass over a renderer that appends the same cause
to everything.

⚠ **RESIDUE, stated not discovered later.** The two *declaration* causes still share a sentence: both
reach the raise through one `mut_readable` bool. Separating them means the flag carrying its reason —
a fifth return value growing a second meaning, which is the shape this branch spent three rounds
deleting. The class a reader actually confuses is now separated; that is what M1 asked for.

⚠ **The predicted orphan happened exactly as measured.** Entry 22's anchor spanned
`except VerdictContractError:`, which naming the exception rewrites. The reviewer called it *before*
the fix; it is retargeted in the same commit, onto the raise **message** above the construction —
both `Measured(...)` constructions in this file are byte-identical, so the message is the only unique
and stable surface.

## r4 M2 — the split's own justification had no falsifier. ACCEPTED, and it is the sharpest of the three.

`746178f6` split one conjunction into two branches *because "each now says which one failed"*, and the
reviewer collapsed both messages into one identical string and got **223/223**. The two manifest
entries there mutate the *predicates*, so they defend the behaviour and say nothing about the text.

That is a **fix that shipped without its case**, in a commit written during this very round, in a
branch whose subject is fixes that ship without cases. **Fixed** with three cases: the two messages
differ, and each names its own half. It matters more than a normal Medium because the split was
**forced by a tool**, so the diagnostic distinction is the only thing making it a design improvement
rather than a concession.

## Lows

**L1 — a near-miss `<!-- mutations -->` tag is ignored silently.** The reviewer raised it and then
argued *against* it: the parser deliberately ignores near-miss tags and has a case saying so. **Not
fixed.** The asymmetry it names (an invisible *fence* is reported loudly, an invisible *tag* is not)
is real and worth one docstring sentence; recorded as residue rather than patched, because chasing
near-misses would break an existing case.

**L2 — "one line, one mutation" is a property of the instrument, not the code.** Accepted as a
statement about method. It belongs in `review-method.md`, not in this file's comments, and M2's fix is
what stops it being a concession. Recorded for the user; **filing to the backlog is their step.**

---

## What was EXECUTED for this fold

| run | result |
|---|---|
| `check-plan-code.py --self-test` | **231/231** (223 → 231) |
| `coverage_verdict.py --self-test` | **27/27** (22 → 27) |
| `stage_tree` | `NONE — tree complete` |
| control, `check-plan-code.py` | **231/231, green** |
| control, `coverage_verdict.py` | **27/27, green** |
| the **15** new or retargeted entries across BOTH manifests | **15/15** caught, measured, `survivors: []`, each red via the case it NAMES |
| `load_manifests(REPO)` — the harness's own loader | **374 entries, problems: NONE** |
| docs · anchors · review-rounds · dashboard-entry · ratchet-contract · producer-enumeration · selftest-counts | all rc 0 |

`EXPECTED_MUTATIONS`: check-plan-code 41 → **44**, coverage_verdict 5 → **6**; sum 370 → **374**.

⭐ **The harness caught a defect in one of my own new cases, and the shape is worth recording.** The
M1 case read `_c2_v.reason` directly. Under entry 22's retargeted mutation that verdict becomes a
`Measured`, which has no `reason` — the union working as designed — so the case raised
`AttributeError` and killed the **suite** instead of printing a named red case. `run_mutations` then
reported `matched 0 red case(s) … caught by something else: []` for an entry doing its job exactly.
That is this project's recorded *a report format is a CONTRACT* failure: coverage that exists and
cannot be seen. The variant is now asserted as part of the tuple rather than assumed.

A second self-inflicted one: M2's first mutation didn't kill its named case, because both messages
embed `{type(parsed).__name__}` and stay unequal even when merged. The `expect` was retargeted onto
the case that *can* fail. **Both were found by running the mutations, not by reading them.**

---

## ⛔ The Phase 6 decision, against a rule I wrote down in advance

`dev-process.md` fires Phase 6 at **four** non-converging rounds. This is the fourth. My r3 coordinator
half pre-registered the test so it could not be rationalised afterwards:

> *"if round 4 produces another self-contradicting artifact, the finding is not the sentence — it is
> that the block has no single producer for 'what was this run about', and Phase 6 convenes instead of
> a fifth fold."*

**The literal trigger fired: H1 IS a self-contradicting artifact.** And the diagnosis I attached to it
was **measured false.** The reviewer went looking for exactly the predicted cause and found the three
narrators — `evidence()`'s subject, `verify_evidence`'s mode, `main()`'s mode string — all deriving
from the flag and all agreeing, plus a fourth (`not_measured_line`'s subject) consistent with both.
H1 is not two sentences from two variables; it is **one number with two increment sites**.

So the rule's trigger and the rule's reason came apart, and `dev-process.md`'s own instruction —
*read the trigger off the CAUSE, not the count* — decides between them. Recording both readings:

| | round 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Highs | 3 | 3 | 4 | **1** |
| introduced by the previous round's fix | — | 3 of 3 | 3 of 4 | **0 of 1** |

**Round 4 introduced no regression, and its own fix survived being attacked as a subject** — 19 inputs
through both `extract()` versions, zero behaviour differences. That is the first time on this branch.

**My decision: do NOT convene Phase 6 on `evidence()`, and escalate the question the reviewer named
instead.** Round 3's M2 measured **0 of 92** plans on disk reaching plan mode's file path. Four rounds
of adversarial review have been spent on a renderer whose only exerciser is its own `--self-test`.
That is a design question — *should this mode exist, and if so what exercises it?* — and it is the one
this branch has never asked. It is also the kind of question that **moves the goal**, so it is the
user's to answer, not mine. Notified 2026-09-08; the merge proceeds under the standing authority for
this series, and the corpus question is carried out of it as a backlog candidate.

**Verdict: round 4's findings are folded and each falsified. The branch is merged on the strength of
CI's full sweep, not on a claim of convergence — no round has produced zero findings, and I am not
claiming this one would have.**
