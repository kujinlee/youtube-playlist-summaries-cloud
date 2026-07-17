# Stage 3 — Cloud Sync (local ↔ cloud reconciliation) — Design Spec

**Status:** Draft **v4** — revised after dual adversarial review round 3 (Codex CONVERGED; opus found 2
fix-introduced High). v4 closes: **H-1** — the model companion could serve *content-stale* prose (the serve
gate was body-blind); v4 adds `sourceMdHash` to `ModelEnvelope`, makes `isFresh` content-aware, and
invalidates a non-matching companion (§4.2). **H-2** — the restamp enumeration missed `merge_video_data`,
the only cloud writer of `title`/`corrections` (§5.1). Plus M-1 (the local-delete §5.5 transition), L-1
(conflict-log dedup), L-2 (companion is best-effort, outside the MD atomic commit).
(v3 had closed round-2: model→companion, non-destructive backfill, baseline-aware deletes, `archived` out of
hash, restamp enumeration, `corrections`.) Pending: dual re-review round 4 to convergence → user approval → plan.
Reviews: `.superpowers/sdd/cloud-sync-spec-{codex,claude}{,-r2,-r3}.md`.

**Roadmap:** M2 of `docs/roadmap-to-launch.md`.

**Goal:** Give the single author a **Cloud Sync** that reconciles their local research corpus with their own
multi-tenant cloud account — per-video newer-wins — so the cloud portal mirrors local work for peer sharing
and multi-device access, and a second device can hydrate from the cloud.

---

## 1. Scope

**M2 decomposition:**
- **M2a — THIS spec:** local↔cloud reconciliation of each video's **summary MD + user-authored text
  metadata**, both directions, per-video **newer-wins** (timestamp-primary), honest **additive** create with
  **baseline-aware** best-effort delete-suppression. Manual trigger.
- **M2b — later slice (own spec):** deep-dive/dig (per-section blobs + `DIG_GENERATOR_VERSION` + slide
  images), **cross-replica tombstone** delete propagation, background/auto-sync, true-conflict
  loser-preservation, cross-replica conflict-log surfacing.

**In scope (M2a) — the hashed source set is deliberately small:** summary **MD** + user-authored text
(`title`, `personalNote`, `personalScore`, `corrections`) + playlist/video identity metadata; union
hydration; a portable canonical change signal + non-destructive legacy backfill; Supabase-Auth login;
per-playlist local manifest; a manual **Cloud Sync** command.

**Out of scope (M2a — deferred, explicitly):**
- **Model JSON as a *compared source*.** It rides along as an **opaque companion of the winning MD** (§4.2)
  — never independently hash-compared or newer-wins-decided. Not a synced source in its own right.
- **Deep-dive / dig + slide images** (M2b). Summaries embed no images.
- **`archived`** and all membership/ordering fields (replica-local, §4.1).
- **Cross-replica tombstones / delete propagation** (M2b). M2a is additive with best-effort suppression.
- Background/auto-sync; true-conflict loser-preservation; HTML/PDF transfer.

---

## 2. Terminology

| Term | Meaning | NOT to be confused with |
|---|---|---|
| **Cloud Sync** | This feature: reconcile local corpus ↔ cloud tenant. | The existing local **"Sync"** button = *refresh a playlist's video list from YouTube*. Distinct feature, distinct name. |
| **Replica** | One copy of the corpus: a local install, or the cloud tenant. | — |
| **Reconcile** (this spec) | Merge two **replicas** to agreement (newer-wins). | The pre-existing codebase sense = a DB↔blob/ledger consistency sweep. Prefer "sync-merge"/"reconcile **replicas**". |
| **Change signal** | `(contentGeneratedAt, contentHash)` over the **hashed source set** — the portable per-video freshness + identity. | `docVersion` (a code/format version, not recency, §5.3); model JSON (a companion, §4.2). |
| **Hashed source set** | summary MD + `title` + `personalNote` + `personalScore` + `corrections` (§4.1). The *only* inputs to `contentHash` and newer-wins. | Everything derived/charged/membership-driven (§4.1 exclusions). |
| **Companion artifact** | A blob copied *with* the winning MD but never compared (model JSON, §4.2). | A hashed source. |
| **Newer-wins** | On divergence, the replica whose hashed source set is more recently generated/edited replaces the older. | — |

