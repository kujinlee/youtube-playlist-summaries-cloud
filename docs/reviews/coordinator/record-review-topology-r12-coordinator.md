# record-review-topology — round 12, coordinator adjudication

Both halves ran against HEAD `dc9fe107` **plus the uncommitted r11 repair**, which was the shipping
state — the practice this branch exists to protect, used on the branch itself.

* Claude: `docs/reviews/claude/record-review-topology-r12-claude.md` — 0 Blocking, 1 High, 1 Medium, 1 Low.
* Codex: `docs/reviews/codex/record-review-topology-r12-codex.md` (`gpt-5.5`) — 0 Blocking, 1 High.
* Verdict: `docs/reviews/verdicts/record-review-topology-r12-codex.verdict.json`, `gate_ran: true`.

## ⭐ THE TWO HALVES OVERLAPPED, AND THAT IS ITSELF A FINDING ABOUT THIS BRANCH

They found **the same High**, independently, with independent reproductions. That matters because
the pull-request body's central measurement is *"zero overlapping findings"* across three rounds on
two branches, offered as proof that neither half is wasted effort. It is still true that neither is
wasted — but the *zero* is now a sample, not a law, and this round is the counter-example. The
claim that survives is the weaker and more useful one: **the halves are not redundant**, evidenced
by r11, where Codex found a Blocking (unmeasurable manifests) that the Claude half's three lenses
missed entirely, and the Claude half found a Blocking (a working evasion of the rule) that ten
Codex rounds had missed. One round of agreement does not undo that; it does retire the absolute.

## The High — and it is mine, in the shape this project has a name for

`scripts/codex-review.py` has **TWO** `[FAIL]` printers inside `self_test()`, 21 lines apart. The
r11 repair fixed `chk`'s at `:928` and left the classifier's at `:907` emitting
`got={got} ({reason})` — the exact broken shape the round was convened to remove. All **17**
`classify` cases — the half that decides whether a review gate RAN — stayed invisible to
`parse_fail_names`.

**Fixing the instance and calling it the class, inside the same function, in the round whose brief
named that as the highest-value question.** Worse, two documents asserted it settled: the code
comment at `:919` (*"THE CANONICAL LINE"*) and
`docs/reviews/coordinator/record-review-topology-r11-coordinator.md` (*"The printer is now
canonical"*). Both were false about the file they described.

**FIXED.** `:907` now prints `got {got!r} want {want!r} ({reason})`; the trailing `({reason})` is
safe because the parser truncates at the LAST `": got "`, which is still the one that line writes.
Measured after: **79 printed case lines, 0 carrying a got-tail.**

⭐ The Claude half then swept **all 44 manifests** against their targets' failure printers and
classified every shape — comma variants, name-only, continuation lines, assembled markers,
append-then-print. Exactly one was broken: this one. That sweep is the class question actually
answered, and it is worth more than the fix.

## The Medium — sharper than it was filed, and the round made it worse

`extra += 13` double-counted. `chk` already does `extra += 1` per call, so 13 of the declared 92
cases had no assertion behind them, could never fail, and printed nothing. **I grew it**: the line
read `extra += 8` before this branch and r11 changed it to 13 while adding five fixture cases —
reasoning about the literal instead of asking what incremented the variable. The round paying down
this file's measurement debt made the debt larger.

**FIXED** — the literal is deleted; the real total is `len(cases) + chk calls` = **79**, and the
declaration follows it.

⚠ `check-selftest-counts.py` **structurally cannot see this**: it compares the suite's own printed
denominator against the suite's own declared count, and both are authored in the subject. A literal
added to `extra` moves them together, so the gate stays green over fiction. That is the
declared-count-drift class this project has already paid for three times, one layer in. Recorded
here rather than fixed — closing it needs a different observer, and inventing half a mechanism in a
convergence round is how the next defect gets written.

## The Low

The duplicate-anchor refusal compares **exact tuples**, so two entries aimed at the same behaviour
clear it by shortening one anchor. Its message — *"it measures nothing new"* — claims a property the
test does not deliver; the property is really carried by the exact-`expect` rule. A sentence now
says so at the rule. r11's repair does not abuse it: both pairs were verified as genuinely different
behaviours, attributed.

## Measured on this tree

```
--mutate .   44 file(s), 618 mutation(s), 618 killed, 618 attributed to the case each names,
             0 survivor(s)          — run twice: before and after the r12 repair
codex-review          --self-test   79/79      check-review-recorded  --self-test  117/117
check-plan-code       --self-test  128/128     check-ratchet-contract --self-test   41/41
check-fixture-variation --self-test 60/60      check-selftest-counts  --self-test   18/18
check-review-rounds   --self-test   29/29
live: check-selftest-counts, check-fixture-variation, check-ratchet-contract, check-docs — rc=0
```

The Claude half independently ran the full mutation gate in its own isolated copy and got the same
verdict, as did the Codex half. Three independent runs agreeing is the strongest available evidence
of non-interference, which is the standard `docs/review-method.md` sets for the concurrency table.

## ⚠ ROUND 13 IS OWED

The r12 repair touches `scripts/codex-review.py` and `scripts/check-plan-code.py` — guarded code —
so both r12 verdicts are stale against the tree that ships, and Codex r12 in particular was
dispatched *before* the repair existed. The branch's own rule will say so. Round 13 runs both halves
against a **frozen** tree; if it returns no Blocking or High, the loop has converged.

NOT CONVERGED — r13 owed.
