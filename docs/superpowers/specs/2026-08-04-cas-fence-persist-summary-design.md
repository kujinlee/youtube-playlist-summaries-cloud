# Conditional Write on `persist_summary` — Design Spec

**Status:** v3 — revised after review round 2 (**not converged**; round 3 pending)
**Backlog:** #17 (durable fix; partial mitigation shipped as PR #45) · **Task:** #19
**Review trail:** round 1 [codex](../../reviews/spec-conditional-write-codex-r1.md) ·
[claude](../../reviews/spec-conditional-write-claude-r1.md) ·
[live probe](../../reviews/spec-conditional-write-live-probe.md) — round 2
[codex](../../reviews/spec-conditional-write-codex-r2.md) ·
[claude](../../reviews/spec-conditional-write-claude-r2.md) ·
[coordinator](../../reviews/spec-conditional-write-coordinator-r2.md)
**Feeds:** [stable blob addressing](2026-08-03-stable-blob-addressing-design.md) §5.1.

---

## 0. The idea in plain terms

**A worker writes to an address that someone else moved while it wasn't looking.**

The worker decides *where* a summary will be stored at the start of the job, then spends minutes
generating it. Sync can move that address in the meantime. Nobody checks, so the late write lands at
the old address and the row ends up half-right — pointing at one place while its paid dig files sit in
another.

**The fix: don't write unless the address you read is still the address.** That is a **conditional
write** (compare-and-swap), the same rule as `git push` refusing a non-fast-forward.

> **Not lease fencing.** "Fencing" is taken in this codebase (`0008_jobs_queue.sql:94`, `0009:55`) for
> the lease-token check. That cannot solve this: the worker's lease stays valid throughout; what goes
> stale is the address, which no lease knows about. Backlog #17's title names the wrong mechanism and
> is kept only because commits and memory reference it.

### Sources and the sink

**Sources** move an address (A3 relocation, `copyAdditiveVideo`, whatever comes next). The **sink** is
where a stale summary write lands: `persist_summary`. Several sources, one sink — so guard the sink.
One guard is automatically right about sources nobody has written yet.

> **Scope of that claim.** True for the **summary** write only. The **dig** write has the same exposure
> and a *different* sink — a blob write with no row to attach a condition to (`dig-handler.ts:119-125`).
> Filed as **backlog #21**. Do not read "one sink" as "digs are covered."

### Precisely what is guarded — the two halves are NOT symmetric

`base = pad(serialNumber) + '_' + slugify(title)`. Both halves are compared, but they mean different
things, and conflating them produced the worst defect of round 2 (B-N1):

| Half | Who can change it | What the guard detects |
|---|---|---|
| `serialNumber` | **Not the worker** — row-wins; the whitelist at `0021:120-132` omits it | **any** change |
| `summaryMd` | **The worker, as its whole purpose** — payload-wins at `0021:133` | only a change **the worker did not make** |

So: *the serial is guarded against any change; the key is guarded only against a change this worker did
not make.* That is exactly the property needed to catch a concurrent relocation, and it is why the
expected key **is not constant across the write sequence** (§6).

Round 1 (H5) proved the slug half is a genuine race: `describeDivergence` compares **full bases**
(`reconcile-serial.ts:150-155`; the comment at `:181-182` says *"serial **and** slug"*), so A3 relocates
on slug-only divergence with the serial unchanged. A serial-only guard passes straight through that.

**Unguarded, deliberately:** a re-summarize that moves the key *itself* after a title change, with no
sync involved — there is no second writer to detect. That is **backlog #20**.

---

## 1. The problem

Confirmed in round 5 of `fix/serial-coherence-sync`:

| Step | Actor | Effect |
|---|---|---|
| 1 | worker | `reserveVideoSlot` → serial `7`; pins `baseName = 007_alpha` (`summary-handler.ts:95-96`) |
| 2 | worker | transcription + Gemini — **minutes** |
| 3 | sync | A3 relocates `7 → 3`; copies paid digs to `dig/003_alpha/`, deletes `dig/007_alpha/*` |
| 4 | worker | `persistSummary(…, 'committed')` (`:177`) |
| 5 | — | row = `serialNumber 3` beside `summaryMd 007_alpha.md`; digs stranded |

**Slug-only variant:** step 3 becomes *"title changed; `from='007_alpha'`, `to='007_beta'`; digs moved;
**serial stays 7**"* — identical damage, invisible to a serial-only guard.

