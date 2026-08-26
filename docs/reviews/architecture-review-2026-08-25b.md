# Architecture Review #2 — 2026-08-25 (evening)

> **Anchor:** `stable-blob-addressing` — **ADR:** 0006, 0007, 0011
> **Goal:** A blob's address stops moving when a title or a serial number changes. This review asks whether **the instrument M4 built to verify itself** is the right shape — not whether its statements are correct.

**Trigger:** `docs/dev-process.md` Phase 6, second arming condition — four adversarial rounds without
convergence. It has now fired **twice**. The first firing produced
[`architecture-review-2026-08-25.md`](architecture-review-2026-08-25.md) (17:54) on the v5.1 plan's
five rounds. **This is the second**, on the v2 plan's rounds 1-7, and the user asked for it explicitly
after round 7.

**Subject:** the M4 gate instrument — `scripts/m4_catalog.py`, `check-live-schema.py`,
`gen-m4-manifest.py`, `check-catalog-coverage.py`, `mutate-live-schema-check.sh` — plus the privilege
model in `.../schema/{01,03,04}.sql`.

⚠ **This subject is what Phase 6 #1's finding 3 created.** That finding said *"M4 needs one gate that
introspects `pg_class`/`information_schema` on the live stack."* It was right that the axis was
missing. This review is about the shape the answer took.

**Method, and an honest note on it.** A subagent was dispatched to do this review and **failed twice
to deliver its output** — the first delivery vanished, the second returned an empty transcript. Rather
than wait a third time I wrote this myself, which is what `dev-process.md` requires of the coordinator
anyway (*"agent output is a lead, not a finding — verify every load-bearing claim by hand"*). Every
number below is from a command run in this session. ADRs are not re-litigated.

---

## The one-paragraph answer

**M4 built a FINGERPRINT COMPARATOR — "does the deployed catalog match a derived manifest?" — when the
milestone's actual risk is BEHAVIOURAL: "does the deployed schema still refuse what it promises to
refuse?" A fingerprint carries two obligations an assertion does not: it must ENUMERATE what to
compare, and it must be COMPARABLE ACROSS ENVIRONMENTS. Every Blocking and High finding in rounds 4
through 7 — nine of them — lives in one of those two obligations.** And the behavioural instrument
already exists: `05_assert.sql` is 2,239 lines carrying **104 `raise exception`** assertions across 60
blocks, covering exactly the properties the digest has spent four rounds learning to approximate. It
has **zero `@RE-RUNNABLE` markers**, so `run-schema-assertions.sh` is a permanent fail-closed CANNOT
RUN. **The milestone's most expensive instrument was built from scratch while its cheapest one sat
unwired.**

---

## Finding 1 — 🔴 Blocking. Nine findings across four rounds are one architectural choice: fingerprint over assertion

**The measurement that frames everything:**

```
05_assert.sql            2,239 lines · 60 do-blocks · 104 raise exception · 0 @RE-RUNNABLE markers
gate instrument          2,002 lines (m4_catalog + check-live-schema + gen-manifest
                                      + check-catalog-coverage + mutate harness)
the schema it guards     1,878 lines
v2 review documents      5,548 lines
```

And what `05_assert.sql` already asserts, by keyword count in that file:

```
tenant / cross-tenant / owner_id   39      append-only   18
anon                               17      rls / row level level security   10
truncate                            3      security definer                  2
```

Now place each round's headline finding against the two ways of asking the question:

