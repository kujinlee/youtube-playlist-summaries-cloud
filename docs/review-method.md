# Review Method

How adversarial review is run here, and the classification passes that go between rounds.

**Read this when a review round is about to start**, not at session start — that is why it is not in
`docs/dev-process.md`. The spine says *when* a review gate applies; this says *how* to run one.

> **Why it is a separate file (2026-08-08).** These sections grew to ~190 lines — a third of the
> process document — almost entirely in the two days after round 6. Every addition was justified by a
> measured defect, and the aggregate was unreadable, which is the *"individually thoughtful, fail as
> a set"* verdict these very reviews keep producing, applied to their own documentation.

---

## Two rules for PREMISES, not findings (added 2026-08-08)

Both were bought with a full review round. The existing discipline — *a finding you MEASURED beats
one you reasoned about* — was applied to findings and never to the premises a design rests on.

**1. Quote the code you rely on; do not characterise it.**
A design decision that depends on how existing code behaves must paste the relevant lines, with a
`file:line`. Measured cost of not doing it: a spec comment asserted *"worker_id is stable config"*,
`worker/main.ts:69` says
`` `${os.hostname()}-${process.pid}-${randomUUID().slice(0, 8)}` ``, and an entire ownership
mechanism was built on the false half. Quoting forces a read; characterising lets you write from
memory. Where a premise genuinely cannot be verified, label it **unverified** in the same sentence —
what must never happen is a premise sitting in a table beside measured facts in the same voice.

**2. Ask "what caller reaches this state?" of every measured defect.**
A rolled-back probe can construct any state you can type, including states no caller can reach.
Round 8 measured a doubly-lost worker being refused and graded it Blocking; two rounds then designed
against it; round 10 established the state cannot occur. *"Is this refused?"* and *"can a caller BE
here?"* are different questions, and only the second decides whether a fix is needed.

> A defect with no reachable caller is a fact about the schema's expressiveness, not about the
> system. It may still be worth a guard — but it is not worth a mechanism.

## The stop condition: when to stop fixing and start redesigning (added 2026-08-09)

Adversarial review answers *"is this correct?"* — a **local** question, and a local question can
always be answered *yes* by patching. So a wrong shape never fails a round; it emits a stream of
defects that get fixed, and **each fix makes the gates greener**. The process does not merely
tolerate patching a bad design — it rewards it.

> **If a component produces findings caused by the PREVIOUS round's fixes in two consecutive rounds,
> it escalates from FIX to REDESIGN, and the next round is a design review — not another defect hunt.**

**Two, not three.** The stable-blob-addressing reservation hit it at round 9 and ran to round 12
anyway; two would have cost four rounds instead of six.

**The evidence was already being collected and no rule acted on it.** The standing shape list tracks
*"a fix that moved or reintroduced a defect"* — counted to nine, then ten, then eleven across rounds
8–12, carried forward as **trivia in a prompt** because nothing said what to do when the number went
up. The fix is not a new measurement. It is permission for the existing one to conclude something.

**What a design review asks instead:**

1. **What already serves this concern?** — answered with a `file:line`, not a characterisation. The
   reservation's 2800-line spec never mentions `jobs` once, which already had exclusivity,
   idempotency, leases and a durable money guard.
2. **Which coordination pattern is this?** — append-only-plus-merge, mutual exclusion, or idempotency
   key. A design holding two of them cannot be repaired locally: that fence had to be PERMISSIVE so a
   reclaimed writer could still record paid work and STRICT so a stranger could not complete a
   generation. Five successive credentials failed on that contradiction.
3. **Who are the writers, and what identity does each carry?** — if two writer classes cannot present
   the same credential, it is a broker or merge problem and a lock will never converge on it. One
   four-minute read (`sync-run.ts:380-394` — sync *replicates*, it does not produce) would have ended
   the credential search on day one.

**Convergence is not enough on its own.** *"No new Blocking or High"* is a statement about the
REVIEWERS, not the design. A locally-repairable design passes it forever.
## Premise tags, and the asymmetry they exist to fix (added 2026-08-08)

**The diagnosis, which is sharper than "my instruments only look at the schema":** the validation
stack was **asymmetric**. Heavy automated verification on the TARGET layer (122 assertions, 57
mutations, guard coverage) and *nothing at all* on the ASSUMPTIONS layer — the external runtime code
the design rests on. That asymmetry manufactures false confidence: a green 57/57 feels like maximum
rigour while the whole premise sits in one unread line of another file.