---

## 3. Identity (cross-replica keys) — *reviewed sound (rounds 1–2)*

- **Playlist** = YouTube **list-id** = cloud `playlists.playlist_key` (`0001:13`, unique **per `owner_id`** `:17`);
  `Principal.indexKey` abstracts local-path ↔ cloud playlist_key (`lib/storage/principal.ts:7`).
- **Video** = YouTube **`video_id`** (`types/index.ts:30`).
- **Owner** = authenticated `auth.uid()`. Composite FK `videos(playlist_id, owner_id)→playlists(id,owner_id)`
  (`0001:31-32`) + forced RLS guarantee a video's owner == its playlist's owner; two owners sharing a
  list-id are isolated by `auth.uid()`. No synthetic mapping table. Peers get access via share tokens, not sync.

---

## 4. What syncs (M2a)

### 4.1 Video field classification (the crux — round-2 BLK-1/H-D/H2)
- **Hashed source (synced; in `contentHash`; restamps `contentGeneratedAt` on change):**
  summary **MD** (section-timestamp `▶` markers ride *inline* in it), `title` (author-corrected),
  `personalNote`, `personalScore`, `corrections`.
- **Companion (copied with the winning MD, NOT hashed/compared — §4.2):** model JSON (`ModelEnvelope`).
- **Replica-local / derived / membership-driven (NOT synced, NOT hashed):** `position`, `serialNumber`,
  `playlistIndex`, `removedFromPlaylist`, **`archived`** (set by `reconcile_membership` `0007:60-71` from
  *each replica's own* YouTube fetch → would flip-flop; round-2 H-D), `updatedAt`, `summaryReady`
  (DB-computed, already stripped by `supabase-metadata-store.ts`).
- **Regenerable cache (never synced):** HTML doc, PDF (deterministic re-render from MD + model).

### 4.2 Model JSON as a companion (round-2 BLK-1; round-3 H-1)
Model JSON is a **non-deterministic, `GENERATOR_VERSION`-axed, charged, self-healing cache** (Gemini
transform; lazily regenerated + charged on the serve path — `lib/html-doc/model-store.ts`,
`read-model.ts`). It therefore **cannot** be a hash-compared source (identical MD would hash-diverge on the
model and churn/overwrite). Instead, when a video's **MD** wins newer-wins and is transferred, the model is
handled as a companion — but **safely**, not "opaquely":

**Content-aware freshness (required — closes round-3 H-1).** Today's serve freshness gate
(`isFresh`, `lib/html-doc/read-model.ts:21-25`) checks only section titles + `GENERATOR_VERSION`, **not the
MD body** — so a model built from an *older MD body with identical headings and the same version* would
serve silently after an MD change. M2a therefore:
1. **Extends `ModelEnvelope` with `sourceMdHash`** — the canonical §5.2-style hash of the MD the model was
   built from — and **extends `isFresh` to also require `sourceMdHash == hash(current MD)`.** A
   content-stale model can then never serve.
2. **On MD transfer:** ship the sender's model blob as a companion **only if** its `sourceMdHash` matches
   the winning MD (i.e. it was built from exactly that MD). Otherwise **invalidate/delete the receiver's
   model blob** for that video, so the receiver's next serve lazily regenerates from the new MD (the
   existing self-heal, now correctly triggered). Either way the receiver never renders stale prose.

The companion copy is thus a **best-effort re-charge avoidance** (common case: matching model ships → no
regen), with correctness guaranteed by (1)+(2), not by the copy. The model is never a newer-wins participant.

---

## 5. Conflict model (per video)