| Round | Finding | As a FINGERPRINT it needs… | As an ASSERTION it is… |
|---|---|---|---|
| r4 B1 | a DISABLED trigger passes | `tgenabled` in the digest | *"an update to a frozen row must raise"* — already written |
| r5 B2 | `disable row level security` passes | `relrowsecurity`, `relforcerowsecurity` | *"another owner sees 0 rows"* — already written (39 hits) |
| r6 B1 | ACL text can never match production | an environment-invariance crisis | assertions never compare two environments |
| r6 B2 | `attacl` missing | a column + a written reason | *"anon cannot insert"* — already written |
| r6 (codex) | `proisstrict` missing | a column + a written reason | *"the guard raises on this input"* |
| r7 B2 | `TRUNCATE` missing | a column + a written reason | `set role anon; truncate …` **must raise** — one line |
| r7 B1 | `proargdefaults` missing | a column + a written reason | *"an omitted argument still writes NULL"* |
| r7 (codex) | `service_role` EXECUTE invisible | a grantee-list decision | *"the RPC path works as service_role"* |
| r7 H1 | an unlisted grantee is invisible | unsolvable inside a portable fingerprint | assertions do not enumerate grantees |

**Every cell in the third column is an enumeration problem or a comparability problem. Every cell in
the fourth is one executable statement that needs neither.**

This is not hindsight. `m4_catalog.py`'s own docstring states the rule it kept failing to satisfy —
*"every catalog column that decides whether a rule EXECUTES belongs in the digest"* — which is a
definition of behaviour written as a specification for a fingerprint. Four rounds were spent trying to
make a structural comparator answer a behavioural question, and each round's answer was correct and
insufficient in the same way.

**⚠ The fingerprint is not worthless, and this is not "delete it".** It answers one question nothing
else can: *did the migration APPLY — are all 161 objects there at all?* That was Phase 6 #1's finding
3 and it stands. What it should not have been asked to answer is *are the rules still in force*, and
every round since r4 has been an attempt to make it do that.

**Direction — the fork, and the choice is the user's:**

- **(a) Split the instrument by question.** The manifest keeps STRUCTURE — object exists, definition
  matches (`pg_get_*def`, `prosrc`, enum labels) — and stops carrying enforcement flags and
  privileges entirely. BEHAVIOUR moves to `05_assert.sql`, which means **doing Task 8 now instead of
  last**: add `@RE-RUNNABLE` markers, and add the ~6 assertions rounds 4-7 taught us to want
  (`anon` cannot TRUNCATE; RLS is in force for a second owner; the guard raises when disabled-shaped;
  the RPC path works as `service_role`). Per-environment privilege goes to `check-anon-exposure.py`,
  which is already environment-aware and whose `MONEY_TABLES` must gain the five M4 tables.
  **Cost:** Task 8 moves early; the digest loses ~40% of its content; roughly six new assertions.
  **Buys:** the enumeration obligation disappears, the comparability obligation disappears, and both
  of the recurring defect classes go with them.
- **(b) Keep one whole-catalog fingerprint and continue widening it.** **Cost:** the next round finds
  the next column. Four rounds of evidence say the supply is not exhausted; `pg_proc` alone offers 30
  columns and the digest reads 11.

**I would take (a).** It is the only option that subtracts, and Phase 6 #1's own successful direction
was also a subtraction (option (a): corrections stay per-playlist).

---

## Finding 2 — 🟠 High. Environment-invariance is a self-inflicted obligation, and it caused the two worst findings

`m4_catalog.py:109-149` documents at length why privileges are digested as *effective access* rather
than ACL text: production's default ACL names `claude_ro`, a role no container has, so raw ACLs can
never match. That reasoning is correct. **But it is only necessary because a fingerprint must be
comparable across environments at all.**

Measured, read-only, on production tonight:

```
defacl|public|r|{postgres=arwdDxtm, anon=arwdDxtm, authenticated=arwdDxtm,
                 service_role=arwdDxtm, claude_ro=r}
local roles: anon, authenticated, service_role          (no claude_ro)
```

The consequences, all from this one obligation:

- **r6 B1** — the gate would have argued for rolling back a *successful* production migration.
- **r7 H1** — a grant to any role outside a hand-chosen four-name tuple is structurally invisible, and
  production really does have a fifth.
- **r7 codex B1** — `service_role` was excluded from the function grantees *to dodge the environment
  difference*, which blinded the digest to the one EXPLICIT grant the spec makes
  (`04_artifacts.sql:1232`). Removing it is a production write outage the gate exits 0 over.