So every foundational statement in a spec, review brief or ADR carries a tag:

| Tag | Means |
|---|---|
| `[VERIFIED: path/to/file:line]` | read from the CURRENT head, this round |
| `[ASSUMPTION]` | believed, not read this round |

**A safety fence, credential, or invariant may not be designed on an `[ASSUMPTION]`.** Upgrade it to
`[VERIFIED]` first, or design for both branches. A tag that was `[VERIFIED]` three rounds ago is an
`[ASSUMPTION]` today — the point is not that someone once checked, it is that someone checked *this*
round.

**And when a fence depends on caller behaviour, write a CONTRACT TEST at the runtime boundary.**
Prose in a design doc is a rule that depends on remembering, which is the failure mode this whole
document exists to remove. See `tests/lib/blob-addressing-caller-contract.test.ts`: it asserts the
properties `…-stable-blob-addressing-design.md` §12b relies on, lives in the CI-covered suite, and is
itself mutation-checked so it cannot pass vacuously. A future refactor that adds auto-reconnect or
job resumption then fails *there*, instead of silently invalidating a schema nobody thought to
re-read.

## Adversarial Review

Dispatch Codex (`codex:rescue`) with an explicit adversarial mandate at every phase.
- **Spec:** architectural gaps, underspecified behaviour, security risks, contradictions, edge cases
- **Plan:** missing tasks, wrong order, underspecified acceptance criteria, implementation risks
- **Code:** per-task (Claude + Codex independently). Both must complete before marking a task done.

Address all High/P1 findings before showing the user. Present Medium/P2 for a decision.

### Iterative Re-Review (big / critical changes) — required

One review round is not the gate; **convergence** is. After addressing a round's Blocking/High findings, **re-run the full dual adversarial review (Codex + Claude) on the *revised* artifact**, and repeat until a round reaches **diminishing returns**. Fixes routinely introduce new defects or expose deeper ones that the first pass could not see — a single round gives false confidence.

**When this is required** (any one triggers it):
- Schema / identity / idempotency changes; concurrency, leasing, or locking; auth / RLS / multi-tenant isolation; money-spending or irreversible paths.
- Refactors that touch already-merged, shared code (e.g. a function used by both local and cloud).
- **Any round that returned a Blocking finding, or whose fixes were non-trivial** (more than a reworded line). A Blocking fix is itself a new, unreviewed design — it must be re-reviewed.

For small, contained changes (single-file logic, config, thin wrappers), one round is fine — do **not** over-apply this.

**The loop:**
1. Review (Codex + Claude, independent) → group Blocking/High/Medium/Low.
2. Address all Blocking/High (present Medium for a decision).
3. **Re-review the revised artifact** — both passes again, explicitly scoped to (a) verify each prior finding is *genuinely* fixed, not reworded, and (b) hunt for defects the fixes introduced.
4. Repeat from 2.

**Four rules for the loop** — evidence for each in `docs/process-rationale.md`:
- **At fix time, list the consumers.** Before a fix that changes what state *means*, name every reader
  — including the same code in a **different process**. `grep` for the field name is usually the job.
- **Reviewer disagreement is the signal.** Never resolve a split by majority or by trusting a CONVERGED
  verdict. Adjudicate by reading the code, and **record the adjudication in the review doc**.
- **Each gate re-derives ONE inherited assumption** — chosen because this gate has information the
  earlier one lacked (per-task review re-derives what produces each variant of the types it consumes).
  One question, not a re-review.
- **Convergence measures the prompt too.** Carry a standing list of root-cause *shapes* into each
  round's prompt and ask for siblings by shape, not another read-through. List: rationale doc.

### Between rounds: classify the rules, then cross-derive them (added 2026-08-06)

**Do this after round 2, before dispatching round 3.** Two rounds of review on the stable-blob-addressing
spec produced a reviewer verdict that no individual finding could have: *"the fixes are individually
thoughtful and most of them land. They fail **as a set** — each was written into its own section and
none was re-derived against the others. Every Blocking is an interaction between two fixes, not a
defect in either one."* A review round is the expensive way to learn that.

**Step 1 — classify every rule the artifact now states.** Three kinds:

| | Meaning |
|---|---|
| **P — Physical** | Imposed by the database, the platform or a vendor. Not negotiable |
| **I — Invariant we chose** | Load-bearing but **ours**. Changing it has a cost, not an impossibility |
| **H — Heuristic** | A tuned value or default. Expected to move; must never block a design |

