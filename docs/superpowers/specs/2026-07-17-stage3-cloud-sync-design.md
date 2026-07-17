# Stage 3 — Cloud Sync (local ↔ cloud reconciliation) — Design Spec

**Status:** Draft **v2** — revised after dual adversarial review round 1 (Codex + Claude/opus, both NOT
CONVERGED, consensus on the `docVersion`-primary data-loss flaw). v2 addresses all Blocking/High + the
Medium/Low dispositions and narrows M2a to **summary-only** (deep-dive deferred to M2b, user-approved
2026-07-17). Pending: dual re-review to convergence → user approval → implementation plan.
Round-1 reviews: `.superpowers/sdd/cloud-sync-spec-{codex,claude}.md`.

**Roadmap:** M2 of `docs/roadmap-to-launch.md` (Deploy → **Sync** → Acceptance).

**Goal (one sentence):** Give the single author a **Cloud Sync** that reconciles their local research
corpus with their own multi-tenant cloud account — per-video newer-wins — so the cloud portal mirrors
local work for peer sharing and multi-device access, and a second device can hydrate from the cloud.

---

## 1. Scope

**M2 decomposition:**
- **M2a — THIS spec:** local↔cloud reconciliation of **summary** source-of-truth + video/playlist
  **metadata**, both directions, per-video **newer-wins** (timestamp-primary), with a **delete-intent**
  guard (not pure-additive — see §5.5). Manual trigger.
- **M2b — later slice (own spec):** **deep-dive/dig** sync (its per-section blob model + `DIG_GENERATOR_VERSION`
  axis + slide **images**, both directions), tombstone-based delete propagation, background/auto-sync, and
  true-conflict loser-preservation.

**In scope (M2a):**
- Reconcile, per YouTube playlist, each video's **summary** source-of-truth + syncable metadata, both
  directions, including **union hydration** (a fresh device pulls cloud-only playlists/videos; new local
  work creates cloud-only ones).
- A portable, canonical **change signal** (`contentGeneratedAt` primary + `contentHash`) added on both
  replicas, with a one-time **backfill** for legacy records.
- Local↔cloud auth via the existing Supabase Auth login (local acts as the authenticated user).
- A per-playlist local **sync manifest** (last-synced baseline) for incremental sync + conflict detection.
- A **delete-intent** marker so an explicit deletion is not resurrected by the next sync.
- A manual **Cloud Sync** command (all playlists or one).

**Out of scope (M2a — deferred to M2b, explicitly):**
- **Deep-dive / dig** in any direction (per-section blobs, `DIG_GENERATOR_VERSION`, slide images). A cloud
  video's dig content is simply not touched by M2a sync.
- **Slide / dig images** (deep-dive-only; summaries embed no images, so M2a has no image dependency).
- Tombstone-propagated deletes (M2a uses a *local* delete-intent marker, not cross-replica tombstones).
- Background/automatic sync (v1 is a manual command).
- Preserving the losing side of a true conflict (v1 logs it; newer-wins overwrites).
- HTML/PDF transfer (regenerable cache — each side rebuilds locally; see §4).

---

## 2. Terminology

| Term | Meaning | NOT to be confused with |
|---|---|---|
| **Cloud Sync** | This feature: reconcile local corpus ↔ cloud tenant. | The existing local **"Sync"** button, which *refreshes a playlist's video list from YouTube* (`docs/superpowers/plans/2026-05-27-header-redesign.md`). Distinct feature; distinct name everywhere. |
| **Replica** | One copy of the corpus: a local install, or the cloud tenant. | — |
| **Reconcile** (this spec) | Merge two **replicas** to agreement (newer-wins). | The pre-existing codebase sense — a **DB↔blob / ledger consistency sweep** (architecture §4 M3). Same word, different domain; in Cloud Sync code prefer "**sync-merge**"/"reconcile **replicas**". |
| **Reconcile unit** | One **video** (its summary source-of-truth + syncable metadata move together). | — |
| **Change signal** | `(contentGeneratedAt, contentHash)` — the portable per-video freshness + identity used by newer-wins. | `docVersion` — a code/format version, **not** a recency signal (§5.2). |
| **Newer-wins** | On divergence, the replica whose video content is **more recently generated/edited** replaces the older. | — |

---

## 3. Identity (cross-replica keys)  — *reviewed sound (round 1)*

