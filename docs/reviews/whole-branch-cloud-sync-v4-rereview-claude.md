# Whole-branch re-review — round 4 (Claude, adversarial)

Branch `feat/stage3-cloud-sync`, HEAD `3bc8cc7`. Read-only. Scope: shipped state.

Trail: R1 (`32a164c`) → R2 (`1f54c60`) → R3 B1 (`3bc8cc7`).

---

## Part A — verdict on the round-3 B1 fix: **INCOMPLETE**

The guard at `lib/cloud-sync/sync-run.ts:510-511` is correct in what it does, is placed
correctly (before the corrections guard and before `reconcileClassA`), and its two tests are
honest. But it has one uncovered consumer and it is over-broad on the local side.

### A.1 — the fix is genuine for the path it covers ✅

`la`/`ca` are derived at :491-492 from the freshly-read bodies, and the throw at :510-511 fires
before `correctionsUnresolved` (:519) and before `reconcileClassA` (:528). The throw is caught by
the per-video `catch` (:559), so it lands in `report.errors` and — critically — `writeVideoBaseline`
is never reached on that iteration. With the guard in place, `reconcileClassA`'s `!lHas` / `!cHas`
branches (`reconcile-class-a.ts:21-23`) now mean what they claim.

`transferClassA` re-reads the winner body at :279 and **throws** if it comes back null
(:280-281) — so a read that succeeds at :491 and fails at :279 does not silently produce a
half-transfer. Correct.

### A.2 — the two new tests are honest ✅

`tests/integration/cloud-sync/e2e.int.test.ts:564` (P1) and `:598` (P2) each loop over two runs
and assert (a) an error for the video, (b) `updatedLocal === 0 && updatedCloud === 0`, (c) the
local body byte-for-byte unchanged and the cloud blob still `null`, (d) `docVersion.major`
unchanged on both sides (P2), (e) **no manifest entry on either run**, (f) unchanged
`spendLedgerTotal`. Remove the guard and control reaches `reconcileClassA`, whose `!cHas` branch
returns `copyToCloud`, which runs `transferClassA` and overwrites the cloud side — so the
byte/format/baseline assertions fail for exactly the reason the guard exists, not incidentally.
The two-run loop is the right shape: it is precisely the run-2 laundering that made the original
bug permanent. Matches the reported mutation result.

### A.3 — legitimate cases still work ✅

- Summary-less video (`summaryMd == null`): both conjuncts at :510/:511 are false, guard silent.
  `copyAdditiveVideo` (:160) and the `else` at :185-190 continue to handle it.
- M-R2-2 one-sided hydration: `tests/…/e2e.int.test.ts:524` seeds `summaryMd: null` locally, so
  the guard does not fire and the narrowed corrections skip at :520 still admits the hydration.

### A.4 — **COVERAGE GAP: `companionTransfer` is not covered** → see Finding H1

The guard covers `readMdBody`. It does not cover the *other* blob read on the same code path,
`readModelEnvelope` at `sync-run.ts:350`, which has the identical null-conflation and drives a
**DELETE**. Details in Part B / H1.

Other callers audited and clean: `transferClassA` (:279, throws), `backfill.ts`
(`deriveClassASignals` only consumes the body handed to it), `manifest.ts`, `registry.ts` (no
blob reads), `supabase-metadata-store.readIndex` (`throw` on every query error — no
empty-index-on-failure conflation), `lib/index-store.readIndex` (throws on anything but ENOENT,
and distinguishes a missing dir).

### A.5 — **OVER-BROAD: throwing is wrong for a genuinely-absent LOCAL blob** → see Finding H2

The prompt's question "is there any case where this new throw makes a previously-working sync
fail?" has a yes. Details in Part B / H2.

---

## Part B — findings

### H1 (High) — `companionTransfer`: an unreadable *cloud* model envelope is read as "no model", and DELETES the local one, forcing a paid regeneration

**Files:** `lib/cloud-sync/sync-run.ts:345-359`; `lib/cloud-sync/companion.ts:13-16`;
`lib/storage/supabase/supabase-blob-store.ts:23-33`; `lib/html-doc/model-store.ts:58-59`.