**The whole point is separating I from P.** Measured on that spec: of roughly 30 findings across two
rounds, **~9 dissolved outright when a rule was reclassified** — and they were specifically the ones
that **kept coming back**. Ordinary defects (a missing FK target, a stale citation, judgments written
into frontmatter) had nothing to do with premises and were simply fixed.

> **So the trigger is recurrence, not volume.** When a *third* finding lands in the same area, stop
> patching and ask which rule there is a choice wearing the costume of a constraint. Both clusters below
> were on their third appearance before anyone questioned the premise underneath them.

- *"The workspace id must never equal a uid"* — sounded physical, was a choice, and forced a
  whole-corpus migration of paid content. Restated as an **I about a predicate** (*no predicate may
  compare the path segment to `auth.uid()`*) it dissolved a Blocking and made the migration incremental.
- *"The manifest is mutable state protected by a conditional write"* — a choice. Deriving `current`
  instead deleted a CAS, a limbo state, a requeue protocol and a whole table, and closed three findings.
- *"Everything in the bucket is an artifact the manifest tracks"* — a choice. Reclassifying assets as
  **sources** closed two more.

Note the mirror: the openly-heuristic rules (a 0.8 threshold, a 90-day retention) **never caused a
problem**. *Visible tuning knobs are safe; invisible ones are the dangerous kind*, because nobody
thinks to question them.

**Step 2 — cross-derive.** Check each rule against every other and record the conflicts. On that spec
this found **five**, all between rules written within hours of each other — including one **new**
defect introduced inside a fix (an eligibility test that read a blob, silently reintroducing
absent-vs-failed in the fix that removed a different instance of it).

**Step 3 — evaluate the I rules.** For each, ask **not** *"is it true?"* but ***"is what it buys still
worth what it forbids?"*** Name what it forbids explicitly — a rule whose cost is unwritten cannot be
re-evaluated. Expect refinements rather than deletions: on that spec, 8 of 12 were sound as written,
2 were right in substance and wrong in wording (one had an undocumented exception **already in
production**), and 1 was a relaxation candidate whose stated justification no longer held.

**Why it goes here rather than in the review prompt.** The reviewer can only see the artifact. Which
rules are *chosen* is authorial knowledge, and re-deriving your own fixes against each other is cheap,
while paying a review round to discover the same interaction is not.

### Step 4 — classify the GUARDS: SHAPE or SEQUENCE (added 2026-08-07)

Steps 1–3 classify the **rules**. This classifies the **enforcement**, and it is a different pass with
a different yield. Run it over *every* guard — constraints, unique indexes, foreign keys, trigger
raises, early returns — including the boring ones.

| | Asks | A violation means | Must |
|---|---|---|---|
| **SHAPE** | is this well-formed and referentially sound? | the **caller is wrong** | **reject** |
| **SEQUENCE** | who got here first? has this already happened? is this in flight? | **concurrency** — the caller did nothing wrong, and may already have spent money | **reconcile**: an upsert, a no-op, or a typed outcome. **Never a raw rejection** |

**The one question to ask of each guard: what does this do when the caller is merely SECOND?**

That is deliberately *not* "is this guard correct?" Both defects this found were **plainly correct**
guards — a reviewer reads them, agrees, and moves on. Seven rounds of adversarial review with
unlimited depth missed both; one shallow pass over all 32 found them in an hour.

**Measured on the blob-addressing schema (2026-08-07):** 32 guards, 26 SHAPE, 6 SEQUENCE. Every CHECK
and FK was SHAPE and correct, so the pass concentrates attention on ~6 items out of 32 — most of its
value. Of the six, three were already reconcilers (including the one predicted broken), one was a
deliberate fence, and **two were rejecters**: an entire *kind* of write was unreachable (every
re-render failed with a raw `23505`), and the retention sweep **could never run at all**, because its
safety rule aborted the batch and the row it tripped on was permanently in that state.

**When to run it:** before a review round on anything with a write protocol, and *always* before
promoting a schema into `supabase/migrations/`. It is cheap, total, and mechanical — the opposite
axis from adversarial review, which is deep and selective. **Depth and coverage do not substitute for
each other**, and a project buying a lot of depth should notice when it has bought no coverage.

**⟳ IT IS NOW A RATCHET, NOT A DISCIPLINE (added 2026-08-07).** A rule that depends on remembering is
the shape this project's own reviews keep finding in the *code*; running the classification by hand
would have been the same defect in the *process*. Two mechanical checks:

| Check | What it enumerates | Fails when |
|---|---|---|
| `scripts/check-guard-coverage.py` | every constraint, unique index, FK and trigger, read from **`pg_catalog`** | a guard is unclassified, a classification is stale, or a SEQUENCE guard has no mutation |
| the coverage assertion in `schema/05_assert.sql` | every value of the `artifact_kind` enum × free/paid | any kind is never written a **second** time to the same slot |

The population comes from the live catalog and the enum, never from a hand-maintained list — so a
guard added tomorrow cannot be silently skipped. **Both earned their place on the first run:**
the first found four guards nobody had ever inventoried (two auto-named `state` CHECKs among them),
and the second, verified by deletion, reproduces the exact free-render defect that survived seven
rounds. The machine count also corrected the manual one — 28 SHAPE / 4 SEQUENCE, not 26 / 6.

**Both are LOCAL gates today**, alongside `verify-schema.sh`, because they need a live Postgres and
CI has none while this schema is still outside `supabase/migrations/`. Wiring them into CI is part of
the promotion slice, not a separate task — a gate that only runs when someone remembers is halfway
back to a discipline.

**Two rules that fall out, both learned by getting them wrong:**
- **A promise like "this never refuses" is a NEGATIVE property over every guard on its write path.**
  Count them before believing it. `record_artifact` promised exactly that across **32** rejection
  mechanisms; each new guard was a new way to break it, and one added a day later did.
- **Never convert a rejecter into a silent no-op.** Move the test into a predicate the caller selects
  *through*, and keep the rejecter as a backstop. Suppressing the write quietly tells the caller it
  succeeded — shape #5, and worst on delete paths, which have no undo.

*(Origin: round 7's `B1` was a decision that had an assertion **and** a passing mutation and broke
anyway. Asking why led here — see `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md`
§5.2.5.)*

### And apply the Enumerated Behaviors table to DECISIONS, not only to tasks (added 2026-08-07)

The Per-Task Checklist already demands an **Enumerated Behaviors** table before tests are written.
Nothing demanded one for a **decision** — and a decision is exactly where it is most needed, because
a decision is recorded as prose and defended by a test written against *the scenario that prompted
it*.

Measured: the user decision *"the reservation guards spending, not recording"* had an assertion naming
it and a mutation confirming that assertion was load-bearing. Both passed. It broke anyway, because
the assertion passed a *different* generation id and *supplied* the span — the one configuration where
the implementation happened to be correct. Three other arrivals at the same function violated the same
promise with no assertion at all.

> **Mutation testing proves a guard is LOAD-BEARING. It never proves the assertion set is COMPLETE.**
> It answers *"does deleting this code break a test?"*, not *"does the test cover the promise?"*

So: when a decision is made — especially one made **against** a recommendation — enumerate the ways a
caller can reach the code it constrains, and assert the property at each. For `record_artifact` that
was four cells (holder vs lost token × same vs different generation × args supplied vs omitted ×
generation pending vs completed-by-another). Three were broken.

**Related but different:** the `zoom-out` skill orients you in unfamiliar **code** (a map of modules and
callers). This orients you in your own **assumptions**. Both are "go up a level"; only one questions
whether a constraint is real.

---

**Where review effort belongs:** per-task review is structurally blind to composition defects. Keep it
light for internally-simple tasks; spend the budget on whole-branch rounds.

**Before deferring a finding, try to turn it into an assertion.** "Unverified — check at deploy" is a
bet that a manual check happens later. If the claim can be expressed as a test using scaffolding that
already exists, write it NOW: it is usually minutes, it either promotes the finding to a fixed bug or
retires it, and either way it leaves a regression guard. Applies hardest to money and data-loss paths,
where the alternative first evidence is a production incident. Determine external behaviour by probing
the live system, not by reading vendor types.
*(Why: a suspected double-charge sat as a roadmap line for a day; one test measured it at 6¢→12¢ —
`docs/process-rationale.md`.)*

**Stop (diminishing returns) when** a full re-review round returns **no new Blocking or High** — only Low/nits, or findings already known-and-accepted (recorded as deferred with an owner). That round is the gate; then get human approval. Do **not** stop merely because you are tired of reviewing or the artifact "feels done."

**Keep going when** a round surfaces a *new* Blocking/High (common after a big rewrite) — that is proof the loop is still earning its cost; another round is mandatory.

**Save every round** to `docs/reviews/` with a version/round suffix (e.g. `-v2-rereview.md`) so the convergence trail is auditable.

*(Empirical basis — Stage 1E-b and Stage 3 cloud-sync: `docs/process-rationale.md`.)*