### 5.1 The change signal + stamping (round-2 H-C/H-E)
**`contentGeneratedAt`** (ISO-8601 UTC) — **primary** freshness signal — is stamped on **every** write that
mutates a **hashed-source** field, on both replicas. The complete writer enumeration — verified by grepping
every cloud RPC/allowlist and the local index writer (round-2 H-E, round-3 H-2); each must add
`contentGeneratedAt` and restamp when it mutates a hashed field:
- summary generation — local (`lib/pipeline.ts`) and cloud **`persist_summary`** (its layer-3 allowlist,
  `0009`) → writes MD/`title` → restamp;
- cloud annotation edits — **`update_video_annotations`** (`0016`), allowlist *closed* to
  (`personalScore`, `personalNote`, `archived`) — add `contentGeneratedAt`; restamp only when
  `personalScore`/`personalNote` change (`archived` is not hashed);
- **cloud `title`/`corrections` edits — `merge_video_data` via `updateVideoFields`**
  (`lib/storage/supabase/supabase-metadata-store.ts:119-125`; the regenerate route writes `corrections`
  here, `app/api/videos/[id]/regenerate/route.ts:55`). This is the **only** cloud writer of `title`/
  `corrections` and neither allowlisted RPC covers them, so it MUST restamp `contentGeneratedAt` when it
  mutates `title`/`corrections` (round-3 H-2);
- local metadata edits (note/score/title/corrections) via the local index writer.
Membership writers (`reconcile_membership`) touch only **non-hashed** fields (`archived`,
`removedFromPlaylist`) → no restamp.

**`contentHash`** — canonical digest over the **hashed source set only** (§5.2).

### 5.2 Canonical `contentHash` (round-1 B3 / round-2 confirmed)
Computed from a **normalized in-memory shape** (never a backend's stored bytes — Postgres `jsonb` doesn't
preserve key order/whitespace), by a **single shared impl** `lib/cloud-sync/content-hash.ts` called by both
replicas: recursively sorted keys, canonical numbers, NFC Unicode, MD normalized to LF + fixed
trailing-newline, absent/null collapsed. Digest = SHA-256 hex. §10 requires cross-backend golden fixtures
(same logical content as a local file vs `jsonb` → equal hash). Inputs = §4.1 hashed source **only**.

### 5.3 Decision `resolve(L, C)` for a video on both sides (round-1 B1)
1. `L.contentHash == C.contentHash` → **no-op** (skip).
2. Else, **if a manifest baseline exists and exactly one side differs from it** → that side is the
   unambiguous update → copy it (+ its companion model) to the other.
3. Else (both differ from baseline, OR **no baseline** — round-2 H-C) → this is a **potential conflict**: do
   **NOT** destructively overwrite based on backfilled/asymmetric timestamps. Resolve by newer
   `contentGeneratedAt` **only if both timestamps are real (non-backfilled)**; otherwise **log a conflict and
   skip the destructive write** (surface for the user), leaving both sides intact. Exact-timestamp tie with
   real stamps → deterministic lexicographic `contentHash` tiebreak (replica-symmetric) + log.
`docVersion` is **never** a recency input (`.minor` = render/cache axis, excluded; `.major` = a
format-capability guard only — never *downgrade* a higher-major MD onto a lower-major renderer, skip+log).

### 5.4 Backfill (legacy records) — non-destructive (round-2 H-C / Codex-r2 B1)
Legacy records lack `contentGeneratedAt`. A one-time backfill computes `contentHash` and records a
**provisional** `contentGeneratedAt` (local: `processedAt`; cloud: `updated_at`) **flagged as backfilled**.
Because these seeds are non-comparable across replicas (cloud `updated_at` is bumped by non-content touches
— `reconcile_membership`, serve merges), a backfilled timestamp **must never drive a destructive overwrite**:
per §5.3 step 3, a divergence where either side's timestamp is backfilled resolves to **conflict → skip +
log**, never overwrite. Once a real (post-feature) generation/edit restamps a side, its timestamp becomes
authoritative. Equal hashes always skip (and seed the baseline) regardless of timestamps.

