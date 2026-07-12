# Cloud Dig-Deeper Generation — Design Spec

**Status:** Approved (design dialogue 2026-07-12) — ready for implementation plan.
**Slice:** Sub-project 2, cloud dig-deeper **generation only**. Follows the merged cloud summary
PDF slice (PR #14). Serving, frontend, slide capture, and dig PDF are each deferred to their own
later slices with their own spec + merge gate.

---

## 1. Terminology (load-bearing)

`CONTEXT.md` draws a hard line this spec honors:

- **Deep-dive doc** — *legacy*. A whole-video analysis generated up-front in one pass. **Frozen — no
  new ones are produced.** Nothing in this spec builds or touches deep-dive docs.
- **Dig-deeper doc** — the *live* concept: per-section, generated lazily, only for a section a reader
  chose to dig. All running generation code is this. The env var `GEMINI_DEEPDIVE_MODEL`, the module
  `lib/dig/generate.ts`, and `DIG_GENERATOR_VERSION` keep the legacy name but drive the live
  per-section path.

"Cloud dig-deeper generation" = producing a dig-deeper doc for **one section** of one video through
the **cloud durable job queue**, for an authenticated cloud user.

---

## 2. Goal

Let a cloud user trigger generation of a **text-only** dig-deeper doc for a single section, produced
by the durable worker, charged once through the existing job-queue money path, and persisted as a
**per-section blob** — with no serving route, no frontend, and no slide screenshots in this slice.

---

## 3. Scope

### In scope
1. **Admit `dig` in `enqueue_job`.** Flip the `unsupported_job_kind` guard (migration
   `0011_cost_guardrails.sql:71`, "dig rejected until 1E-b-2") so the RPC accepts `p_job_kind='dig'`.
   The dig quota / estimate / attempts config already exists in the schema — this slice does **not**
   add cost config, only unblocks the code path.
2. **Cloud dig trigger** — extend the existing `POST /api/videos/[id]/dig/[sectionId]` route with a
   `STORAGE_BACKEND === 'supabase'` branch that authenticates, authorizes, dedups, and enqueues a
   durable `{ kind: 'dig', sectionId }` job. Cloud body delegated to a `lib/` helper (thin route).
3. **`makeDigHandler`** + worker kind→handler dispatch — the worker (`worker/main.ts`) currently
   registers a single handler; introduce a `job_kind → handler` map and add the dig handler.
4. **Per-section dig blob writer** — persist one dug section as its own source-of-truth blob via
   staged→promote.

### Out of scope (deferred, each its own later slice)
- **Slide screenshots** on the hosted worker (video download + frame capture + non-recapturable
  source-of-truth blobs + GC).
- **Cloud dig serving** route and **dig-state** endpoint.
- **Frontend** VideoMenu "dig" wiring and **live progress (SSE)**.
- **Dig PDF**.

---

## 4. Architecture

Four units, each with one responsibility and a well-defined interface.

| # | Unit | Files (create/modify) | Responsibility |
|---|---|---|---|
| 1 | Enqueue-dig migration | Create `supabase/migrations/0018_enqueue_dig.sql` (latest is `0017`) | Replace the `unsupported_job_kind` guard so `enqueue_job` admits `'dig'`. No other RPC behavior changes. |
| 2 | Cloud dig trigger | Modify `app/api/videos/[id]/dig/[sectionId]/route.ts`; create `lib/dig/cloud/enqueue-dig-core.ts` | Session-auth, playlist-UUID owner-assert, validate, dedup, enqueue; return immediate outcome. |
| 3 | Dig worker handler | Create `lib/job-queue/dig-handler.ts`; modify `worker/main.ts` | Consume a leased dig job; produce the text-only per-section blob. |
| 4 | Per-section blob writer | Create `lib/dig/cloud/write-dig-section-blob.ts` | Write one section as `dig/{base}/{sectionId}.r{V}.md` via staged→promote. |

The local path (`lib/dig/dig-section.ts`, in-memory `job-registry`, the `stream` and `dig-state`
routes) is **untouched** — the cloud branch is additive.

---

## 5. Trigger route contract

`POST /api/videos/[id]/dig/[sectionId]` — cloud branch (`STORAGE_BACKEND === 'supabase'`).

**Ordering:** backend gate and input validation (400s) run **before** auth (401), matching the PDF
route's 400-before-401 discipline.

### 5.1 Request
| Part | Value |
|---|---|
| Path `[id]` | YouTube video id — validated by `assertVideoId` (400 on bad shape). |
| Path `[sectionId]` | Section start-second (integer). Non-integer → 400. |
| Query `playlist` | Playlist **UUID** (not the YouTube list-key). Missing/malformed → 400. |
| Query `outputFolder` | **Rejected if present** (`.has()`) → 400. It is a local-only concept; presence signals a mis-targeted client. |
| Auth | Session cookie → `createServerSupabase(cookieStore)` → `supabase.auth.getUser()`. RLS-scoped session client; **never** service_role from the route. |

### 5.2 Responses
| Outcome | Status | Body |
|---|---|---|
| Current-version dig blob already present | `200` | `{ status: 'ready', sectionId }` — **no job, no charge** (dedup). |
| Enqueued (absent or older-version) | `202` | `{ status: 'enqueued', jobId, sectionId }` — charged once at enqueue. |
| In-flight dig for same (playlist, video, section) | `202` | `{ status: 'enqueued', jobId, sectionId }` — joins the existing job via the jobs unique index; no second charge. |
| Backend not supabase | `400` | error — cloud branch requires supabase backend. |
| Bad video id / sectionId / playlist / outputFolder present | `400` | error. |
| Unauthenticated | `401` | error. |
| Playlist not owned by caller | `404` | "not found" (owner isolation — do not distinguish "not yours" from "absent"). |
| Summary for this video not committed yet | `409` | "summary not ready" — dig presupposes a committed summary to source sections from. |
| `sectionId` not a real section of this video | `404` | "section not found". |
| Anonymous user (dig quota = 0) | `403` | quota — anon cannot dig. |
| Daily dig quota exhausted (> 5 registered) | `429` | quota-exceeded. |

**No SSE / progress stream in this slice.** The response reports the *enqueue decision*, not the
*render result*. How a caller learns the job finished (poll the jobs table, or a future SSE) is the
consumption slice's contract.

---

## 6. Worker handler (`makeDigHandler`)

Reimplements the `digSection` core against the storage abstraction (`BlobStore` / `MetadataStore`)
instead of `fs`. Runs under the service-role worker persistence path
(`getWorkerStorageBundle(serviceClient, ownerId, playlistId)` — resolves playlist by UUID with an
explicit ownership assert, never by key), threading the dig progress phase (`digging`), the cancel
signal, and the generation caps.

**Steps:**
1. Read the summary blob for the video via `BlobStore.get`; `parseSummaryMarkdown`.
2. Find the section whose `timeRange.startSec === sectionId`. Missing → permanent failure
   (should not happen — the trigger validated it, but the handler re-checks defensively).
3. `resolveTranscriptSegments(videoId, url, duration)` — shared resolver: YouTube captions first,
   Gemini transcription fallback. Both-empty → `PermanentTranscriptError` (non-retryable).
4. `windowForSection(section, sections, segments, duration)` → `SectionWindow`.
5. `generateDig(window, videoId, lang)` → raw markdown (may contain `[[SLIDE:...]]` tokens).
6. `resolveTranscriptTokens(...)` as local does.
7. **Skip `resolveSlideTokens`** — no video download, no frame capture. Slide tokens remain **inline
   and verbatim**.
8. `writeDigSectionBlob(...)` — staged→promote the per-section blob (Unit 4).

**No shared companion-doc read-modify-write** — that is the whole point of the per-section design
(§8). The handler only ever *writes its own* section blob; it never reads-then-rewrites a document
another concurrent dig also writes.

---

## 7. Output File Format

### 7.1 Blob key
```
dig/{base}/{sectionId}.r{DIG_GENERATOR_VERSION}.md
```
- `base` — the video's canonical basename (serial + slug), the same `base` the summary/PDF blobs use.
- `sectionId` — the section start-second integer (safe as a path segment).
- `.r{V}` — the `DIG_GENERATOR_VERSION` in effect at write time. A version bump changes the key, so a
  stale-version blob is simply *absent* at the current key → the trigger re-enqueues (§9).
- Owner namespacing is provided by the principal/blob-store (playlist_key scope) exactly as for
  summary blobs — the key above is relative within that namespace.

### 7.2 Doc format (one section per blob)
YAML frontmatter + the section's markdown body. Self-describing so the deferred serving slice can
merge sections without a separate index.

```markdown
---
videoId: dQw4w9WgXcQ
sectionId: 132
startSec: 132
title: How the encoder attends to earlier tokens
language: en
sourceVideoUrl: https://youtu.be/dQw4w9WgXcQ?t=132
generatedAt: 2026-07-12T18:04:11.522Z
genVersion: 9              # DIG_GENERATOR_VERSION at write time
slides: []                 # empty in the text-only slice; tokens preserved inline, unresolved
---

The encoder builds a contextual representation of each token by attending over the
whole input sequence. [[SLIDE:2:12|2:20|Self-attention weights heat-map]] Concretely,
each query vector is compared against every key...

### Why this matters for long inputs

...
```

**Field notes:**
- `slides: []` — deliberately empty. Slide `[[SLIDE:M:SS|M:SS|caption]]` tokens are preserved
  **verbatim in the body**, not stripped and not resolved. This is lossless: the timestamps and
  captions (already generated and paid for) survive for the later slide-capture slice to resolve
  in place, and the serving slice decides how to render an unresolved token.
- `generatedAt` is a free-form timestamp; the blob is **section-keyed, not content-addressed**, so
  non-determinism here is harmless (unlike the PDF cache key).
- `genVersion` duplicates the `.r{V}` in the key for self-description and audit.

---

## 8. Concurrency model

**Hazard avoided:** locally there is one `-dig-deeper.md` per video and `upsertDugSection` is a
read-modify-write (read whole doc, splice section block, write back), safe only because a single
local process serializes it. In the cloud, two sections of the same video dug concurrently are two
jobs → two worker leases → two concurrent read-modify-writes of one blob → **lost update**.

**Design:** **per-section blobs eliminate the shared mutable document.** Each dig job writes exactly
one blob at a key unique to its `(video, sectionId, version)`. No two dig jobs ever target the same
blob, so there is no read-modify-write and no lost update — by construction, without a lock.

- "Which sections are dug" is **derivable** (completed dig jobs in the `jobs` table, and/or listing
  `dig/{base}/` blobs) — the deferred dig-state endpoint will expose it; this slice does not need it.
- Job-level leasing (existing) still prevents two workers from processing the *same* section
  concurrently; the unique index dedups concurrent enqueues of the same section.

---

## 9. Charging, quota, idempotency, version

- **Dig is a durable Job**, charged **once at enqueue** via `enqueue_job` — the same charge-once
  invariant summary ingest uses. It is **not** the serve-side `reserve_serve_model` lazy-restyle
  path; there is no second/magazine model for dig.
- Config already in schema: quota `dig` = **5/day registered, 0 anon**; `dig_est_cents = 150`;
  `dig_max_attempts = 1`. This slice adds none of it — only unblocks the RPC.
- **No charge on dedup.** The authoritative "already done" signal is the **current-version blob's
  existence**. The trigger checks that blob first; present → `200 ready`, no enqueue, no charge.
- **Version-aware regeneration.** Because the blob key embeds `.r{DIG_GENERATOR_VERSION}`, a version
  bump makes the current-version blob absent → the trigger enqueues + charges for a fresh generation.
  Older-version blobs are ignored (and are GC candidates for a future slice; not deleted here).

### 9.1 Open question flagged for the plan + adversarial review
The jobs idempotency unique index keys on `(playlist, video, section, kind)` but **not version**. A
completed dig-job row must not permanently block a legitimate version-bump re-enqueue. The plan must
resolve enqueue-idempotency-vs-version explicitly. Intended resolution: **the blob is the dedup
authority** (trigger enqueues only when the current-version blob is absent), and the unique index is
scoped so it only prevents *concurrent/in-flight* duplicate enqueues — not a permanent lock after
completion. The plan must verify the actual index/DDL semantics against this intent and adjust the
migration if the index would otherwise block re-enqueue.

---

## 10. Data flow

```
client → POST /api/videos/[id]/dig/[sectionId]?playlist=<uuid>
   ├─ backend gate (supabase?) ──────────────── no → 400
   ├─ validate id / sectionId / no outputFolder  → 400 on fail
   ├─ auth (session client) ──────────────────── none → 401
   ├─ owner-assert playlist by UUID ──────────── not owned → 404
   ├─ summary committed? ─────────────────────── no → 409
   ├─ section exists? ────────────────────────── no → 404
   ├─ dedup: current-version blob present? ── yes → 200 {status:'ready'}   (no charge)
   └─ enqueue_job(kind=dig, section)  [quota 5/day reg, 0 anon; charge-once; est 150]
         ├─ anon / quota exhausted → 403 / 429
         └─ ok → 202 {status:'enqueued', jobId}

worker leases dig job → makeDigHandler
   → read summary blob → parse → find section
   → resolve transcript (captions → Gemini fallback)
   → windowForSection → generateDig (text-only)
   → resolveTranscriptTokens → (skip resolveSlideTokens)
   → writeDigSectionBlob: stage → promote  dig/{base}/{sectionId}.r{V}.md
```

---

## 11. Enumerated behaviors (contract for the plan's behaviors tables + tests)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Enqueue new dig | Authed owner, summary committed, section valid, no current-version blob | 202 `{status:'enqueued', jobId}`; one charge; job row `kind=dig`, `section_id=sectionId`. |
| 2 | Dedup (already done) | Current-version blob present | 200 `{status:'ready'}`; **no** new job, **no** charge. |
| 3 | Join in-flight | A dig job for same (playlist,video,section) already pending | 202 with the existing jobId; no second charge. |
| 4 | Version bump regenerates | Blob exists only at an older `.r{V}` | 202 enqueued + charge (current-version blob absent). |
| 5 | Bad video id | `assertVideoId` fails | 400, before auth. |
| 6 | Non-integer sectionId | `[sectionId]` not an int | 400, before auth. |
| 7 | `outputFolder` present | `?outputFolder=` (even empty) | 400. |
| 8 | Non-supabase backend | cloud branch on local backend | 400. |
| 9 | Unauthenticated | no session | 401. |
| 10 | Not owner | playlist owned by another user | 404 "not found". |
| 11 | Summary not committed | video summary artifact not `promoted`/committed | 409. |
| 12 | Section not found | sectionId not a section of the video | 404. |
| 13 | Anonymous | anon principal, dig quota 0 | 403 quota. |
| 14 | Quota exhausted | > 5 dig enqueues that day | 429. |
| 15 | Transcript absent | captions empty + Gemini fallback empty | job fails with `PermanentTranscriptError` (non-retryable); no blob promoted. |
| 16 | Worker crash mid-render | lease expires before promote | staged blob never promoted → no torn source-of-truth; retry bounded by `dig_max_attempts=1`. |
| 17 | Concurrent two-section dig | sections A and B of one video enqueued together | both jobs complete; **both** per-section blobs present; neither clobbers the other. |
| 18 | Slide tokens preserved | `generateDig` emits `[[SLIDE:...]]` | tokens appear **verbatim** in the persisted blob; `slides: []` in frontmatter. |

---

## 12. Testing strategy

Mocking boundaries per project policy: Gemini mocked at `lib/gemini.ts`; YouTube + transcript at
`lib/youtube.ts` / the transcript resolver; E2E/integration mock at the API-route / worker seam.

**Unit**
- Trigger: each branch in §11 rows 1–14, 18 — validation ordering (400-before-401), dedup no-charge,
  quota/anon, owner isolation. Charge assertion via spy with a **mutation control** (prove the spy
  fires only on the enqueue path, not on dedup).
- Handler: happy path (rows 1, 18) and each error path (rows 12, 15) with Gemini/transcript mocked;
  assert the persisted blob's frontmatter + inline token preservation.

**Integration (real Supabase)**
- Enqueue → worker → blob **round-trip**.
- **Owner isolation** — a second owner cannot read/trigger the first's dig; RLS holds.
- **No-charge-on-dedup** with mutation control (spend ledger unchanged on the dedup path; changes by
  exactly one dig charge on the enqueue path).
- **Concurrency proof** (row 17) — two sections of one video dug concurrently; assert **both** blobs
  land intact (the per-section-blob race guarantee; must fail against a hypothetical shared-doc
  regression).
- **Version-bump regenerates** (row 4).

---

## 13. Gaps deliberately left for the plan / adversarial review

- §9.1 enqueue-idempotency-vs-version index semantics (must verify actual DDL).
- Exact `base` derivation reuse (confirm the summary blob's `base` is reachable in the worker/trigger
  context for keying).
- Whether the trigger's "summary committed?" check reuses `loadSummaryForServe`'s gate or a lighter
  index read (dig does not need to resolve/charge a magazine model — it only needs the summary blob
  to source sections, so it must **not** go through the `resolveMagazineModel` charge path).
- Worker kind→handler dispatch shape (map vs switch) and how the existing single-handler registration
  is refactored without regressing summary.

---

## 14. Out of scope — explicit deferrals (future slices)

1. **Slide capture on the hosted worker** — video download, frame grab, source-of-truth slide blobs
   (staged→promote), token resolution, GC of orphaned slide blobs.
2. **Cloud dig serving** — a serve route (extend `html`/`pdf` past the `type=summary` gate) that
   merges per-section blobs and renders, plus a **dig-state** endpoint listing dug sections.
3. **Frontend** — VideoMenu "Dig deeper" affordance and **live progress (SSE)** driven by the worker.
4. **Dig PDF** — the dig analog of the summary PDF slice.