This is the exact B1 shape, one module over. `readModelEnvelope` returns `null` for three
different situations: the envelope is **absent**, it is **corrupt/schema-invalid**, or its bytes
**could not be read**. On the cloud side the third is indistinguishable from the first, because
`SupabaseBlobStore.get` is `if (error) return null` — the very swallow the B1 fix was written
around. `decideCompanion` (`companion.ts:16`) maps `null` to `deleteReceiverModel`.

**Trace (input → wrong outcome).** `reconcileClassA` returns `copyToLocal` (cloud MD wins —
e.g. cloud is corrections-current, or the recency tiebreak). `transferClassA` succeeds; the cloud
body is now on local. Then `companionTransfer(winner=cloudSide, loser=localSide, …)`:

1. `:350` `readModelEnvelope(cloudP, base, deps.cloudBlob)` hits a transient 5xx / network blip /
   timeout on `models/<base>.json`. `get` returns `null`; `readModelEnvelope` returns `null`.
2. `:351` `decideCompanion({ senderEnvelope: null })` → `deleteReceiverModel`.
3. `:357` the **local** model blob is deleted; `shareNeedsOwnerServe` is incremented (a false
   report — nothing about the *share* is stale).
4. `companionTransfer` does not throw, so `:558 writeVideoBaseline` runs and the baseline
   advances to full agreement.
5. **Run 2:** both mdHashes are now equal and both corrections-current → `reconcileClassA`
   returns `skip` (`reconcile-class-a.ts:33`) → `:550` is false → `companionTransfer` never runs
   again. The correct model on the cloud is never shipped.

**Why this is a money finding, not a cache nit.** The correct behavior was `ship` — a free blob
copy of a model that already matches the winning MD. Instead local ends with **no** model, and
the only way to get one back is `runHtmlDoc` (`lib/html-doc/generate.ts:41`) →
`generateMagazineModel` — a paid Gemini magazine transform. On the mirror path the receiver is the
cloud and regeneration goes through `resolveMagazineModel` → `reserve_serve_model` →
`spend_ledger` (`lib/html-doc/serve-doc.ts:60,98`). Silent (no `report.errors` entry), sticky (the
baseline advanced), and it forces the user to re-spend for content that was already paid for.

Note the asymmetry that makes this cloud-specific: on the `copyToCloud` direction the sender read
is the **local** store, whose `get` returns null only on ENOENT (`local-blob-store.ts:18-21`), so
there the null genuinely means "no model" and the delete is correct.

