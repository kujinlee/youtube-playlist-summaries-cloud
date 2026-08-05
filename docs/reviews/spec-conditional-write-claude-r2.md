# Claude adversarial review — `2026-08-04-cas-fence-persist-summary-design.md` (round 2)

**Reviewer:** Claude (adversarial mandate)
**Branch:** `docs/cas-fence-spec` @ `3dca7b0` (spec v2)
**Date:** 2026-08-04
**Method:** every v2 citation re-read on this branch; Postgres semantics, `create or replace`
behaviour and **PostgREST overload resolution measured live** against
`supabase_db_youtube-playlist-summaries-cloud` and `supabase_rest_youtube-playlist-summaries-cloud`
(both up). Probe objects created in `public`/`probe_r2` were dropped; the schema is back to its
pre-review state.

---

## Verdict

**NOT CONVERGED.** Round 1's findings are genuinely addressed — the fixes are substantive, not
reworded, and one of them (the second conjunct, H5) is a real correction. But the fixes are new
design and they carry **three Blocking defects**, two of which are worse than what they replace:

- **B-N1** — the guard as specified **rejects the normal first-time write**. §6 passes the *same*
  `expected_summary_md` to both the `'committed'` and `'promoted'` persists, but the `'committed'`
  persist is what *sets* `summaryMd`. Every bare-row summary — the dominant path — fails its second
  persist, is misclassified as `address-moved`, and enters the recovery loop. Fail-closed on a
  legitimate write.
- **B-N2** — §6's recovery **silently deletes the summary it just paid for**.
  `SupabaseBlobStore.promote` skips the move when the destination already exists, and after an A3
  relocation the destination *always* exists. The row is then published as `promoted` pointing at
  A3's copy of the **old** body. §8's mandated assertions check pointers, so they pass.
- **B-N3** — §4's deploy-safety stub **cannot be applied** (`cannot change name of input parameter`,
  measured), and the shape it writes cannot be called by PostgREST at all.

One piece of good news, **measured rather than argued**: §10's Open Question 3 is now answered.
With both signatures present and the two new parameters required-and-undefaulted, PostgREST resolves
a 5-key body to the 5-arg function and a 7-key body to the 7-arg function. **No PGRST203.** §4's
deploy argument is sound in principle; only its SQL is wrong.

---

## (A) Round-1 findings — fixed, or reworded?

### Claude round 1