### 5.5 Presence & deletes — additive + baseline-aware, honestly scoped (round-2 H-A/H-B)
- **On only one side, never in this replica's baseline** → additive **create** on the other (hydration /
  publish). Re-creation is a **pure metadata/doc copy**: it MUST NOT route through the metered enqueue
  (`lib/job-queue/producer.ts`), consume `spend_ledger`, or resurrect derived cache.
- **In this replica's manifest baseline but now ABSENT on the other side** → treated as a **remote delete**:
  do **not** re-create it; record the removal locally. (Best-effort, using the baseline as the "seen
  before" record — no cross-device tombstone.)
- **In this replica's baseline but now ABSENT on THIS side (present on the other)** → *this replica*
  deleted it (round-3 M-1). M2a does **not** propagate the delete (that is M2b tombstones): do **not**
  re-create it locally (it stays deleted here), and do **not** delete it on the other replica (it remains
  there). The entity simply diverges until M2b — a disclosed consequence of R2 (deletes don't propagate).
- **No delete-intent marker mechanism** (round-2 H-A showed a local marker has no sound lifecycle and
  suppresses legitimate re-adds). Deletion is inferred from baseline presence/absence, so a genuine
  local re-add (new `contentGeneratedAt`) simply syncs as a create/update — nothing to "clear."

**Disclosed residual (R2):** delete detection is **baseline-scoped and does not propagate**. A device with
**no baseline** for an entity (a *fresh* device, or after a lost/`§8`-tolerated manifest) cannot distinguish
"deleted on the other side" from "never seen" → it **may re-create** (resurrect) a deleted entity. Full
cross-replica delete-safety = **M2b tombstones**. This is the honest form of the user's "additive now,
tombstones later."

---

## 6. Auth (local → cloud) — *reviewed sound; hardened credential storage*

Local uses the **same Supabase Auth login** as the web app; all cloud I/O uses that user session → RLS-scoped
to `auth.uid()`. **No service-role key on the local machine**; any server-mediated sync endpoint derives
`owner_id` from the session and resolves playlists by `(auth.uid(), playlist_key)`, never from a
client-supplied owner id. Credential storage: prefer **OS keychain**; file fallback only with mode **600** +
parent-dir permission check + gitignore + **fail-closed** on broad perms. The refresh token is a long-lived
full-tenant bearer credential (theft = full same-tenant read/write, no cross-tenant break) — documented
blast radius; sign-out clears it. No session → refuse with a `cloud-sync login` hint.

---

## 7. Sync run (flow) — *union enumeration + per-video atomicity (round-1 H5, H2/H3)*

1. **Playlist set = UNION** of local-registry `playlist_key`s (§7.1) ∪
   `SELECT playlist_key FROM playlists WHERE owner_id = auth.uid()`. One-sided playlists are created on the
   other (subject to §5.5): cloud-only → hydrated into a deterministic local root; local-only → created on cloud.
2. **Per playlist**, enumerate the **union** of `video_id`s via `MetadataStore`.
3. **Per video**, compute the change signal (§5.1) each side; apply §5.3/§5.5.
4. **Per-video atomic transfer**, aligned with the existing staged→committed→promoted protocol
   (`lib/storage/supabase/consistency.ts`, `summary-handler.ts`): stage the winning **MD** (the hashed
   source) under an idempotency key, verify, promote to the final key, **then** finalize the receiver
   metadata (record + `contentGeneratedAt` + `contentHash`). The metadata must not advertise the new
   `contentHash` until the MD is promoted; a crash leaves staged (not final) objects + an unadvanced
   baseline; re-run finishes/rolls back. The **companion model** (§4.2) is written **best-effort, outside**
   the MD's atomic commit (its writer is a plain upsert — `model-store.ts`; a lost/absent companion
   self-heals via §4.2's invalidate + lazy-regen), so a companion failure never blocks the MD's baseline
   advance and never leaves the metadata inconsistent (round-3 L-2).
5. **Update the manifest (§8) strictly AFTER** the receiver's metadata commit is verified durable, recording
   the **receiver-observed committed hash**. Never advance a baseline for a partial transfer.
6. **Report** created / updated-local / updated-cloud / skipped-identical / **conflicts-logged (skipped)** /
   removed / errors. Per-video errors isolated; run is **idempotent + resumable** (single-run, no concurrency
   — §10 L). HTML/PDF never transferred; receiver re-renders lazily from MD (+ regenerates model if the
   companion drifted, §4.2).

### 7.1 Local playlist discovery (round-2 M-A)
A **local playlist registry**: each local root persists its `playlist_key` (backfilled from `playlistUrl`
for legacy roots that predate it) + title in `playlist-index.json`. Cloud Sync discovers local playlists by
scanning the configured data root(s), de-duplicating by `playlist_key` (a valid root holds an index;
`<root>/<dir>` and `<root>/<dir>/raw` shapes map to one key — never two). Cloud-only playlists hydrate into
deterministic roots named by `playlist_key`.

---

## 8. Sync state — per-playlist local manifest

One git-ignored file per playlist (`<data-root>/<playlist_key>/.cloud-sync-manifest.json`), recording per
`video_id` the last-synced baseline: `contentGeneratedAt`, **receiver-observed `contentHash`**, `syncedAt`.
Written **only after** §7.5's verified commit — never ahead of reality. It is the "seen before" record for
§5.5 delete inference and the baseline for §5.3 conflict classification. Lost/corrupt manifest degrades to
full hash comparison: correctness preserved (equal hash → skip; divergence with no baseline → §5.3 step 3
conflict-skip, never a destructive overwrite), only delete-detection and conflict-classification weaken
(disclosed R2).

### 8.1 Conflict log
Per-playlist git-ignored `<data-root>/<playlist_key>/.cloud-sync-conflicts.log` (JSON lines): `video_id`,
timestamp, both sides' `(contentGeneratedAt, contentHash, backfilled?)`, and reason (true-conflict /
backfilled-ambiguous / tiebreak). **De-duplicated** by `(video_id, hashL, hashC)` — a still-diverged legacy
pair that conflict-skips on every run is logged **once**, not per run (round-3 L-1), so the log doesn't grow
unbounded until the user resolves it. **Replica-local** (R3) — cross-replica surfacing is M2b.

---

## 9. Trigger
**Manual** `cloud-sync` command (`npm run cloud-sync [-- --playlist <list-id>]`, and/or a local **"Cloud
Sync"** button) over the union of playlists (all) or one. Background/auto-sync is M2b.

---

## 10. Testing
- **Boundary:** mock cloud at the `MetadataStore`/`BlobStore` seam; integration exercises real local FS ↔
  local-Supabase.
- **Canonical hash:** cross-backend golden fixtures (file vs `jsonb` → equal); changing a replica-local field
  (`position`/`archived`/`removedFromPlaylist`) does **not** change the hash; changing MD/`title`/
  `personalNote`/`personalScore`/`corrections` **does**; **model JSON change does NOT** change the hash (§4.2).
- **Newer-wins:** local-newer, cloud-newer, equal-skip, exact-tie→tiebreak; **B1 regression** — cloud
  `docVersion 4.0`+old-stamp vs local `3.3`+new-stamp → local wins.
- **Backfill non-destructive (round-2 H-C):** legacy divergence with a backfilled timestamp → **conflict,
  skip, no overwrite** (the "local note added, cloud `updated_at` bumped by ingestion" case must NOT lose the
  note); equal hash → skip; a real post-feature edit restamps and then wins.
- **Restamp (round-2 H-E, round-3 H-2):** a cloud `personalNote` edit (`update_video_annotations`) **and** a
  cloud `title`/`corrections` edit (`merge_video_data`/`updateVideoFields`) each restamp `contentGeneratedAt`;
  a `reconcile_membership` `archived` flip does **not** (not hashed, no restamp).
- **Companion model / content-stale gate (round-3 H-1):** after an MD wins and transfers, the receiver never
  serves a model built from the *old* MD — `isFresh` rejects a model whose `sourceMdHash` ≠ the current MD
  (even with identical section titles + same `GENERATOR_VERSION`); a matching companion serves without regen,
  a non-matching/absent one is invalidated and lazily regenerated. `GENERATOR_VERSION` drift also regenerates.
- **Union hydration:** empty local + non-empty cloud → full local hydration; local-only → created on cloud.
- **Atomicity/resume:** failure between promote and commit → no record advertises a hash for a missing blob,
  no baseline advance; re-run heals; two no-change runs → second all-skips.
- **Delete (round-2 H-A/H-B):** baseline-present + other-side-absent → **not re-created** (remote delete
  honored); fresh device (no baseline) + cloud-absent → additive-create allowed (**disclosed R2**); local
  delete → re-add with new stamp → syncs again; re-creation never calls the metered enqueue / touches
  `spend_ledger`.
- **Auth/RLS:** no session → refusal; write lands only in caller's tenant (client `owner_id` rejected);
  broad session-file perms → fail-closed.
- **Render parity:** synced MD (+ regenerated or companion model) renders HTML/PDF without error.

---

## 11. Accepted residuals / risks (v1)
- **R1 — True-conflict / tiebreak overwrite.** Two real concurrent edits of one video's hashed source resolve
  by newer-wins; loser overwritten but **logged** (§8.1). Loser-preservation is M2b.
- **R2 — Baseline-less delete resurrection.** A replica with no baseline for an entity (fresh device / lost
  manifest) cannot distinguish "deleted elsewhere" from "never seen" → may re-create it. Full delete-safety =
  M2b tombstones. This is the honest "additive now, tombstones later."
- **R3 — Replica-local conflict log** (§8.1); cross-replica surfacing is M2b.
- **R4 — Clock skew (load-bearing).** `contentGeneratedAt` primary → newer-wins leans on device clocks
  (bounded for one author's NTP-synced devices; equal content never races via the hash; backfilled stamps
  never overwrite, §5.4; exact ties are deterministic). A grossly-wrong clock can mis-order two *real* edits
  — accepted v1; logical-clock is an M2b option.
- **R5 — Companion model re-charge on drift.** If a synced MD's companion model is `GENERATOR_VERSION`-stale,
  the receiver regenerates it on first serve (a small charge) via the existing lazy-upsert — not new
  behavior, and avoided in the common (non-drift) case by copying the companion.
- **R6 — Cloud capture capability (to verify).** M2b's image backfill assumes cloud eventually generates its
  own slides; unverified; does not affect M2a (no images in summary scope).

---

## 12. Resolved decisions
1. **Deep-dive → M2b** (retired fields, per-section blobs, `DIG_GENERATOR_VERSION`, images).
2. **Newer-signal = `contentGeneratedAt` primary; `docVersion` never a recency signal** (round-1 B1).
3. **Model JSON = companion, not a compared source** (round-2 BLK-1) — copied with the winning MD; receiver
   lazily regenerates on drift.
4. **Hashed source set = summary MD + `title`/`personalNote`/`personalScore`/`corrections` only.** `archived`
   + membership/ordering fields excluded (round-2 H-D).
5. **Backfill is non-destructive** — a backfilled timestamp never drives an overwrite; ambiguous divergence =
   conflict-skip (round-2 H-C).
6. **Deletes: additive + baseline-aware best-effort suppression; no local marker; resurrection on a
   baseline-less replica is a disclosed residual** (round-2 H-A/H-B); cross-replica tombstones = M2b.
7. **Per-playlist manifest**; every allowlisted SQL writer restamps `contentGeneratedAt` (round-2 H-E),
   **including `merge_video_data`** for `title`/`corrections` (round-3 H-2).
8. **Model companion is content-safe, not opaque** (round-3 H-1): `ModelEnvelope.sourceMdHash` + a
   content-aware `isFresh` + invalidate-on-mismatch guarantee a content-stale model never serves; the
   companion copy is a best-effort re-charge avoidance, outside the MD's atomic commit.