Both replicas already carry YouTube identifiers, so identity needs **no synthetic mapping table**:

- **Playlist** = YouTube **list-id** = cloud `playlists.playlist_key` (`0001_core_schema.sql:13`,
  unique **per `owner_id`**, `:17`); `Principal.indexKey` already abstracts "local data-root ↔ cloud
  playlist_key" (`lib/storage/principal.ts:7`).
- **Video** = YouTube **`video_id`** (`types/index.ts:30`).
- **Owner** = the authenticated cloud `auth.uid()` (the local tool's Supabase session, §6). Sync always
  targets **your own tenant**; the composite FK `videos(playlist_id, owner_id) → playlists(id, owner_id)`
  (`0001:31-32`) + forced RLS guarantee a video's owner equals its playlist's owner. Two owners sharing a
  YouTube list-id are isolated by `auth.uid()`. Peers get access via existing share tokens, never via sync.

---

## 4. What syncs (M2a)

| Artifact | Tier | M2a? | Notes |
|---|---|---|---|
| Playlist record (title, `playlist_key`, `playlistUrl`) | source | ✅ | Small; reconciled by the change signal. |
| Video index/metadata record (see §4.1 field split) | source | ✅ | The per-video reconcile carrier. |
| Summary **MD** | source | ✅ | Un-regenerable without Gemini. Section-timestamp `▶` markers live **inline in this MD** (`lib/summary-section-timestamps.ts`) — they ride along; **not** a separate artifact. |
| Model **JSON** (`ModelEnvelope`: magazine + quick-view) | source | ✅ | Un-regenerable. §10 asserts cloud `ModelEnvelope` ↔ local model shape render-parity. |
| **Deep-dive / dig** (per-section blobs, model, `DIG_GENERATOR_VERSION`) | source | ⛔ **M2b** | Incompatible cross-replica shape + separate version axis + slide images; specced properly in M2b. |
| **Slide / dig images** | source | ⛔ **M2b** | Deep-dive-only; summaries embed none → M2a has no image dependency. |
| **HTML doc / PDF** | cache | ⛔ never | Deterministic re-render from MD + model JSON (`rerender-html`, Chromium). Each side rebuilds; avoids cache-version skew. |

### 4.1 Video field split (drives the hash + reconcile)
- **Content (synced, in `contentHash`, restamps `contentGeneratedAt` on change):** summary MD, model JSON,
  and **user-authored** metadata — `title` (author-corrected), `personalNote`, `personalScore`, `archived`.
- **Replica-local / fetch-derived (NOT synced, NOT in `contentHash`):** `position`, `serialNumber`,
  `playlistIndex`, `removedFromPlaylist` (each replica maintains these from its own YouTube fetch/ordering;
  reconciling them by content newer-wins would flip-flop across syncs — round-1 opus L3, H2). `updatedAt`,
  `summaryReady` are DB-computed and excluded (`supabase-metadata-store.ts` already strips them).

---

## 5. Conflict model (per video) — *rewritten in v2 (round-1 B1/B2/B3, H2/H3)*

### 5.1 The change signal
**`contentGeneratedAt`** (ISO-8601 UTC) — the **primary** freshness signal. Stamped on **every**
content-mutating path, on **both** replicas:
- summary generation — local (`lib/pipeline.ts`) **and** cloud worker (`lib/job-queue/summary-handler.ts`);
- **non-generation content edits** — `personalNote`, `personalScore`, `archived`, in-MD section-timestamp
  fixes, author `title` correction.
Every such write MUST restamp `contentGeneratedAt = now()`. It is added to `VideoSchema`, local writes,
the cloud worker payload, **and** the cloud `persist_summary` / metadata-merge SQL whitelists (a field the
whitelist omits is silently dropped — round-1 B2). Deep-dive generation does **not** stamp it (dig is M2b).

**`contentHash`** — a **canonical** digest identifying the content set (§5.2), used to skip identical
content and detect divergence.

**Back-compat backfill (required before first reconcile):** legacy records have neither field. A one-time
backfill seeds `contentGeneratedAt` from the best existing signal — local: `processedAt` (`types/index.ts:60`);
cloud: `videos.updated_at` — and computes `contentHash`, **persisting both before** the first sync-merge.
`contentGeneratedAt` is **never null at reconcile time**; if a value is genuinely absent it is treated as a
**conflict** (log + no destructive overwrite), never as epoch-oldest (round-1 B2/H3).

### 5.2 Canonical `contentHash` contract (round-1 B3/H2)
The hash is computed from a **normalized in-memory shape**, never from either backend's stored bytes
(Postgres `jsonb` does not preserve key order/whitespace; a local JSON file does). A **single shared
implementation** (`lib/cloud-sync/content-hash.ts`) is called by both replicas. Algorithm:
1. Assemble the **content field set** (§4.1 "content" only): summary MD, model JSON, `title`,
   `personalNote`, `personalScore`, `archived`. Exclude every replica-local/derived/cache/volatile field.
2. Normalize: recursively **sort object keys**; canonical number formatting; **NFC** Unicode; MD normalized
   to **LF** with a fixed trailing-newline rule; absent vs `null` collapsed to a single canonical form.
3. Serialize the normalized shape to a canonical UTF-8 byte stream; digest = SHA-256 hex.
§10 requires **cross-backend golden fixtures**: the same logical content stored as a local file and as
Postgres `jsonb` must hash **equal**.

### 5.3 Decision function `resolve(L, C)` for a video on both sides
1. `L.contentHash == C.contentHash` → **no-op** (identical; skip transfer).
2. Else newer **`contentGeneratedAt`** wins. *(Primary signal — not `docVersion`.)*
3. Exact-timestamp tie, different hash → deterministic tiebreak: keep the replica with the
   lexicographically greater `contentHash` (**replica-symmetric** — both machines pick the same winner and
   converge), and **log a conflict**.
`docVersion` is **not** a recency input: `.minor` is a render/cache axis (excluded entirely); `.major` is
consulted only as a **format-capability guard** — never *downgrade* a higher-`major` MD onto a replica
whose renderer is lower-`major` (skip + log instead), but it never decides "who is newer."

### 5.4 True-conflict detection (both changed since last sync)
Using the manifest baseline (§8): if **both** `L.contentHash` and `C.contentHash` differ from the
last-synced hash → **true conflict** → resolve by §5.3 (newer-wins) + record in the conflict log (§8.1).
Loser-preservation is M2b. If only one side differs from baseline → unambiguous update (no conflict). If
**no manifest baseline exists** (fresh device), a both-sides-present divergence is logged as a conflict
**before** newer-wins is applied (round-1 M1) — the log stays honest even without a baseline.

### 5.5 Presence & deletes (round-1 H4/M3)
- **Video/playlist on only one side, never seen before** → additive **create** on the other (this is how a
  fresh device hydrates and new local work publishes).
- **Delete-intent guard (not pure-additive):** deleting a video/playlist on a replica records a local
  **delete-intent marker** (in the manifest, §8). Sync **must not resurrect** an entity with a live
  delete-intent, and **must not re-push** an entity the *cloud* hard-deleted (the app has real
  hard-delete: cascade FKs `0001:32`, playlist-sidebar hard-delete). "Absent because deleted here" is
  distinguished from "absent because never seen." A cloud-only-hard-deleted playlist is not auto-recreated
  from local without explicit confirmation.
- **Re-creation is a pure metadata/doc copy** — it MUST NOT route through the metered enqueue
  (`lib/job-queue/producer.ts`), MUST NOT re-consume spend/`spend_ledger`, and MUST NOT resurrect derived
  cache. (Sync moves already-produced source artifacts; it never triggers generation.)

---

## 6. Auth (local → cloud) — *reviewed sound; v2 hardens credential storage (round-1 M2/L1)*

Local signs into the cloud with the **same Supabase Auth login** as the web app; the sync client issues all
cloud reads/writes with that user session → every write is **RLS-scoped to `auth.uid()`**. **No service-role
key on the local machine**, and any server-mediated sync endpoint derives `owner_id` from the session and
resolves playlists by `(auth.uid(), playlist_key)` — **never** from a client-supplied owner id (round-1 L2).

- **Credential storage:** prefer the **OS keychain** for the refresh token. File fallback only with mode
  **600** + a **parent-directory permission check** + gitignore enforcement + **fail-closed** if perms are
  too broad. The refresh token is a long-lived, auto-refreshing **full-tenant bearer credential** — theft =
  full same-tenant read/write (no cross-tenant break); document this blast radius; sign-out clears it.
- No cloud session → Cloud Sync refuses with a clear "run `cloud-sync login`" message (fail-closed).

---

## 7. Sync run (flow) — *v2 fixes union enumeration + atomicity (round-1 H5, H2/H3)*

1. **Enumerate the playlist set as the UNION** of both replicas' `playlist_key`s: local (a discovery of
   local playlist roots, §7.1) **∪** cloud (`SELECT playlist_key FROM playlists WHERE owner_id = auth.uid()`).
   A playlist on only one side is **created** on the other (cloud-only → hydrated into a local root; local-only
   → created on cloud), subject to §5.5 delete-intent. *(A fresh device with an empty local corpus thus pulls
   the full cloud corpus — the core hydration use case.)*
