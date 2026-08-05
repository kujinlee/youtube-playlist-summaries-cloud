# Conditional Write on `persist_summary` — Design Spec

**Status:** v2 — revised after round 1 of dual adversarial review (**not converged**; round 2 pending)
**Backlog:** #17 (durable fix; partial mitigation shipped 2026-08-04 as PR #45)
**Task:** #19
**Round 1 reviews:** [`spec-conditional-write-codex-r1.md`](../../reviews/spec-conditional-write-codex-r1.md) ·
[`spec-conditional-write-claude-r1.md`](../../reviews/spec-conditional-write-claude-r1.md) ·
[`spec-conditional-write-live-probe.md`](../../reviews/spec-conditional-write-live-probe.md)
**Feeds:** [`2026-08-03-stable-blob-addressing-design.md`](2026-08-03-stable-blob-addressing-design.md) §5.1.

---

## 0. The idea in plain terms

**A worker writes to an address that someone else moved while it wasn't looking.**

The worker decides *where* a summary will be stored at the start of the job, then spends minutes
generating it. Sync can move that address in the meantime. Nobody checks, so the late write lands at
the old address and the row ends up half-right — pointing at one place while its paid dig files sit in
another.

**The fix is one sentence: don't write unless the address you read is still the address.**

That is a **conditional write** (compare-and-swap, "CAS"), and it is the same rule as `git push`
refusing a non-fast-forward: *if the thing moved since you looked, your write is stale — go re-read and
try again.* It costs two extra conditions on an `UPDATE`. The conditions together are the **address
guard**.

> **Terminology — this is NOT lease fencing.** "Fencing" is already taken in this codebase
> (`0008_jobs_queue.sql:94`, `0009:55`) and means the standard thing: a lease-token check that stops a
> stale lease-holder from acting. That mechanism **cannot** solve this problem, because the worker's
> lease never expires here — it stays valid the whole time, and what goes stale is the *address*, which
> no lease knows about. Backlog #17 is titled "fence the worker persist"; the title names the wrong
> mechanism and is kept only because it is referenced from commits, memory and the roadmap.

### Sources and the sink

| | | |
|---|---|---|
| **Sources** | The places that **move** an address | A3 relocation, `copyAdditiveVideo`, whatever gets added next |
| **Sink** | The one place a stale **summary** write lands | `persist_summary` |

There are several sources and there will be more. For the summary write there is exactly one sink.

**So guard the sink, not the sources.** Guarding sources means N guards that must each be written, each
be correct, and each be remembered by whoever adds source N+1. Guarding the sink means one guard that
is automatically right about sources nobody has thought of yet.

> **Scope of the one-sink claim (round 1, Claude M4 / Codex H3).** This holds for the **summary** write
> only. The **dig** write has the same exposure and a *different* sink — it is a blob write with no row
> to attach a condition to (`dig-handler.ts:119-125`), so nothing here protects it. Filed as
> **backlog #21**; see §9. Do not read "one sink" as "digs are covered."

### What the guard compares

`base = pad(serialNumber) + '_' + slugify(title)`. **Both halves can move, and both are guarded** — the
serial directly, the slug via the `summaryMd` key that carries it.

Round 1 (Claude H5) proved the slug half is a genuine race, not a bookkeeping detail:
`describeDivergence` compares **full bases**, not serials (`reconcile-serial.ts:150-155`), and the
comment at `:181-182` says so outright — *"Prefer local's ACTUAL base (serial **and** slug)."* So A3
relocates on a slug-only divergence with the serial **unchanged**. A serial-only guard passes straight
through that interleaving while the paid digs are moved and the old prefix deleted. An earlier draft of
this spec asserted the slug half "is not a race"; that was **false**, and correcting it is why the guard
has two conjuncts rather than one.

**What remains unguarded** is the *non-concurrent* slug case — a re-summarize after a title change with
no sync involved — because there is no second writer to detect. That is **backlog #20**.

