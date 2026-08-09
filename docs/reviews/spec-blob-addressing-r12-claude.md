# Round 12 — Claude adversarial review (stable blob addressing)

**Verdict: NOT CONVERGED.** 1 Blocking, 2 High, 3 Medium, 2 Low.

Probes ran against `chore/caller-contract-and-premise-tags` @ `d2dcd40` (the checkout moved from
`master` mid-review; the schema files are byte-identical between the two, and B1 was re-measured
against HEAD after the move). Mutation copy:
`…/scratchpad/r12-claude`. `git status --porcelain` is clean.

---

## BLOCKING

### B1 — `reserve_artifact_slot` hands out a token that cannot complete the generation it just reserved [MEASURED]

**§12b's load-bearing claim is false, and the counter-example is produced by this schema's own RPC.**
The claim is *"the party that holds paid bytes always still holds the token"*. Here the party holds
paid bytes **and** the token the RPC gave it, and that token is not the one the fence checks.

The mechanism is two lines that were written for different reasons and never read together.
`04_artifacts.sql:307-313` creates the generation `on conflict … do nothing`:

```sql
  if p_generation_id is not null then
    insert into public.video_generations
      (workspace_id, video_id, generation_id, kind, state, reserved_by)
    values (p_ws, p_video, p_generation_id, p_kind, 'pending', v_token)
    on conflict (workspace_id, video_id, generation_id) do nothing;
    v_made_generation := found;
```

`v_token` is minted fresh on every call (`04:237`). So when the generation row **already exists and
is still pending**, `do nothing` leaves `reserved_by` pointing at the *previous* caller's token,
while the artifact upsert below re-points `lease_token` to the *new* one (`04:335`) and the function
returns `'reserved'` (`04:342`). The two halves of what `04:235-237` calls *"minted ONCE and shared
by the generation and the artifact, so the holder of a slot and the reserver of its generation are
provably the same party"* have come apart.

`record_artifact` then fences on the generation half (`04:535-537`):

```sql
     where g.workspace_id = p_ws and g.video_id = p_video and g.generation_id = p_generation_id
       and g.state = 'pending'
       and g.reserved_by = p_token;
```

no match → not `complete` → the artifact flip is refused by the completeness trigger.

**MEASURED** (`…/scratchpad/p1.sql`, re-run against `d2dcd40`):

```
W1 reserve  -> outcome=reserved token=033b93cb-2d21-4289-8b21-42812778a365
   generation gX.reserved_by = 033b93cb-…  (== W1 token: t)
W2 reserve  -> outcome=reserved token=7c6791de-901c-418f-a62b-645b2f787919 attempts=2
   generation gX.reserved_by = 033b93cb-…  (== W2 token: f)  STALE=t
W2 record   -> ✖ RAISED [P0001] video_artifacts: cannot mark dig:8 as recorded — generation gX is pending
retry w/ T1 -> recorded_after_token_loss
```

W2 did everything right: it asked, it was told `reserved`, it paid, it presented the credential it
was issued. It got a raw SQLSTATE. The only token that can ever complete `gX` is `T1` — held by a
process that is gone. This is shape **#13** (a credential the honest caller cannot present) and
shape **#12** (a guard rejecting a caller who did nothing wrong), reached without an attacker,
without a forged token and without a second tenant.

**What caller reaches this state.** Any caller that re-presents an existing generation id for a slot
whose reservation has expired. That is not hypothetical — it is the shape both branches of
`reserve_artifact_slot` are *written for*:

- the idempotency short-circuit at `04:283-288` matches on
  `generation_id is not distinct from p_generation_id`, and its comment (`04:272-275`) names the
  caller: *"a worker that crashed between recording and reporting job completion retries, and must
  learn it is done rather than be handed an error."* It fires only for `state in ('recorded',
  'detached')` — so a crash in the **paid-call window**, where the row is still `pending`, falls
  through into exactly this hole;
- the `do nothing` above exists precisely because *"a generation that already exists is either a
  completed one being retried … or one sync replicated in full"* (`04:296-299`);
- the brief's own "future queue with at-least-once delivery" produces it whenever the generation id
  is derived from job identity rather than minted per attempt — and §14 Q1 leaves the id form **open**,
  so nothing rules that out.

The reachability that matters is architectural, not statistical: the schema advertises a call shape
(*present an existing generation id*) and, on one of the two states that shape can be in, issues a
credential that provably cannot be used. `already_recorded` is a typed answer for the recorded case;
the pending case gets a lie followed by a raw exception.

**The change.** Winning the slot **is** the authorization event — `reserved_by` exists to stop a
party that never held the slot from completing someone else's generation, and a caller the upsert
has just granted the slot under that id is by definition its new reserver. So re-point it, and only
once the upsert has actually won:

```sql
  if found then
    update public.video_generations
       set reserved_by = v_token
     where workspace_id = p_ws and video_id = p_video and generation_id = p_generation_id
       and state = 'pending' and reserved_by is distinct from v_token;
    return query select 'reserved'::text, v_row.lease_token, v_row.lease_attempts; return;
  end if;
```

**MEASURED in the mutation copy:** `W2 record -> recorded_as_holder`, `gX.reserved_by == W2 token`,
and `verify-schema.sh` still reports `ASSERTIONS_OK` / `ALL_STATEMENTS_OK` — all 122 assertions
green, nothing else moved. Placing it after `if found` is load-bearing: a losing caller must not
re-point a live reserver's generation.

**And add the assertion.** Every existing reclaim fixture reclaims under a *different* generation id
— R2/B1c goes `gR2 → gR2b` (`05:1181-1187`), R3b/P22 goes `gP1 → gP2` (`05:1251-1256`). Not one
assertion in 122 reserves the **same** id twice, which is why this survived eleven rounds.

---

## HIGH

### H2 — `video_artifacts_generation_complete` is classified SHAPE, and it is the guard that raises in B1 [MEASURED]

`check-guard-coverage.py:23-32` defines the classes and states the one question to ask:

> `SEQUENCE - who got here first? … A violation is CONCURRENCY: the caller did nothing wrong and may
> already have spent money. It must RECONCILE - an upsert, a no-op, or a typed outcome - never a raw
> rejection.`

`video_artifacts_generation_complete` is listed as `("SHAPE", "")` (`check-guard-coverage.py:100`) —
bare SHAPE, so the ratchet requires no reconciler note and no mutation of one. B1 is a caller that
was merely **second**, had already spent money, and received `[P0001] … generation gX is pending`:
a raw rejection, which is precisely what the definition says a SEQUENCE guard may not do.

This is the round-8 classification pass's own thesis turned on its output: the pass asked the right
question and recorded the wrong answer for this guard, and because the label is bare `SHAPE` rather
than `SHAPE(reconciled)`, nothing in the ratchet ever asked *what reconciles it*. Answering that
question is what surfaces B1 — the reconciler is missing, not merely undocumented.

**Change:** reclassify to `SEQUENCE` (or `SHAPE(reconciled)` once B1's re-point lands, naming that
re-point as the reconciler) and add the mutation the reclassification then obliges.

### H3 — `completed_by_another` is returned to the writer that itself completed the generation [MEASURED]

Round 11 added `completed_by_another` (`04:548-555`) so a writer is never told "success" while
another writer's content stands. Its predicate is content divergence:

```sql
    if not found and exists (
         select 1 from public.video_generations g
          where … and g.state = 'complete'
            and p_md_hash is not null and g.md_hash is distinct from p_md_hash)