2. **Per playlist**, enumerate the **union** of `video_id`s across both replicas via the `MetadataStore`
   contract (cloud impl exists; local impl is the FS/`playlist-index.json` bundle).
3. **Per video**, compute the change signal (§5.1) on each side and apply §5.3 (skip / newer-wins / create,
   honoring §5.5).
4. **Apply a transfer atomically, per video**, aligned with the existing **staged → committed → promoted**
   protocol (`lib/storage/supabase/consistency.ts`, `summary-handler.ts`): upload each source blob to a
   staged key under an **idempotency key**, verify, promote **all** to final keys, then commit the receiver's
   metadata (record + `contentGeneratedAt` + `contentHash`). A crash mid-transfer leaves staged (not final)
   objects and an unadvanced baseline; a re-run finishes or rolls back deterministically. The metadata record
   MUST NOT advertise the new `contentHash` until **every** source blob is `promoted` (round-1 H2/H3).
5. **Update the manifest (§8) strictly AFTER** the receiver's metadata commit is verified durable, recording
   the **receiver-observed committed hash** (not the planned winner hash). Never advance a baseline for a
   partial transfer (round-1 H2 / M1).
6. **Report**: counts of created / updated-local / updated-cloud / skipped-identical / conflicts-logged /
   errors. Per-video errors are isolated (one bad video never aborts the run); the run is **idempotent and
   resumable** (re-run reconciles only what still differs). Cloud→local writes go through the local FS
   bundle; local→cloud through the Supabase bundle under the user's session. HTML/PDF are **not** transferred;
   the receiver re-renders lazily from MD + model JSON as today.

