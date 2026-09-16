# Round 2 — `peer-sites` — coordinator

```yaml
round: 2
fixes_nontrivial: true
subject: peer-sites
halves:
  claude: ran
  codex: "GAP: alternating protocol — rounds 2+ send ONE half; Codex carries round 3"
findings:
  - {id: Q1, severity: High, aim: deliverable, fix_induced: true, component: if-chain, disposition: fixed}
  - {id: R1, severity: High, aim: instrument, fix_induced: true, component: activation, disposition: fixed}
  - {id: R2, severity: High, aim: instrument, fix_induced: true, component: activation, disposition: fixed}
  - {id: R3, severity: High, aim: deliverable, fix_induced: true, component: activation, disposition: fixed}
  - {id: R4, severity: High, aim: deliverable, fix_induced: false, component: main-diff, disposition: fixed}
  - {id: R5, severity: Medium, aim: deliverable, fix_induced: true, component: parse-hunks, disposition: fixed}
  - {id: R6, severity: Medium, aim: deliverable, fix_induced: false, component: main-diff, disposition: fixed}
  - {id: R7, severity: Medium, aim: deliverable, fix_induced: false, component: except-shape, disposition: filed}
  - {id: R8, severity: Medium, aim: instrument, fix_induced: false, component: peer-sites-manifest, disposition: fixed}
  - {id: R9, severity: Low, aim: deliverable, fix_induced: true, component: activation, disposition: declined}
  - {id: R10, severity: Low, aim: deliverable, fix_induced: false, component: activation, disposition: declined}
  - {id: R11, severity: Low, aim: deliverable, fix_induced: true, component: activation, disposition: fixed}
  - {id: R12, severity: Low, aim: deliverable, fix_induced: false, component: activation, disposition: filed}
  - {id: C3, severity: High, aim: instrument, fix_induced: true, component: peer-sites-hook-suite, disposition: fixed}
deliverable_findings: 8
stopping_rule: not_triggered
```

**REVIEW GAP:** codex — not run for this round **by protocol, not by absence**. `review-method.md`
step 4: *"Rounds 2+ alternate, scoped to the delta, sent to the half that did NOT author the fix."*
Round 1 ran both halves concurrently; round 2 is the Claude half against round 1's fixes. **Codex has
round 3**, dispatched against the uncommitted round-2 fixes with `--timeout 3600`, and the protocol's
own reasoning says it should get this one: *"match the reviewer to the risk — reproduction and
execution → Codex"*, and the largest new artifact is a hook that had to be live-fired to be
understood.

## The verdict, and it is a clean boundary

> **"NOT CONVERGED. The python is close to done, the bash is not."**

**10 of the 12 findings were in the hook I added as round 1's fix for P2**, or in decisions nobody
cased. The reviewer verified all 16 r1 manifest entries itself rather than taking my word, found
every one honest, and explicitly cleared C1: *"you did not just add cases that pass."*

## Q1 — the r1 Blocking came back through a different door, and that is the round's real lesson

I asked the reviewer to settle whether `_if_chain`'s `else`-arm handling was correct. The answer was
**no**, and worse than I had framed it. r1's fix made the `else` member `_span(orelse[0])` — its
whole first statement. When that statement is a nested `if`, the else member swallows the entire
inner container. Measured on **B1's own fixture**:

```
members [(3,3), (6,9)]   <- the else arm spans the whole nested chain
report(…, {8})  ->  "you changed 1 of 2 branches /  :3  if x:  /  > :6-9  if y == 1:"
```

Line 8 is the *inner* chain's `elif`. It belongs to no arm of the outer chain. The outer `if x:` is
offered as its peer, and the printed body text says `if y == 1:` for an edit to `elif y == 2:`.

⭐ **That is B1 — the round-1 Blocking — arriving through the RANGE instead of through the AST.**
`_is_elif` shut the AST door; r1's own `_span` fix opened a second one. The reviewer also showed it
could *silence* a container: touching `{3, 6}` put line 6 inside `(6,9)`, both members read as
touched, and the chain was filtered as "fully touched".

Fixed by making all three arms follow **one rule — a member is its head**. The `else` has no test, so
its head is its first statement's single line.

⚠ **And the fix was green under all 59 cases before I wrote its falsifier.** That is C1 for the third
time on this branch. Two cases now die when r1's version is restored.

## C3 — my own finding, and it is the ambient trap

The new `scripts/peer-sites-hook.py` suite passed 36/36 **in this repo and nowhere else**. Copied to
a scratch directory it failed with an `IndexError` and no tally: `main()` took the
`PEER_SITES.is_file()` early return, the stub was never called, and three cases were asserting
against an empty list.

The suite was passing for an **ambient** reason — `scripts/peer-sites.py` happened to sit next to it.
Under `--mutate .` the harness stages `scripts/`, so it would have passed there too, and the defect
would have shipped invisible. Found by this project's own prescribed practice: **run the suite
somewhere other than the tree it lives in.** It now runs three ways — in repo, copied elsewhere, and
under a redirected `HOME` — 38/38 in all three.

## R1/R2 — the fix for "no mechanism" introduced a second, unmeasured mechanism

The reviewer's measurement is the whole argument:

```
7 of 7 mutations to the hook's BODY survived — including the rc=1 fail-open
I had found and fixed by hand hours earlier (C2 in round 1)
2 of 2 control-positives died — so the suite worked; it just never reached the code
```