---

## 1. The problem

The interleaving was confirmed in round 5 of `fix/serial-coherence-sync` (2026-08-03):

| Step | Actor | Effect |
|---|---|---|
| 1 | worker | `reserveVideoSlot` → serial `7`; pins `baseName = 007_alpha` (`summary-handler.ts:95-96`) |
| 2 | worker | transcription + Gemini — **minutes** |
| 3 | sync | A3 relocates: serial `7` → `3`, copies paid digs to `dig/003_alpha/`, deletes `dig/007_alpha/*` |
| 4 | worker | `persistSummary(…, video, 'committed')` (`summary-handler.ts:177`) |
| 5 | — | row = `serialNumber 3` **beside** `summaryMd 007_alpha.md`; digs stranded at `dig/003_alpha/` |

Step 5 is not cosmetic. `serialNumber` is what every subsequent reader derives the base from, so the
paid digs at `dig/003_alpha/` are unreachable from a row advertising `007_alpha.md`. Recovering them
costs fresh Gemini spend for content already paid for.

**The slug-only variant of the same table** (round 1, H5): step 3 becomes *"local's title changed;
`describeDivergence` → `from='007_alpha'`, `to='007_beta'`; digs copied to `dig/007_beta/`, old prefix
deleted; **`serialNumber` stays `7`**"*. Identical damage, identical mechanism, and invisible to a
serial-only guard.

### 1.1 Why the row ends up incoherent

**The address has two halves, and they come from two different places.** One is trusted to the row, the
other to the job — so when they disagree, nothing notices.

`persist_summary` (`0021_cloud_sync_signals.sql:99-153`) sources them from **different writers**, and
the asymmetry is deliberate on both sides:

- **`serialNumber` comes from the row.** The whitelist at layer (3) (`:120-132`) does not list it, so
  layer (2) — `|| (v.data - 'artifacts')` — restores the row's own value. This is by design: it is what
  stops a stale job payload reverting operational state a concurrent writer changed.
- **`summaryMd` comes from the payload.** Line `:133` resolves
  `coalesce(p_video->>'summaryMd', v.data->>'summaryMd')` — **payload wins**. Also by design: writing
  that key is the entire purpose of the job.

Neither rule is wrong alone. The defect is that nothing asserts the payload's key and the row's serial
describe the *same* base.

### 1.2 What the shipped mitigation does and does not close

PR #45 (`reconcile-serial.ts:239-251`) makes A3 refuse to relocate while a job for that video is
pending or recently swept. That closes the **wide** window — the minutes at step 2.

It does not close the residual one. The refusal is checked once, before the copy phase, and that copy
phase is a loop of N sequential blob round-trips (the loop is `reconcile-serial.ts:281-290`; the
comment describing it is `:231-236`). A job enqueued and claimed inside that span reads the
pre-relocation address and is invisible to a probe that already ran. The comment at `:236` states the
honest scope: *"a large reduction, not an elimination."*

Widening the freshness check cannot fix the residual: **when A3 checks, the worker has written
nothing.** Its write lands strictly afterwards. Only making that write conditional closes it.

---

## 2. Scope

**In scope:** a worker summary persist landing against a row whose **address** — `serialNumber` or the
`summaryMd` key carrying the slug — changed after the worker read it.

