# record-review-topology — round 13, coordinator adjudication

**REVIEW GAP:** codex — timed out; `gpt-5.5` produced no usable final message within the wrapper's
900s budget, so `scripts/codex-review.py` refused to write a review rather than writing an empty one
and filed `docs/reviews/verdicts/record-review-topology-r13-codex.verdict.json` with
`gate_ran: false`. Per `docs/plugins.md` the rule is **do not wait, do not retry repeatedly** — fall
back to a rigorous Claude adversarial review and record the gap. The Claude half ran and is below.
Round 14 re-attempts the Codex half against the final tree with a doubled budget.

Claude half: `docs/reviews/claude/record-review-topology-r13-claude.md` — 0 Blocking, 1 High,
2 Medium, 1 Low, against HEAD `dc9fe107` plus the uncommitted delta.

The wrapper behaving correctly here is worth one sentence: it failed **loud**. A caller checking only
the exit code of a raw `codex exec` would have recorded a completed gate.

## ⭐ H1 — the round-12 repair had no falsifier, and that was proved by execution

Reverting the classifier printer to the exact broken shape r12 filed left the **whole gate green**:

```
shipping tree      44 file(s), 618 mutation(s), 618 killed, 618 attributed, 0 survivor(s)   rc=0
:907 REVERTED      44 file(s), 618 mutation(s), 618 killed, 618 attributed, 0 survivor(s)   rc=0
```

Byte-identical verdicts. All nine manifest entries for that file named `chk` cases, so nothing
measured the printer at all — in the file that has now broken the `[FAIL] <case>` contract **twice**,
on a branch whose thesis is that a guard must be falsifiable. `docs/dev-process.md` states the
standard as *"State the observation that would make it FAIL."* There was none.

**FIXED, and the fix is structural rather than an added entry.** The two printers were two copies of
one contract — the duplicate-mechanism shape this repo refuses everywhere else, and the direct cause
of both breaks. There is now **one**: `case_line()`, pure, module-level, called by both. Six cases
assert it, four of them round-tripping through `check-plan-code.parse_fail_names` **imported**, not
re-derived — because a local copy of "truncate at the last `': got '`" would be a second
implementation of the exact rule whose two copies caused both breaks. `_load_fail_parser` RAISES if
it cannot load; cannot-run is a failure, never a skip. Suite 79 → 85.

### ⚠ The obvious manifest entry is IMPOSSIBLE, and that is worth recording

A mutation reverting the line to `got={got}` **is** caught — the suite goes red — but its own
`[FAIL]` line is printed by the very printer it broke, so the detecting case's name is garbled and
cannot be attributed. **The detector is printed by what it detects.** Measured: the exact `expect`
would have had to be
`"…parses back to the case name, via the harness's OWN parser: got=['a plain case: got=1']"`.

So the two new entries aim at the parts that stay readable — the dropped `reason`, and the parser
being a stub instead of the imported one — while the full revert is caught by `--self-test` going
red, which is the defence that actually matters and did not exist before this round.
`EXPECTED_MUTATIONS["scripts/codex-review.py"]` 9 → 11, declared total 618 → 620.

⚠ A related contract fell out of it: the two literal-shape cases assert **booleans**, not the line
itself. A `[FAIL]` line quoted inside a `[FAIL]` line puts a SECOND `": got "` into the output, and
the parser truncates at the LAST one — so the case's own name would be cut at the quoted text and
the kill attributed to a name nobody wrote. Same family as the `.get`-not-`[...]` rule the sibling
file already records: **a case must fail READABLY.**

## M1 — my r13 comment asserted a mechanism that does not exist, and could not

The r12 Low was repaired by a comment claiming the duplicate-in-substance property is *"really
carried by the exact-`expect` rule"*. **False twice over.** That rule is evaluated per mutation
inside the per-entry loop, so two entries sharing an `expect` are each attributed independently and
neither is refused — measured at both layers. And the rule could not be added: sharing an `expect` is
legitimate and common, and a duplicate-`expect` refusal would red **six** shipping manifests today.

This is the branch's signature defect — a comment asserting a property the code lacks — landed
inside the repair for a finding about exactly that. **FIXED**: the comment now says plainly that a
duplicate-in-substance entry is caught by nothing, and names what the two literal rules do cover.

## M2 — this branch broke a prose count inside the sentence promising that could no longer happen

`docs/plugins.md` said *"Run `--self-test` (63 cases)"* while the suite ran 85 — and this branch
caused the drift, having moved the count twice. The sentence around it promises *"the next drift
fails a gate instead of sitting in prose."* `CLAUDE.md` imports that file, so the wrong number was
loaded into every session. Nothing was red: `check-selftest-counts.py` reads only `scripts/*.py`.

**FIXED by DELETION, not correction.** The number is gone and the sentence now points at the script,
which declares its own count and has it verified by running it. A count with no owner drifts again.

⚠ **Three more stale prose counts exist in `docs/dev-process.md`** (`check-ratchet-contract` says 21
/ runs 41; `check-review-rounds` says 27 / runs 29; `check-plan-file-tags` says 21 / runs 44). All
three were **already stale at the merge-base** — not this branch's doing — so they are reported here
and deliberately NOT fixed in a convergence round. Filing them is the user's step.

## L1 — recorded, not fixed

The harness never checks that a mutation anchor is **unique** in its target, while the
duplicate-anchor rule actively pressures authors toward shorter anchors. Measured clean today: all
620 anchors occur exactly once. Closing it is one `src.count(find) != 1` refusal in
`load_manifests` — which is a new rule, needing its own case and its own mutation, i.e. another
round. Recorded rather than added, for the same reason `check-selftest-counts`'s blind spot was:
inventing half a mechanism during convergence is how the next defect gets written.

## ⭐ The frame, which the Claude half was asked for and gave

Two observations worth keeping, both uncomfortable:

1. **Every round from r11 on has attacked the `[FAIL] <case>` contract by READING printers** — and
   reading missed it twice, in the same function, 21 lines apart. The class question was ultimately
   answered by *executing*: forcing every one-sided `[FAIL]` branch in all 44 targets red and parsing
   the real output. That is the branch's own thesis turned on the branch's own method.
2. **Thirteen rounds and ~1,800 lines of review have gone almost entirely into the INSTRUMENT** —
   the mutation harness, printer formats, declared counts — rather than `check-review-recorded.py`,
   the gate this branch ships. That gate was reviewed in r1–r10; r13 found nothing new in it, its 117
   cases pass and all 35 of its mutations are attributed. M2 is the small measurable proof that
   attention drifted: the branch updated the script's count twice while the number a reader actually
   sees went stale.

## Measured on this tree

```
codex-review          --self-test   85/85      check-review-recorded  --self-test  117/117
check-plan-code       --self-test  128/128     check-ratchet-contract --self-test   41/41
check-fixture-variation --self-test 60/60      check-selftest-counts  --self-test   18/18
check-review-rounds   --self-test   29/29      check-guard-coverage   --self-test   37/37
live: check-selftest-counts, check-fixture-variation, check-ratchet-contract, check-docs,
      check-anchors — all rc=0
```

NOT CONVERGED — r14 owed: the r13 repair touches guarded code, and the Codex half is owed a real run.