### 7.1 Local playlist discovery (round-1 M3/H5)
`LocalFsMetadataStore` is keyed by a data-root path, not a `playlist_key`. M2a defines a **local playlist
registry**: each local playlist root persists its `playlist_key` (+ `playlistUrl`, title) in its
`playlist-index.json`, and Cloud Sync discovers local playlists by scanning the configured data root(s) and
reading those keys. Cloud-only playlists are hydrated into **deterministic** local roots (named by
`playlist_key`), with `playlist_key`/title/`playlistUrl` persisted so the next run round-trips stably.

---

## 8. Sync state — per-playlist local manifest — *v2: ordering + conflict-log + delete-intent*

One manifest **file per playlist** (git-ignored JSON, `<data-root>/<playlist_key>/.cloud-sync-manifest.json`
— per-playlist for isolation), recording per `video_id` the **last-synced baseline**: `docVersion`,
`contentGeneratedAt`, **receiver-observed `contentHash`**, `syncedAt`; plus **delete-intent** entries
(§5.5). Rules:
- The baseline is written **only after** §7 step 5's verified commit — never ahead of reality (round-1 M1).
- The manifest is an **optimization + conflict input, not the source of truth**: a lost/corrupt manifest
  degrades to a full content-hash comparison; a both-sides divergence with no baseline is **logged as a
  conflict** before newer-wins (§5.4), so correctness (never a silent destructive overwrite) is preserved.

### 8.1 Conflict log (round-1 M2)
Conflicts (§5.3 tiebreak, §5.4 true conflicts) are appended to a **per-playlist** git-ignored
`<data-root>/<playlist_key>/.cloud-sync-conflicts.log` (JSON lines): `video_id`, timestamp, winner
(`local|cloud`), both sides' `(contentGeneratedAt, contentHash, docVersion)`, and reason. **Caveat (v1):**
the log is **replica-local** — a conflict resolved on device A is not visible on device B; surfacing/merging
the conflict log across replicas is M2b (it depends on cloud-stored sync state).

---

## 9. Trigger