**Out of scope, each filed with a number** (see §9): the `transferClassA` content race (**#19**), the
non-concurrent title-change orphaning (**#20**), and the dig-write exposure (**#21**).

**Why this scope is smaller than backlog #17 assumed — guard the sink, not the sources.** That entry
says the fix "must cover the whole sync write path," listing `transferClassA` and `copyAdditiveVideo`
alongside A3. That is **half right**.

For the address race it is wrong, and the sizing follows from §0: those are all *sources*. Guarding
`persist_summary` guards the *sink*, the one place a stale summary write can land. One guard covers
every source at once, including sources not written yet.

For the content race it is right — but only because `transferClassA` is not a source in this sense: it
never moves the address, it replaces the *content* at an unchanged one (`sync-run.ts:397-432`, whose
`completeTuple` contains no `serialNumber`). Nothing at the sink can see that, which is precisely why it
is a different problem and a different spec.

---

## 3. Verified ground truth

Every claim was read from the code on 2026-08-04 and re-verified by two independent reviewers in round
1. Citations marked ✎ were **wrong in v1** and are corrected here.

| # | Fact | Evidence |
|---|---|---|
| G1 | `serialNumber` is **maintained by convention at every writer, not enforced by the schema** — there is no CHECK, no NOT NULL, no trigger. `reserve_video_slot` maintains it and raises `(invariant)` on an existing row that lacks it, and that raise is what keeps the worker path safe — but `SupabaseMetadataStore.upsertVideo` replaces `data` **wholesale** (`supabase-metadata-store.ts:113-121`), so a `Video` without the (optional) field erases the key | `0009:79-96`, insert `:95`, raise `:90`; `types/index.ts:67`; live probe: **154 of 2902 rows have no `serialNumber`**, 22 of them carrying a `summaryMd` |
| G2 | A bare reserved row has **no `summaryMd`** — only `id` and `serialNumber` | `0009:95` |
| G3 | `summaryMd` is payload-wins; `serialNumber` is row-wins | `0021:133` vs whitelist `:120-132` ✎ |
| G4 | Zero affected rows currently raises exactly one error: `persist_summary: no video row for %/%` | `0021:152` |
| G5 | The MD body does **not** embed its own base — `summaryCore` accepts `baseName` and deliberately never destructures it | `lib/ingestion/summary-core.ts:60-62` |
| G6 | The worker write sequence is stage → persist(committed) → promote → persist(promoted) | `summary-handler.ts:172-179` |
| G7 | `persistSummary` has exactly one **production** caller — but ~19 **test** call sites invoke the RPC by name and all break on an arity change (§4) | `worker-persistence.ts:18-27`; `summary-handler.ts:177,179`; `tests/integration/worker-persistence-rpcs.test.ts` (16 sites), `helpers/cloud.ts:118-125`, `worker-storage-bundle.test.ts:87` |
| G8 | `transferClassA` never writes `serialNumber` | `sync-run.ts:397-432` |
| **G9** | **`describeDivergence` compares FULL BASES, not serials** — so A3 relocates on slug-only divergence with the serial unchanged | `reconcile-serial.ts:150-155`; comment `:181-182` ✎ *new in v2* |
| **G10** | Every writer of `data->serialNumber` writes a JSON **number** (14 sites enumerated, SQL and TS); **0 of 2748** populated rows store a string | `0007:37`, `0009:95`, `0023:67,:89`, `types/index.ts:67`; live probe |
| **G11** | `jobs.max_attempts` defaults to **5**; a retryable throw after Gemini has metered keeps the reservation and requeues | `0008_jobs_queue.sql:14`; `worker-runner.ts:66-76` |

**G5 is load-bearing** for §6: because the bytes are base-independent, a re-address changes only the
destination key, never requiring regeneration.

**G2 is load-bearing** for §4: it is why the `summaryMd` conjunct must use `is not distinct from`
rather than `=`.

**G9 is load-bearing** for §0 and §4: it is the reason the guard is not serial-only.

---

## 4. The conditional write

**Two extra parameters in, two extra conditions on the `UPDATE`.** The worker says which address it
believes it holds; the write happens only if the row still agrees about **both halves**.

```sql
create function persist_summary(
  p_owner_id uuid, p_playlist_id uuid, p_video_id text,
  p_video jsonb, p_artifact_status text,
  p_expected_serial int,                     -- required, no default
  p_expected_summary_md text                 -- required; NULL is MEANINGFUL (bare row, G2)
) …
begin
  -- B1 (round 1): "required" in SQL means "must be supplied", NOT "must be non-NULL".
  -- to_jsonb(null::int) IS NULL, so a NULL serial would make the predicate NULL -> 0 rows ->
  -- misclassified as address-moved -> retried -> re-billed. Mirror claim_video_slot (0023:46-48).
  if p_expected_serial is null then
    raise exception 'persist_summary: p_expected_serial is required' using errcode = '22004';
  end if;
  -- NOTE: p_expected_summary_md has NO such check — NULL is the legitimate bare-row value.

  update videos v set …
   where v.playlist_id = p_playlist_id
     and v.video_id    = p_video_id
     and v.owner_id    = p_owner_id
     and v.data->'serialNumber' = to_jsonb(p_expected_serial)          -- serial half
     and v.data->>'summaryMd' is not distinct from p_expected_summary_md;  -- slug half
```

**Why `is not distinct from` for the second conjunct.** By G2 a bare reserved row has no `summaryMd`,
so the first-summary case compares NULL to NULL. Plain `=` yields NULL there and would reject **every
first-time write** — fail-closed, silent, and misclassified as a race. `is not distinct from` is the
null-safe equality and makes both cases one predicate. This is the shape v1 wrongly concluded was
impossible: §7 rejected keying on the *base string* because a bare row has no base to compare, which is
true — but comparing the **key including its absence** is well-defined.

**Why jsonb equality rather than a cast, honestly stated.** v1 argued `(v.data->>'serialNumber')::int`
"would raise on a malformed row" and called the jsonb form *"total."* Round 1 (Claude M1) showed that
rationale is wrong twice over: the same unguarded cast already exists at `0009:86` — inside
`reserve_video_slot`, the *first* call the §6 loop makes — so a serial malformed enough to raise raises
before this guard is consulted. And the jsonb form makes the **predicate** total, not the **operation**:
its real difference is that it is **silent** where the cast is loud. That is the correct reason to
choose it — *the predicate must distinguish "different" from "unreadable" instead of conflating them
into a raise* — and it is exactly why §5's `jsonb_typeof` branch must accompany it.

**Required, not defaulted.** A defaulted parameter would leave every existing call site silently
unguarded — the failure the last slice's rule was written against.

**Deploy safety — the 5-arg signature must survive, and must raise** (round 1, Claude H1). `fly.toml:32-34`
runs `web` and `worker` as two process groups from one image, and migrations apply **before** the
rollout completes, so old workers keep calling the 5-arg form for the length of the window. A `DEFAULT`
does not help: `0023:27-35` documents that **PostgREST resolves an RPC by the named arguments in the
request body**, and `0021:5-12` documents the sibling PGRST203 footgun. Dropping the old signature
outright means every in-flight persist from an old worker fails **after Gemini has been billed**, then
requeues and re-bills.

The resolution that satisfies both deploy safety and "no unguarded path": **keep the 5-arg signature and
make its body `raise`.**

```sql
create or replace function persist_summary(uuid, uuid, text, jsonb, text) returns void … as $$
begin
  raise exception 'persist_summary: caller must pass p_expected_serial/p_expected_summary_md'
    using errcode = '0A000';
end $$;
```

Old callers get a clean, classifiable error rather than a schema-cache miss, and no unguarded write can
ever land. Remove the stub in a later migration once no old image can be running.

**Grants do not survive a drop** (round 1, Claude H2). `0023:24-25` states the rule; the default for a
newly created function is EXECUTE to PUBLIC, so **omitting the grants fails open and silently** — every
legitimate caller still works, no test goes red. The migration must re-issue, mirroring `0021:154-155`:

```sql
revoke all on function persist_summary(uuid,uuid,text,jsonb,text,int,text) from public;
grant execute on function persist_summary(uuid,uuid,text,jsonb,text,int,text) to authenticated, service_role;
```

Impact is contained rather than critical — the function is `security invoker` and raises
`'not authorized'` at `0021:103` — but it is a hardening regression and a break from the pattern every
other migration follows.

---

## 5. Failure taxonomy — three outcomes, decided in one statement

**"I wrote nothing" has several possible reasons, and they need opposite responses.** Round 1 found v1's
two-way split both **incomplete** and **racy**: incomplete because the predicate is not-true for four
distinct states, and racy because v1 proposed re-probing *row existence* in a second statement, which
observes later state than the failed `UPDATE` did.

Measured states that yield zero rows:

| State | v1 classification | Correct |
|---|---|---|
| Row absent | fatal | **fatal** |
| Serial or key differs | retryable | **retryable** |
| `serialNumber` key absent from `data` (G1: 154 live rows) | *retryable* ❌ | **fatal** |
| Stored serial is not a JSON number | *retryable* ❌ | **fatal** |

The two ❌ rows are the expensive ones. Both route into retry, where `reserve_video_slot` raises
(`0009:86` cast, `:90` invariant) — a plain raise, not a `NonRetryableError`, so `worker-runner.ts:69-76`
requeues. With `max_attempts` = 5 (G11) that is **five full Gemini runs ≈ 40¢ ending in `dead_letter`
with no summary**, where today the same row succeeds on attempt 1 for 8¢. *The guard would make the money
outcome five times worse for that input, and it would look like the guard working.*

**The classification must therefore be decided by the same statement that observes the state**, inside
the function, under the row lock — the TOCTOU argument §4 already makes about the predicate, applied one
level up:

```sql
select v.data->'serialNumber', v.data->>'summaryMd'
  into v_actual_serial, v_actual_md
  from videos v
 where v.playlist_id = … and v.video_id = … and v.owner_id = …
   for update;                                    -- one snapshot, held for the decision

if not found then                                   raise … 'row-gone'         (FATAL)
elsif v_actual_serial is null
   or jsonb_typeof(v_actual_serial) <> 'number' then raise … 'serial-unusable' (FATAL)
elsif v_actual_serial <> to_jsonb(p_expected_serial)
   or v_actual_md is distinct from p_expected_summary_md then
                                                    raise … 'address-moved'    (RETRYABLE)
end if;
-- … then the guarded UPDATE, which cannot now fail for any of the above reasons
```

**The caller must map the two fatal codes to `NonRetryableError`.** Otherwise §5's "distinguishable by
the caller" is satisfied on paper while the caller still burns `max_attempts`. Distinct SQLSTATEs (or a
structured `detail`) are part of the contract, not diagnostics.

**Returning the observed address is preferable to a re-read** (round 1, Claude M5). Because the function
already has both values in hand, it should surface them in the error. The worker then needs **no
re-read at all** on the recovery path — one fewer round-trip, no extra lock, and the classification is
decided where the state was seen.

---

## 6. Recovery — bounded re-address

**Rejected doesn't mean wasted.** The summary is already generated and already paid for; only its
destination was wrong. So the worker re-files it under the new address instead of generating it again —
one blob round-trip versus roughly 8¢ of Gemini.

That works only because the MD bytes are base-independent (G5): the file does not contain its own name,
so the same bytes are valid under any address.

```
attempt (bounded, N = 3):
  if ctx.signal.aborted -> throw AbortError          # EVERY attempt, not just the first (H4)

  serial, currentMd := observed address              # from the rejection's payload (§5), no re-read
  baseName          := pad(serial) + '_' + slug(title)

  REBUILD the payload:                               # B2 — NOT reused from the first attempt
      video.serialNumber := serial
      video.summaryMd    := baseName + '.md'

  ref := putStaged(baseName + '.md'); verify staged

  if this is a RE-ADDRESS attempt (not the first):
      promote(ref)                                   # bytes land BEFORE metadata — see below
      persistSummary(..., expected := (serial, currentMd), 'promoted')
  else:
      persistSummary(..., expected := (serial, currentMd), 'committed')
      promote(ref)
      persistSummary(..., expected := (serial, currentMd), 'promoted')

  address-moved -> discard temp; next attempt
  row-gone / serial-unusable -> NonRetryableError
```

**The payload is rebuilt every attempt — this is the fix for a defect the v1 pseudocode invited**
(round 1, Claude B2). `summary-handler.ts:149-164` builds the `Video` literal **once**, carrying
`serialNumber: serial` (`:156`) and `summaryMd: \`${baseName}.md\`` (`:157`). v1's loop recomputed
`serial` and `baseName` but never mentioned `video`. An implementer following it literally would, on
attempt 2, pass `expected := 3` (matching, guard **passes**) while the payload still carried
`summaryMd: '007_alpha.md'` — and `0021:133` is payload-wins. The row would land as `serialNumber 3`
beside `summaryMd 007_alpha.md`: **byte-for-byte the incoherence in §1 step 5, produced by the fix, with
the guard green.**

**Re-address attempts promote before persisting metadata** (round 1, Codex B2 / Claude M3). The
monotonic-status rule at `0021:142-149` preserves `'promoted'` against a `'committed'` write **when the
key is unchanged**, and its comment (`:138-141`) states the assumption: *"A different key is a genuinely
new artifact."* A re-address makes the key the **same** as one A3 already wrote as `promoted`
(`reconcile-serial.ts:296`), so an intermediate `'committed'` write would be silently upgraded to
`'promoted'` while the bytes are still staged — beside Class-A scalars (`ratings`, `tldr`, `docVersion`)
freshly updated from the new payload. Not writing that intermediate record avoids it: the bytes are
durable first, then the metadata is advertised, which is strictly the safer ordering. **This is a
deliberate departure from G6's sequence and must be reviewed as such in round 2.**

**Abort is re-checked every attempt.** `summary-handler.ts:170` checks `ctx.signal.aborted` exactly once,
and its comment says why: *"don't start the irreversible blob/persist sequence"* if the lease was lost.
The loop re-enters that sequence up to three more times. A lost lease means `sweep_expired_leases`
(`0009:63-77`) requeues the job and a second worker starts Gemini concurrently — a double charge caused
by the fix for a stale write. The loop must also fit the wall-clock budget: the lease is 120 s
(`worker-runner.ts:25,28`), heartbeat ≈ 40 s (`:48-52`), hard abort at `wallClockMs` = 600 000 (`:45`).

**N = 3 is bounded by PR #45, not by taste** (round 1, Claude M5 supplies the justification v1 lacked).
While the job is `active`, `supabaseInFlightJobProbe` reports `inFlight` and A3 **refuses** to relocate
(`in-flight-job.ts:21,:116`), so a second relocation cannot occur *during* the loop. Attempt 2 therefore
faces a stable address in every interleaving we can construct; N = 3 is one spare. Exhausting the bound
throws retryable — the situation is transient — and each exhaustion is logged with both addresses,
because repeated exhaustion means something is relocating in a loop, which is a different bug.

**Cleanup, corrected.** A leaked *staging* object is inert and swept by existing staging cleanup. But
the second branch leaks differently: once `promote(ref)` has run, `<oldBase>.md` is a **promoted,
permanent** object that no staging sweep collects, and A3's cleanup will not catch it either — 
`reconcile-serial.ts:358-361` deletes only the plan computed from `paidKeysUnder` **before** the copy
phase, so a blob promoted after that enumeration is never in the plan. Small (storage, not loss), but
v1's sentence was factually wrong about the branch that actually leaks.

---

## 7. Migration to stable blob addressing

**The question: stable blob addressing is coming soon — can we build the guard the way that design wants
it, so the migration is free?**

**The answer: closer than v1 thought, and the throwaway is one line.**

The stable-blob-addressing design (§5.1) publishes through a manifest row with the conditional write
`update video_artifacts … where blob_key = <what I read>` — a guard on the **address string**. v1
concluded that shape was unavailable today because a bare reserved row carries no `summaryMd` (G2), so
there would be nothing on the left-hand side.

That reasoning was half wrong, and round 1's H5 forced the correction: comparing the key **including its
absence** (`is not distinct from`) is well-defined, and it is now the second conjunct. So this guard
already compares an address, exactly as the manifest CAS will — it simply compares a *derived* address
stored on the video row rather than an *authoritative* one stored in a manifest.

| Piece | At migration |
|---|---|
| Bounded re-address loop (§6) | unchanged |
| Three-way failure taxonomy decided in one statement (§5) | unchanged |
| Null-safe address comparison | unchanged — the manifest's `blob_key` is `not null`, so it simplifies |
| Test corpus — interleavings, mutation checks | retargeted, cases intact |
| Deploy-safe raising stub, grants discipline | unchanged as rules |
| **The two `where` conjuncts** | **replaced by one** — `blob_key = <what I read>` |

**This slice is also the first evidence for §5.1's central claim.** That section asserts a conditional
write on one small row is *"trivially sufficient"* — and **nothing in this codebase performs a
conditional publish today**, so the claim is untested. Round 1 already dented it: two Blockings arose
not from the predicate but from everything *around* it — NULL semantics, payload rebuild, status
inheritance, deploy windows. That is worth knowing before the manifest design leans on the word
"trivially."

---

## 8. Testing

The gate is not "the guard exists" but "the guard fires on the interleavings that motivated it, and the
recovery leaves a coherent row."

**Required — both races, end to end (integration).**
1. *Serial race:* reserve a slot, relocate the serial, persist with the stale address.
2. *Slug race (G9):* reserve a slot, relocate with the **serial unchanged and only the slug moved**,
   persist with the stale address. This one passes trivially against a serial-only guard, so it is the
   test that proves the second conjunct.

Both assert the row is coherent **and** the paid dig keys under the new base are still reachable.
Asserting only that the RPC raised would pass in a world where the digs are still stranded.

**Required — positive assertions after a successful re-address** (B2). Not "the row is not incoherent"
but: `data->>'summaryMd'` **equals** `<newBase>.md` **and**
`data->'artifacts'->'summaryMd'->>'key'` **equals** `<newBase>.md`. v1's wording was satisfiable by a
test that only checked the RPC raised.

**Required — one test per §5 outcome**, asserting the caller can *distinguish* them, and that both fatal
codes map to `NonRetryableError` rather than requeueing.

**Required — the `serialNumber`-absent row** (G1: 154 live rows). Assert a clean non-retryable failure,
**not** a retry storm. This is the state that would otherwise cost 40¢.

**Required — NULL `p_expected_serial`** raises rather than silently matching zero rows.

**Required — the re-address loop terminates.** A relocation on every attempt exhausts the bound and
throws retryable, without spinning.

**Required — mutation checks, one per conjunct.** Delete the serial conjunct → the serial-race test MUST
go red. Delete the `summaryMd` conjunct → the **slug**-race test MUST go red. Restore. Per the standing
rule, **commit the fix before mutating** — `git checkout` has reverted uncommitted work three times on
this project. A guard that passes in both worlds is not a guard, and with two conjuncts it is possible
for one to be dead while the suite stays green.

**Required — the money claim, stated honestly** (round 1, L1). Assert Gemini runs exactly once across a
successful re-address, **and** assert the exhaustion path. The honest bound: `jobs.reserved_cents` is
per-job and reused across retries (`0020_reservation_release.sql`), so there is **no second
reservation** — but there can be up to `max_attempts` **real** Gemini charges against one reservation,
i.e. the ledger **under-counts actual spend** on this path. That is the claim to assert, not "no double
charge."

**Required — the arity migration.** All ~19 named-argument call sites (G7) updated in the same commit,
plus one test that the 5-arg stub raises rather than writing.

---

## 9. Out of scope — each with a number

| # | What | Why separate |
|---|---|---|
| **19** | `transferClassA` content race | Replaces content at an **unchanged** address; invisible to an address guard. Loses a sync decision, not paid blobs, and self-heals next run |
| **20** | Non-concurrent title-change orphaning | No second writer and no window, so nothing to compare against. This spec closes its **concurrent** half (§0) |
| **21** | Dig-write exposure | Same damage, **different sink**: a blob write with no row to attach a condition to (`dig-handler.ts:119-125`). Needs a different mechanism |

Also out of scope: any change to A3's in-flight probe (PR #45 and this guard are complementary — the
probe narrows the window, the guard closes what remains); the local pipeline (`persist_summary` is a
Supabase RPC and local has no concurrent sync writer); `videos.position` (A6b); the manifest itself.

