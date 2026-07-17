# Stage 3 — Cloud Sync (local ↔ cloud reconciliation) — Design Spec

**Status:** Draft v1 — brainstormed + user-approved design (2026-07-17). Pending: grill-with-docs
terminology pass + dual adversarial review to convergence, then user approval → implementation plan.

**Roadmap:** M2 of `docs/roadmap-to-launch.md` (Deploy → **Sync** → Acceptance).

**Goal (one sentence):** Give the single author a **Cloud Sync** that reconciles their local research
corpus with their own multi-tenant cloud account — per-video newer-wins — so the cloud portal mirrors
local work for peer sharing and multi-device access, and a second device can hydrate from the cloud.

---

## 1. Scope

**Decomposition (M2 splits into two slices):**
- **M2a — THIS spec:** local→cloud push **and** cloud→local pull of **metadata + documents**; per-video
  **newer-wins**; **additive** (no cross-replica deletes). Manual trigger.
- **M2b — later slice (own spec):** image/slide-asset backfill (both directions), tombstone-based delete
  propagation, background/auto-sync, and true-conflict loser-preservation. Named here so M2a's seams
  anticipate them, not built here.

**In scope (M2a):**
- Reconcile, per YouTube playlist, the **source-of-truth** artifacts of each video, both directions.
- A portable per-video change signal (`contentGeneratedAt` + content hash) added on both sides.
- Local↔cloud auth via the existing Supabase Auth login (local acts as the authenticated user).
- A local **sync manifest** (last-synced baseline) enabling incremental sync + conflict detection.
- A manual **Cloud Sync** command (all playlists or one).

**Out of scope (M2a — deferred to M2b, explicitly):**
- **Slide/dig image assets — deferred in BOTH directions** for v1 (see §4 and §11 residual R1). A synced
  doc may reference images not present on the receiving side; it renders with a placeholder.
- Delete propagation (v1 is additive; deletes are per-surface and explicit).
- Background/automatic sync (v1 is a manual command).
- Preserving the losing side of a true conflict (v1 logs it; newer-wins overwrites).
- HTML/PDF transfer (regenerable cache — each side rebuilds locally; see §4).

---

## 2. Terminology

| Term | Meaning | NOT to be confused with |
|---|---|---|
| **Cloud Sync** | This feature: reconcile local corpus ↔ cloud tenant. | The existing local **"Sync"** button, which *refreshes a playlist's video list from YouTube* (`docs/superpowers/plans/2026-05-27-header-redesign.md`). Distinct feature; distinct name. All UI/code/docs use **"Cloud Sync"** to avoid the collision. |
| **Replica** | One copy of the corpus: a local install, or the cloud tenant. | — |
| **Reconcile unit** | One **video** (all its source-of-truth artifacts move together). | — |
| **Source of truth vs derived cache** | Per the cloud-publishing architecture §4: MD/model-JSON/slides/index are source; HTML/PDF are regenerable cache. | — |
| **Newer-wins** | On divergence, the replica whose video content is newer replaces the older. | — |
| **Reconcile** (this spec) | Merge two **replicas** to agreement (newer-wins). | The pre-existing codebase sense — a **DB↔blob / ledger consistency sweep** that repairs orphaned blobs or `reserved_cents` (architecture §4 M3; `local-validation-findings`). Same word, different domain; in Cloud Sync code prefer "**sync-merge**"/"reconcile **replicas**" to keep the two senses distinct. |

---

## 3. Identity (cross-replica keys)

Both replicas already carry YouTube identifiers, so identity needs **no synthetic mapping table**:

- **Playlist** = YouTube **list-id** = cloud `playlists.playlist_key` (`0001_core_schema.sql:13`,
  unique per `owner_id`); `Principal.indexKey` already abstracts "local data-root ↔ cloud playlist_key"
  (`lib/storage/principal.ts`).
