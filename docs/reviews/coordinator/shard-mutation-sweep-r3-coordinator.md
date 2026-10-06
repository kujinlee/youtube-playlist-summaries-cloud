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

---

# ⟳ CORRECTION, 2026-10-06 — §3 WAS REFUTED BY ROUND 4. Appended, not edited, per §5.

§5 of this record pre-registered the falsifier: *"if round 4 finds a third defect of this class,
that refutes §3's claim that the redesign was sufficient."* **It did.** Round 4's Claude half
(`docs/reviews/claude/shard-mutation-sweep-r4-claude.md`) exhibited a **third** unasserted
precondition and both of the entries that exist solely to carry r3's finding **survived**:

```text
with a `python3` shim on PATH that adds -B  (PATH is itself allow-listed)
  [m16+shim] check-rc-contract.py:    rc=0  56/56   ← MUTANT SURVIVES
  [m20+shim] check-surface-recall.py: rc=0  59/59   ← MUTANT SURVIVES
```

A second route reached the same end: swapping the key for `PYTHONPYCACHEPREFIX` in the allow-list,
with that variable set ambiently → 56/56 green.

## What §3 got wrong, precisely

§3 claimed the redesign (proxy → property) was the right KIND of fix and was sufficient. **The kind
was right and the ALTITUDE was wrong.** The probe still measured the filesystem, which is two
processes away from the thing being asserted, and a filesystem absence has preconditions that live
in CPython — the half we do not own. Each round asserted one more of them:

| Round | Preconditions asserted | Defeated by |
|---|---|---|
| r2 | none — asserted the constant's value | the call site not reading the constant |
| r3 | "the spawn ran" | the import not running |
| r3 fold (§3) | "the import ran" | **bytecode not being written anyway** — ambient `-B` |

A fourth row would have been a fourth widening. **The class was never going to close on the
filesystem**, which is what §3 could not see and round 4 could.

## The repair, and why it is not a fourth widening

The measurement moves UP one level: capture the env dict the production spawn hands
`subprocess.run`, and assert the key is in it. `subprocess.run` is replaced for the length of one
call and restored in a `finally`; the stand-in returns a well-formed envelope so the capture sits on
the SUCCESS route. Asserted at TWO distinct inputs, per `check-fixture-variation`'s rule.

⭐ **The reviewer's structural point, which is the durable lesson here:** `check-plan-code.py:3847`
has asserted exactly this property, for exactly this variable, in two lines, ever since the harness
gained `child_env`. The right-altitude instrument already existed in this repository. It was
unavailable to these two guards for one reason — **the scrub is an inline dict comprehension, not a
named producer, so there was nothing a two-line case could assert.** *Three rounds were downstream
of one missing abstraction.*

**Why `-B` and `PYTHONPYCACHEPREFIX` are now unreachable rather than defended:** the case computes a
dict comparison. It opens no file and starts no interpreter, so there is no precondition to forget.
That is the difference between guarding a boundary and moving it.

Measured on a mirrored copy of the tree, with a shim calling the interpreter by ABSOLUTE path:

