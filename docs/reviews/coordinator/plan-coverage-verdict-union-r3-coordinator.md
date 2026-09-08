# Post-Plan Gate round 3 — coordinator half — backlog #91 coverage-verdict union

Scope: **round 2's own fixes** — the `compared`-state deletion (r2 H1), the third subject sentence
(r2 H2), the `mut_unreadable` string set (r2 H3), and the three manifest entries committed as
`ea2566cc`.

Partner half: [`../claude/plan-coverage-verdict-union-r3-claude.md`](../claude/plan-coverage-verdict-union-r3-claude.md)
— **NOT CONVERGED**, 0 Blocking, 4 High, 2 Medium, 1 Low.

**REVIEW GAP:** codex — unavailable for the third consecutive round. Round 1's models returned HTTP
400, `gpt-5.5` timed out, and the wrapper recorded `gate_ran=false` each time; `codex-frontier-model.py`
still resolves `gpt-5.6-sol`, which CLI 0.142.5 rejects as requiring a newer client. One further
attempt was dispatched for this round before merge, per `docs/plugins.md`; a Claude adversarial half
ran in its place and this coordinator half is the second. **Treat the Codex-specific pass as NOT RUN,
not as clean.**

⭐ **Three of the four Highs were regressions introduced by round 2's own fixes** — the third
consecutive round of that shape. See *Verdict* for what that costs and what it does not.

---

## r3 H1 — `mut_unreadable` guarded ONE of two returns. ACCEPTED, and it is the finding that matters most.

The reviewer is right and the demonstration is exact: r2's predicate lived inside `if not files:`, so
the return sixty lines below — **the one any plan with code takes** — reached `declared = len(muts)`,
which is `0` for a lost declaration exactly as it is for a plan that declared none. Clause 2 of the
`Measured` contract then passes, and the durable block prints `mutations declared and run: 0, caught 0`
over a plan whose text declares one.

This is r1 H2's sentence for the **third** time (*a number the producer invented rather than one it
measured*) and this project's recorded *instance-not-class* shape, committed inside the change whose
entire purpose is to delete that class.

**Fixed at both returns**, and not by copying the predicate: the fact is produced once, by the parser,
and read at every exit. The main-path refusal is raised **into** the existing `VerdictContractError`
handler rather than branched around it, so there remains exactly one `Measured` construction and one
fallback on that path.

## r3 H2 — the two matched strings were not the complete set. ACCEPTED, and the fix is the one I deferred in r2.

I flagged the string-matching as a convention against my own r2 fix and deferred the stronger form as
"a wider change". The reviewer found the instances that make the deferral wrong: **three** routes reach
`muts == []` from a declaration that was never read, producing neither string —

* a `FILE_TAG` silently clearing `want_mut` (three of the four clobber directions report themselves;
  this one did not);
* `{}` and `""` — valid JSON that `muts.extend()` accepts and that yields nothing, with an **empty
  problems list**, which is the shape no string set could ever have matched.

**Fixed as the reviewer specified:** `extract()` returns `mut_readable` as a fifth value. Searching for
what else the class was true of found two routes the review did not name — a **second mutations tag**
clobbering the first, and `[1, 2]`, a list whose elements are not entry objects and whose "names" every
downstream `mut.get(...)` would have read off a `str`. Both are now problems with cases.

⚠ **Why a fifth positional value and not a `tally` key.** A caller that has not been updated raises
`ValueError` on the unpack — nineteen call sites failed loudly and were fixed. A dict key would have
been free to add and silent to miss: the dict-shaped fail-open that `coverage_verdict.py` exists to
delete, reintroduced one function away from it.

## r3 H3 — the census contradicted the subject sentence. ACCEPTED.

`tally['tagged']` counted python fences the parser tagged; the subject sentence speaks for what
survived into `files`. On a block that is tagged and then dropped by the unsafe-tag branch those are
different numbers, and one durable artifact printed `1 assembled` four lines above
`no block was assembled`. The reviewer's regression table is the sharp part: master and r1 were each
wrong in one direction and **self-consistent**; r2's new sentence was the first to make the block
disagree with itself, on r2's own motivating fixture.

**Fixed by giving the word one owner.** The count moves with the file at the drop site, the tally key
is renamed `assembled` because that is now what it means, and the drop is **stated** rather than
deducted invisibly — `(0 assembled, 1 tagged then DROPPED, 0 illustrative)`. An exclusion nobody can
see is the hiding vector this same renderer already refuses for illustrative blocks.

Per the reviewer's explicit instruction, **both lines are asserted in one case**, with a presence twin
asserting that an assembled block is counted as assembled and carries no `DROPPED` clause.

## r3 H4 — `verify_evidence`'s mode keyed off the RESULT. ACCEPTED, and it is the cheapest and the most damning.

Three lines. `mode` is a statement about the **invocation**, so it reads the flag. What earns the
finding is not the defect but its provenance: r1's `{}` had incidentally corrected this line, **r2's
own review recorded it as checked-and-clean**, and deleting the `{}` state reverted the correction with
nothing to fail — because the note was prose. Both directions are now cased.

## Mediums and the Low

