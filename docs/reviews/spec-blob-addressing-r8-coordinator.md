# Round 8 — coordinator adjudication

**Verdict: NOT CONVERGED.** 3 Blocking, 5 High, 6 Medium. Round 9 is mandatory.

Both reviewers ran at **full strength** for the first time. Codex reached Docker (`gpt-5.5`,
`-s danger-full-access`) and measured its findings instead of reading them — the round-7 gap is closed.

**Every Blocking below was re-measured by me from scratch before being accepted**, per round 7's rule
that reviewer disagreement is the signal. That re-measurement changed one finding's mechanism and one
finding's severity. Probes: `…/scratchpad/r8-probe{,2,3,4}.sql`, live Postgres inside a rollback.

**The headline result is a disagreement, not a finding.** The two reviewers reported *opposite*
defects in the *same* mechanism — round 7's ownership fence. Codex: any trusted caller can complete a
generation it does not own. Claude: the one worker that legitimately needs to is refused, and its paid
work destroyed. Both measured, both reproduced by me. A fence that is simultaneously too permissive
and too strict is not mis-tuned; it is authenticating with the wrong credential.

---

## BLOCKING

### B1 — a routine GC sweep permanently buries paid work that is still being produced
*(found independently by both reviewers)*

`video_generations_collectable` excludes only **current** generations, and "current" requires a
`recorded` artifact. An in-flight reservation has none, so the sweeper is offered a generation whose
paid call is still running.

MEASURED (probe 2) — no attacker, no second worker:

```
collectable WHILE IN FLIGHT (0 = safe): 1
sweep collected 1 row(s)
holder recorded: recorded_as_holder
 gen_state | collected | art_state | current_rows
 complete  | t         | recorded  |            0
```

The worker's own record **succeeds** and reports success. The row is invisible in
`video_artifacts_current` forever. Money spent, bytes queued for deletion, no error anywhere.

**This is round 8's own fix reproducing the defect it was written to remove.** The `collectable` view
came from the classification pass (C3); it copied the currency test faithfully **including its blind
spot** — neither the view nor the trigger asks whether the generation is *finished*. Shape #10.

**Fix, measured (probe 8):** add `g.state = 'complete'`. `collectable today: 1 → with a
state=complete floor: 0`. Item 3 introduced `state` for exactly this and the view never consulted it.

### B2 — the doubly-lost worker is REFUSED and its paid work destroyed
*(Claude B2; re-measured)*

The round-7 fence states its own coverage argument — *"fencing on the token alone breaks the restarted
worker, and fencing on the slot alone breaks the reclaimed one"* — and both disjuncts consider a
**single** loss. The conjunction is ordinary: a crash loses the token, and the lapsed lease is exactly
what invites a reclaim.

MEASURED (probe 10):

```
F1. W1 reserved dig:8 with gW1 -> reserved   (W1 now PAYS Gemini)
F2. W2 reclaimed dig:8 with gW2 -> reserved
F3. restarted W1 records PAID work -> REFUSED [P0001] … generation gW1 is pending
F4. gW1 state=pending ; recorded artifacts for gW1 = 0
F5. CONTROL — same call WITH the token -> recorded_after_loss
```

The control isolates the cause: the identical call succeeds with the token. Blocking because the
design says of this exact function *"THE FLIP — and it NEVER REFUSES"* (`04:387`), and because it
discards paid Gemini output — the outcome the 2026-08-07 user decision (*the reservation guards
spending, not recording*) exists to prevent. **Third** later change to revoke that decision without
mentioning it.

### B3 — after this migration nothing can ingest a new video
*(Claude B3; re-measured)*

`01_workspaces.sql:41-43` sets `videos.workspace_id NOT NULL` with no default and no trigger;
`03_generations.sql:96-97` then adds `videos_workspace_video_fk`, whose parent table's only population
is a one-shot seed. Every live writer's column list omits `workspace_id`.

MEASURED (probe 9), running `claim_video_slot`'s INSERT verbatim:

```
I1. claim_video_slot INSERT -> [23502] null value in column "workspace_id" … not-null constraint
I2. same INSERT + workspace_id -> [23503] … violates foreign key "videos_workspace_video_fk"
```