**Fix.** Corroborate the null against the record the same way B1 does — do not let an
unproven-absent model drive a delete. Concretely: make the sender-side read distinguish
absent-from-unreadable and, when it cannot prove absence, **skip** the companion step entirely
(leave the receiver's model alone, do not increment `shareNeedsOwnerServe`) rather than deleting.
Throwing is also acceptable here since the Class-A commit already landed durably and a re-run is
idempotent — but a skip is enough, because the receiver model is only ever a cache. The
cheap version: give `readModelEnvelope` (or a sync-local wrapper) a tri-state return
(`ship` | `absent` | `unknown`) and treat `unknown` as no-op.

---

### H2 (High) — the B1 guard is over-broad on the local side: a genuinely-dangling local `summaryMd` can no longer self-heal, and now errors forever

**File:** `lib/cloud-sync/sync-run.ts:510`.

`if (lv.summaryMd && la.mdHash == null) throw` treats the **local** side fail-closed. But the
local blob store is exactly the backend where absent and unreadable *are* distinguishable:
`LocalFsBlobStore.get` returns `null` only on `ENOENT` and rethrows every other errno
(`local-blob-store.ts:18-21`). So on the local side, `la.mdHash == null` with `lv.summaryMd` set
is not ambiguous at all — it positively means **the file is not there**.

**Trace (input → wrong outcome).** A local record advertises `summaryMd: "notes/abc.md"` but the
file is gone — the user deleted or moved the `.md` by hand in their `-data` folder, or a local
generation crashed between the index write and the blob write. The cloud holds a good body for the
same video.

- **Before `3bc8cc7`:** `la.mdHash == null` → `reconcileClassA` `!lHas` → `copyToLocal` →
  `transferClassA` writes the cloud body to the local key and finalizes the record. The dangling
  pointer **heals**, at zero cost. Purely additive — nothing on local could be destroyed, because
  nothing is there.
- **After `3bc8cc7`:** the guard throws first. The video errors on **every** run, forever. It
  never advances a baseline, so it also never becomes eligible for delete-inference. The user's
  only exits are hand-editing `playlist-index.json` or regenerating the summary — a paid Gemini
  run for content that is sitting intact in the cloud.

This is a previously-working sync that now permanently fails, and it contradicts the fix's own
stated rationale: the M-R2-2 narrowing at `:513-518` argues precisely that a side holding no MD
must be hydrated rather than stranded, and the B1 comment at `:507-509` claims the guard leaves
that intent intact. It does not — for the local side it re-introduces exactly the stranding
M-R2-2 removed, just via a different door.

**Fix.** Scope the fail-closed behavior to the case where absence is genuinely unprovable. When
the body is null and the record advertises a key, probe the store:

- `LocalFsBlobStore.exists` returns `false` only on ENOENT and throws otherwise
  (`local-blob-store.ts:23-26`) → `false` proves absence → treat as "no MD" and let the additive
  hydration run.
- `SupabaseBlobStore.exists` is `get() !== null` (`supabase-blob-store.ts:35-37`) and inherits the
  same swallow → it can never prove absence → the cloud side stays fail-closed exactly as
  `3bc8cc7` has it.

That asymmetry is the honest one: the guard exists because *one* backend cannot tell the two
apart, so only that backend should pay for it. If a probe is judged too subtle, the narrower
alternative is to have `SupabaseBlobStore.get` surface a distinguishable error (or add a
`tryGet`) and drop the guard's local half — but that touches already-merged read paths, which
`supabase-blob-store.ts:28-30` deliberately declined to do.

No existing test covers "local advertises `summaryMd`, blob genuinely absent, cloud has a body" —
the closest, M-R2-2 at `e2e.int.test.ts:524`, seeds `summaryMd: null`, which is a different input.

---

### H3 (High) — a local-only video wipes the cloud playlist's `playlist_title` on every sync

**Files:** `lib/cloud-sync/sync-run.ts:93-101` (`playlistMetaFor`) and `:135`
(`ensureReceiverSlot`); `lib/cloud-sync/registry.ts:6,26-29`;
`lib/storage/supabase/supabase-metadata-store.ts:78`.

Same "absent means null" conflation, on playlist metadata rather than a blob — the candidate the
brief flagged as `''`-vs-absent.

`playlistMetaFor` checks the **local** registry first (`:96-97`) and returns
`{ playlistUrl: lp.playlistUrl }` with **no** `playlistTitle`, because `LocalPlaylist`
(`registry.ts:6`) never carries one — `discoverLocalPlaylists` reads the full index at
`registry.ts:26` and discards `idx.playlistTitle`. Only the cloud-registry branch (`:99`) carries
a title, and it is unreachable whenever the playlist also exists locally.

`ensureReceiverSlot:135` then calls `to.setPlaylistMeta(toP, playlistMeta)` **unconditionally** —
before the "does the row already exist" check at `:137`, so it fires even when nothing else about
the playlist changes. On the cloud store that is an upsert with
`playlist_title: meta.playlistTitle ?? null` (`supabase-metadata-store.ts:78`) — an explicit NULL.

**Trace (input → wrong outcome).** A playlist exists in both replicas; the cloud row has
`playlist_title = 'Deep Learning Lectures'` (set by `lib/job-queue/producer.ts:97` at enqueue).
The user summarizes one new video locally. Sync runs: that video is local-only with no baseline →
`copyAdditiveVideo` → `ensureReceiverSlot` → `setPlaylistMeta(cloudP, { playlistUrl })` →
`UPDATE playlists SET playlist_title = NULL`. The cloud sidebar/`listPlaylists` now shows an
untitled playlist. This recurs on every sync that carries any local-only video — i.e. the ordinary
case. Recovery needs the `POST /api/playlists/backfill-titles` route plus a YouTube API key.

**Cross-backend divergence (the tell).** The local store spreads conditionally —
`...(meta.playlistTitle ? { playlistTitle } : {})` over the existing index
(`local-metadata-store.ts:13-21`) — so the cloud→local direction **preserves** the title while
local→cloud **destroys** it. Same interface, opposite semantics for the same input. The codebase
already has the never-clobber primitive for exactly this reason — `setPlaylistTitleIfNull`
(`metadata-store.ts:34`, `supabase-metadata-store.ts:208`) — and the sync path bypasses it.

No test in `tests/lib/cloud-sync/` or `tests/integration/cloud-sync/` asserts anything about
`playlistTitle` / `playlist_title` surviving a sync.

**Fix.** Two parts, both small:
1. Carry the title through discovery — add `playlistTitle?: string` to `LocalPlaylist` and
   populate it from `idx.playlistTitle` at `registry.ts:29`.
2. Make `playlistMetaFor` merge rather than first-wins: take the URL from the local entry when
   present, but fall back to the cloud summary's title when local has none. Belt-and-braces, have
   `ensureReceiverSlot` use `setPlaylistMeta` for the URL and `setPlaylistTitleIfNull` for the
   title, so a sync can only ever fill a title, never clear one.

---

## Checked and clean (no finding)

- **Baseline advance.** Every branch either writes a baseline or throws before doing so:
  additive (`:460`, only after `copyAdditiveVideo`'s row+artifact verification at `:195-208`),
  corrections-unresolved (`:523`, preserving the previous Class-A per WB-B1), reconciled (`:558`,
  after the verified commit). The B1 throw correctly advances none. Class-B writes assert
  `found` (`:266`). No advance without a durable write.
- **Money-safety.** No producer/enqueue import on the sync path (`tests/lib/cloud-sync/import-guard.test.ts`
  guards it); no `spend_ledger` touch; `sanitizeAdditiveVideo` (:107-124) clears
  `summaryHtml`/`digDeeperHtml`/`digDeeperMd` and drops every non-`summaryMd` artifact pointer;
  `transferClassA` clears only the two HTML caches and preserves the paid `digDeeperMd` (H-R2-2
  holds at `:322-331`); `needsRegen` remains report-only. H1 and H2 above are the two paths that
  can force re-spend.
- **Atomicity.** stage → verify-by-hash → `put` (overwrite, uniform across backends) → drop temp →
  `updateVideoFields` advertising `promoted` only after the bytes are live (`:286-337`). The
  `promote()` create-if-absent divergence is correctly worked around, with the reason recorded.
- **Idempotency across two runs.** Additive → row exists → `ensureReceiverSlot` returns null →
  upsert is a no-op-equivalent; transfer → identical hashes → `skip`; conflict → preserved
  baseline → re-evaluated. Verified per branch.
- **Failed-read-as-default siblings, audited and clean.** `supabase-metadata-store.readIndex`
  throws on every error (`:34,42`); `lib/index-store.readIndex` throws on non-ENOENT and
  distinguishes a missing directory (`:87-97`); `listPlaylists`/`claimVideoSlot`/`upsertVideo` all
  `if (error) throw`.
- **Lost/corrupt manifest → empty (`manifest.ts:20`).** Real, but explicitly accepted by the spec
  (§8 "Lost/corrupt manifest degrades to a direct compare"; Residual R2 "a fresh device / lost
  manifest may re-create a deleted entity"). Not reported as a finding.
- **RLS / service-role.** `cloudP.id = deps.ownerId` (`:435`); `SyncDeps` exposes no raw client;
  no service-role key reachable from the sync path. Unchanged.

Known/deferred items (T14-M1, T14-M2, T5 coverage, T4 automock, Claude-R2-M1, Codex-R2-Medium,
Claude-R3-M1) were re-checked against the shipped state and none of them masks any of the above.

---

**NOT CONVERGED**
