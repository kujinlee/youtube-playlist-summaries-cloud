# Round 3 — coordinator's record: the thrashing call, and why no separate Phase 6 is owed

**Subject:** the bytecode-scrub property case in `scripts/check-rc-contract.py` and
`scripts/check-surface-recall.py` · branch `shard-mutation-sweep` · PR #366
**Reviewed trees:** `77316edc` (r2 fold), `8c1a207a` (r3 fold) · **Folded at:** `fa7a6d73`
**Round 3 halves:** `docs/reviews/claude/shard-mutation-sweep-r3-claude.md`,
`docs/reviews/codex/shard-mutation-sweep-r3-codex.md`
**Written:** 2026-10-06, by the coordinator, after folding.

This file exists because [`docs/review-method.md`](../../review-method.md) requires the thrashing
call to be recorded with its per-finding evidence. The review documents are **testimony** and are
not edited here.

---

## 1 · The surface condition is met

`docs/dev-process.md` arms an architecture review when **two consecutive rounds carry findings
caused by the previous round's own fix, in one component.**

| Round | Finding | Component | Caused by the previous round's fix? |
|---|---|---|---|
| r2 codex | `SUBPROCESS_ENV_KEYS` omits `PYTHONDONTWRITEBYTECODE` | the scrub allow-list | **Partly** — pre-existing; the reviewer's own word. The fold's completeness claim made it load-bearing |
| r3 claude | the r2 case asserts the constant's VALUE; nothing asserts the spawn READS it | the property **case** for that allow-list | **Yes** |
| r3 codex | the r3 case asserts an ABSENCE with no precondition — an import that never ran also leaves no cache | the **same** case | **Yes** (its own table says so) |

Two consecutive rounds, fix-induced findings, one component. **The surface condition holds.**

## 2 · But the surface condition is not the test

`review-method.md:198` is explicit, and `:212` records why it is written down rather than assumed —
applying the symptom list as a checklist produced a **false REDESIGN** in one reviewer and a true
one in the other, on the same document:

> **⚠ THE SYMPTOM LIST IS A PROMPT, NOT THE TEST. There is one test, and it is this:**
> ### Can a redesign remove it?

**Applying the single test, per finding:**

| Finding | Would a different shape dissolve it? | Verdict |
|---|---|---|
| r3 claude — asserts the constant, not the spawn | **Yes.** Taking the measurement *through the production spawn* removes the question entirely; there is no longer a constant whose readers must be trusted | **mechanism** |
| r3 codex — asserts an absence with no precondition | **Yes.** A conjunction carrying a positive witness dissolves it; "nothing happened" can no longer satisfy "nothing was written" | **mechanism** |

Both are mechanism defects. **The redesign is owed.**

⚠ **Neither is branch-coverage**, and the distinction is the one `:218` warns about: these are not
*"the rule doesn't say what happens in case X"* for an X the design merely governs. The rule itself
could not be satisfied by the instrument as shaped — the instrument measured a **proxy** for the
property and the proxy was satisfiable without the property.

## 3 · The call: the redesign was OWED and was DONE in the fold — there is no override to record

The remedy was applied **inside this fold** rather than deferred to a separate Phase 6 review,
because the redesign the test pointed at is local to one function and nameable:

> replace the **proxy** — *no `.pyc` file appeared* — with the **property** — *the import ran under
> the scrubbed production spawn, AND left no cache.*

⭐ **This is the same transformation `main-drivable-r10-coordinator.md` §3 records for PR #365's own
Blocking** — *"replace the proxy … with the property"* — reached independently, in a different
component, by a different reviewer. Two slices converging on one cure is evidence about the KIND of
fix, not a coincidence worth leaving unremarked.

**Why it is a kind change and not a third widening.** r2 → r3 widened the SCOPE of the same
assertion (constant → spawn) and was defeated by a new way for the assertion to be vacuous. r3 → r4
changes the assertion's SHAPE, from a bare negative to a conjunction with its own precondition:

    import never ran  -> []                 RED   (r3-codex's false pass)
    key absent        -> ["ran", "<pyc>"]   RED   (the r2 / r3 defect)
    correct           -> ["ran"]            GREEN

A negative proved by interception cannot terminate; a negative conjoined with its precondition can.
A probe that **cannot run** is now RED rather than green, which is this repository's standing rule
about CANNOT RUN mechanised instead of hoped for.

## 4 · Falsifiers — all four known attacks refuse, each via the case it names

Measured per file, at `fa7a6d73`:

| Falsifier | Origin | `check-rc-contract` | `check-surface-recall` |
|---|---|---|---|
| constant sever | r2 codex | RED 55/56 | RED 57/59 |
| call-site inline hand-copy | r3 claude | RED 55/56 | RED 58/59 |
| key removed **+** import of a missing module | r3 codex | RED 55/56 | RED 57/59 |
| import broken ALONE, key present | added in this fold | RED 55/56 | RED 58/59 |

The third row was **green** before this fold; it is the r3-codex false pass.

⚠ **Stated as verified against every falsifier known, NOT as proven complete.** Two previous
versions of this probe were also believed sufficient, and each was defeated by the next reviewer.
That history is the reason round 4's brief leads with a design verdict — *sound, salvageable, or
replace* — rather than asking for a fourth instance of the same class.

## 5 · What is NOT claimed here

- **No separate Phase 6 architecture review is owed**, for the reason in §3: the redesign the test
  named was local, was identified, and was applied. Had it required a different shape across more
  than one function, it would have been deferred and recorded as owed.
- **The deliverable was never in question.** All findings from r2 onward aimed at the instrument.
  The shipping change — the key in both allow-lists — has been unchanged since r2 and green in CI
  across all 8 shards at `fcc46c01` and `8c1a207a`.
- **Round 4's verdict is not pre-empted.** If it finds a third defect of this class, that refutes
  §3's claim that the redesign was sufficient, and the right response is a design review rather
  than a fourth fold. This record will then need a correction appended, not an edit.