```

`p_md_hash` is optional, and legitimately so — `gen_summary_has_hash` (`03:411-412`) applies only to
`kind = 'summary'`, so a `dig`/`digDeeper`/`model` writer may complete without one. When it does,
`md_hash = coalesce(p_md_hash, g.md_hash)` leaves the column NULL, and the row is then frozen
(`03:481-489` rejects any later change to `md_hash`). A retry that now *supplies* its hash trips the
divergence test against its own generation.

**MEASURED** (`…/scratchpad/p2.sql`, case 2d) — one writer, one token, one generation, no second party:

```
2d first record (no md_hash)                -> recorded_as_holder
2d same worker retries with its OWN hash    -> completed_by_another
```

The outcome string asserts a fact — *another writer's content stands* — that is false; no other
writer exists. Per §12b's own doctrine the caller must then abandon, and `04:554` returns **before**
the append, so it records no artifact row at all: paid bytes orphaned on the strength of a false
attribution. This is the same class as round 10's B1 second half (a success/failure string that
misdescribes who owns the content), moved to the other side of the branch that was added to fix it —
shape **#9**.

**Change:** distinguish "someone else's content stands" from "this generation was completed without a
hash". Gate the branch on `g.md_hash is not null` as well, and either let a still-unset `md_hash` be
filled by a completing caller (relaxing the freeze for `null → value` only) or make `p_md_hash`
mandatory for every paid kind, so the column can never be recorded absent. Absent-vs-failed (shape
**#1**) on a value round 5 B3 introduced specifically to stop sync deriving it by reading the blob.

---

## MEDIUM

### M1 — the guard ratchet's "enumerated whole" omits 26 guards, including the one the schema says carries all the protection [MEASURED]

Codex filed the RLS-policy half of this today; this is the rest of it, and it is larger. The catalog
query (`check-guard-coverage.py:170-189`) takes CHECKs on **two** tables, FKs, unique indexes whose
name matches `%_uq`, and triggers. Enumerated against the live schema
(`…/scratchpad/p3.sql`), what that leaves outside the whole:

| Category | Count | Examples |
|---|---|---|
| `NOT NULL` columns (`attnotnull`, never `contype='c'`) | 19 | `workspace_videos.corrections_hash`, `video_artifacts.blob_key`, `video_generations.state` |
| PK / UNIQUE constraints (`contype in ('p','u')`) | 4 | `video_generations_workspace_id_video_id_generation_id_kind_key` — the FK target added by round 2 C2 |
| unique indexes not named `*_uq` | 4 | all three PK indexes |
| RLS policies | 3 | (Codex) |
| view `security_invoker` | 3 | `video_summary_current`, `video_artifacts_current`, `video_generations_collectable` |
| CHECKs on any table but `video_artifacts` / `video_generations` | — | `workspace_videos` is not in `TABLES` |

Two of those are named **in this schema** as the load-bearing thing:

- `04:746-752`, on the corrections rung: *"THIS LINE CARRIES NO GUARD OF ITS OWN … The protection
  lives **ENTIRELY in the NOT NULL**; this is a clarification riding on it … if the NOT NULL is ever
  relaxed, this line silently stops being equivalent and B4 returns."* That NOT NULL cannot be seen
  by the ratchet at all.
- `04:717`: *"`security_invoker = true` ON BOTH VIEWS IS A SECURITY CONTROL, NOT A STYLE CHOICE"* —
  the setting whose absence round 5 B2 measured leaking two other tenants' `blob_key`s.

The script prints `guards in schema: 45` and `✅ every guard classified`. Both read as totals. The
`%_uq` filter is the sharpest single defect: it makes a **naming convention** the boundary of an
enumeration, in the instrument whose docstring argues that conventions are exactly what an
enumeration replaces. Shape **#11**, instance seven.

**Change:** add `attnotnull`, `contype in ('p','u','x')`, `pg_policy`, and `reloptions` on the
spec's views to `CATALOG_SQL`; drop the `%_uq` filter and enumerate every unique index on the target
tables; extend the CHECK clause to `TRIGGER_TABLES` as the FK clause already is. Classifying the
resulting entries is cheap — the point is that adding a guard of any of these kinds currently
requires no decision.

### M2 — a free slot can be reserved exactly once in its life, and `already_recorded` tells a re-render it is done [MEASURED]

Round 9 gave the free path lease columns on the argument (`04:468-469`) that *"a free render has no
spend to guard but may still want a lease against two workers doing the same CPU work."* The
short-circuit at `04:283-288` is not scoped to paid rows, so it fires for a recorded **free** slot too.

**MEASURED** (`…/scratchpad/p4.sql`):

```
4a first render              -> recorded_free
4a reserve for a RE-render   -> already_recorded  (token=<NULL>)
4a re-render without a lease  -> recorded_free
```

Two costs. The lease the round-9 fix enabled is available for the first render only, so every
subsequent re-render — the case the design calls *overwritable* — runs unprotected, which is the
duplicate-CPU-work case the lease exists for. And `already_recorded` carries the paid meaning
(*"must learn it is done"*, `04:272-273`); a caller that honours it will silently skip a
user-requested re-render, because for a free slot "recorded" is not terminal. Same literal, opposite
semantics across the seam — the **sixth** face of the free/paid split after the reconciler, the
short-circuit, the tenant confinement, the lease columns and round 10's H2.

**Change:** scope the short-circuit to `p_generation_id is not null`. A free slot with no live
reservation should simply be re-reservable.

### M3 — three `pending` biconditionals are labelled bare `SHAPE`, and they are `SHAPE(reconciled)` by the script's own rule [REASONED]

`art_pending_is_leased`, `art_pending_has_token` and `art_pending_has_reserved_at`
(`check-guard-coverage.py:68-70`) are `("SHAPE", "")`. Round 9 measured what they do when the caller
is second (`04:460-465`): *"a free slot that had been RESERVED became permanently unrecordable —
`RAW [23514] art_pending_has_reserved_at`, on every retry, forever."* They are SHAPE **only because**
`record_artifact` clears all three columns — which is verbatim the premise round 9's
`SHAPE(reconciled)` class was created to stop discarding (`check-guard-coverage.py:104-108`).

A mutation for that reconciler does exist (`mutate-schema.py:432`, *"the free branch stops clearing
the lease columns"*), so coverage is real today — but it is there because somebody wrote it, not
because the ratchet obliges it. Delete that mutation and the gate still passes. Lower than M1
because nothing is currently unprotected.

**Change:** relabel all three `SHAPE(reconciled)`, naming the lease-clearing as the reconciler.

---

## LOW

- **L1 — "122 assertions" is not reported by any gate [MEASURED].** `check-schema-gates.sh` prints
  the mutation count (`57/57`) and the guard count (`45`), and for the assertions prints only
  `ASSERTIONS_OK`. The number lives in prose (`docs/review-method.md:41`) and in eight different
  historical values inside `05_assert.sql`'s own comments (73, 89, 103…). This is the same
  hand-maintained-number shape as round 8's M6 (`dig_max_attempts` drift), in the one figure every
  round's brief opens with. Have `05_assert.sql` count and print its own assertions.
- **L2 — the honest stale-token caller and a tokenless caller are indistinguishable [MEASURED].**
  `record_artifact` with `p_token := null` on a live paid reservation raises
  `[P0001] video_artifacts: cannot mark dig:1 as recorded — generation gA is pending` — byte-identical
  to B1's refusal of a caller holding a valid RPC-issued token. Fail-closed, which is right, but the
  message blames the generation's state rather than the credential, so neither caller can act on it.
  A typed outcome (`not_reserver`) would separate them.

---

## What I verified rather than found

Checked because the brief said not to inherit them. All true.

- **57/57 mutations, 45 guards, 122 assertions all green** — `./scripts/check-schema-gates.sh`
  exit 0.
- **`mutate-schema.py` really does mutate a temp copy [MEASURED].** Two concurrent full suites:
  both `57/57`, `baseline restored: GREEN`, and a `diff` of the two verdict columns is **identical**.
  `git status --porcelain` clean afterwards. Round 8's M3 is genuinely fixed, not merely claimed.
- **§12b's "there are NO callers yet"** — `grep -rn 'reserve_artifact_slot|record_artifact|
  renew_artifact_lease' worker/ lib/ app/ tests/` returns one hit, a comment in the contract test.