Two independent breakages, one behind the other. This is **not** the out-of-scope "it is not a real
migration" report: the defect is that the schema mandates two values per new video and **the design
names no producer for either**. §5.0.1 calls `workspace_videos` *"the entity the manifest keys on"*
and never says who inserts a row into it.

---

## HIGH

### H1 — the same fence accepts a caller with no proof of ownership *(Codex B1, downgraded)*

Codex headlined this *"tokenless"*. **The headline is wrong in a way that matters**, because the fix
it implies does nothing. MEASURED (probe 1) with `p_token = NULL`: another worker's in-flight
generation completed with `md_hash=SHA_ATTACKER`, `tldr=ATTACKER`. MEASURED (probe 4) with a **random
valid non-NULL token**: identical — `SHA_FOREIGN`, `FOREIGN_TOKEN`. NULL is not the crux; the `exists`
disjunct is satisfied by anyone who can *name* the slot and generation.

Downgraded from Blocking on measured blast radius: **not cross-tenant** (probe 5 —
`P0001 … generation gV2 is <absent>`), **not externally reachable** (probe 6 — granted to
`service_role` and `postgres` only; `anon` and `authenticated` cannot call it), and the caller must
already know the generation id. A correctness and money defect among trusted callers, not a security
hole.

**H1 and B2 are one defect.** The disjunct that lets an impostor complete a generation is the same one
added so a restarted worker could. Tightening it deepens B2; loosening it deepens H1. **The resolution
both directions point at: make the token durable** — the worker persists it with its job before
spending, so a restart recovers it. Then the slot disjunct can be deleted (closing H1) and the
doubly-lost worker recovers its token (closing B2). One change, both directions. Note that Claude's
alternative — re-read `reserved_by` from `video_generations` — is *not* proof of ownership, since any
trusted caller can read it too.

### H2 — `reserve_artifact_slot` hits `video_artifacts_free_uq` raw *(Claude H1)*

Round 8's C1 gave the free path a reconciler in `record_artifact` and left the sibling entry point
alone. The root cause is invisible on inspection: the `already_recorded` short-circuit tests
`generation_id = p_generation_id`, and for a free slot both sides are NULL — `NULL = NULL` is NULL,
**never true**, so the short-circuit is not merely wrong for free slots, it is *unreachable*. Shape
#10, in the round that added the fix.

### H3 — the check-then-act race, no longer analysis