### 1.1 Why the row ends up incoherent

The address's two halves come from different writers, deliberately on both sides: `serialNumber` is
restored from the row by layer (2) (so a stale payload cannot revert concurrent state), while
`summaryMd` is `coalesce(p_video->>'summaryMd', v.data->>'summaryMd')` at `0021:133` — payload wins,
because writing that key is the job's purpose. Neither rule is wrong alone. Nothing asserts they
describe the *same* base.

### 1.2 What PR #45 does not close

PR #45 (`reconcile-serial.ts:239-251`) makes A3 refuse to relocate while a job is pending — closing the
**wide** window. The residual remains: the refusal is checked once, before a copy phase that is N
sequential blob round-trips (loop at `:281-290`), so a job claimed inside that span reads the
pre-relocation address and is invisible to a probe that already ran (`:236` — *"a large reduction, not
an elimination"*). Widening the check cannot help: **when A3 checks, the worker has written nothing.**

---

## 2. Scope

**In:** a worker summary persist landing against a row whose address changed after the worker read it.

**Out, each numbered** (§9): `transferClassA` content race (**#19**), non-concurrent title-change
orphaning (**#20**), dig-write exposure (**#21**).

Backlog #17 says the fix "must cover the whole sync write path." That is **half right**: those are all
*sources*, and guarding the sink covers them at once. It is right about `transferClassA` only because
that is not a source at all — it replaces *content* at an unchanged address (`sync-run.ts:397-432`,
whose `completeTuple` has no `serialNumber`), which nothing at the sink can see.

---

## 3. Verified ground truth

Read from code and re-verified by two independent reviewers across two rounds. ✎ = corrected after v1.

| # | Fact | Evidence |
|---|---|---|
| G1 | `serialNumber` is **maintained by convention, not enforced** — no CHECK, no NOT NULL, no trigger. `reserve_video_slot` maintains it and raises on an existing row lacking it; `upsertVideo` replaces `data` **wholesale** so an absent optional field erases it | `0009:79-96`; `supabase-metadata-store.ts:113-121`; live probe: **154 of 2902 rows lack it**, 22 with a `summaryMd` ✎ |
| G2 | A bare reserved row has **no `summaryMd`** — only `id` and `serialNumber` | `0009:95` |
| G3 | `summaryMd` payload-wins; `serialNumber` row-wins | `0021:133` vs `:120-132` ✎ |
| G4 | Zero affected rows today raises one error, classified **retryable** by the runner | `0021:152`; `worker-runner.ts:76` |
| G5 | The MD body does not embed its base — `summaryCore` accepts `baseName` and never destructures it | `summary-core.ts:60-62` |
| G6 | Write sequence: stage → persist(committed) → promote → persist(promoted) | `summary-handler.ts:172-179` |
| G7 | One **production** caller; **18** named-arg RPC sites total break on an arity change | `worker-persistence.ts:22`; `worker-persistence-rpcs.test.ts` (16), `helpers/cloud.ts:118` ✎ |
| G8 | `transferClassA` never writes `serialNumber` | `sync-run.ts:397-432` |
| G9 | `describeDivergence` compares **full bases**, so A3 relocates on slug-only divergence | `reconcile-serial.ts:150-155`, comment `:181-182` |
| G10 | Every writer of `data->serialNumber` writes a JSON **number**; **0 of 2748** store a string | 14 sites; live probe |
| G11 | `jobs.max_attempts` defaults to **5**; a retryable throw after metering keeps the reservation and requeues | `0008:14`; `worker-runner.ts:66-76` |
| **G12** | **`SupabaseBlobStore.promote` is create-if-absent**: if the destination exists it **deletes the staged bytes** and returns void. `LocalBlobStore` renames (overwrites). `transferClassA` already hit this and uses `blob.put()` instead | `supabase-blob-store.ts:90-97`; `local-blob-store.ts:58-62`; precedent + comment `sync-run.ts:386-395` ✎ *new in v3* |
| **G13** | **`'committed'` is not bookkeeping** — the serve path returns **503 "not ready"** for it, and the UI derives `summaryReady` from `'promoted'`. It publishes the key while declaring the artifact unservable | `serve-summary-core.ts:50`; `supabase-metadata-store.ts:54-55` ✎ *new in v3* |
| **G14** | **PostgREST resolves overloads by named arguments** — measured live with both signatures present: 5-key body → 5-arg, 7-key → 7-arg, **no PGRST203**. A key omitted from the body → **PGRST202/404**, so `undefined` (which `JSON.stringify` drops) is *not* `null` | measured 2026-08-04 by coordinator and reviewer independently ✎ *new in v3* |
| **G15** | **`create or replace` cannot change parameter names** — *"cannot change name of input parameter"* (measured). A positional-only replacement aborts the migration; a name-less recreate is unroutable by PostgREST | measured; `0023:27-35` ✎ *new in v3* |

---

## 4. The conditional write

Two required parameters; the classifier in §5 does the work.

```sql
create function persist_summary(
  p_owner_id uuid, p_playlist_id uuid, p_video_id text,
  p_video jsonb, p_artifact_status text,
  p_expected_serial int,             -- required AND non-null (checked)
  p_expected_summary_md text,        -- required; NULL is MEANINGFUL (bare row, G2)
  p_artifact_is_new boolean default false   -- see §6: suppresses promoted-inheritance on re-address
) …
  if p_expected_serial is null then
    raise exception 'persist_summary: p_expected_serial is required' using errcode = '22004';
  end if;
```

**Required is not non-null, and required is not present.** Two distinct traps, both measured:
"required" in PostgreSQL means *supplied*, not *non-NULL* — hence the explicit raise, mirroring
`0023:46-48`. And in PostgREST, supplied means **the key is present in the request body** (G14) —
`JSON.stringify` drops `undefined` keys, so the TS wrapper **must coerce**:

```ts
p_expected_summary_md: expectedSummaryMd ?? null
```

Without it the bare-row case (where `existing?.summaryMd` is `undefined`) sends a 6-key body and gets
**PGRST202/404 after Gemini has been billed**. `tsc` will not catch it: `readVideo` returns
`data.data as Video` — an unchecked cast — so the type claims `string | null` while the runtime value is
`undefined`.

**Why jsonb equality rather than a cast.** Not because the cast "would raise" — the same unguarded cast
already runs first inside `reserve_video_slot` (`0009:86`). The honest reason: the predicate must
distinguish *different* from *unreadable* instead of collapsing both into a raise. That is why §5 has an
explicit `jsonb_typeof` branch.

**Deploy safety — the 5-arg signature survives as a raising stub, with its parameter NAMES preserved**
(G15). `fly.toml:32-34` runs `web` and `worker` from one image and migrations apply before rollout
completes, so old workers keep calling the 5-arg form.

```sql
-- Names MUST match 0021:99 exactly; `create or replace` cannot rename parameters (G15),
-- and a name-less function is unroutable by PostgREST (G14).
create or replace function persist_summary(
  p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text
) returns void language plpgsql as $$
begin
  raise exception 'persist_summary: caller must supply p_expected_serial/p_expected_summary_md'
    using errcode = '0A000';
end $$;
```

`create or replace` **preserves** the existing grants (`0021:154-155`), so the stub needs none. The new
7-arg signature does: grants do **not** survive a create, and the default is EXECUTE-to-PUBLIC, so
omitting them **fails open silently** — every legitimate caller still works and nothing goes red.

```sql
revoke all on function persist_summary(uuid,uuid,text,jsonb,text,int,text,boolean) from public;
grant execute on function persist_summary(uuid,uuid,text,jsonb,text,int,text,boolean) to authenticated, service_role;
```

---

## 5. Classification — three outcomes, one statement, named codes

Zero affected rows means four different things, and v1's two-way split routed two of them into the
bucket that spends money: `reserve_video_slot` then raises plainly (`0009:86`, `:90`), the runner
classifies retryable, and with `max_attempts` = 5 (G11) that is **five Gemini runs ≈ 40¢ ending in
`dead_letter`**, where today the same row succeeds for 8¢.

Classification is therefore decided **inside the function, in the same statement that observes the
state, under the row lock** — v1's separate re-probe observed later state than the failed `UPDATE`:

```sql
select v.data->'serialNumber', v.data->>'summaryMd'
  into v_actual_serial, v_actual_md
  from videos v
 where v.playlist_id = … and v.video_id = … and v.owner_id = …
   for update;                                   -- one snapshot, held for the decision

if not found then                                  raise … errcode 'PS001'  -- row-gone       FATAL
elsif v_actual_serial is null
   or jsonb_typeof(v_actual_serial) <> 'number' then raise … errcode 'PS002' -- serial-unusable FATAL
elsif v_actual_serial <> to_jsonb(p_expected_serial)
   or v_actual_md is distinct from p_expected_summary_md then
                                                   raise … errcode 'PS003'  -- address-moved  RETRYABLE
end if;
```

**The contract is the code, not the message.** Three distinct `errcode`s; the observed address rides in
`detail` as `{"serialNumber":…, "summaryMd":…}` (JSON, so the worker parses rather than scrapes).
`supabase-js` surfaces these as `error.code` and `error.details`. Matching on message text is
forbidden — it is what naming the codes exists to prevent.

**The caller maps `PS001`/`PS002` to `NonRetryableError`.** Otherwise "distinguishable by the caller" is
satisfied on paper while the caller still burns `max_attempts`.

**Behaviour change to record** (L-N2): a zero-row persist is retryable today (G4); `row-gone` becomes
fatal. That is the right direction — a cascade-deleted playlist never returns — but it is a live change
to an existing error path.

**No deadlock, no RLS change** — measured both rounds. No transaction anywhere takes `videos → playlists`
(`persist_summary` takes no `playlists` lock; `0021:104` is a bare `perform 1`), so there is no cycle.
`videos` has one forced `FOR ALL` policy, so `FOR UPDATE` applies the same `USING` the `UPDATE` already
did; `service_role` bypasses RLS and the worker uses it.

---

## 6. The write sequence

Round 2 found **three** Blockings here — every one of them in the recovery path, none in the predicate.
The sequence below is specified in full because prose invited each of them.

```
attempt (bounded, N = 3):
  if ctx.signal.aborted -> throw AbortError                    # EVERY attempt (H4)

  # ── the observed address: WHERE IT COMES FROM (B-R3-1) ─────────────────────
  # Attempt 1:  observedSerial    := reserveVideoSlot(...)     # NOT the :84 read — see below
  #             observedSummaryMd := existing?.summaryMd ?? null   # the :84 read; null on a bare row
  # Attempt 2+: both := PS003's `detail`, which is a SINGLE snapshot under the row lock (§5)
  #
  # ATTEMPT 1's TUPLE IS A TORN READ, and the spec must not pretend otherwise. The serial comes
  # from reserveVideoSlot (`:95`) and the key from the `:84` read — two statements, two snapshots.
  # A relocation landing between them yields a tuple that never simultaneously existed, so the
  # guard rejects with PS003. That is CORRECT (a relocation did occur) and self-correcting
  # (attempt 2 uses one atomic snapshot), but it means attempt 1 can fail for a reason no single
  # observed state explains. Do not "fix" it by widening the :84 read to also supply the serial:
  # reserveVideoSlot is what CREATES the row on a first ingest, so its serial is the only one that
  # exists at that point (G2).
  #
  # Both values are coerced `?? null` at the wrapper. §4 originally mandated this for the key only;
  # `p_expected_serial` needs it just as much — `undefined` is dropped by JSON.stringify, and a
  # 6-key body is PGRST202/404 *after Gemini has been billed* (G14).

  # ── the destination: ADOPT, never re-derive from stale inputs (C1) ──────────
  if observedSummaryMd is not null:
      baseName := adoptBase(observedSummaryMd)                 # VALIDATED — see below
  else:
      baseName := pad(observedSerial) + '_' + slug(payload.title)   # first summary only (G2)
  key := baseName + '.md'

  REBUILD the payload every attempt (B2):
      video.serialNumber := observedSerial
      video.summaryMd    := key

  ref := putStaged(key); verify staged bytes

  # ── publish: committed -> durable -> promoted, ALWAYS (H-N3) ────────────────
  persistSummary(..., expected := (observedSerial, observedSummaryMd),
                 status := 'committed', artifactIsNew := isReAddress)
  publish(ref, key)                                            # see "durability" below (B-N2/G12)
  persistSummary(..., expected := (observedSerial, key),        # ← NOTE: `key`, not observedSummaryMd
                 status := 'promoted')

  on PS003 -> discard temp; observed := PS003.detail; next attempt
  on PS001 / PS002 -> NonRetryableError
```

**The expected key changes mid-sequence, and that is the whole of B-N1.** The `'committed'` persist is
the write that *sets* `summaryMd` (payload-wins, `0021:133`). Passing the same expected value to the
`'promoted'` persist means comparing the pre-write value against the post-write row — which fails for
**every first-time summary** (bare row: `NULL` expected vs `'007_alpha.md'` actual → rejected) and every
title-changed re-summarize. It fails *silently*, classified as `address-moved`, so the dominant path
would quietly run the recovery loop, the `'committed'` record would never be written, and `address-moved`
would carry no information. The second persist must expect **the key the first one just wrote**. This is
the asymmetry §0 names: the serial the worker cannot move, the key it moves by design.

**Durability must overwrite, and `promote` does not** (G12, now confirmed against live storage: `move`
onto an existing destination returns **409 Duplicate**; `put` with upsert overwrites). On a re-address
the destination **always** exists, because A3's copy phase writes `${newBase}.md` before advancing
metadata (`:281-290`, `:293-296`) — and `promote` then **deletes the staged new bytes and returns
void**. The row would advertise `promoted` over A3's *old* body with the fresh Gemini output discarded,
silently, with pointer-level assertions passing.

So `publish(ref, key)` uses `put`, as `transferClassA` already does for this exact reason
(`sync-run.ts:386-395`). **But `put` is a second write, and that forfeits the property the staged
verify was buying** (B-R3-3): the object that was verified is the *temp*; the final key receives a
fresh, unverified upload. `putStaged → verify → promote` was safe because finalisation *moved* the
verified object. `putStaged → verify → put` proves nothing about what ends up at the final key.

**`publish` must therefore verify after writing, not before:**

```
publish(ref, key):
    put(key, stagedBytes)                 # atomic upsert, overwrites on both backends
    readBack := get(key)
    if readBack is null or mdHash(readBack) != mdHash(stagedBytes):
        throw            # do NOT persist 'promoted'; the row stays 'committed' → 503 → retry repairs
    delete(ref.tempKey)   # best-effort
```

This is not a new invention: `copyBlob` already verifies after write for precisely this reason
(`blob-store.ts:161-171` — *"an unproven copy is not a copy"*). Note the precedent this spec cited,
`transferClassA`, does **not** verify after its `put` — so copying it uncritically would have inherited
an unverified write on a money path. That is a defect in `transferClassA` worth its own entry, not a
pattern to follow.

**`'committed'` is retained** — round 2 answered v2's open question against it. It is not bookkeeping:
the serve path returns **503 "not ready"** for `committed` (G13). That 503 *is* what makes the ordering
safe — the only window in which the row can point at unpromoted bytes is a window in which readers are
told to wait. Dropping it (v2's proposal) replaced a **visible, non-serving** crash window with a
**silent** one: die between publish and the final persist and the serve path returns **200** with the
new body beside A3-era scalars, and the idempotency skip at `summary-handler.ts:86-92` can freeze that
state permanently.

**Promoted-inheritance is fixed narrowly instead** (round 1 M3 / C-B2). The key-scoped rule at
`0021:142-149` preserves `'promoted'` against a `'committed'` write **when the key is unchanged**,
assuming — per its own comment at `:138-141` — that *"a different key is a genuinely new artifact."* A
re-address makes the key the same while the artifact is new, falsifying that. `p_artifact_is_new`
(passed true only on a re-address, where the worker has *just been told* the address moved) suppresses
the preservation, so the row correctly reads `committed` → 503 → until publish lands. Briefly
downgrading a servable A3 copy is the honest cost, and it is the same 503 the normal path already uses.

**N = 3 is a choice, not a derivation.** v2 justified it from PR #45's probe — but §1.2 refutes exactly
that reasoning for the first relocation, and an A3 run past its probe completes regardless. The honest
statement: three attempts, chosen because each costs one blob round-trip while exhaustion costs a
requeue and a fresh ~8¢ Gemini run. Exhaustion throws retryable and logs both addresses; repeated
exhaustion means something is relocating in a loop, which is a different bug.

**Cleanup.** A leaked staging object is inert and swept. The `publish`-then-rejected branch leaks
differently: `<oldBase>.md` is a permanent object no staging sweep collects, and A3's cleanup will not
either — `reconcile-serial.ts:358-361` deletes only the plan computed **before** the copy phase.

**`baseOf` should be shared.** It is module-private at `reconcile-serial.ts:84-86` and duplicated inline
at `dig-handler.ts:57`. This slice adds a third caller; extract it.

---

## 7. Migration to stable blob addressing

The manifest CAS is `update video_artifacts … where blob_key = <what I read>` — a guard on the address
string. v1 wrongly concluded that shape was unavailable today; comparing the key **including its
absence** is well-defined, and is now the second conjunct. So this guard already compares an address —
a *derived* one on the video row rather than an *authoritative* one in a manifest.

| Piece | At migration |
|---|---|
| Adopt-the-observed-address recovery, publish semantics, abort checks | unchanged |
| Classifier structure | **narrows** to two outcomes — a `not null` `blob_key` has no `serial-unusable` state |
| Test corpus | retargeted, cases intact |
| Deploy stub, grants, named-errcode discipline | unchanged as rules |
| The two comparisons | **replaced by one** |

**This slice is the first evidence for §5.1's claim** that a conditional write is *"trivially
sufficient."* Two rounds have now produced **six Blockings, none in the predicate** — all in NULL
semantics, payload rebuild, publish semantics, status inheritance and the deploy window. The write is
trivial; the protocol around it is not. The manifest design should not lean on that word.

---

## 8. Testing

Round 2 showed v2's list was satisfiable while the defect shipped: it asserted **pointers** where the
loss was in **bytes**, and mandated mutating a construct that is unreachable as a guard.

**Races, end to end.** (a) serial moved; (b) **slug moved with the serial unchanged** — the test that
proves the second comparison, and which passes trivially against a serial-only guard. Both assert row
coherence **and** that paid dig keys under the new base are reachable.

**Bytes, not pointers.** After a successful re-address, `get(<newBase>.md)` **equals the newly generated
MD**. Every re-address test runs with `promoteSemantics: 'create-if-absent'`
(`in-memory-blob-store.ts:52` defaults to `'overwrite'`, the *local* behaviour — the non-production one)
or against real Supabase. Also assert the pointers (`data->>'summaryMd'` and
`artifacts.summaryMd.key`), which remain necessary but insufficient.

**The normal path never enters the loop.** A plain first-time summary completes with **one**
`'committed'` persist, **one** publish, **one** `'promoted'` persist, and **zero** `address-moved`
rejections. This is the test that catches B-N1; every race test passes without it.

**Mutation checks target the classifier, not the `where`.** After §5 the `UPDATE`'s conjuncts are
unreachable as guards — deleting both leaves every test green. Mutate each `elsif` branch instead. And
because A3 always moves **both** halves (`reconcile-serial.ts:293-295`), the serial branch needs a
**serial-only** move constructed directly in the fixture (modelling `claim_video_slot:65-68`, not A3);
otherwise deleting the serial check leaves the race tests green. **Commit before mutating** — `git
checkout` has reverted uncommitted work three times here.

**Per-outcome, by code.** One test per `PS001`/`PS002`/`PS003`, asserting the caller distinguishes them
by `error.code` and that the two fatal codes map to `NonRetryableError`.

**Wrapper-level nullability.** The bare-row case exercised **through the TS wrapper**, not a raw
`admin.rpc` with a hand-written `null` — that is the only way the `?? null` coercion is under test.

**Grants.** After migration, `has_function_privilege('anon', 'persist_summary(uuid,uuid,text,jsonb,text,int,text,boolean)', 'EXECUTE')` is **false**. Without this the H2 fix has no covering test and its failure mode is silence.

**Also required:** the `serialNumber`-absent row yields a clean non-retryable failure, not a retry storm
(154 live rows); NULL `p_expected_serial` raises; abort honoured on **every** attempt; the loop
terminates under repeated relocation; both signatures live simultaneously with the 5-arg stub raising;
all 18 named-arg call sites updated in the same commit.

**Money, stated honestly.** Gemini runs exactly once across a successful re-address, **and** the
exhaustion path is asserted: `jobs.reserved_cents` is per-job and reused across retries (`0020`), so
there is no second *reservation* — but up to `max_attempts` real charges land against one, i.e. the
ledger **under-counts actual spend**. That is the claim to assert, not "no double charge."

**Not covered, and named as such:** the crash window between publish and the `'promoted'` persist, and
the wall-clock interaction between the loop and the 120 s lease. Both are structural arguments, not
measurements.

---

## 9. Out of scope

| # | What | Why separate |
|---|---|---|
| **19** | `transferClassA` content race | Replaces content at an **unchanged** address; invisible to an address guard. Loses a sync decision, not paid blobs; self-heals next run |
| **20** | Non-concurrent title-change orphaning | No second writer, so nothing to compare against. The **concurrent** half is closed here |
| **21** | Dig-write exposure | Same damage, **different sink** — a blob write with no row to condition on |

Also out: A3's in-flight probe (complementary — probe narrows, guard closes); the local pipeline
(`persist_summary` is a Supabase RPC); `videos.position` (A6b); the manifest.

---

## 10. Open questions

**Closed across rounds 1–2, with the answers kept:** `reserveVideoSlot` in a retry loop is safe (no
deadlock — re-verified twice) and is no longer used there; the positional-caller question was the wrong
question (all 18 sites call by **name**); `docVersion` is out of scope (`summary-handler.ts:73-77`, and
it is not part of `base`); PostgREST overload resolution is unambiguous (**measured**, G14); and
promote-before-metadata is **not** safe — `'committed'` carries the 503 window (G13), so the ordering
stays and inheritance is fixed narrowly instead.

Open for round 3:

1. **`p_artifact_is_new` — ANSWERED: NO, it is not safe. The circularity is real.** Both round-3
   reviewers reached this independently, which per the standing rule makes it high-confidence.

   The refutation of the coordinator's counter-argument matters and is recorded so it is not
   re-derived: it was argued that the address guard *subsumes* the monotonic rule, since a stale caller
   can no longer reach the `UPDATE`. **That is wrong.** A caller can be stale in **content** while its
   **address never moved** — it generated bytes minutes ago against an address nobody has touched. Such
   a caller passes the guard cleanly, and the flag then lets it disable the one defence aimed at it.
   Combined with `publish = put` (which overwrites unconditionally), that converts a stale write from
   *non-corrupting* into *destructive*. Measured window: the heartbeat fires every `leaseSeconds/3` =
   **40 s** (`worker-runner.ts:47-52`), so a worker can run that long past lease loss with
   `ctx.signal.aborted` still `false`.

   A second, independent defect in the same parameter (Codex round 3): a **same-key re-summarize** at a
   new `docVersion` is *also* a new artifact, yet §6 sets the flag only on re-address. So it inherits
   `promoted`, and a crash before publish leaves current-version scalars over an old blob — which the
   idempotency skip (`summary-handler.ts:86-92`) can then freeze permanently. The flag is both unsafe
   where it is passed and absent where it is needed.

   **The parameter must go. What replaces it is the open question**, and it is genuinely forked:
   the honest fix needs an **artifact identity the row does not carry** — which is precisely what the
   manifest introduces (`generation_id`). So the options are (a) find a narrower resolution that works
   without one, or (b) accept that this specific defect is not properly fixable before the manifest and
   scope it out with the residual named. **This is a goal-affecting decision and is with the human.**
2. **Should `serial-unusable` self-heal rather than fail?** 154 live rows are in that state; a fatal
   error is right for this write but leaves them permanently unsummarizable. Repair may belong to a
   separate migration.
3. **Does the 503 downgrade on re-address have a user-visible cost worth bounding?** A servable A3 copy
   becomes 503 for the duration of one publish. Probably negligible; not measured.

---

## 11. Verification

- `scripts/check-docs.py` — run from the repo root, **passing**.
- `grill-with-docs` — **run**. Forced the rename from "fence" (taken for lease fencing) to **conditional
  write**, and added an **Addressing** section to `CONTEXT.md` defining *base*, *serial number*, *slug*,
  *conditional write* and *lease fencing* — none previously defined despite being load-bearing in two specs.
- Dual adversarial review — **rounds 1 and 2 complete, NOT converged.** Round 3 mandatory: round 2
  returned three Blockings from one reviewer, two from the other and one from the coordinator, and v3's
  fixes are themselves new unreviewed design.
- **Standing root-cause shapes** — carry into round 3; every one hit in round 2, inside v2's own fixes:
  *a guard with no covering test* (assertions checked pointers, loss was in bytes); *an optional member
  that does not propagate* (`undefined` is not `NULL`); *absent-vs-failed conflation* (a self-inflicted
  key change reported as "someone else moved it"); *a test double that opts out of real behaviour*
  (`promoteSemantics` defaults to the non-production adapter).
- **Round-3 specific shape, new:** *the guard is easy; what the caller does with a rejection is where
  this slice keeps breaking.* Six Blockings, zero in the predicate.
