# Retrospective — why the reservation protocol never converged (2026-08-09)

Twelve adversarial rounds. Every component of the stable-blob-addressing spec converged and stayed
converged **except one**, which produced a Blocking or High in six consecutive rounds and was, four
times, broken *by the previous round's own fix*.

This document is the durable record of what that turned out to mean. It is the input to ADR-0007 and
to the process changes that follow it.

---

## A. Architectural findings

**A1 — Sync replicates; it does not produce.** `[VERIFIED: lib/cloud-sync/sync-run.ts:380-394]`
`transferClassA` copies an **existing** body between replicas. No Gemini call, no payment. The two
writers are a *producer* (worker, job-driven, pays) and a *replicator* (sync, not job-driven, free).

**A2 — The two writers never contend, because stable addressing made their writes disjoint.** The
producer writes a **new** generation → `…/<newGen>/summary.md`. The replicator copies an **existing**
one → `…/<existingGen>/summary.md`. Different keys, different append-only rows. The only shared
question is *which row is current*, which is a ranking — `video_artifacts_current` — not a lock.

**A3 — Producer exclusivity and idempotency already exist.**
`[VERIFIED: jobs_idem_active]` — `unique (owner_id, playlist_id, video_id, section_id, job_kind,
job_version) where status in ('queued','active','completed')`. One index, both properties.