**An assertion has no such obligation.** *"`anon` cannot TRUNCATE `video_artifacts`"* is independently
true or false in each environment; it needs no baseline, no manifest, and no grantee list.

**Direction.** Fold into finding 1(a): structure is portable and belongs in the manifest; privilege is
environmental and belongs in the per-environment ratchet. ⚠ `check-anon-exposure.py:265` hard-codes
database `postgres`, so it cannot be pointed at a scratch database and its `--local` arm cannot be
mutation-tested — that must be fixed if it is to carry this weight.

---

## Finding 3 — 🟠 High. A human-audited list of exclusion REASONS cannot bear the weight put on it

`check-catalog-coverage.py` was round 6's answer to the enumeration problem: enumerate every catalog
column, and require each to be digested **or excluded with a written reason**. The design is right —
it converts *"did I remember?"* into *"is this reason true?"*, and a false reason is at least
auditable where a silent omission is not.

**Then four of the reasons written under it turned out to be false**, all by the same author, the same
day, in the file the script was written to protect:

| Reason | Reality (measured) |
|---|---|
| TRUNCATE "already covered by `check-anon-exposure.py`" | `MONEY_TABLES` holds no M4 table; `anon` TRUNCATEs to 0 rows, gate exit 0 |
| a default's value "changes the identity arguments" | identity args byte-identical; `record_artifact` has 7 defaults in 13 params |
| `attmissingval` "covered by `pg_get_expr`" | it is not |
| `indisreplident` "cannot admit or reject a write" | with a publication it refuses UPDATE and DELETE |

The script's own docstring predicted this exactly: *"a wrong reason here is a real defect that this
script will happily report as green."*

**The architectural point is not that I wrote bad reasons.** It is that the mechanism's load-bearing
element is a paragraph of prose per column, ~15 of them, with no falsifier — in a repo whose own
process rule is *"state the observation that would make it FAIL"* (`CLAUDE.md`). **Every other gate
here is a script; this one is an essay with a test harness around its index.** A 27% error rate on
first authorship is the measurement, and there is no reason to expect the next 15 to be better.

**Direction.** Under finding 1(a) most of this dissolves, because a much smaller set of columns needs
excluding. For what remains: **a reason that claims coverage elsewhere must NAME the check and that
check must be asserted to cover the subject** — e.g. the TRUNCATE reason should have been mechanically
false until `MONEY_TABLES` contained the M4 tables. That is a script, and it is the only class of
reason that has actually been wrong so far (2 of the 4 claimed coverage that did not exist).

---

## Finding 4 — 🟡 Medium. The instrument is disproportionate, and the reason is visible in the numbers

```
gate instrument   2,002 lines        the schema it guards    1,878 lines
v2 review docs    5,548 lines        production impact       ZERO — 0027 does not exist
                                     application callers     ZERO
```

`record_artifact` has **no non-test caller anywhere in `lib/`, `worker/` or `app/`** — verified by
grep. The plan says so itself: *"No application caller yet — the schema lands inert."*

So the milestone has produced more verification machinery than schema, and more review prose than
both, for a change that currently cannot affect a user. **This is not an argument that the work was
wasted** — the gate found real defects, and the `workspaces` anon-write hole it surfaced would have
shipped to production. It is an argument that the *ratio* is a symptom of finding 1: a fingerprint
needs a manifest, a generator, a coverage ratchet, a mutation harness and a baseline; an assertion
needs a `raise exception`.

**Direction.** Under 1(a) roughly 800 of those 2,002 lines stop being needed.

---

## Finding 5 — 🟡 Medium. The `service_role` design question DISSOLVES at M4, and reappears at M5

Round 7 asked whether the write path is RPC-only, because `service_role` holds INSERT on
`video_artifacts` but cannot use it (`art_slot_kind` calls `slot_kind()`, executable by nobody) in a
container — while production's default ACL makes the same INSERT succeed.