---

## 10. Open questions

Round 1 **closed three** of v1's questions; they are recorded here rather than deleted, because the
answers are load-bearing.

| v1 question | Status |
|---|---|
| Is `reserveVideoSlot` safe inside the retry loop? | **CLOSED — yes, and it is no longer used there.** Both reviewers independently disproved the deadlock concern: each PostgREST RPC is its own transaction so the `for update` at `0009:84` is acquired and released within one call, and A3's metadata write (`merge_video_data`, `0021:71-72`) takes no such lock. §5 removes the re-read anyway |
| Does anything call `persistSummary` positionally? | **CLOSED — wrong question.** Nothing does; ~19 sites call **by name**, and PostgREST resolves by name, so all break at runtime invisibly to `tsc` (G7) |
| Should the guard cover `docVersion`? | **CLOSED — no.** A version mismatch is already handled non-retryably at `summary-handler.ts:73-77`, and `docVersion` is not part of `base`, so a relocation cannot strand blobs through it |

Genuinely open for round 2:

1. **Is promote-before-metadata on re-address (§6) the right resolution of the status-inheritance
   problem?** It departs from G6's established ordering. The alternative — teaching the monotonic rule to
   distinguish "same key, different artifact" — needs an artifact identity the row does not carry today,
   which is precisely what the manifest introduces. Confirm the departure is safe rather than merely
   convenient.
