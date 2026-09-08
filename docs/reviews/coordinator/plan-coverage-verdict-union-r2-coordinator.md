# Post-Plan Gate round 2 — coordinator half — backlog #91 coverage-verdict union

Scope: **round 1's own fixes**, because this project's recorded failure mode is a defect introduced
by the previous round's fix.

Partner half: [`../claude/plan-coverage-verdict-union-r2-claude.md`](../claude/plan-coverage-verdict-union-r2-claude.md)
— **NOT CONVERGED**, 0 Blocking, 3 High, 2 Medium, 2 Low.

**REVIEW GAP:** codex — still unavailable (round 1's models all returned HTTP 400 / timed out and the
wrapper recorded `gate_ran=false`); a second Claude adversarial half ran in its place per
`docs/plugins.md`. Re-attempt before merge if access returns.

⭐ **All three Highs were regressions introduced by round 1's fixes.** That is the pattern that
produced backlog #91 in the first place, arriving on schedule — and it is the argument for the round-2
scoping rule, not against it.

---

## r2 H1 — my H3 case asserted the WRONG SUBJECT. ACCEPTED, and fixed differently than asked.

The case read `ctx.compared` — an **input** to the sentence — while the defect is the sentence a
reader sees. The reviewer proved it: `evidence()`'s `if cmp is None:` weakened to `if not cmp:`
restored the defect end-to-end and the suite stayed **201/201**. My own "verification" of that fix was
therefore vacuous. Recorded shape: *assert the PROPERTY, not the mechanism*.

**The reviewer asked for a case asserting the rendered sentence. I did something stronger: I deleted
the state that made the two predicates differ.** `compared` is now only ever `None` or a NON-EMPTY
dict, so `cmp is None` and `not cmp` are equivalent on every reachable input and the reviewer's
mutation is **semantically dead** rather than merely guarded.

**MEASURED** (`scratchpad/probe_compared_states.py`), five fixtures:

| fixture | `compared` | `compare_requested` |
|---|---|---|
| no file tags, no `--compare` | None | False |
| no file tags, WITH `--compare` | None | True |
| unsafe tag (assembled then DROPPED), WITH `--compare` | None | True |
| real block, WITH `--compare` | dict[1] | True |
| real block, no `--compare` | None | False |

**No empty dict is reachable.** Removing a state beats guarding it — but it moves what must be
guarded, so **the INVARIANT now has its own case**. Verified by reviving `compared = {}`:
**203/207, red through FOUR cases**, including `a DROPPED block with --compare leaves 'compared'
None, never an empty dict: got {} want None`.

⚠ Consequence for the reviewer's mutation: it now survives, and that is **correct** — a surviving
equivalent mutation is not a coverage gap. Recorded here so a future round does not "fix" it by
reintroducing the state.

## r2 H2 — `{}` asserted a diff that never ran. ACCEPTED.

On a plan whose only block was assembled and then DROPPED, the durable block said *"DIFFED against
the delivered files"* with zero rows — a **permissive** false claim, which this project rates worse
than master's conservative one. One value, a meaning with an OR in it: exactly the shape
`check-sentinel-meanings.py` exists to catch, committed inside the change that is about a value
meaning two things.

**Fixed** with a third branch and a third honest sentence — *"--compare was given, but no block was
assembled"* — and `compare_requested` on `RunContext` so the two facts travel separately.
Red via its own case when the branch is collapsed: **204/207**.

## r2 H3 — `not muts` conflated three worlds. ACCEPTED.

`muts == []` means "none declared" **or** "the JSON did not parse" **or** "the tag had no block", and
only the first is honest. The r1 fix narrowed the hole to the *likelier* case, since an unparseable
block is what a typo produces. **Fixed** by branching on whether the declaration was readable.
Red via its own case: **205/207**, plus the presence twin at 204/207 when every early return is
treated as unreadable.

⚠ The reviewer flagged, correctly, that matching on problem STRINGS is itself a convention and the
stronger form is for `extract()` to return the fact. That is a wider change; this one is falsifiable
today. **Carried as residue, not claimed as closed.**

## Mediums

**M1 — three new behaviours, zero manifest entries.** Real. The fold's behaviours are guarded by
cases but not by mutations, so their guards are held only by the self-test count ratchet. Owed before
merge or explicitly deferred.

**M2 — the orphaned-anchor class has no cheap detector; only a full `--mutate .` sees it.** Confirmed
independently and at my own expense: the r1 H2 fix orphaned
`the plan-mode HONEST ZERO becomes a refusal (r3 B2 successor)`, `--self-test` stayed green at
201/201, and only the sweep caught it (`358 of 359`, NOT MEASURED, rc=1). Retargeted in `8afbf40f`.
**This is a genuine gap in the verification stack and belongs on the backlog.**

Round 1's M1 (`NotMeasured`'s integrity is a convention) and M2 (frozen dataclass, lists by
reference) remain unfixed and carried.

## Verdict

**NOT CONVERGED at round 2.** Three Highs, all regressions from round 1, all fixed and each falsified
over a green control (207/207). Counts 201 → **207**. Round 3 is required and must again be scoped to
this round's own fixes.

⚠ **Two non-converging rounds. `dev-process.md` fires Phase 6 at FOUR.** Not yet — but the trajectory
is the one that cost this project twelve rounds on blob addressing, and the honest read is that the
defect class here is *shifting* (r1: fail-open defaults; r2: sentinels with an OR in their meaning)
rather than repeating, which `review-method.md` treats as the healthier of the two shapes.