| # | Finding | Status | The v2 text, and whether it resolves the behaviour |
|---|---|---|---|
| **B1** | NULL serial → misclassified → retry storm; two-way taxonomy | **FIXED** | §4 adds `if p_expected_serial is null then raise … using errcode = '22004'`, explicitly mirroring `0023:46-48`. §5 replaces the taxonomy with three outcomes decided by **one** statement under `for update`, with `jsonb_typeof(v_actual_serial) <> 'number'` as a distinct fatal branch, and requires the caller to map both fatal codes to `NonRetryableError`. This is behaviour, not prose. **But the same shape recurs at the *new* parameter — see H-N1.** |
| **B2** | Loop reuses the payload → re-persists the stale key under a green guard | **FIXED** | §6 has an explicit `REBUILD the payload:` block setting `video.serialNumber` and `video.summaryMd` per attempt, plus a paragraph naming `summary-handler.ts:149-164` as the literal that must not be reused. §8 adds the positive assertions (`data->>'summaryMd'` **equals** `<newBase>.md` *and* `data->'artifacts'->'summaryMd'->>'key'` equals it). Behaviour specified. **The assertions are insufficient for a different reason — B-N2.** |
| **H1** | Rolling deploy: 5-arg callers break after Gemini billed | **PARTIALLY FIXED** | §4 chooses the right resolution — "keep the 5-arg signature and make its body `raise`" — and the deploy reasoning is now stated with `fly.toml:32-34`. But the SQL given is **unapplyable and uncallable**: see **B-N3**. The decision is fixed; the mechanism is not. |
| **H2** | Grants do not survive a drop; omission fails **open and silently** | **PARTIALLY FIXED** | §4 now carries the exact `revoke all … from public` / `grant execute … to authenticated, service_role` for the 7-arg signature, and states the silent-failure direction. The migration line is there. **But H2's whole point was that no test goes red — and §8 still has no grant test.** A fix whose failure mode is silence, with no covering assertion, is the repo's own *"a guard with no covering test"* shape. See **H-N4**. |
| **H3** | ~19 named-arg call sites break at runtime, invisible to `tsc` | **FIXED** | G7 records the sites with file names and counts; §8 requires *"All ~19 named-argument call sites (G7) updated in the same commit."* §10 records OQ2 as **closed — wrong question**. (Actual count: 16 in `worker-persistence-rpcs.test.ts` + `helpers/cloud.ts:118` + the production wrapper = 18 named RPC sites, plus `worker-storage-bundle.test.ts:87` through the TS wrapper. "~19" is fair.) |
| **H4** | Loop never re-checks `ctx.signal.aborted` | **FIXED (behaviour) / untested** | §6 line 1 of the attempt block: `if ctx.signal.aborted -> throw AbortError  # EVERY attempt, not just the first (H4)`, plus the wall-clock budget (`120 s` lease, `≈40 s` heartbeat, `600 000 ms` hard abort). Specified. **§8 has no test for it** — see H-N5/coverage. |
| **H5** | §0 and §7 contradict; §0's reason for deferring the slug is false | **FIXED** | This is v2's largest change and it is real, not cosmetic: §0 now states *"Both halves can move, and both are guarded"*, G9 is added with `reconcile-serial.ts:150-155` and the `:181-182` comment, §1 gains the slug-only variant table, §4 gains the second conjunct, §7 is rewritten to say the earlier reasoning was *"half wrong"*, and §8 mandates a slug-race test. §0's false sentence is gone. **The conjunct it produced is where B-N1 and M-N2 live.** |
| **M1** | jsonb-over-cast rationale wrong ("total") | **FIXED** | §4 now says the v1 rationale *"is wrong twice over"*, cites the same unguarded cast at `0009:86` running first, and restates the honest reason: *"the predicate must distinguish 'different' from 'unreadable' instead of conflating them into a raise."* |
| **M2** | G1 is convention, not a constraint | **FIXED** | G1 restated verbatim as *"maintained by convention at every writer, not enforced by the schema — there is no CHECK, no NOT NULL, no trigger"*, with `upsertVideo`'s wholesale replace and the live 154/2902 count. |
| **M3** | Re-address can inherit a foreign `promoted` | **NOT FIXED — deliberately open** | §6 proposes promote-before-metadata and says so honestly: *"This is a deliberate departure from G6's sequence and must be reviewed as such in round 2."* §10 OQ1 carries it. It is correctly flagged, not resolved — and the proposed resolution is **worse than the problem**: see **H-N3**. |
| **M4** | Dig has the same exposure, a different sink | **FIXED** | §0 gains a scoped block (*"Do not read 'one sink' as 'digs are covered.'"*), §2 and §9 list it as **#21** with `dig-handler.ts:119-125`. |
| **M5** | OQ1 answerable; `reserveVideoSlot` is the wrong re-read; N=3 needs a justification | **FIXED** | §10 closes OQ1 with both reviewers' reasoning. §5 returns the observed address in the error so the worker needs no re-read (`# from the rejection's payload (§5), no re-read`). §6 supplies the N=3 argument. **The N=3 argument is self-contradicting — M-N1.** |
| **M6** | Cleanup sentence wrong for the promoted-blob branch | **FIXED** | §6 *"Cleanup, corrected."* names the promoted leak, cites `reconcile-serial.ts:358-361` and why the plan predates the promote. |
| **L1** | Money claim under-scoped | **FIXED** | §8 *"Required — the money claim, stated honestly"*, with the `reserved_cents`-reused-across-retries bound and *"the ledger **under-counts** actual spend"* rather than "no double charge". |
| **L2** | `check-docs.py` listed but not run | **FIXED** | §11: *"— **run, passing**."* |
| **L3** | Close the `docVersion` question | **FIXED** | §10 closes it with `summary-handler.ts:73-77`. |

### Codex round 1

| # | Finding | Status | The v2 text |
|---|---|---|---|
| **C-B1** | Predicate semantics: JSON `"7"` vs `7`; jsonb equality diverges from the repo's cast-through-text reads | **FIXED by decision** | §5 makes a non-`number` stored serial a **fatal** `serial-unusable` rather than a silent mismatch; G10 measures **0 of 2748** populated rows storing a string and enumerates all 14 writers. Codex asked for "migrate, or match existing semantics" — v2 takes a third option (detect and refuse loudly), which is defensible and is the fail-closed direction. §10 OQ2 carries the residual honestly: 154 rows become *permanently unsummarizable*, and repair *"may belong to a separate migration."* Recorded, not hidden. |
| **C-B2** | Recovery publishes `promoted` before the blob is promoted (key-scoped monotonic status) | **NOT FIXED — deliberately open** | Same as M3. §6 proposes promote-first; §10 OQ1 asks round 2 to confirm. See **H-N3**. |
| **C-H3** | Dig worker has the same exposure and does not go through `persist_summary` | **FIXED** | §9 **#21**, with the "different sink" reason and the `in-flight-job.ts:69-70` acknowledgement folded into §0. |
| **C-H4** | Two-outcome taxonomy is itself racy (second probe sees later state) | **FIXED** | §5: *"The classification must therefore be decided by the same statement that observes the state … under the row lock"*, with `select … for update` and the comment `-- one snapshot, held for the decision`. Both of Codex's concrete failures (A: relocation then cascade-delete; B: absent then recreated) are closed by holding the lock. |
| **C-M5** | Arity change breaks test fixtures and helpers | **FIXED** | G7 + §8's arity requirement (same as H3). |
| **C-NF** | "No deadlock from `reserveVideoSlot` in the loop" | **Agreed, and independently re-verified** — see *Verified, not findings* below. |

**Nothing in this table is a rewording.** v2 addresses round 1 in behaviour. The problem is what the
behaviour now says.

---

## (B) Defects the fixes introduced

### Blocking

#### B-N1 — The `'promoted'` persist reuses a stale `expected_summary_md`, so the guard rejects **every first-time summary**

§6 specifies both persists with the *same* expected tuple:

```
      persistSummary(..., expected := (serial, currentMd), 'committed')
      promote(ref)
      persistSummary(..., expected := (serial, currentMd), 'promoted')
