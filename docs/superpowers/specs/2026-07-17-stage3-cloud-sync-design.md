# Stage 3 — Cloud Sync (local ↔ cloud reconciliation) — Design Spec

**Status:** Draft **v8** — the **two-class model** (v7) reviewed as "directionally better / sound" by both
reviewers; v8 fixes the Class-B mechanics + the `corrections`↔MD coupling they surfaced: **per-field**
`annotationsEditedAt` (v7 Blocking B1 — a per-video stamp lost the newer edit); sync carries the **source**
timestamp not `now()` (H1); **clear-aware** per-field merge (H-2, no resurrection); `corrections`-currency so
a stale MD never overwrites a corrected one + `needs_regen` (Codex-H1/opus-M2); **derived scalars re-derived
on transfer** (opus-M1); explicit **required migrations §5.7** (schema fields, `ModelEnvelope` forward-
tolerance, annotation allowlist, conditional restamp — H-4/M-1/M-2); token cosmetic (L2). v6 had CONVERGED
on the single-class model; v7/v8 are the two-class rework, re-entering review.
Reviews: `.superpowers/sdd/cloud-sync-spec-*.md`.

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
- **Class A — generated (reconcile by corrections-currency + format, §5.3):** summary **MD** (section-timestamp
  `▶` markers ride inline in it); **model JSON** (`ModelEnvelope`), carried as a **companion** (§4.2), never a
  compared source.
- **Class A-derived scalars (never synced independently; recomputed from the winning MD on every Class-A
  transfer):** `ratings`, `overallScore`, `videoType`, `audience`, `tags`, `tldr`, `takeaways` —
  `reconstructVideo` (`lib/pipeline.ts:72-125`) derives these deterministically from the MD, and the
  `MagazineModel` companion carries only `{sections}`, so a Class-A transfer must re-derive them (uncharged)
  or they drift from the transferred prose (round-v7 opus-M1).
- **Class B — independent human annotations (per-field 3-way merge, §5.4):** `personalNote`, `personalScore`.
- **`corrections` — human field AND the MD's generation input (special):** reconciled as a human field (§5.4,
  newer-wins, preserved) AND tracked as the MD's **corrections-currency** — because `corrections` is *applied
  into* the MD via `fixSummary`/regenerate (`app/api/videos/[id]/regenerate/route.ts:51-71`), the MD records
  `mdCorrectionsHash` and §5.3 never lets a stale MD overwrite a corrected one.