- **Video** = YouTube **`video_id`** (`types/index.ts:30`).
- **Owner** = the authenticated cloud `auth.uid()` (the local tool's Supabase session, §6). Sync always
  targets **your own tenant**; peers receive access via existing share tokens, never via sync.

A local playlist that was fetched from a YouTube playlist URL knows its list-id; that is the join key to
the cloud `playlist_key`. The cloud internal UUID `playlists.id` is resolved from `(owner_id, playlist_key)`.

---

## 4. What syncs

| Artifact | Tier | M2a? | Rationale |
|---|---|---|---|
| Playlist record (title, key, metadata) | source | ✅ | Small; newer-wins by its own signal. |
| Video index/metadata record | source | ✅ | The per-video reconcile carrier. |
| Summary **MD** | source | ✅ | Un-regenerable without Gemini. |
| Model **JSON** (magazine/quick-view) | source | ✅ | Un-regenerable. |
| Deep-dive **MD** | source | ✅ | Un-regenerable. |
| Section timestamps | source | ✅ | Small structured data on the video record. |
| `docVersion` / `deepDiveVersion` | source | ✅ | Content-version signal (travels with the record). |
| **Slide / dig images** | source | ⛔ **deferred (M2b)** | Large; cloud may soon generate its own (see R2); isolating the blob-copy path keeps M2a's reconcile engine focused. Receiving side shows a placeholder (R1). |
| **HTML doc** | cache | ⛔ never | Deterministic re-render from MD (`rerender-html`, no Gemini). Each side rebuilds; avoids cache-version skew. |
| **PDF** | cache | ⛔ never | Chromium re-render from MD. Rebuilt on demand each side. |

---

## 5. Conflict model (per video)

### 5.1 The signal — "version + timestamp + hash"
Add a **portable** per-video field **`contentGeneratedAt`** (ISO-8601 UTC), stamped whenever *any* of the
video's source-of-truth artifacts is (re)generated, **on both replicas** (local generation path and cloud
worker). This is required because today's `updatedAt` is **cloud-only** (a DB trigger, `0015`; "the local
path never sets it", `types/index.ts:81`) and local relies on file mtime — not the same clock, not portable.

Also add a per-video **`contentHash`**: a stable hash over the video's source-of-truth artifact set
(summary MD + model JSON + deep-dive MD + section timestamps + syncable metadata; **excludes** volatile
fields like `updatedAt`, `summaryReady`, and image bytes). Deterministic and order-independent.

### 5.2 Decision function `resolve(L, C)` for a video present on both sides
1. If `L.contentHash == C.contentHash` → **no-op** (identical content; skip transfer).
2. Else compare **`docVersion`** (parsed `major.minor`): strictly higher **wins**.
3. Tie on `docVersion` → newer **`contentGeneratedAt`** wins.
4. Still tied (equal version, equal timestamp, different hash — a genuine clock-collision) → **deterministic
   tiebreak**: keep the replica with the lexicographically greater `contentHash`, and **log a conflict**
   (never silently pick "local" or "cloud" — the choice must be replica-symmetric so both machines converge).

The winner's source-of-truth artifacts overwrite the loser's for that video.

### 5.3 True-conflict detection (both changed since last sync)
Using the manifest baseline (§8): if **both** `L.contentHash` and `C.contentHash` differ from the
last-synced hash, both sides changed independently → a **true conflict**. v1 resolves it by §5.2 (newer-wins)
and **records it in a conflict log** (playlist_key, video_id, winner, loser version/timestamp). Preserving
the loser's content is deferred (M2b). If only one side differs from baseline, it is an unambiguous update
(no conflict) and simply propagates.

### 5.4 Video present on only one side
Create it on the other (additive). This is how a fresh device hydrates and how new local work publishes.

### 5.5 Deletes
**Additive-only in v1.** A video/playlist deleted on one replica is **not** deleted on the other; it will
be **re-created** on the deleting side on next sync (it still exists on the other side) — an accepted v1
behavior (§11 R3). Tombstone-based deletion is M2b.

---

## 6. Auth (local → cloud)

The local tool signs into the cloud with the **same Supabase Auth login** as the web app, obtains a user
session (access + auto-refreshing refresh token), and the sync client issues all cloud reads/writes with
that session → every write is **RLS-scoped to `auth.uid()`** (your tenant). No new credential type; no
service-role key on the local machine (that would bypass RLS — forbidden).

- Session is persisted locally in a **git-ignored** config file (e.g. `~/.config/<app>/cloud-session.json`
  or under the data root), treated as a secret (file perms 600). `supabase-js` handles refresh.
- Sign-in is a one-time local command (`cloud-sync login`) that runs the auth flow; sign-out clears the file.
- No cloud session → Cloud Sync refuses to run with a clear "run `cloud-sync login`" message (fail-closed).

---

## 7. Sync run (flow)

A **Cloud Sync** run, for each in-scope playlist (matched by `playlist_key`):

1. **Resolve** the cloud playlist (`owner_id, playlist_key`); create the cloud `playlists` row if absent
   (additive). Reconcile playlist-level metadata by the same version/timestamp rule.
2. **Enumerate** both replicas' videos for that playlist via the `MetadataStore` contract (cloud impl
   exists; local impl is the FS/`playlist-index.json` bundle).