Rounds 6 and 7 could only reason about it. **Now measured** (probe 7) by constructing the post-race
state and running reserve's own insert verbatim: `[23505] duplicate key value violates unique
constraint "video_artifacts_paid_uq"` — where the contract promises the typed `already_recorded`.
Claude reached the same defect deterministically through the free path (H2 above): same structure,
no race needed. A SEQUENCE guard behaving as a rejecter.

### H4 — `produced_at > now()` has zero tolerance *(both reviewers)*

`now()` is `transaction_timestamp()`. MEASURED (probe 3): 0.63 s into a transaction,
`clock_timestamp()` is already "in the FUTURE". The realistic trigger is **app-vs-database clock
skew** — worker on Fly, Postgres on Supabase, `produced_at` stamped in app code — turning a
successful summarize into a raw exception *after* the paid call. Fix: a bounded tolerance
(`now() + interval '5 minutes'`) fully preserves round 7 B2's intent, which was to stop values *years*
in the future winning the ranking permanently.

### H5 — a free artifact's `blob_key` has no workspace confinement *(Claude H5; inherited, not re-measured)*

`art_key_names_generation` is gated on `generation_id is not null`, so free rows are unchecked.
Flagged as inherited: I did not reproduce this one.

---

## MEDIUM — the instruments, and the classification

### M1 — the guard-coverage ratchet is satisfiable without being true *(both reviewers)*

`check-guard-coverage.py:180` substring-searches the whole mutation file. Claude showed **every**
SEQUENCE guard is satisfied today by its name appearing in a *label string only*, and that
`video_artifacts_inflight_uq`'s "mutation" does not touch the index at all — it inverts a branch order
in the RPC. The script's own docstring says it exists because *"an absence is only visible against an
enumerated whole"*, and then verifies coverage against free text. Fix: an explicit `covered_by=[…]`
matched against mutation labels.

### M2 — SHAPE/SEQUENCE records the conclusion and discards the premise *(Claude M3 — this is JOB 3's audit)*

**The audit was delivered, and the answer is yes.** At least three guards labelled SHAPE have a
sequencing face; `video_artifacts_generation_complete` is measured in B2 rejecting a caller whose only
fault was restarting and being reclaimed.

The pattern: a guard is SHAPE *given* a reconciler somewhere in an RPC — and the classification stores
the label while forgetting the reconciler it depends on. The ratchet then attaches its obligations (a
note, a mutation) to the **label**, so the reconcilers holding three SHAPE guards away from rejecting
a blameless second caller are exactly what nothing protects. `art_dig_has_span`'s reconciler appears
**zero** times in `mutate-schema.py`.

Both defects the classification pass was built from were found by asking the SEQUENCE question of
something that looked like SHAPE — so the ratchet enforces the half that was never the problem.

### M3 — the mutation gate mutates repo-tracked files in place *(Claude M4)*

`mutate-schema.py:445` does `target.write_text(...)` on the real `schema/*.sql` and restores in a
`finally`. Two agents running the gate concurrently read each other's mutations — which is exactly
what happened this round: Codex's own report mentions *"restoring mutation residue left by the first
interrupted run"*, and Claude measured `23/44` in the repo against `44/44` in an isolated copy of the
same commit. Shape #11, and the expensive kind: it fails **loud and wrong**. The `finally` also does
not survive `SIGKILL`, leaving a mutated tracked file on disk. Fix: `cp -r` to a temp dir and mutate
the copy — `verify-schema.sh` already resolves its schema dir from its own location.

*(The working tree is clean as of this writing — `git diff` vs `HEAD` is empty.)*

### M4 — the population ratchet counts row-writes, not second callers *(Codex)*

`t_writes` fires `after insert or update`, so a paid artifact's normal `reserve`(INSERT) →
`record`(UPDATE) is two rows, one caller, no SEQUENCE case exercised. Measured how bad: **currently
truthful** — every `artifact_kind` has a genuine second INSERT (`summary` 11, `digDeeper` 3, `model`
2, `render` 2, `dig` via `dig:700` and `dig:8`) — though four `dig:*` slots pass only on a
single-writer lifecycle. **The fix is free:** require ≥2 INSERTs per kind; the tightened assertion
passes today unchanged.

### M5 — the live `dig_max_attempts` is 1, not the 2 the schema reasons from *(Claude M6)*

Measured from `guardrail_config`. `04:230-231` argues the per-kind bound is needed because the knobs
*"disagree by 5x"*, citing `dig_max_attempts=2`; the assertions **set** the value they then verify. So
the schema's reasoning and the running system have drifted, and B2's scenario is unreachable in
production for the accidental reason that no dig slot is reclaimable at all.

### M6 — a dig detached one second ago is immediately collectable *(Claude M5)*

Correct under the 2026-08-06 retention decision *only* because §8's 90-day clock lives in the sweeper.
Deliberate, so Medium — but worth stating in the view's comment, since the view is what a future
sweeper author will read. Same structure as B1: a correctness-shaped consequence resting on a knob
outside the "correctness floor".

---

## JOB 2 — the three open agenda items

| Item | Status after round 8 |
|---|---|
| check-then-act race on `paid_uq` | **SETTLED — real, measured** (H3), plus a deterministic sibling in the free path (H2) |
| the inert `pending` generation | **NOT inert** — B1 is the counterexample |
| `persist_summary` merge semantics | **Still open.** Neither reviewer found a measured freeze-trigger failure in the live path |

## JOB 3 — the invariants

- *"The reservation guards spending, not recording"* — **not structurally protected.** Now violated by
  three separate later changes (round 7 B1, the GC path in B1, and B2's fence). Fixed three times,
  protected zero times. This is the rule to make structural in round 9.
- *"A generation must be complete when something recorded points at it"* — held at the tenant boundary
  under attack (probe 5). Bulk paths (`COPY`, logical replication) remain unprobed.
- **The SHAPE/SEQUENCE labels** — audited, and found to record conclusions without their premises.
  See M2.

## Gate state

`./scripts/check-schema-gates.sh` green when run in isolation: 103 assertions, 44/44 mutations, 32
guards classified, docs OK. **Read M3 before trusting any concurrent run of it.**
