---
status: accepted
---

# Cloud summary PDF is a serve-side cached derived-cache blob, not a durable Job

The cloud summary **PDF** is produced by a **synchronous serve+cache route**
(`GET /api/pdf/[id]`) that renders on demand and caches the result — **not** by a durable
**Job** on the cloud queue, and it is written with a **bare atomic `blobStore.put`** to a
**content-addressed key**, **not** through the `committed → promoted` staging the summary uses.

A future reader steeped in this system's two dominant patterns will reasonably ask two
questions, and this ADR answers both:

1. *"All expensive generation here is a durable **Job** (`summary`, `dig`) — enqueued, leased,
   polled. Why is the PDF a plain synchronous route instead?"*
2. *"Every source artifact is written through `putStaged → verify → committed → promote →
   promoted` (`consistency.writeArtifact`) to survive the finalizing window. Why does the PDF
   skip that and just `put`?"*

The answer to both is the PDF's nature in the glossary: it is a **derived-cache blob** — the
*printable, model-less, deterministic render of the rendered HTML doc* — not source-of-truth
generative work.

## Considered options

- **Durable `pdf` Job (rejected).** Add a `pdf` job kind + worker handler + dispatch, enqueue,
  and have the client poll then download. This is the right shape for *expensive, off-request,
  chargeable generative* work (a Gemini call that can take a minute). A PDF is none of those:
  it is a ~1–2s CPU render with **no model call and no charge of its own**. Making it a Job
  would add queue infrastructure and an async enqueue→poll→download UX for work that completes
  in the time of a normal request, and would isolate Chromium to the worker at the cost of the
  best UX (click → inline view). Reserved as the **fallback** only if the web tier cannot host
  Chromium (see the slice spec's deploy section).
- **Two-phase `committed → promoted` staging for the PDF blob (rejected).** Mirror the summary
  write for uniformity. Rejected because that staging exists to protect a **source-of-truth**,
  **index-referenced** blob during its finalizing window — so a reader that sees the index
  reference never reads a half-written file. The PDF is **derived-cache** (safe to lose and
  rebuild), **not index-referenced** (no `artifacts.pdf` record — pure blob existence check),
  and **content-addressed** (concurrent first-views write the *same* key with *byte-identical*
  content, so "last write wins" is harmless). The only failure the staging would guard against
  is a torn read of a partial upload — which cannot occur if the blob store's `put` is atomic
  (the object becomes visible only when the upload completes).
- **Synchronous serve+cache route with a bare atomic put (chosen).** Render on demand, cache
  the PDF at a content-addressed key `pdfs/{base}.{sha256(html).slice}.pdf`, stream it back
  inline. Reuses the entire `serveCloud` gate→read→resolve→render core (extracted to a shared
  helper); adds only Chromium + the cache check. Precedent: the **local** PDF (also a
  derived-cache blob) already writes with a bare `blobStore.put`, not the staging dance.

## Consequences

- **Atomicity is the load-bearing assumption.** Skipping `committed → promoted` is safe **only
  if** the cloud blob store's `put` (`upload(..., { upsert: true })`) is **visibility-atomic** on
  both new and existing objects — a concurrent `get` sees either the old object or the complete
  new one, never a partial. Supabase Storage is S3-backed and a single PUT has this property, but
  it **must be verified during implementation** (provider docs + a concurrent overwrite/read
  test) **before plan approval** (round-1 dual review: Codex flagged it Blocking-until-proven;
  Claude judged the S3 PUT atomic — the verification settles it empirically).
  **Correction (round-1 B2):** an earlier draft of this ADR named `putStaged → promote` as the
  "atomic fallback." That is **wrong** — `promote` is `copy + delete`, which is **non-atomic**
  (`lib/storage/supabase/supabase-blob-store.ts:45`). If `put` is ever shown *not* to be atomic,
  the correct fallback is **unique staging keys + an atomic manifest pointer** (a DB/cache row
  whose single-row update flips the "current PDF key"), keeping the content-addressed blob and a
  bare-existence read — **not** `promote`.
- **No artifact record, so `merge_video_data` and the `artifacts` map stay untouched.** The
  cache is invisible to `consistency.resolveMissing`; superseded content-addressed blobs orphan
  on content change and are swept by a later GC (a recorded backlog item, not built here).
- **Chromium moves into the web tier.** Because generation is synchronous, headless Chromium
  runs in the web process, so the web deployment must be containerized (this is the codebase's
  first cloud Chromium use). Revisiting this decision — moving PDF to a durable Job — would mean
  building the `pdf` job kind + handler + dispatch and an async client UX, but would *not*
  disturb the cache format (content-addressed blobs work for either producer). So the route
  architecture is reversible; the blob format is stable across the reversal.
- **The money invariant is preserved by construction.** A serve-side render inherits the
  existing on-view magazine-model materialization (per-owner serve budget + daily cap) and adds
  no new charge; a Job would have forced a new charging decision. The PDF itself never charges.