- **Replica-local / fetched (NOT synced):** `title` (YouTube-fetched, no author-edit path), `position`,
  `serialNumber`, `playlistIndex`, `removedFromPlaylist`, `archived` (all membership/ordering, set by
  `reconcile_membership` `0007:60-71` from each replica's own fetch → would flip-flop), `updatedAt`,
  `summaryReady` (DB-computed).
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
  envelope's `sourceMdHash`), `mdGeneratedAt` (UTC, a **tie-break only**, never a quality signal), and
  **`mdCorrectionsHash`** — the §5.2 hash of the `corrections` value this MD was generated/fixed from, for
  corrections-currency (§5.3). `docVersion.minor` (HTML style) is **ignored** — sync moves MD, not HTML;
  each app re-renders the MD in its own current style, so nothing is "stuck" in an old style.
- **Class B / `corrections`:** each field's value + a **PER-FIELD** timestamp,
  `annotationsEditedAt.{personalNote, personalScore, corrections}` — a same-field tie compares *that field's*
  real edit time (round-v7 Blocking B1: a single per-video timestamp is contaminated by unrelated field edits
  and would pick the older edit).
- **Stamping:** `mdGeneratedAt` + `mdCorrectionsHash` on MD generation (`persist_summary` `0009`; local
  `pipeline.ts`). Each human-field write stamps **only that field's** `annotationsEditedAt`
  (`update_video_annotations` `0016`; `merge_video_data`/`updateVideoFields` for `corrections` — **conditional
  on a Class-B key being present**, so a generic MD-finalize / artifact / membership write never bumps a human
  timestamp, round-v7 L-1; the local index writer). Membership writers → no restamp.
- **Sync-path writes carry the SOURCE timestamp, NOT `now()` (round-v7 H1):** when sync applies a winning
  human value to the receiver, it sets that field's `annotationsEditedAt` to the **source's** value — the
  writers accept an explicit timestamp on the sync path (distinct from the user-edit path, which stamps
  `now()`) — so the baseline records true authorship and later ties compare real edit times.

### 5.2 Canonical `mdHash` (rounds 1–3, 5)
`mdHash` is an **MD-body-only** canonical digest — a shared impl (`lib/cloud-sync/content-hash.ts`) called
by both replicas: MD bytes normalized to LF + fixed trailing-newline + NFC, SHA-256 hex. It is **not** over
the human fields (they reconcile separately, §5.4), so a `personalNote` edit never invalidates the model
(round-5 M-1). §10 requires cross-backend golden fixtures (local file vs Postgres `jsonb` → equal).

### 5.3 Class A reconcile (generated MD + model) — corrections-currency FIRST, then format
Recency does **not** decide generated content (the LLM is non-deterministic; a newer generation is not
"better"). But `corrections` is *applied into* the MD, so a **corrected** MD is not an equivalent variant of
an uncorrected one (round-v7 Codex-H1). `corrections` is reconciled **first** (§5.4); an MD is
**corrections-current** iff `mdCorrectionsHash == hash(reconciled corrections)`. Priority: **corrections-
current > format > recency-tiebreak.**

| Situation | Action |
|---|---|
| Both present, `mdHash` equal | **skip** (identical) |
| One MD corrections-current, the other corrections-stale | **corrections-current wins** — never overwrite a corrected MD with a stale higher-format one. Copy it (+ companion §4.2). |
| Both corrections-current (or both equally stale), `docVersion.major` differs | **higher `major` wins** (format upgrade; never downgrade) |
| Both corrections-current, same `major`, `mdHash` differs (equivalent LLM variants) | **unify** — newer `mdGeneratedAt` wins; copy so the prose **converges** (intention-respecting tie-break, not a quality claim; avoids undoing a deliberate re-generation) |
| **Neither** MD reflects the reconciled corrections (both stale) | keep the higher-major MD but **flag `needs_regen`** (report it, §7 step 6) — the author regenerates to apply the corrections at the current format; sync **never fabricates** a corrected MD (residual **R8**) |
| Present on only one side (never in this replica's baseline) | **copy** (hydrate / publish) |

**On every Class-A MD transfer, re-derive the Class-A-derived scalars** (§4.1: `ratings`, `overallScore`,
`videoType`, `audience`, `tags`, `tldr`, `takeaways`) from the winning MD via `reconstructVideo`
(deterministic, uncharged) so they never disagree with the transferred prose (round-v7 opus-M1). No
data-loss: a losing MD is corrections-stale-or-equivalent, the `corrections` instruction survives (§5.4) and
re-applies on regen. Clock skew stays non-load-bearing (a same-format tie just picks one equivalent variant).

### 5.4 Class B / `corrections` reconcile — per-field 3-way merge, clear-aware (runs BEFORE §5.3)
Human fields (`personalNote`, `personalScore`, `corrections`) are precious and **carried across every
format**. Each reconciles **independently** against the manifest baseline (§8). **Absence is a value** (a
*clear*), not "never had" (round-v7 H-2):

| Per-field state vs baseline | Action |
|---|---|
| L == C | no action |
| Only one side changed vs baseline (incl. a **clear** = baseline-present→absent) | take the changed side — **propagate the edit or the clear** |
| **Both** changed vs baseline (different values, incl. one cleared) | newer **per-field `annotationsEditedAt`** wins + log (R1) |
| No baseline (fresh device) + differ | newer per-field `annotationsEditedAt` wins + log |
| Present one side, absent other, **no baseline** | copy (additive hydration) |

Independent fields merge cleanly — a note edit on one side + a score edit on the other **both survive**; a
cleared field is **not** resurrected (with a baseline, present-vs-absent is a real change → the clear
propagates). A human field is **never** lost to a Class-A format change (they reconcile independently).
`corrections` reconciles here too and, because it feeds §5.3's corrections-currency, is reconciled **first**.

### 5.5 Backfill (legacy records) — non-destructive (round-2 H-C)
Legacy records lack `mdGeneratedAt`/`mdCorrectionsHash`/`annotationsEditedAt`. A one-time backfill records
**provisional** values (MD: `processedAt`; human: `updated_at`) flagged as backfilled, and a backfilled
timestamp **never drives a destructive overwrite**: a same-format Class-A tie with a backfilled
`mdGeneratedAt` just picks one equivalent variant (harmless); a Class-B same-field conflict with a backfilled
per-field `annotationsEditedAt` resolves to **conflict → skip + log**, never overwrite. Format (Class A) and 3-way field merge (Class B)
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

### 5.7 Required schema / migration changes (NOT optional — the reconcile depends on them)
The reconcile signals are new; these ship **with** M2a (round-v7 H-4/M-1/M-2 flagged that the code
preconditions aren't yet true):
- **`VideoSchema` +** `mdGeneratedAt?`, `mdCorrectionsHash?`, and per-field `annotationsEditedAt?: {personalNote?,
  personalScore?, corrections?}` (datetimes). One-time backfill per §5.5.
- **`ModelEnvelopeSchema`:** add `sourceMdHash?: string` **and drop `.strict()`** (→ ignore unknown keys) so a
  new-writer envelope doesn't make an old reader's `readModelEnvelope` return null → notReady/re-charge
  (round-5 M-2, still `.strict()` in `model-store.ts:22`).
- **`update_video_annotations` (`0016`) allowlist → `{personalScore, personalNote, corrections}`** — add
  `corrections` (Class B, currently dropped), remove `archived` (now replica-local). Each write restamps
  **only the changed field's** `annotationsEditedAt`.
- **`merge_video_data` restamp is CONDITIONAL** on a Class-B key in the patch (it is a blind generic merge also
  used for MD-finalize / artifact / membership writes — round-v7 L-1).
- **Writers accept an explicit timestamp on the sync path** (vs `now()` on the user-edit path — round-v7 H1).
- **`persist_summary` / local `pipeline.ts`** stamp `mdGeneratedAt` + `mdCorrectionsHash` on generation.

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
   (skipped) / removed / **`share_needs_owner_serve`** (R7) / **`needs_regen`** (no MD reflects the current
   corrections at the top format — author should regenerate, §5.3/R8) / errors. Per-video errors isolated;
   the run is idempotent + resumable (single-run, no concurrency — §10).

### 7.1 Local playlist discovery (rounds 1–2)
A **local playlist registry**: each local root persists its `playlist_key` (backfilled from `playlistUrl`
for legacy roots) + title in `playlist-index.json`. Cloud Sync scans the configured data root(s),
de-duplicates by `playlist_key` (`<root>/<dir>` and `<root>/<dir>/raw` shapes map to one key), and hydrates
cloud-only playlists into deterministic roots named by `playlist_key`.

---

## 8. Sync state — per-playlist local manifest

One git-ignored file per playlist (`<data-root>/<playlist_key>/.cloud-sync-manifest.json`), recording per
`video_id` the last-synced baseline: **Class A** (`docVersion`, `mdGeneratedAt`, `mdCorrectionsHash`,
receiver-observed `mdHash`) and **Class B** (the last-synced `corrections`/`personalNote`/`personalScore`
values + their **per-field** `annotationsEditedAt`).
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
- **Class A (corrections-currency + format):** higher-major wins over a newer-timestamp lower-major
  (anti-recency); **a stale higher-major MD does NOT overwrite a corrections-current lower-major MD**
  (round-v7 Codex-H1); neither-current → `needs_regen` flag, no fabrication (R8); same-major-different-prose
  unifies to the more recent (both converge, no churn); **derived scalars (`tldr`/`videoType`/`overallScore`
  …) are re-derived from the winning MD on transfer** (round-v7 opus-M1); `mdHash` cross-backend fixtures;
  a human-field edit does **not** change `mdHash`.
- **Class B (per-field merge):** a note edit on local + a score edit on cloud → **both survive**; a
  **cleared** field is **not** resurrected (baseline-aware clear propagates, round-v7 H-2); same-field-both-
  changed → newer **per-field** `annotationsEditedAt` wins (the B1 regression: an unrelated later field edit
  must NOT flip a same-field tie); sync-applied write carries the **source's** timestamp, not `now()` (H1).
- **Companion/serve (rounds 3–5):** non-synced legacy model still serves as today (no re-charge, share
  unaffected); synced+shared model-deleted → anon share not-ready until owner serve, counted; old-schema
  reader (`.strict()` dropped) tolerates a `sourceMdHash`-bearing envelope.
- **Stamping:** every MD-writer stamps `mdGeneratedAt`+`mdCorrectionsHash`; a human-field writer restamps
  **only the changed field's** `annotationsEditedAt` and **only when a Class-B key is present** (a bare
  `merge_video_data` MD-finalize does NOT bump it — round-v7 L-1); membership writers do not.
- **Union hydration / atomicity / deletes / auth:** empty-local→full-hydrate; promote-then-commit crash never
  advertises a hash for a missing blob nor advances the baseline; baseline-present remote-delete not
  re-created; re-creation never calls the metered enqueue; no-session refusal; client `owner_id` rejected.

---

## 11. Accepted residuals (M2a)
- **R1 — Class-B same-field concurrent edit:** newer **per-field** `annotationsEditedAt` wins; loser logged
  (§8.1); loser-preservation is M2b. (Class A has no analogous loss — its variants are equivalent.)
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
- **R8 — `needs_regen` (corrections/format skew):** if no replica has an MD reflecting the current
  `corrections` at the top format (e.g. corrections applied on an older-code replica), sync keeps the best
  available MD (corrections-current if any, else the highest format) but flags `needs_regen` — the summary is
  the best that exists until the author regenerates on a top-format replica (which re-applies the surviving
  `corrections`). Sync never fabricates a corrected MD; nothing is lost (the instruction survives, §5.4).

---

## 12. Resolved decisions
1. **Two-class model** (user, 2026-07-17): generated content (Class A) reconciles by **format**, human edits
   (Class B) reconcile **per-field newer-wins** — opposite rules, reconciled independently. Dissolves the
   format-vs-recency tension of v1–v6.
2. **`docVersion` = format signal, never recency.** `.major` decides Class A (higher wins; never downgrade);
   `.minor` (HTML style) ignored (each app re-renders in its own style). `mdGeneratedAt` breaks a same-format
   tie only.
3. **Class B (independent per-field merge) = `personalNote`/`personalScore`; `corrections` is special** — a
   human field (preserved, per-field newer-wins) that is ALSO the MD's generation input, so it drives §5.3
   corrections-currency (a stale MD never overwrites a corrected one). **`title` is NOT Class B** (YouTube-
   fetched, no author-edit path → replica-local). MD-derived scalars (`tldr`/`videoType`/…) are Class-A-derived
   (recomputed from the winning MD on transfer, never independently synced).
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
- **But cloud DOES produce the capture *tokens*.** Gemini's dig output emits **`[[SLIDE:M:SS|M:SS|
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