**It has no consumer.** Zero callers, schema inert. So at M4 this is latent, not live, and it is not a
reason to hold the milestone.

**But it is a genuine trap for M5**, whose whole content is moving every writer onto generations. The
same grant set means different things in the two environments, so a writer developed against the
container will behave differently in production — the exact shape of r6 B1, one layer up.

**Direction.** Record it as a decision now, while the answer is cheap: **the write path is
`record_artifact` only, and the direct DML grants to `service_role` are removed** (they are unusable
in the container and unintended in production), **or** `slot_kind` gets an explicit grant and direct
DML is supported in both. ⚠ **Do not leave it environment-dependent.** This belongs in an ADR, not in
a gate.

---

## Finding 6 — what we decided this milestone that isn't written down

Phase 6 #1's finding 4 named three; two are now recorded (ADR-0011; the symlink note). These are new:

1. **Revoke-before-grant is now a schema-wide rule** — every M4 relation revokes from
   `public, anon, authenticated, service_role` before granting, so the resulting privileges are a
   property of the file rather than of the cluster. This is a real, durable policy about a security
   boundary and it exists only in a code comment and a commit message. **ADR material**, and it
   generalises past M4: it is the fix for `anon-execute-is-the-default-not-a-decision`.
2. **The function revokes were NOT extended with the relation ones** — measured. So the rule in (1)
   is half-applied, and nothing states that it is a rule at all.
3. **The dual-review gate has a new failure mode** — a review agent's output can be destroyed by the
   harness that captures it (measured tonight, twice: `codex-review.py` overwrote a real review with
   a summary of itself; a subagent delivered nothing at all). The wrapper is fixed and self-tested;
   **the general rule is not written anywhere: a task reporting "completed" is not evidence its
   deliverable exists.**

---

## What I checked and did NOT find — recorded so round 8 does not re-pay for it

| Hypothesis | Outcome |
|---|---|
| The r6 `service_role` revoke breaks the application | **REFUTED by execution** (r7 claude, re-verified). All six live-table writes succeed as `service_role`; no sequences exist; trigger firing does not check EXECUTE; the `workspaces` revoke is load-bearing |
| The live-catalog gate was the wrong idea (Phase 6 #1 finding 3) | **REFUTED.** It is the only instrument that can answer *did the migration apply*. The defect is what it was subsequently asked to also answer |
| ADR-0006/0007/0011 need revisiting | **NOT RE-LITIGATED, and no gap found.** ADR-0011 dissolved the r1-r5 series and nothing in rounds 5-7 touches it |
| The mutation harness is decorative | **REFUTED.** 21/21, and mutation 19 (production-shaped) is what proved r6 B1's fix |
| `check-catalog-coverage.py` should be deleted | **NOT SUPPORTED.** Its enumeration half is sound and found six unclassified columns on first run. Only the reason half is over-loaded |

**Still NOT VERIFIED and must not be repeated as fact:** `db push --linked`'s one-transaction property
(unchanged since Phase 6 #1); whether production's post-M4 ACL matches a prod-shaped simulation
(unknowable until M4-β, because `claude_ro` cannot be created locally).

---

## Disposition

**M4 proceeds, with the instrument re-scoped. It does not proceed as-is.**

Order:

1. **Settle finding 1's (a)-or-(b) with the user.** Everything else depends on it.
2. Fix the two money-path round-7 findings regardless of that choice, because both are live under
   either shape: **TRUNCATE** and **`proargdefaults`**.
3. Record findings 5 and 6(1) as ADRs *before* writing more gate code.
4. Then the remaining round-7 fixes, sized to the chosen shape.

⚠ **Phase 6 has now fired twice and produced a subtraction both times.** #1 removed `corrections` from
workspace scope; #2 proposes removing behaviour from the fingerprint. If a third firing is needed, the
question to ask first is not *"what is wrong with the instrument"* but *"what is this instrument being
asked to prove that something else already proves."*

⛔ Merging is a human gate. Applying M4-β to production is a second one. `0027` still does not exist.