- **`worker/main.ts:69`** is verbatim
  `` const workerId = `${os.hostname()}-${process.pid}-${randomUUID().slice(0, 8)}`; ``.
- **The new §12b citation of `complete_job` is accurate** —
  `supabase/migrations/0008_jobs_queue.sql:136` filters
  `where id = … and locked_by = … and lease_token = … and status = 'active'`, and
  `0009_job_playlist_identity_and_worker_persistence.sql:72` nulls
  `locked_by, lease_token, lease_expires_at` and moves the row off `active`. A premise that was
  quoted and is true.
- **Premise 1 / "the worker stops"** — I measured this independently before seeing `d2dcd40`: a
  handler that never reads `ctx.signal` runs to completion after `leaseLost.abort()`, because
  `worker-runner.ts:56` is a plain `await handler(job, ctx)`. Trace: `PAID BYTES IN HAND` /
  `signal.aborted = true` / `record_artifact(...) <-- REACHED` / `runOnce returned 'lost'`. Codex
  filed it and `d2dcd40` fixed both the section and the test an hour before I got here; my
  measurement is a second, independent confirmation of the corrected text, not a finding. Note the
  actual guarantee is provided by each **handler** — `summary-handler.ts:170` and
  `dig-handler.ts:117` each carry one hand-written `if (ctx.signal.aborted) throw` — not by the
  runner, so a third handler inherits nothing.
