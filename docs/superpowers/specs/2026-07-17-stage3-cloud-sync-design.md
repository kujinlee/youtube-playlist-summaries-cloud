# Stage 3 — Cloud Sync (local ↔ cloud reconciliation) — Design Spec

**Status:** Draft **v7** — reworked after a design refinement from the user: **generated content and human
edits reconcile by opposite rules**, so v7 splits the per-video state into two classes instead of one
"hashed source set" (dissolving the format-vs-recency tension that drove rounds 1–6). v6 had **converged**
(dual review, 0 B/H/M) on the single-class model; v7 is a *model* change, so it re-enters review.
Prior converged reviews: `.superpowers/sdd/cloud-sync-spec-{codex,claude}{,-r2..-r6}.md`.

**Roadmap:** M2 of `docs/roadmap-to-launch.md`.

**Goal:** Give the single author a **Cloud Sync** that reconciles their local research corpus with their own
multi-tenant cloud account — so the cloud portal mirrors local work for peer sharing and multi-device
access, a second device can hydrate from the cloud, and reconciliation matches how the two kinds of content
actually behave.

---

## 1. Scope

**M2 decomposition:**
- **M2a — THIS spec:** local↔cloud reconciliation of each video's **summary** (LLM-generated MD + model) and
  **human edits** (rating/note/corrections), both directions, per the two-class rules (§5). Honest
  **additive** create with **baseline-aware** delete-suppression. Manual trigger.
- **M2b — later slice (own spec):** deep-dive/dig **+ slide images** via the cloud-tokens → local-capture →
  sync-back pipeline (§13), cross-replica tombstone deletes, background/auto-sync, true-conflict
  loser-preservation.

**In scope (M2a):** summary MD + model-JSON companion; human fields (`corrections`, `personalNote`,
`personalScore`); playlist/video identity; union hydration; the two-class change signals + non-destructive
backfill; Supabase-Auth login; per-playlist manifest; manual **Cloud Sync**.

**Out of scope (M2a):** deep-dive/dig + slide images (M2b, §13); tombstone delete propagation; background
sync; true-conflict loser-preservation; HTML/PDF transfer (regenerable cache).

---

## 2. Terminology