| Attack | Before | After |
|---|---|---|
| call-site mutant + `-B` shim, `check-rc-contract` | survived 56/56 | **RED 55/56**, named case only |
| call-site mutant + ambient `PYTHONPYCACHEPREFIX` | survived | **RED 55/56**, named case only |
| call-site mutant + `-B` shim, `check-surface-recall` (#20, the unconfounded carrier) | survived 59/59 | **RED 58/59**, named case only |

## What is NOT taken, and why — stated so the next round need not re-derive it

The reviewer's design verdict was **REPLACE**, and its fuller form was to extract a shared
`scrub_env()` so the allow-list, the round-8 agreement case and the duplicated probe all collapse.
**That extraction was NOT done.** The right-altitude half of the verdict was taken in place.

Reasoning, offered to be refuted rather than asserted: the reviewer's second Medium was that the
*"a shared module would be heavier than the problem"* justification had a denominator that had moved
~6× (31 duplicated lines). Replacing the 31-line probe with a ~12-line capture **restores** that
justification rather than deferring it. Extraction would additionally mean manifest surgery and a
ratchet fall on a PR whose subject is sharding.

⚠ **Two findings therefore remain open and are NOT closed by this fold:**
- the duplication itself (now ~12 lines rather than 31) — a maintainability finding;
- the reviewer's Low 1, **pre-existing and not caused by any fold**: the bytecode this suite actually
  writes to its own tree (measured: 2 `.pyc`) comes from three in-process `exec_module` sibling
  imports — a route **no allow-list governs and no case observes**, because it never crosses a
  process boundary at all.

⚠ **And §19's confounding qualification still stands, unaltered:** `check-surface-recall.json` #19
fires the round-8 agreement case independently, so it would report `caught` even were the bytecode
property vacuous. #20 is that file's only unconfounded carrier. The extraction would have removed
the confounding by removing the agreement case; the in-place repair does not.
## ✅ r4 Low 1 BOUNDED, 2026-10-06 — the exec_module route cannot reproduce the defect this PR removes

The r4 Claude half found that this suite writes bytecode to its own tree through three in-process
`exec_module` sibling imports (`check-surface-recall.py:333, :565, :626`) — a route no allow-list
governs, because it never crosses a process boundary. Measured, on a mirrored copy:

    check-surface-recall --self-test, NO harness env   -> 2 .pyc
                                                          check-ratchet-contract.cpython-314.pyc
                                                          check-rc-contract.cpython-314.pyc
    check-surface-recall --self-test, HARNESS env      -> 0 .pyc
    check-rc-contract    --self-test, either way       -> 0 .pyc   (route is in ONE file, not the family)

⭐ **Why it is correctly Low and not a deliverable concern wearing an instrument label.**
`exec_module` runs IN-PROCESS, so it honours `PYTHONDONTWRITEBYTECODE` from the process's own
environment — and `child_env` sets precisely that for every suite the harness spawns. The route is
therefore already closed in the ONLY context where it could matter.

The original defect required a **mutant** `.pyc` outliving the restore of its own source, which
requires the mutation harness; the harness suppresses the write (this measurement) and refuses the
inbound copy (`stage_tree(..., ignore=shutil.ignore_patterns("__pycache__"))`). Both halves closed.

⚠ **The bound, stated rather than implied:** outside the harness — an interactive run, or CI's
`verify` step on a fresh checkout — the two caches ARE written, and nothing governs them. They are
current for the source at hand, so they are harmless there; the claim is specifically that they
cannot carry a MUTANT across a restore.

## ✅ ROUND 4 CLOSED — quiet round 1 of the 2 the method requires

`docs/reviews/codex/shard-mutation-sweep-r4-codex.md` found **no Blocking, High, Medium or Low**
against the fold, and owed no proposed fix. It ran shard **5/8 AND 8/8** — both slices carrying this
component — at 150 killed / 150 attributed / 0 survivors each, and independently reproduced the
`exec_module` measurement above (unset → 2 `.pyc`, `env=1` → 0), concluding it is "not a
mutation-sweep poison route".

It also sustained the reasoning this record offered for refutation in §"What is NOT taken":
> *"extraction is still attractive, but I do not think it is owed by this fold … the coordinator's
> '31-line filesystem probe denominator collapsed' argument holds after this fold. Extraction would
> be a design cleanup, not a convergence blocker."*

**Its verdict is NOT CONVERGED, and that is the rule working rather than a defect:**
`review-method.md:110` stops only on **two consecutive** rounds with no Blocking, no High, no
deliverable finding and no non-trivial fixes. This is the first such round.

⚠ **Round 5 is therefore a CONFIRMATION round and must be aimed differently**, for a reason this
record should state so the next session does not spend a fifth pass on a settled component:

> **The actual subject of PR #366 — the sharding — has had ONE round of review.** r1 reviewed it;
> r2, r3 and r4 were entirely about a bytecode race discovered while fixing the CI red. The half
> that SHIPS (`--shard I/N`, the 8-way matrix, `mutation-sweep-complete`) has had far less
> adversarial attention than the instrument that measures it.

Specific questions round 5 owes, beyond re-reading the partition proof: does
`mutation-sweep-complete` go red when a shard is **cancelled or skipped** rather than failed — a
*cancelled* job being exactly how PR #365's sweep died — and does `fail-fast: false` still let the
remaining shards report? Plus Q4(b), tree identity (`:114`): **no round has yet reviewed the tree
that would merge**, because each reviewed an earlier commit.