**M1 — the new anchor sits on the line H1's fix rewrites. ACCEPTED, and this is the first time on this
branch the orphaning was callable BEFORE the fix.** My `ea2566cc` note said the anchors avoided "the
branch expression under active revision"; the reviewer's verdict — *"true, and it is the wrong axis"* —
is correct. The predicate assignment I chose instead was itself deleted by this fold.

Two entries were orphaned and are **retargeted, not adjusted**: `an UNREADABLE mutations declaration…`
(the line is gone entirely) and `the plan-mode HONEST ZERO becomes a refusal`, for the **fourth** time
on this branch. The lesson I am willing to write down is narrower than "pick a better anchor": *there
is no anchor that a rewrite of its own subject cannot break*, so the **sweep is the instrument** and
the anchor choice is a cost reduction, not a guard. That gap belongs on the backlog and is named in the
plan's residue.

**M2 — zero of 92 plans exercise plan mode's file path. ACCEPTED as stated, and it bounds the merge
claim, not the findings.** The honest framing is *"the durable artifact would lie if this mode were
used"*, not *"it is lying today"*. It does not dissolve H1–H4: they are defects in the delivered
producer, reachable from the command line, and r2's accepted Highs had identical standing. Applying it
retroactively would downgrade r2 H3 too, which the reviewer says itself.

**L1 — `null` / a bare number crashed with an unhandled `TypeError`. FIXED, in the same edit as H2**,
exactly as the reviewer predicted: validating the parsed value at the point of parsing is where the
fact comes from, so the crash and the silent acceptance had one cause.

## What the reviewer checked and cleared, recorded so round 4 does not re-spend it

r2 H1's central claim **survives an attack aimed at it**: no empty `compared` dict is reachable, both
assignment sites are accounted for, and the reviewer's r2 mutation is genuinely *equivalent code*
rather than unguarded. The invariant case is **not** vacuous — its presence twin sits immediately
below it. `compare_requested` is honest in both directions. ⛔ **Do not "fix" any of this by
reintroducing `{}`.**

## What was EXECUTED for this fold

Controls first, and the tree was staged with the harness's own `stage_tree` so it carried
`node_modules/typescript` — a scripts-only copy gave a red control three separate times on 2026-09-08,
and every verdict under one of those is an artefact.

| run | result |
|---|---|
| `check-plan-code.py --self-test` | **223/223**, rc 0 (207 → 223) |
| `coverage_verdict.py --self-test` | **22/22**, rc 0 |
| `stage_tree(REPO, dest)` | `problems: NONE — tree complete` |
| `run_suite(dest, …)` control | rc 0, `223/223 passed`, `control_is_green: True` |
| the **10 new or retargeted** manifest entries, one at a time | **10/10** `caught=True measured=True survivors=[]`, each red via the case it NAMES |
| static anchor sweep, all 32 manifests | **375 edits, 0 orphaned, 0 ambiguous** |
| `check-selftest-counts` · `check-docs` · `check-anchors` · `check-dashboard-entry` · `check-ratchet-contract` | all rc 0 |

`EXPECTED_MUTATIONS["scripts/check-plan-code.py"]` 33 → **41**; declared sum 362 → **370**.

⚠ **One of my own mutations was wrong before it was right, and it is worth recording.** The first
edit written for H2's route (a) re-appended the same message and left the flag standing — a **no-op
dressed as a mutation**. It reported `SURVIVED`, and the honest reading was *the mutation is empty*,
not *the code is unguarded*. It is the same class as the mutations this project has already recorded
as unfalsifiable, arriving in the very commit that adds eight of them, and only running them caught it.

**NOT RUN locally:** the full `--mutate .`. CI runs it on every push, the ten changed entries were
executed individually above over a proven-green control, and the static sweep covers the orphan class
across all 32 manifests. **If CI's sweep goes red, treat this fold as NOT VERIFIED.**

## Verdict

**NOT CONVERGED at round 3.** Four Highs, three of them regressions from round 2, all fixed and each
falsified over a green control. Counts 207 → **223**; mutations 362 → **370**.

⛔ **THREE non-converging rounds. `dev-process.md` fires Phase 6 at FOUR — and the trigger is read off
the CAUSE, not the count.** Both readings are on the table and I am not going to pretend they agree:

* *Shifting* (healthier): r1 fail-open **defaults** → r2 **sentinels with an OR** → r3 **one fix
  covering one of two paths**, and **two narrators of one run with no shared derivation**.
* *Repeating* (the twelve-round blob-addressing shape): three consecutive rounds whose findings are
  mostly the previous round's own fixes.

The reviewer names the sharper version, and I accept it: `evidence()` and `verify_evidence()` narrate
the same run to the same reader from different variables, and **every round so far has fixed one
narrator and left the other disagreeing**. H3 and H4 are that, twice, in one round.

**So the round-4 rule is set in advance rather than after the fact: if round 4 produces another
self-contradicting artifact, the finding is not the sentence — it is that the evidence block has no
single producer for "what was this run about", and Phase 6 convenes instead of a fifth fold.** Round 4
must again be scoped to this round's own fixes, and must attack `mut_readable`'s completeness first.