**Manual** in v1: a `cloud-sync` command (`npm run cloud-sync [-- --playlist <list-id>]`, and/or a local UI
button labeled **"Cloud Sync"**) running §7 for the **union** of playlists (all) or one. Explicit,
debuggable, safe. Background/auto-sync is M2b.

---

## 10. Testing

- **Boundary:** mock the cloud at the `MetadataStore`/`BlobStore` seam (project mocking policy); no real
  network in unit tests. An integration layer exercises the real local FS bundle ↔ a local-Supabase cloud
  bundle.
- **Canonical hash (round-1 B3/H2):** **cross-backend golden fixtures** — identical logical content stored
  as a local JSON file vs Postgres `jsonb` (different key order/whitespace) hashes **equal**; replica-local
  fields (`position`, `serialNumber`, `playlistIndex`, `removedFromPlaylist`) changing does **not** change
  the hash; a `personalNote`/`title`/MD change **does**.
- **Newer-wins matrix:** local-newer, cloud-newer, equal-hash-skip, exact-timestamp-tie→deterministic
  tiebreak+log, `docVersion` drift does **NOT** override a newer timestamp (the B1 regression test:
  cloud `docVersion 4.0` + old timestamp vs local `docVersion 3.3` + newer timestamp → **local wins**).
- **`contentGeneratedAt` (round-1 B2/H3):** every content-mutating path restamps it (summary gen
  local+cloud; `personalNote`/`archived`/section-fix edits); a legacy null is backfilled from
  `processedAt`/`updated_at` before reconcile; a genuinely-missing value → conflict (no overwrite).
- **Union hydration (round-1 H5):** empty local corpus + non-empty cloud → **full local hydration**;
  local-only new work → created on cloud.
- **Atomicity/resume (round-1 H2/H3):** a simulated failure between blob-promote and metadata-commit never
  leaves a record advertising a hash for a missing blob, and never advances the manifest baseline; a re-run
  heals; two consecutive no-change runs → second is all-skips, zero writes.
- **Delete-intent (round-1 H4/M3):** a video/playlist deleted on one side is **not resurrected** while the
  intent is live; re-creation of a genuinely-new one-sided entity **never** calls the metered enqueue and
  never touches `spend_ledger`.
- **Auth/RLS:** no session → login-hint refusal; a sync write lands only in the caller's tenant
  (client-supplied `owner_id` rejected); broad session-file perms → fail-closed.
- **Render parity (round-1 M4):** a synced-in summary MD + model JSON renders HTML/PDF on the receiver
  without error (cloud `ModelEnvelope` ↔ local model shape confirmed compatible).

---

## 11. Accepted residuals / risks (v1)

- **R1 — True-conflict data loss.** A genuine concurrent edit of the same video on two replicas resolves by
  newer-wins; the older side's change is overwritten (but **logged**, §8.1). Rare for a single author;
  loser-preservation is M2b.
- **R2 — Clock skew (now load-bearing).** With `contentGeneratedAt` as the **primary** signal, newer-wins
  leans on the two replicas' clocks. Bounded for one author's roughly-NTP-synced devices; the content hash
  prevents needless transfers (equal content never races), and an exact-timestamp collision falls to the
  deterministic §5.3 tiebreak. A grossly-wrong clock on one device can still mis-order edits — accepted for
  v1 (single author); a logical-clock upgrade is a possible M2b hardening.
- **R3 — Replica-local conflict log.** A conflict resolved on one device isn't visible on another (§8.1);
  cross-replica conflict surfacing is M2b.
- **R4 — Cloud capture capability (to verify, unchanged).** M2b's cloud→local image backfill assumes cloud
  will eventually generate its own slides; unverified, does not affect M2a (no images in summary scope).

---

## 12. Resolved decisions

1. **Deep-dive → M2b** (user, 2026-07-17, review-driven): not cleanly implementable in M2a (retired fields,
   per-section blob model, separate `DIG_GENERATOR_VERSION` axis, entangled with deferred images).
2. **Newer-signal = `contentGeneratedAt` primary; `docVersion` is NOT a recency signal** (round-1 B1).
3. **Delete-intent guard** (not pure-additive) — required because the app has real hard-delete (round-1 H4).
4. **Manifest granularity — per-playlist** (§8), for isolation.
5. **Images deferred (M2b)**; summaries have no image dependency, so M2a needs no image handling.