```

But the `'committed'` persist is precisely the write that **changes `summaryMd`**. `0021:133`:

```sql
|| jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
```

Payload wins (G3). So on a bare reserved row (G2 — `0009:95` inserts only `id` and `serialNumber`):

| Step | `v.data->>'summaryMd'` | `p_expected_summary_md` | second conjunct |
|---|---|---|---|
| worker reads row (`summary-handler.ts:84`, before `reserveVideoSlot:95`) | *(absent)* | — | — |
| persist #1 `'committed'` | absent → **`'007_alpha.md'`** | `NULL` | `NULL is not distinct from NULL` → **true**, passes ✅ |
| `promote(ref)` (`:178`) | `'007_alpha.md'` | — | — |
| persist #2 `'promoted'` (`:179`) | `'007_alpha.md'` | `NULL` (unchanged) | **false → REJECTED** ❌ |

Measured on the live DB:

```
'007_alpha.md' is not distinct from NULL  ->  false
NULL           is not distinct from NULL  ->  true
```

**This is the fail-closed rejection of a legitimate write** that the brief names as Blocking, and it
hits the *dominant* path: every video summarized for the first time (`createdThisRun` at
`summary-handler.ts:93`). It also hits every re-summarize whose title changed, for the same reason
(persist #1 moves `007_alpha.md` → `007_beta.md`).

**It does not fail loudly** — which is worse. §5 classifies it as `address-moved` → **retryable** →
§6's loop runs. Attempt 2 reads the observed address (`serial 7`, `'007_alpha.md'`), recomputes the
identical `baseName`, re-stages the same bytes, takes the *re-address* branch — `promote(ref)` then
`persistSummary(..., 'promoted')` — and succeeds. So the steady state is:

- every first-time summary re-uploads its blob and burns one of the three attempts;
- the `'committed'` record is **never written on the normal path** (the re-address branch skips it),
  silently removing the serve path's 503 finalizing window (`serve-summary-core.ts:50`) from 100% of
  first-time summaries;
- `address-moved` — the signal the whole slice exists to produce — fires on every normal write, so
  it carries no information and cannot be alerted on;
- §6's *"each exhaustion is logged with both addresses, because repeated exhaustion means something
  is relocating in a loop"* is now noise.

**Root cause, and why it is not a typo.** The two conjuncts are **asymmetric** and §4 does not say
so. `serialNumber` is row-wins (the whitelist at `0021:120-132` omits it), so the worker cannot
change it and `expected_serial` is stable across both calls. `summaryMd` is payload-wins
(`0021:133`), so the worker **does** change it and `expected_summary_md` is *not* stable. A single
"expected tuple" is the wrong shape.

**Fix.** §6 must state that the `'promoted'` call passes `expected_summary_md := <baseName>.md` —
the value persist #1 just wrote — not the value read before it. §4 should state the asymmetry
explicitly (one half the worker cannot move, one half the worker moves as its purpose). §8 needs a
test that a plain first-time summary completes **without entering the recovery loop at all**; none
of the currently-listed tests would catch this, because all of them assert on the *race* paths.

---

#### B-N2 — §6's recovery discards the summary it just generated and publishes A3's stale copy

§6's premise is *"Rejected doesn't mean wasted … the worker re-files it under the new address instead
of generating it again — one blob round-trip versus roughly 8¢ of Gemini,"* justified by G5 (the MD
bytes are base-independent). G5 is true. The premise still fails, because of what `promote` does.

`lib/storage/supabase/supabase-blob-store.ts:90-97`:

```ts
async promote(ref: StagedRef): Promise<void> {
  const from = this.objectKey(ref.principal, ref.tempKey);
  const to   = this.objectKey(ref.principal, ref.finalKey);
  // move = copy+delete (non-atomic). Idempotent: if final already present, ensure temp gone and return.
  if (await this.exists(ref.principal, ref.finalKey)) {
    await this.b().remove([from]).catch(() => {});   // <-- deletes the STAGED NEW BYTES
    return;                                          // <-- and reports success
  }
```

**The destination always exists on the re-address path.** A3's copy phase copies `${oldBase}.md` →
`${newBase}.md` (`paidKeysUnder:98` seeds the list with `${base}.md`; `remap:117` maps it; the loop
is `:281-290`; `:288` makes the MD the one key whose absence is *not* tolerated), and the metadata
write at `:293-296` only happens after every copy succeeded. So by the time the worker's guard
rejects and it re-addresses to `<newBase>`, `<newBase>.md` is guaranteed to hold **A3's copy of the
old summary body**.

Sequence, with values:

1. Worker generates the new summary; guard rejects at `007_alpha`.
2. Re-address to `003_alpha`. `putStaged('003_alpha.md')` → staged bytes = **new** summary. Verified.
3. `promote(ref)` → `exists('003_alpha.md')` is **true** (A3 put the old body there) → the staged
   object is **deleted**, `promote` returns **void, no error**.
4. `persistSummary(..., expected := (3, '003_alpha.md'), 'promoted')` → guard **passes**, row is
   stamped `key='003_alpha.md', status='promoted'`, and the Class-A scalars from the *new* payload
   (`ratings`, `tldr`, `docVersion`, `processedAt`) land.

Result: the row advertises a **promoted** artifact whose bytes are the **old** summary, the ~8¢ of
Gemini output is gone, and there is no error anywhere. The serve path
(`serve-summary-core.ts:47-50`) sees `promoted` and serves it — no 503, no 404.

**§8's mandated assertions pass.** B2's fix requires asserting `data->>'summaryMd'` and
`data->'artifacts'->'summaryMd'->>'key'` equal `<newBase>.md`. Both do. §8 asserts **pointers**; the
defect is in **bytes**.

**A default test double hides it.** `InMemoryBlobStore.promoteSemantics` defaults to `'overwrite'`
(`lib/storage/testing/in-memory-blob-store.ts:52`), which is the *local* adapter's behaviour
(`local-blob-store.ts:58-62` does `fs.renameSync`, which overwrites). The Supabase behaviour is the
non-default option, and the double documents it in so many words at `:170-175`:

```ts
if (finalExists && this.promoteSemantics === 'create-if-absent') {
  // Supabase: the move is SKIPPED, so the final keeps its old body. The temp is
  // still dropped, which is what makes the stale body survive silently.
```

So the repo already knows this hazard, already has scaffolding for it, and v2 is unaware of it. Per
the standing rule (*"before deferring a finding, try to turn it into an assertion"*), this one is
already assertable with existing scaffolding.

**Fix.** §6 must specify publication semantics for a destination that already holds different bytes
— the honest options are `delete(finalKey)` then `promote`, an explicit overwriting `put`, or
routing the decision through the same `CopyResult`-style `destination-exists` union `copy()` already
uses (`blob-store.ts:26-31`). §8 must assert **bytes**, not pointers: after a successful re-address,
`get(<newBase>.md)` equals the newly generated MD. Every re-address test must run with
`promoteSemantics: 'create-if-absent'` or against the real Supabase store.

---

#### B-N3 — §4's deploy-safety stub cannot be applied, and the shape it specifies cannot be called

§4's snippet:

```sql
create or replace function persist_summary(uuid, uuid, text, jsonb, text) returns void … as $$
```

**Measured** (same statement shape, live DB):

```
create function probe_r2.f(p_a int, p_b text) …            -> CREATE FUNCTION
create or replace function probe_r2.f(int, text) …
   ERROR:  cannot change name of input parameter "p_a"
   HINT:  Use DROP FUNCTION probe_r2.f(integer,text) first.
```

The existing 5-arg `persist_summary` has **named** parameters (`0021:99`), so `create or replace`
with positional-only parameters aborts the migration. **The migration does not apply.**

And the obvious workaround makes it worse. `drop` + `create` with unnamed parameters produces a
function PostgREST **cannot route to at all**: it resolves an RPC by the named arguments in the
request body (`0023:27-35`), and a function with no parameter names matches no named body. Every
old-image worker would get PGRST202 — exactly the failure the stub exists to prevent, now
permanent rather than window-limited.

**Fix.** The stub must be `create or replace function persist_summary(p_owner_id uuid,
p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text) …` — names preserved,
body replaced with the `raise`. Also state which route is taken for the 5-arg grants: `create or
replace` **preserves** the existing `0021:154-155` grants, so re-issuing them is optional there
(unlike the new 7-arg signature, where H2's rule applies in full). §8's *"one test that the 5-arg
stub raises rather than writing"* stays as written.

**Open Question 3 is now closed — measured, and in v2's favour.** With both signatures live and the
two new parameters required-and-undefaulted, against `supabase_rest_…` on `127.0.0.1:54321`:

| Request body | Resolved to | Result |
|---|---|---|
| 5 keys (`p_owner_id … p_artifact_status`) | **5-arg** | `{"code":"0A000","message":"STUB-5ARG-RAN"}`, HTTP 400 |
| 7 keys, `p_expected_summary_md: null` | **7-arg** | `"SEVEN-ARG-RAN"`, HTTP 200 |
| 7 keys, all populated | **7-arg** | `"SEVEN-ARG-RAN"`, HTTP 200 |

**No PGRST203.** §4's deploy-safety argument is correct; only its SQL is not. This also confirms
that an explicit JSON `null` for `p_expected_summary_md` routes correctly — the bare-row case works,
**provided the key is present**, which is H-N1.

---

### High

#### H-N1 — `undefined` is not `NULL`: the bare-row case, as it would actually be written, 404s

§4 turns on *"NULL is MEANINGFUL (bare row, G2)"*. In PostgREST, **required means the key must be
present in the body** — and JavaScript deletes `undefined` keys on serialisation. Measured:

```
body with p_expected_summary_md omitted (6 keys) ->
  {"code":"PGRST202", … "Could not find the function public.probe_ps(
   p_artifact_status, p_expected_serial, p_owner_id, p_playlist_id, p_video, p_video_id)
   in the schema cache"}   HTTP 404

node -e "JSON.stringify({a:1,b:undefined,c:null})"  ->  {"a":1,"c":null}
```

The natural implementation produces exactly that. `readVideo` returns `Video | null`
(`worker-persistence.ts:32-40`), so `existing?.summaryMd` is `undefined` whenever the row did not
exist — which is precisely the bare-row case §4 is reasoning about. Worse, `readVideo` returns
`data.data as Video` — an **unchecked cast**, no zod parse — so even for a row that *does* exist,
a bare reserved row (`{id, serialNumber}`) yields `existing.summaryMd === undefined` at runtime
while the type says `string | null` (`types/index.ts:56`). **`tsc` will not force the coercion**,
because the type already claims it cannot be `undefined`.

Consequence: PGRST202 **after Gemini has been billed**, on the first-time path, requeued and
re-billed up to `max_attempts` = 5 (G11). Loud rather than silent, so it would surface in
integration — but only if §8's *"Required — NULL `p_expected_serial`"* test and the bare-row tests
go through **the TS wrapper**, not a raw `admin.rpc` with a hand-written explicit `null`. As written
they can be satisfied by the latter.

**Fix.** `persistSummary` must coerce: `p_expected_summary_md: expectedSummaryMd ?? null`, and §4
must state that "required" means *present in the body*, not merely *declared*. §8 must require the
bare-row test to exercise the wrapper. This is the round-1 standing shape *"an optional member that
does not propagate"* recurring at the parameter B1 introduced.

#### H-N2 — §8's mutation check cannot detect a dead conjunct, and fails **twice over**

§8: *"Delete the serial conjunct → the serial-race test MUST go red. Delete the `summaryMd`
conjunct → the **slug**-race test MUST go red."* Neither will happen.

**(a) After §5, the `where` conjuncts are dead code as guards.** §5's classifier takes
`select … for update` and *raises* on `address-moved` before the `UPDATE` ever runs. Inside one
transaction, no other session can change a row held under `for update`. v2 says so itself: *"then
the guarded UPDATE, which cannot now fail for any of the above reasons."* So **deleting both
conjuncts from the `UPDATE` leaves every test green.** §8 mandates mutating the one place that is
provably unreachable-as-a-guard. The real guard is the classifier's `elsif`, and §8 never mentions
mutating it.

**(b) Even against the classifier, the serial branch is untestable by the mandated tests, because
A3 always moves both halves together.** `describeDivergence` returns diverged only when the full
bases differ (`reconcile-serial.ts:155`), and the relocation patch writes both:

```ts
const patch: Record<string, unknown> = {
  serialNumber: localVideo.serialNumber,
  summaryMd: `${newBase}.md`,            // reconcile-serial.ts:293-295
```

So `summaryMd` changes on **every** relocation, serial-race included. Delete the serial check →
the `summaryMd` check still rejects → the serial-race test stays **green**. (The converse works:
a slug-only divergence leaves `serialNumber` equal, so the slug test does exercise the md branch.)

The serial branch is not useless — a source that moves the serial *without* moving `summaryMd` is
reachable via `claim_video_slot:65-68` (fills a serial on a row that lacks one) and
`sync-run.ts:277` (`copyAdditiveVideo` setting `sanitized.serialNumber`) — but **no test §8 mandates
constructs one**, so the branch ships unverified.

**Fix.** Mutate §5's classifier branches, not the `UPDATE`'s `where`. Add a **serial-only** move
test that changes `data->'serialNumber'` while leaving `data->>'summaryMd'` untouched (a direct
`update videos` in the fixture is the honest way — it models `claim_video_slot`, not A3). Then state
which construct each mutation targets, since after §5 there are two guards, not one.

#### H-N3 — Promote-before-metadata (§6 / OQ1) trades a *visible* crash window for a *silent* one

This answers §10's Open Question 1: **the departure is not safe, and the `'committed'` step is
carrying a property v2 does not account for.**

**What `'committed'` is for.** It is not bookkeeping. `serve-summary-core.ts:50`:

```ts
if (status === 'committed') return { ok: false, status: 503, error: 'not ready, retry' }; // finalizing window (B12)
```

and `supabase-metadata-store.ts:54-55` derives the UI's `summaryReady` from
`status === 'promoted'`. The `'committed'` record publishes the **key** while declaring the artifact
**not servable**. That is exactly what makes the stage→persist→promote→persist ordering (G6) safe:
the only window in which the row can point at unpromoted bytes is a window in which readers are
told 503.

**What §6 does instead.** On a re-address it writes **no** `'committed'` record: `promote(ref)` then
`persistSummary(…, 'promoted')`. Die between them and the row is **unchanged** — still A3's
`key='003_alpha.md', status='promoted'` (`reconcile-serial.ts:296`) — while the blob at that key now
holds the **new** body. So:

- the serve path returns **200 with the new summary body beside the old row scalars** (`tldr`,
  `ratings`, `overallScore`, `docVersion`, `processedAt` are all A3-era). No 503, no error, nothing
  distinguishable from a healthy row.
- **Recovery is not automatic and may be actively prevented.** The job requeues; on the next attempt
  the idempotency skip at `summary-handler.ts:86-92` tests `status === 'promoted' && docVersion
  matches`. If the row's `docVersion` matches, the skip **fires and returns success**, freezing the
  inconsistency permanently. If it does not match, the repair costs a **fresh ~8¢ Gemini run**.

Compare the ordering it departs from: die between `persist('committed')` and `promote` and the row
says `committed` → readers get 503 → the retry repairs it. The window is visible and non-serving.

Note also that with **B-N1** unfixed, this branch is not the exception — it is the path *every*
first-time summary takes, so the 503 window disappears from the normal path entirely.

**Fix.** Do not resolve M3/C-B2 by dropping `'committed'`. The narrower fix is to make the
intermediate write unable to inherit a foreign `promoted` — e.g. have the re-address `'committed'`
persist pass a flag that suppresses `0021:142-149`'s preservation, or (cleaner) have the guard's
own rejection carry enough identity that the monotonic rule can tell "same key, different artifact"
apart. v2 already identifies that this needs an artifact identity the row lacks; that is an argument
for keeping the ordering and scoping the inheritance fix, not for inverting the ordering.

#### H-N4 — The grants fix (H2) has no covering test, and its failure mode is silence

§4 now carries the `revoke`/`grant` lines. H2's finding was not *"the lines are missing"* — it was
*"omitting them fails **open and silently**; every legitimate caller still works and no test goes
red."* v2 restates that (*"omitting the grants fails open and silently"*) and then adds **no test**.
§8's list has no grant assertion. A migration author who drops the `revoke` ships an
EXECUTE-to-PUBLIC function and the entire §8 suite is green.

**Fix.** §8 gains: after the migration, `has_function_privilege('anon', 'persist_summary(uuid,uuid,
text,jsonb,text,int,text)', 'EXECUTE')` is **false**. The repo has the
`service_role`-confinement guard in CI already, so the shape exists.

---

### Medium

#### M-N1 — §6's N = 3 justification contradicts §1.2

§6: *"While the job is `active`, `supabaseInFlightJobProbe` reports `inFlight` and A3 **refuses** to
relocate (`in-flight-job.ts:21,:116`), so a second relocation cannot occur *during* the loop."*

§1.2 refutes exactly this reasoning for the first relocation: *"The refusal is checked once, before
the copy phase … A job enqueued and claimed inside that span reads the pre-relocation address and is
**invisible to a probe that already ran**."* The residual window this whole spec exists to close
**is** the case where A3's probe already ran. An A3 run that probed before the job was claimed is
past its probe and will complete its copy + metadata write regardless of what the loop is doing;
a *second* concurrent sync run of the same playlist is a shape the codebase already treats as real
(`reconcile-serial.ts:309-321`'s `metadata-unverified` re-read exists for it).

The bound is probably adequate in practice; the **argument** for it is not, and v2 presents it as
derived rather than chosen (*"bounded by PR #45, not by taste"*). Exhaustion throws retryable →
requeue → a **fresh Gemini run**, so an unsound bound has a money consequence, which is why this is
worth more than a nit.

**Fix.** State the bound as a deliberate choice with the exhaustion cost named (one extra ~8¢
attempt), or derive it from something that actually holds — e.g. the lease/wall-clock budget §6
already cites — rather than from a probe that has, by construction, already run.

#### M-N2 — §0 overclaims what the second conjunct guards

§0: *"**Both halves can move, and both are guarded** — the serial directly, the slug via the
`summaryMd` key that carries it."*

The conjunct guards **the row's key against moving under the worker**. It does nothing about **the
worker moving the key**, which is the case the brief asks about: a re-summarize after a title change
(row holds `007_alpha.md`, worker intends `007_beta.md`, no sync involved). The guard compares the
row's current value against what the worker *read* — both `007_alpha.md` — so it **passes**, the
write lands as `007_beta.md`, and `dig/007_alpha/*` is orphaned. That is backlog #20, and §0 does
say so two paragraphs later (*"What remains unguarded is the non-concurrent slug case"*), so the
section is not self-contradictory. But "both halves are guarded" followed by "one half is only
half-guarded" reads as stronger than it is, and the sentence is the one a reader will quote.

This is not cosmetic: it is the same asymmetry that produces **B-N1**. Naming it once, precisely,
fixes both. Suggested framing: *the serial is guarded against any change; the key is guarded only
against a change the worker did not make.*

#### M-N3 — §5's error contract is unimplementable as specified: the SQLSTATEs are not named

§5 requires *"Distinct SQLSTATEs (or a structured `detail`) are part of the contract, not
diagnostics"* and *"the caller must map the two fatal codes to `NonRetryableError`."* It then names
**no codes** — only `22004` for the null-argument raise in §4. §8 requires *"one test per §5
outcome, asserting the caller can distinguish them"*, which cannot be written against an unnamed
contract, and the natural fallback (matching on message text) is the thing the requirement exists to
prevent.

**Fix.** Name the three: e.g. `'P0001'`-with-`detail`, or three distinct `errcode`s. Also state
where the observed address rides (`detail`? `hint`? a returned row?) — §5 says *"it should surface
them in the error"* without saying how, and `supabase-js` exposes `error.code`, `error.details`,
`error.hint` and `error.message` differently.

#### M-N4 — Coverage: behaviours specified in §4/§5/§6 with no test in §8

Walking §4/§5/§6 against §8's list, these have **no covering test**:

| Behaviour | Specified at | §8 |
|---|---|---|
| Abort re-checked on **every** attempt (H4's fix) | §6 line 1 | **none** |
| Re-address writes bytes, not just pointers | §6 premise | **none** (B-N2) |
| First-time write completes **without** entering the loop | implied | **none** (B-N1) |
| Promote-before-metadata ordering; crash between the two | §6 | **none** (H-N3) |
| Grants: `anon` cannot EXECUTE | §4 | **none** (H-N4) |
| `p_expected_summary_md` present-but-null via the **TS wrapper** | §4 | ambiguous (H-N1) |
| Both signatures live simultaneously (the deploy window itself) | §4 | only "the stub raises" |
| The `for update` holds across the classification (C-H4's fix) | §5 | **none** — no concurrent-session test |
| Wall-clock budget: the loop does not outlive the lease | §6 | **none** |

The last one matters more than it looks: §6 cites the 120 s lease and 600 000 ms hard abort but
specifies no behaviour when the loop would exceed them beyond the per-attempt abort check.

### Low

- **L-N1 — G7's "~19" is 18 named RPC sites.** Measured: 16 in
  `tests/integration/worker-persistence-rpcs.test.ts`, 1 in `tests/integration/helpers/cloud.ts:118`,
  1 production wrapper (`worker-persistence.ts:22`), plus `worker-storage-bundle.test.ts:87` through
  the TS wrapper. Other `persist_summary` matches in the tree (`helpers/seed.ts:19`,
  `reconcile-serial.test.ts:683`, `sync-run.ts:14`, `stamping.int.test.ts:6,90`) are comments or test
  names, not calls. The "~" makes it fair; recording the exact set makes the arity commit checkable.
- **L-N2 — Behaviour change not called out: a zero-row persist is retryable today, fatal under v2.**
  `0021:152` raises a plain exception, so `worker-runner.ts:76` classifies it retryable. §5 makes
  `row-gone` non-retryable. That is the right direction (a cascade-deleted playlist will never
  return), but it is a live behaviour change to an existing error path and deserves a line.
- **L-N3 — §7's "throwaway is one line" now understates the work.** With §5, the guard is a
  classifier plus two conjuncts; migrating to the manifest CAS replaces the conjuncts *and* rewrites
  the classifier's `serial-unusable` branch (a `not null` `blob_key` has no unusable state). The
  table's *"Three-way failure taxonomy … unchanged"* is not quite right — it becomes two-way.

---

## Verified, not findings

Recorded because the brief asked, and because a checked-and-clean answer is worth as much as a
finding.

- **No deadlock from the new `for update`.** `reserve_video_slot:84` and `claim_video_slot:50-52`
  take `playlists FOR UPDATE` and then touch `videos`. `persist_summary` takes a `videos` row lock
  and **no** `playlists` lock — `0021:104` is a plain `perform 1 from playlists` with no `FOR
  UPDATE`. `merge_video_data` (A3's write, `0021:79-90`) takes neither explicitly. So no transaction
  anywhere acquires **videos → playlists**; there is no cycle, in either runSync's or the worker's
  sequence. Each PostgREST RPC is its own transaction, so no lock is held across a blob round-trip.
  Codex's round-1 "Not Finding" and Claude's M5 both stand.
- **No RLS or privilege change from the `for update`.** `videos` has **forced** row security with a
  single `FOR ALL` policy: `videos_owner USING (owner_id = auth.uid())` (measured:
  `polcmd = '*'`). `SELECT … FOR UPDATE` additionally applies the UPDATE policy's `USING`, but here
  it is the *same* expression the `UPDATE` already applies — so the visible row set is identical for
  `authenticated`. `service_role` has `rolbypassrls = t` (measured), and the worker uses the service
  client, so the worker path is unaffected either way. `security invoker` requires no change.
- **The predicate's type-safety claim (G10) holds.** `('{"s":7}'::jsonb->'s') = to_jsonb(7)` → `t`,
  measured; round 1's enumeration of the 14 writers is unchanged on this branch.
- **PostgREST overload resolution with required extra parameters is unambiguous** — see B-N3's
  table. This closes §10 OQ3 in v2's favour.

---

## What I could not verify, and why

1. **The real Supabase Storage behaviour of `promote` against an existing destination.** B-N2 rests
   on reading `supabase-blob-store.ts:93-96` (`exists` → `remove(temp)` → `return`) plus the
   in-memory double's own comment at `:170-175`, which documents the identical semantics. I did not
   drive a real bucket to observe the skip. The code path is unconditional and does not depend on
   Storage's behaviour — `exists` short-circuits before `move` is ever called — so I regard it as
   established, but the round-trip was not performed.
2. **Whether §8's tests would be written against the wrapper or a raw `admin.rpc`.** H-N1's severity
   depends on it. §8 does not say, which is the finding.
3. **Actual wall-clock cost of a re-address attempt against the 120 s lease.** Same limitation as
   round 1's item 4 — the argument in M-N4's last row is structural, not measured.
4. **Whether two concurrent sync runs of one playlist occur in practice** (M-N1). The code is
   written as if they can (`metadata-unverified` exists for exactly that), but I did not trace the
   scheduler.
5. **`docs/backlog.md` entries #19/#20/#21** — I confirmed §9's internal consistency but did not
   verify the backlog file actually carries those numbers with those titles.

---

## Standing root-cause shapes — hits this round

| Shape | Where it recurred in **v2's own fixes** |
|---|---|
| *a guard with no covering test* | **B-N2** (assertions check pointers, the loss is in bytes); **H-N2** (mutation targets the one construct that is provably unreachable); **H-N4** (grants) |
| *an optional member that does not propagate* | **H-N1** — `undefined` is not `NULL`, and `readVideo`'s unchecked `as Video` cast stops `tsc` from noticing |
| *absent-vs-failed conflation* | **B-N1** — a legitimate self-inflicted key change is reported as `address-moved`, i.e. "someone else moved it" |
| *a value read in one process and written in another* | **B-N1** again — the expected key is read once and compared against a value **this same worker** wrote in between |
| *a test double that opts out of the real behaviour* | **B-N2** — `promoteSemantics` defaults to `'overwrite'`, the adapter that is not in production |