**A4 — The money guard already exists.**
`[VERIFIED: supabase/migrations/0020_reservation_release.sql:25-32]` — `jobs.ever_metered` +
`reserved_cents`, durable across retries, hardened in its own reviewed slice (PR #22).

**A5 — Therefore the artifact reservation was redundant, and worse: it solved a problem its own spec
had already eliminated.** It was designed for the pre-ADR-0006 world where a summary had ONE MUTABLE
ADDRESS and two writers genuinely collided. Stable addressing dissolved that collision; nobody went
back to ask whether the lock was still needed. **That is why six rounds could not converge on it —
there was nothing there to converge on.**

**A6 — The root cause: three coordination patterns in one design.**

| Pattern | Where it lives | What it assumes |
|---|---|---|
| append-only log + deterministic merge | `video_artifacts` + `video_artifacts_current` ranking | don't coordinate; define who wins |
| mutual exclusion | `reserve_artifact_slot`, leases, tokens, attempts | coordinate; one writer proceeds |
| idempotency key | `generation_id` (caller-supplied, addresses the blob) | let it happen twice; make the second a no-op |

Each is sound alone. Together they are incoherent, and **every symptom follows**: the fence had to be
PERMISSIVE so `recorded_after_loss` works (merge thinking) and STRICT so a stranger cannot complete
(lock thinking). Round 8's "wrong credential" diagnosis was right about the symptom and wrong about
the cause — it was two philosophies wired to one predicate.

**A7 — `generation_id is null` conflates two independent facts.**
`[VERIFIED: schema/04_artifacts.sql:95]` —
`((kind in ('summary','model','dig','digDeeper')) = (generation_id is not null))`. The schema
*defines* free-ness as "has no generation id", so one value carries **"this is free"** (a money
property) and **"this address may be overwritten"** (an addressing property).

Give renders a deterministic identity — `hash(source_generation_id, GENERATOR_VERSION)`,
`[VERIFIED: lib/html-doc/constants]` — and six findings **dissolve** rather than needing fixes:

| Finding | Fate |
|---|---|
| r8 C1 — free-render reconciler | gone; no overwrite exists |
| r8 H2 / r9 — `NULL = NULL` made the short-circuit unreachable | gone; no NULL |
| r9 H5 — free rows escaped tenant confinement | gone; the constraint applies to all rows |
| r10 H2 — a tokenless caller stole a free lease | gone; no free lease |
| r11 — the typed `busy` | gone |
| r12 M2 — a free slot can be reserved once in its life | gone |

Plus `video_artifacts_free_uq` and the entire free branch of `record_artifact`. Free-ness becomes a
property of the **kind**, consulted only by the money path.

**A8 — Open design question, not a footnote:** a render derived from MORE THAN ONE generation (a PDF
containing the summary *and* its digs) needs a hash over a **set**; `source_generation_id` is a
single column today. And storage grows instead of being overwritten — handled by the round-8 GC, but
a real trade to state.

---

## B. Process findings

**B1 — Every gate we have is a defect detector. None is a design-integrity detector.** Correctness
questions are LOCAL and can always be answered "yes" by patching. So a wrong shape does not fail the
gates; it emits a stream of defects that we fix, and **each fix makes the gates greener**. The
process does not merely tolerate patching a bad design — it rewards it.

**B2 — Phase 6 IS the design-integrity gate, and it never fired.** `dev-process.md` describes this
exact failure in its own opening sentence (*"per-task review is structurally blind to composition
defects"*), and its trigger is **per milestone**. A spec can run twelve rounds in a week without
crossing one. **The inventory was right; the arming condition was wrong.** Fix the trigger, do not
add a gate.

**B3 — We were already measuring the right thing and never acted on it.** The standing shape list
tracks *"a fix that moved or reintroduced a defect"* — counted to nine, then ten, then eleven across
rounds 8–12. That is the textbook signature of a wrong abstraction, carried forward for five rounds
as **trivia in a prompt** rather than a stop condition.

**B4 — The validation stack was asymmetric.** Heavy automated verification on the TARGET layer (122
assertions, 57 mutations, guard coverage) and *nothing* on the ASSUMPTIONS layer — the external
runtime code the design rests on. That manufactures false confidence: a green 57/57 feels like
maximum rigour while the whole premise sits in one unread line of another file. It did
(`worker/main.ts:69`).

**B5 — Patching moves two metrics in opposite directions.** Each patch REDUCES local defect count
while INCREASING structural incoherence. Only one was measured. Any process that measures defects but
not coherence drifts to exactly this outcome, and feels increasingly rigorous while doing it.

**B6 — A comment describing behaviour the code does not have is an unenforced assertion.** Three
instances: the round-12 Blocking ("minted ONCE and shared" — never implemented), *"'render' is free
and never reserved"* (a convention, not a guard), *"worker_id is stable config"* (false). The
mutation harness catches a guard that STOPS working; nothing catches a guard that never started.

**B7 — Mutation testing proves a test is load-bearing on something; never that it tests the property
you meant.** The round-12 contract test survived its own mutation check because I mutated the
MECHANISM (remove the abort) rather than the CLAIM (does work get recorded?).

---

## C. Already landed

- **Quote, don't characterise** — a premise about existing code pastes the line with `file:line`, or
  is labelled unverified in the same sentence. `docs/review-method.md`, PR #59.
- **Ask what caller reaches this state** — a rolled-back probe constructs states no caller can reach;
  a defect with no reachable caller is a fact about expressiveness, not a bug. PR #59.
- **Premise tags** `[VERIFIED: file:line]` / `[ASSUMPTION]`, and no safety fence may be designed on an
  `[ASSUMPTION]`. A tag verified three rounds ago is an `[ASSUMPTION]` today. PR #60.
- **Contract tests at the runtime boundary** — `tests/lib/blob-addressing-caller-contract.test.ts`,
  mutation-checked, in the CI-covered suite. PR #60.

---

## D. To build, in this order

**1. ADR-0007 — the architecture.** `video_artifacts` is a pure append-only log. Every artifact has an
immutable derived address, **including renders**. No lease, no token, no attempt counter, no
free/paid branch in the write path. Exclusivity and idempotency from `jobs_idem_active`; money from
`ever_metered`/`reserved_cents`; currency from the ranking view. Supersedes the reservation protocol
(handoff item 4) and retires §12b's caller obligation, which stops being load-bearing once nothing is
fenced.

**2. Two scripts, wired into `check-schema-gates.sh`** — built before the process doc claims they
exist:
   - **sentinel-meaning coverage**: enumerate every nullable column and sentinel from `pg_catalog`;
     require one documented sentence each; **fail if the sentence contains "and" or "or"**. Would have
     caught A7, `corrections_hash`, and absent-vs-failed.
   - **vocabulary collision**: flag a new column whose name-stem already exists elsewhere under a
     different owner. Duplicate vocabulary is the observable shadow of duplicate mechanism. Would have
     fired on the FIRST commit of the reservation protocol —
     `jobs.lease_token` / `video_artifacts.lease_token`, `lease_expires_at` on both,
     `jobs.attempts` / `lease_attempts`, `locked_by` / `reserved_by`.

**3. Process changes** — `dev-process.md` + spec template:
   - Phase 6 also triggers on **a spec that has run N rounds without converging** (B2).
   - **Stop condition**: if a round's findings were caused by the previous round's fixes twice in a
     row, the component escalates from **fix** to **redesign**, and the next round is a design review,
     not a defect hunt (B3). Would have fired at round 9, saving rounds 10–12.
   - **Concern → mechanism matrix** in the spec template: every concern has exactly ONE mechanism;
     every mechanism serves exactly ONE concern. Manual and weak — but the only check that catches
     the inverse smell (two mechanisms, one job), which no per-item script can see.
   - **"What already does this?"** — required field before adding a mechanism, answered with a
     `file:line`. The reservation's justification never mentions `jobs` once in 2800 lines.

**Honest limit:** none of this detects "this abstraction is wrong". It narrows the space so wrongness
shows up as something COUNTABLE — a conflated sentinel, a duplicated noun, a component that keeps
producing defects. The global judgement stays with Phase 6 and with the human. The win is that the
next instance is detectable at round 2 instead of round 12.