| Term | Meaning |
|---|---|
| **Cloud Sync** | This feature: reconcile local corpus ↔ cloud tenant. (NOT the local **"Sync"** button = refresh a playlist's videos from YouTube.) |
| **Replica** | One copy of the corpus: a local install, or the cloud tenant. |
| **Class A — generated** | LLM output: **summary MD** + **model JSON**. Non-deterministic; reconciled by **format**, not recency (§5.3). |
| **Class B — human** | Author edits: **`corrections`, `personalNote`, `personalScore`**. Reconciled **per field, newer-wins, additive**; preserved across every format (§5.4). |
| **`docVersion`** | Format/style version stamped *at generation* (`CURRENT_DOC_VERSION`, `lib/doc-version.ts`). `.major` = MD content-format; `.minor` = HTML render style. **A format signal, not a timestamp.** |
| **Companion** | The model-JSON blob, copied *with* the winning MD but never independently compared (§4.2). |

---

## 3. Identity (cross-replica keys) — *reviewed sound (rounds 1–6)*

- **Playlist** = YouTube list-id = cloud `playlists.playlist_key` (`0001:13`, unique per `owner_id` `:17`);
  `Principal.indexKey` abstracts local-path ↔ playlist_key (`lib/storage/principal.ts:7`).
- **Video** = YouTube `video_id` (`types/index.ts:30`).
- **Owner** = `auth.uid()`; composite FK `videos(playlist_id,owner_id)→playlists(id,owner_id)` (`0001:31-32`)
  + forced RLS isolate tenants. No synthetic mapping. Peers get access via share tokens, not sync.

---

## 4. What syncs (M2a) — three classes

### 4.1 Per-video field classification
- **Class A — generated (reconcile by format, §5.3):** summary **MD** (section-timestamp `▶` markers ride
  inline in it); **model JSON** (`ModelEnvelope`), carried as a **companion** (§4.2), never a compared source.
- **Class B — human (reconcile per-field, §5.4):** `corrections`, `personalNote`, `personalScore`. Author-
  authored, format-independent, precious.
- **Replica-local / fetched (NOT synced):** `title` (YouTube-fetched, no author-edit path — converges per
  replica on its own fetch), `position`, `serialNumber`, `playlistIndex`, `removedFromPlaylist`, `archived`
  (all membership/ordering, set by `reconcile_membership` `0007:60-71` from each replica's own fetch →
  would flip-flop), `updatedAt`, `summaryReady` (DB-computed).
- **Regenerable cache (never synced):** HTML, PDF (deterministic re-render from MD + model).

### 4.2 Model JSON companion — sync-transfer only, serve path UNCHANGED (rounds 2–6)
Model JSON is a **non-deterministic, `GENERATOR_VERSION`-axed, charged, self-healing cache** (Gemini
transform; lazily regenerated on serve — `lib/html-doc/model-store.ts`, `read-model.ts`). It is **never**
hash-compared. Its freshness is handled **only at sync-transfer**, leaving the serve path (`isFresh`,
`readTitleStableModel`, the share route, the over-budget fallback) **unchanged** — because a global gate
change would re-charge the whole corpus and dark-serve every share (round-4 BLK-1).
- `ModelEnvelope` gains an OPTIONAL **`sourceMdHash`** — an **MD-body-only** digest (§5.2), set going
  forward; the schema is **forward-tolerant** (old readers ignore the new key). Legacy envelopes lack it.
- On a Class-A MD-transfer: ship the sender's model as a companion **iff** `sourceMdHash == mdHash(winning
  MD)`; else **delete the receiver's model blob** (→ lazy regen on the **owner's** next serve). A **shared
  (anonymous)** view of that specific video is not-ready until the owner serves (the share route is
  generation-free — residual **R7**); sync reports these as `share_needs_owner_serve` (§7 step 6).

---

## 5. Reconcile model — two independent per-video reconciles

Each video reconciles its **Class A** and **Class B** state **independently**: a format upgrade to the MD
never touches the human fields, and a human-field edit never touches the MD. This is the core v7 change.

### 5.1 Signals (per class)
- **Class A:** `docVersion.major` (format — the decider), `mdHash` (the MD-body-only §5.2 digest = the
  envelope's `sourceMdHash`; detects identical/equivalent), and `mdGeneratedAt` (UTC, stamped at MD
  generation — a **tie-break only**, never a quality signal). `docVersion.minor` (HTML style) is **ignored**
  — sync moves MD, not HTML; each app re-renders the MD in its own current style, so you're never stuck in
  an old style and there is nothing to downgrade.
- **Class B:** each field's value + a per-video `annotationsUpdatedAt` (UTC, stamped whenever a human field
  changes) for the rare same-field tie.
- **Stamping (every hashed/human-field SQL writer must restamp — rounds 2–4):** `mdGeneratedAt` on MD
  generation (`persist_summary` layer-3 `0009`; local `pipeline.ts`); `annotationsUpdatedAt` on human-field
  writes (`update_video_annotations` `0016`; `merge_video_data`/`updateVideoFields` for `corrections`; the
  local index writer). Membership writers (`reconcile_membership`) touch only non-synced fields → no restamp.

### 5.2 Canonical `mdHash` (rounds 1–3, 5)
`mdHash` is an **MD-body-only** canonical digest — a shared impl (`lib/cloud-sync/content-hash.ts`) called
by both replicas: MD bytes normalized to LF + fixed trailing-newline + NFC, SHA-256 hex. It is **not** over
the human fields (they reconcile separately, §5.4), so a `personalNote` edit never invalidates the model
(round-5 M-1). §10 requires cross-backend golden fixtures (local file vs Postgres `jsonb` → equal).

### 5.3 Class A reconcile (generated MD + model) — format-first
Recency does **not** decide generated content: the LLM is non-deterministic and a newer generation is not
"better." **Format (`docVersion.major`) decides; recency only breaks a same-format tie.**

| Situation | Action |
|---|---|
| Both present, `mdHash` equal | **skip** (identical) |
| **`docVersion.major` differs** | **higher `major` wins** — copy its MD (+ companion §4.2) to the lower-format side (a format upgrade). Recency ignored. Never downgrade format. |
| Same `major`, `mdHash` differs (equivalent LLM variants) | **unify** — the more recent `mdGeneratedAt` wins; copy it to the other so the prose **converges** (don't leave it diverged — a sync opportunity). Recency here is an intention-respecting tie-break, not a quality claim; it also avoids undoing a deliberate re-generation on either side. |
| Present on only one side (never in this replica's baseline) | **copy** (hydrate a fresh device / publish new work) |

No data-loss: the "losing" MD is an equivalent-or-older-format generation (nothing unique lost); human
edits are Class B (preserved separately, §5.4). Clock skew is therefore **not load-bearing** for Class A —
a wrong same-format tie just picks one equivalent variant.

### 5.4 Class B reconcile (human fields) — per-field 3-way merge, newer-wins, additive
Human ratings/corrections are precious and **carried across every format**. Reconciled **per field** against
the manifest baseline (§8):

- Field present on only one side → **copy** it (additive).
- Field equal on both → no action.
- Field differs: **3-way merge** — if only one side changed it vs the baseline → take that side's value; if
  **both** changed it → the side with the newer `annotationsUpdatedAt` wins (+ log). No baseline (fresh
  device) + differ → newer `annotationsUpdatedAt` wins (+ log).
- Because independent fields merge cleanly (a note edit on one side + a score edit on the other both
  survive), genuine conflict is rare and only ever same-field. A human field is **never** lost to a Class-A
  format change (the two reconcile independently).

### 5.5 Backfill (legacy records) — non-destructive (round-2 H-C)
Legacy records lack `mdGeneratedAt`/`annotationsUpdatedAt`. A one-time backfill records **provisional**
values (MD: `processedAt`; human: `updated_at`) flagged as backfilled, and a backfilled timestamp **never
drives a destructive overwrite**: a same-format Class-A tie with a backfilled `mdGeneratedAt` just picks one
equivalent variant (harmless); a Class-B same-field conflict with a backfilled `annotationsUpdatedAt`
resolves to **conflict → skip + log**, never overwrite. Format (Class A) and 3-way field merge (Class B)
carry the real decisions, so backfill is far less load-bearing than in the single-class model.

### 5.6 Presence & deletes — additive + baseline-aware (rounds 2–4)
- One-sided, never in this replica's baseline → additive **create** (a pure metadata/doc copy that **never**
  routes through the metered enqueue `lib/job-queue/producer.ts`, never consumes `spend_ledger`, never
  resurrects derived cache).
- In this replica's baseline but **absent on the other side** → **remote delete**: do not re-create.
- In this replica's baseline but **absent on this side** (this replica deleted it) → do not re-create
  locally, do not delete on the other (no propagation — M2b tombstones).
- **Residual R2:** a replica with **no baseline** (fresh device / lost manifest) can't tell "deleted
  elsewhere" from "never seen" → may re-create (resurrect). Full delete-safety = M2b tombstones. No local
  delete-intent marker (round-2 H-A showed it has no sound lifecycle).

---

## 6. Auth (local → cloud) — *reviewed sound; hardened storage*

Local uses the **same Supabase Auth login** as the web app; all cloud I/O is under that user session →
RLS-scoped to `auth.uid()`. **No service-role key on the local machine**; a server-mediated sync endpoint
derives `owner_id` from the session, resolves playlists by `(auth.uid(), playlist_key)`, never from a
client-supplied owner id. Refresh token → **OS keychain** preferred; file fallback mode 600 + parent-dir
check + gitignore + fail-closed on broad perms; theft = full same-tenant access (no cross-tenant break);
sign-out clears it. No session → refuse with a `cloud-sync login` hint.

---

## 7. Sync run (flow)

1. **Playlist set = UNION** of local-registry `playlist_key`s (§7.1) ∪ `SELECT playlist_key FROM playlists
   WHERE owner_id = auth.uid()`. One-sided playlists created on the other (subject to §5.6). A fresh device
   (empty local) thus pulls the full cloud corpus.
2. **Per playlist**, enumerate the union of `video_id`s via `MetadataStore`.
3. **Per video**, run the **Class A** reconcile (§5.3) and the **Class B** reconcile (§5.4) independently.
4. **Class A MD transfer is per-video atomic**, aligned with the existing staged→committed→promoted protocol
   (`consistency.ts`, `summary-handler.ts`): stage the winning MD under an idempotency key, verify, promote,
   **then** finalize the receiver record (`mdGeneratedAt`, `mdHash`, `docVersion`). Metadata never advertises
   the new `mdHash` until the MD is promoted; a crash leaves staged objects + an unadvanced baseline; re-run
   heals. The **companion model** is best-effort, outside the MD's atomic commit (a lost companion self-heals
   via §4.2). **Class B field writes** are small record updates applied after the merge (§5.4).
5. **Update the manifest (§8) strictly AFTER** the receiver commit is verified durable (receiver-observed
   `mdHash` + human field values). Never advance a baseline for a partial transfer.
6. **Report**: created / updated-local / updated-cloud / skipped-identical / merged-fields / conflicts-logged
   (skipped) / removed / **`share_needs_owner_serve`** (transferred videos whose receiver model was deleted
   and that have a live share token — anonymous share is not-ready until an owner serve, R7) / errors.
   Per-video errors isolated; the run is idempotent + resumable (single-run, no concurrency — §10).

### 7.1 Local playlist discovery (rounds 1–2)
A **local playlist registry**: each local root persists its `playlist_key` (backfilled from `playlistUrl`
for legacy roots) + title in `playlist-index.json`. Cloud Sync scans the configured data root(s),
de-duplicates by `playlist_key` (`<root>/<dir>` and `<root>/<dir>/raw` shapes map to one key), and hydrates
cloud-only playlists into deterministic roots named by `playlist_key`.

---

## 8. Sync state — per-playlist local manifest

One git-ignored file per playlist (`<data-root>/<playlist_key>/.cloud-sync-manifest.json`), recording per
`video_id` the last-synced baseline: **Class A** (`docVersion`, `mdGeneratedAt`, receiver-observed `mdHash`)
and **Class B** (the last-synced `corrections`/`personalNote`/`personalScore` values + `annotationsUpdatedAt`).
Written **only after** §7 step 5's verified commit. It is the "seen-before" record for §5.6 delete inference,
the Class-A tie baseline, and the Class-B 3-way-merge baseline. Lost/corrupt manifest degrades to a direct
compare (equal → skip; divergence → conflict-skip, never a destructive overwrite); only delete-detection and
3-way merge weaken (disclosed R2).

### 8.1 Conflict log
Per-playlist git-ignored `.cloud-sync-conflicts.log` (JSON lines): `video_id`, class, field (if Class B),
both sides' signals + `backfilled?`, reason. **De-duplicated** by `(video_id, class, field, valueL, valueR)`
so a stuck pair logs once, not per run (round-3 L-1). **Replica-local** (R3) — cross-replica surfacing is M2b.

---

## 9. Trigger
**Manual** `cloud-sync` command (`npm run cloud-sync [-- --playlist <list-id>]`, and/or a local **"Cloud
Sync"** button) over the union of playlists (all) or one. Background/auto-sync is M2b.

---

## 10. Testing
- Boundary: mock cloud at the `MetadataStore`/`BlobStore` seam; integration = real local FS ↔ local-Supabase.
- **Class A (format-first):** higher-major wins over a newer-timestamp lower-major (the anti-`docVersion`-and
  anti-recency regression); same-major-different-prose **unifies to the more recent** (both converge, no
  churn on re-run); `mdHash` cross-backend golden fixtures (file vs `jsonb` → equal); a human-field edit does
  **not** change `mdHash`.
- **Class B (per-field merge):** a note edit on local + a score edit on cloud → **both survive** (3-way
  merge); same-field-both-changed → newer `annotationsUpdatedAt` wins + logged; a field present on one side
  only → copied (additive); human fields **survive a Class-A format upgrade** (reconcile independently).
- **Companion/serve (rounds 3–5):** non-synced legacy model still serves as today (no re-charge, share
  unaffected); a synced+shared video whose model was deleted → anon share not-ready until owner serve, counted
  `share_needs_owner_serve`; old-schema reader tolerates a `sourceMdHash`-bearing envelope.
- **Stamping (rounds 2–4):** every MD-writer restamps `mdGeneratedAt`; every human-field writer
  (incl. `merge_video_data` for `corrections`) restamps `annotationsUpdatedAt`; membership writers do not.
- **Union hydration / atomicity / deletes / auth:** empty-local→full-hydrate; promote-then-commit crash never
  advertises a hash for a missing blob nor advances the baseline; baseline-present remote-delete not
  re-created; re-creation never calls the metered enqueue; no-session refusal; client `owner_id` rejected.

---

## 11. Accepted residuals (M2a)
- **R1 — Class-B same-field concurrent edit:** newer `annotationsUpdatedAt` wins; loser logged (§8.1);
  loser-preservation is M2b. (Class A has no analogous loss — its variants are equivalent.)
- **R2 — Baseline-less delete resurrection:** a fresh device / lost manifest may re-create a deleted entity;
  full delete-safety = M2b tombstones.
- **R3 — Replica-local conflict log** (§8.1); cross-replica surfacing is M2b.
- **R4 — Clock skew (now minor):** only a Class-A same-format tie-break and a Class-B same-field tie lean on
  clocks; the former is harmless (equivalent variants), the latter rare + logged. Format and 3-way merge
  carry the real decisions, so skew is far less load-bearing than in the old single-class model.
- **R5 — Companion re-charge, scoped to synced videos:** a synced MD with no verifiable-matching companion →
  receiver regenerates the model on next serve (existing lazy path); bounded to synced videos, never the fleet.
- **R7 — Synced+shared video:** its anonymous share is not-ready until an owner serve (the share route is
  generation-free); scoped to synced+shared videos only; reported as `share_needs_owner_serve`.

---

## 12. Resolved decisions
1. **Two-class model** (user, 2026-07-17): generated content (Class A) reconciles by **format**, human edits
   (Class B) reconcile **per-field newer-wins** — opposite rules, reconciled independently. Dissolves the
   format-vs-recency tension of v1–v6.
2. **`docVersion` = format signal, never recency.** `.major` decides Class A (higher wins; never downgrade);
   `.minor` (HTML style) ignored (each app re-renders in its own style). `mdGeneratedAt` breaks a same-format
   tie only.
3. **Class B = `corrections`/`personalNote`/`personalScore`** (human). **`title` is NOT Class B** —
   YouTube-fetched, no author-edit path → replica-local.
4. **Model JSON = companion** (sync-transfer scoped, MD-only `sourceMdHash`, forward-tolerant schema, R5/R7).
5. **Deep-dive + images → M2b** (§13), with the cloud-tokens → local-capture → sync-back pipeline.
6. **Deletes: additive + baseline-aware**; resurrection on a baseline-less replica = R2; tombstones = M2b.
7. **Per-playlist manifest**; every MD/human-field SQL writer restamps its timestamp (incl. `merge_video_data`).

---

## 13. M2b forward-notes (deep-dive + slide images) — captured, not in scope

Verified against code; recorded so M2b builds on a settled architecture:
- **Cloud can NEVER capture real pixels server-side (ToS-permanent).** Any datacenter capture (`yt-dlp` *or*
  headless-Chromium screenshotting) is the same YouTube-ToS violation (architecture §2.1, "Codex H9 legal
  gate"); real pixels are obtainable **only on the user's device**. This **corrects the old R6 "cloud may
  gain capture" assumption**: cloud will not.
- **But cloud DOES produce the capture *tokens*.** Gemini's dig output emits **`[[SLIDE:startSec|endSec|
  caption]]`** tokens (`lib/dig/generate.ts:79` — "FIRST M:SS = visual fully built; SECOND = it leaves"),
  ToS-clean (Gemini watches Google's own video). A token is a **portable capture instruction** — clip window
  + what it is.
- **Local resolves tokens → pixels** (`lib/dig/slides.ts`: `yt-dlp --download-sections` + `ffmpeg`, anchored
  on the reliable `end`, so Gemini's timestamp imprecision is already absorbed).
- **The M2b pipeline** is therefore: **cloud generates dig text + slide tokens → sync to local → local
  resolves tokens into real slides → sync the images back to cloud.** Cloud ends up with pixels it could
  never capture itself; any local device with video access can re-resolve the tokens anytime.
- **M2b reconcile shape:** dig MD (with tokens) reconciles like **Class A** (format/version, incl. a
  `DIG_GENERATOR_VERSION` axis); the resolved **slide images** are a **local-authoritative asset layer**
  (local is the only legal producer) — the "asset-bearing side wins" tie-break resolves to local; cloud→local
  image transfer is really "local resolves cloud's tokens," and local→cloud carries the captured pixels.
- Also deferred to M2b: cross-replica tombstone deletes, background/auto-sync, true-conflict loser-preservation.