3. **For each video** (union of both sides' `video_id`s): compute/read `contentHash` + `contentGeneratedAt`
   + `docVersion`; apply §5 to decide winner (or skip / create).
4. **Apply** a transfer for each video that needs one, **blob-before-metadata** (the architecture §4 M3
   write-consistency rule): upload source-of-truth blobs to the receiver's `BlobStore`, verify, then
   commit the receiver's metadata record (record + version + `contentGeneratedAt` + `contentHash`). A
   partial run never leaves a metadata record pointing at a missing blob.
5. **Update the manifest** (§8) with the new agreed baseline per reconciled video.
6. **Report**: counts of created / updated-local / updated-cloud / skipped-identical / conflicts-logged /
   errors. Per-video errors are isolated (one bad video does not abort the run); the run is **idempotent
   and resumable** (re-run reconciles only what still differs).

Cloud→local writes go through the local FS bundle; local→cloud writes go through the Supabase bundle under
the user's session. HTML/PDF are **not** transferred; the receiving side (re)renders lazily from MD as today.

---

## 8. Sync state — local manifest

A local **sync manifest**, **one file per playlist** (git-ignored JSON, e.g.
`<data-root>/<playlist_key>/.cloud-sync-manifest.json` — per-playlist for isolation and to avoid a single
global file becoming a contention/corruption point), records per `video_id` the **last-synced baseline**:
`docVersion`, `contentGeneratedAt`, `contentHash`, `syncedAt`. Purposes:

- **Incremental:** a video whose current hash equals its baseline on the side being read has not changed;
  combined with §5.1, unchanged videos are cheap to skip.
- **Conflict detection:** §5.3 needs the baseline to tell "both changed" from "one changed."

The manifest is an **optimization + conflict-input, not the source of truth** — a lost/corrupt manifest
degrades gracefully to a full content-hash comparison (correctness preserved; only conflict *detection*
weakens to "can't prove it wasn't a conflict," which v1 handles by newer-wins anyway).

---

## 9. Trigger

**Manual** in v1: a `cloud-sync` command (CLI script `npm run cloud-sync [-- --playlist <list-id>]`, and/or
a local UI button labeled **"Cloud Sync"**) that runs §7 for all playlists or one. Explicit, debuggable,
and safe (the author decides when replicas reconcile). Background/auto-sync is M2b.

---

## 10. Testing

- **Boundary:** mock the cloud at the `MetadataStore`/`BlobStore` adapter seam (per the project mocking
  policy); no real network in unit tests. An integration layer exercises the real local FS bundle ↔ a
  local-Supabase cloud bundle.
- **Reconcile matrix (unit):** local-newer, cloud-newer, equal-hash-skip, higher-docVersion-wins,
  version-tie→timestamp, full-tie→deterministic-hash-tiebreak+log, new-on-local-only, new-on-cloud-only,
  both-changed→true-conflict(newer-wins+log), unreachable-cloud (fail-closed, partial-safe), missing-image
  →placeholder, manifest-lost→degrades-to-hash-compare.
- **Consistency:** blob-before-metadata ordering — a simulated failure between blob upload and metadata
  commit must never leave a record pointing at a missing blob; re-run heals.
- **Auth:** no session → refuses with the login hint; RLS scoping — a sync write lands only in the caller's
  tenant (cross-tenant write rejected).
- **Idempotency:** two consecutive runs with no changes → second run is all-skips, zero writes.

---

## 11. Accepted residuals / risks (v1)

- **R1 — Missing images on the receiver.** A synced doc can reference slide images the receiving replica
  lacks (images deferred to M2b). The doc renders with a **placeholder**; no broken state. Closed by M2b
  image backfill.
- **R2 — Cloud capture capability (to verify).** The design assumes cloud will *eventually* generate its
  own slide images (making cloud→local backfill partly moot). **This is unverified** — flagged for
  confirmation. It does not block M2a (M2a moves no images either way).
- **R3 — Re-creation of one-sided deletes.** Additive-only means a video deleted on one replica but still
  present on the other is re-created on next sync. Accepted for v1; closed by M2b tombstones.
- **R4 — True-conflict data loss.** A genuine concurrent edit of the same video on two replicas resolves by
  newer-wins; the older side's change is overwritten (but **logged**). Rare for a single author; loser-
  preservation is M2b.
- **R5 — Clock skew.** Newer-wins leans on `contentGeneratedAt` for version ties. Bounded for one author's
  roughly-NTP-synced devices; `docVersion` is the primary signal and the hash prevents needless transfers,
  so skew only matters in the narrow version-tie-different-content window (then §5.2 step 4 is deterministic).

---

## 12. Resolved decisions (user, 2026-07-17)

1. **Image scope — CONFIRMED deferred (both directions) in M2a.** Keeps v1 a clean metadata/doc reconcile
   engine; local→cloud image *push* is the first item of M2b, alongside cloud→local backfill.
2. **R2 (cloud capture capability) — carried as a flagged assumption.** Does not block M2a (which moves no
   images either way); revisited when M2b is scoped.
3. **Manifest granularity — per-playlist** (§8), for isolation.