2. **Should `serial-unusable` self-heal instead of failing?** 154 live rows are in that state. A fatal
   error is correct for *this* write, but it leaves the row permanently unsummarizable. Repair may belong
   to a separate migration rather than to the worker.
3. **Does PostgREST return PGRST202 (not PGRST203) for a 5-key body against a 6-arg signature?** §4's
   deploy argument rests on documented behaviour from `0023:27-35`, not on a measurement — the local edge
   runtime was stopped. One live probe before implementation.

---

## 11. Verification

- `python3 scripts/check-docs.py` from the repo root (it resolves paths from `__file__`) — **run,
  passing**.
- `grill-with-docs` terminology pass — **run 2026-08-04**. Outcome: the mechanism was renamed from
  "fence" to **conditional write** / **address guard**, because "fencing" was already taken for lease
  fencing (`0008_jobs_queue.sql:94`); and `CONTEXT.md` gained an **Addressing** section defining *base*,
  *serial number*, *slug*, *conditional write* and *lease fencing*, none of which were defined despite
  being load-bearing across two specs.
- Dual adversarial review to convergence — **round 1 complete, NOT converged** (2 Blocking + 2 High +
  1 Medium from Codex; 2 Blocking + 5 High + 6 Medium + 3 Low from Claude). Round 2 is mandatory: the
  standing rule is that any round returning a Blocking earns another, and the fixes above are themselves
  new unreviewed design.
- Standing root-cause shapes to carry into round 2, all of which **hit** in round 1:
  *absent-vs-failed conflation* (the predicate had four false-cases and a two-case taxonomy);
  *a guard with no covering test* (no assertion on the payload key after re-address);
  *a value read in one process and written in another* (the abort signal);
  *an optional member that does not propagate* ("required" in SQL does not mean non-NULL).