- **The free path does not strand a slot when its holder dies (brief Q4) [MEASURED].** The
  non-holder guard tests `lease_expires_at > now()`: live lease → `busy`, dead lease →
  `recorded_free`, `pending rows left: 0`. Reserve's `busy` and record's `busy` are the same literal
  but come from functions with different return types, so no call site can confuse them.
- **`exhausted` is per-slot, not per-generation-id [MEASURED].** I expected the money guardrail to be
  escapable by minting a fresh generation id after an `exhausted`; it is not — the read-back at
  `04:359-360` keys on `(ws, video, slot, state='pending')` and ignores the generation entirely.
  `g2 → exhausted`, `g3 → exhausted`, `g4 → exhausted` under `summary_max_attempts = 1`. The guardrail
  holds.
- **Round 10's population-ratchet Medium is neither fixed nor deferred.** `t_writes` still records
  `(kind, paid, slot, op)` (`05:101-105`) and the check is still `having count(*) > 1` on INSERTs
  (`05:1801-1805`), while the notice claims *"the SEQUENCE case is exercised"*. Codex re-filed it
  today; I am recording only that round 11 dropped it silently rather than deferring it in writing.

---

## On the invariants (Job 3)

**"The reservation guards SPENDING, not RECORDING" (user decision, 2026-08-07) — is round 11 a
violation?** For the case the decision was made about, no: P22's reclaimed writer still holds its
generation's token, still completes, still records (`05:1251-1269`, `recorded_after_loss`). Round 11
narrowed *who* may record without changing *whether* a payer may. But B1 is a second reading of the
same rule and it does violate the decision — a writer that paid is refused, and refused because of a
bookkeeping gap rather than because anything about its claim is wrong. So the decision stands and
round 11 honours it; B1 is a defect measured *against* it, not a re-litigation of it. Fixing B1
restores the invariant rather than trading it away.

**"Anything §12b forbids that a real caller will need."** §12b forbids recording without the token.
The measured problem is not that the rule is too strict — it is that the schema issues a token that
does not satisfy its own rule. §12b should say so explicitly: the obligation is to hold *the token
that reserved this generation*, and `reserve_artifact_slot` owes the caller the guarantee that the
token it returns **is** that token. Today it does not, and that guarantee is the thing worth writing
down.

---

**NOT CONVERGED** — 1 Blocking, 2 High.