And nothing ran even that suite. `check-selftest-counts.py` globs `scripts/*.py`;
`check-ratchet-contract.py` reads `scripts/`. **Neither can see `.claude/hooks/*.sh`.**

So the rule moved to where the machinery looks — `scripts/peer-sites-hook.py`, 38 cases, 8 manifest
entries — and the bash shrank from **127 lines to 37**. This is not a new idea: `enforce-handoff-path.sh`
and `enforce-selection-card.sh` already delegate their rules to a `scripts/check-*.py` with a suite
and manifest entries. The advisory hook was the only message-bearing hook with neither.

⭐ **The proof the fix is structural rather than cosmetic: both ratchets refused the new file the
moment it appeared** — `check-fixture-variation` demanded `main.argv` be varied and its key set
pinned, `check-selftest-counts` demanded POPULATION registration, and `check-plan-code`'s literal
inventory demanded an entry. While the same logic was in bash, not one of them could see it at all.

## R3 — the caller asked a different question from the one the design was justified by

The hook passed the branch's **merge base**, so its window grew with every commit:

| window | silent | max lines | commits printing ≥20 lines |
|---|---|---|---|
| ~1 (per-commit — **what the design was justified by**) | 65% | 30 | 3 |
| ~10 (a normal branch here) | **15%** | **76** | **54** |

The "70% silent, so the cost is bounded" figure is the per-commit number. One token — `--diff HEAD` —
makes the caller ask *what am I about to commit*, which is the question the six-miss experiment
measured. R11 came with it: the pre-filter moved into the shim, so a non-commit no longer pays for a
python spawn. Measured **69 ms → 16 ms** on every Bash tool call.

## Declined and filed, with reasons

- **R9** (a staged-then-reverted edit is invisible: `git diff HEAD` reads the worktree, `git commit`
  commits the index) — **declined**, documented as a stated bound. It needs stage-then-revert to
  bite, and `peer-sites.py` has no `--cached` mode to borrow; adding one to close a Low is scope the
  reviewer did not argue for.
- **R10** (`wants_check` is loose) — **declined and already deliberate**; the reviewer agreed the
  cost is a nudge. Its own case says so.
- **R7** (the `except` shape produced **0** containers across 362 file-diffs on every subject
  measured, and the decision causing it is unfalsifiable in both directions) and **R12** (both
  advisory hooks share a stdout channel this repo has twice recorded as weak) — **filed**. R7 is the
  same question as backlog #131 from a third side: *what does it mean to touch a member?*

## ⛔ THE MACHINE FIRED, AND I AM NOT OVERRIDING IT

```
$ python3 scripts/check-review-decision.py
ARCHITECTURE_REVIEW — thrashing: 'activation' carried fix-induced findings in r1 and r2
```

**That verdict is computed from the `fix_induced` flags I recorded in this document's own header**,
so it is my honest data being read back at me by a rule I wrote down before I needed it. The section
below is the argument I would make for *why* it should not fire. It is an argument, not a
measurement, and the guard's docstring is explicit that it **consumes judgements and does not make
them** — so the argument does not get to quietly win.

⚠ **One thing in my own reasoning is worth flagging against myself.** The arming condition says *the
**previous** round's fix*. r1's C2 was found while building r1's fix, in the same round — there was
no previous round for it to come from. Relabelling it would clear the gate, which is exactly why I am
not doing it: *"a header filled in dishonestly produces confident wrong answers, and nothing detects
that."* The flag stays `true` because the defect was genuinely introduced by a fix.

**The decision waits on round 3, deliberately.** Codex is reviewing the round-2 fixes right now, and
its findings are precisely the evidence this question needs: another fix-induced High in `activation`
means a twice-fixed component is still fighting itself, and the review is owed. A clean round means
this was one under-reviewed artifact, reviewed properly on the second pass. Convening before that
evidence exists would be spending the expensive option to answer a question about to be answered for
free.

## Thrashing — asked rather than assumed

`dev-process.md` arms the architecture review on *two consecutive rounds carrying findings caused by
the previous round's own fix, in one component*. `activation` has fix-induced findings in both rounds
(C2; then R1, R2, R3, R11), so the counter's shape is met. **It does not fire, and here is the
evidence rather than an assertion:** those are all defects in **one artifact that has been written
once**, found across two rounds because round 1 reviewed it for minutes and round 2 reviewed it
properly. Thrashing is *fix → new defect → fix → new defect*; the hook has had one fix, not two. The
test `review-method.md` gives — *can a redesign remove it?* — was answered **yes** and the redesign
was done: the rule left bash. If round 3 finds fix-induced defects in `activation` **again**, that is
the second consecutive round against a twice-fixed component and the review should be convened.

⚠ **Pre-committing the retreat, before round 3 runs:** if round 3 returns another fix-induced High in
`activation`, the answer is **not** a fourth hook revision. It is to **drop the hook from this branch
entirely**, ship the well-reviewed `scripts/peer-sites.py`, and re-file P2 as its own slice with the
experiment-first treatment the reviewer says it deserves.

## What changed, measured

| | r1 end | r2 end |
|---|---|---|
| `peer-sites.py` cases | 59 | **67** |
| `peer-sites.py` manifest | 16 | **21** |
| `peer-sites-hook.py` | — | **38 cases, 8 entries** |
| hook, lines of bash | 127 | **37** |
| declared mutation total | 705 | **718** |
| non-commit hook cost | 69 ms | **16 ms** |

All 29 manifest entries across both files verified RED **via the case each names**, over controls
proved green first.
