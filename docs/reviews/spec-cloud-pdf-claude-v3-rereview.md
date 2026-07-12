# Adversarial Re-Review (Round 3) — Cloud Summary PDF Design Spec

**Artifact:** `docs/superpowers/specs/2026-07-11-cloud-summary-pdf-design.md` (v3) + `docs/adr/0003-cloud-pdf-serve-side-not-a-job.md`
**Reviewer:** Claude (adversarial re-review, round 3)
**Date:** 2026-07-11
**Prior rounds addressed:** Codex v2 (B-1 High, B-2 Medium, B-3/B-4 Low) + Claude v2 (B-N1 Medium, B-N2/B-N3/B-N4 Low).
**Verdict:** **CONVERGED — no new Blocking, no new High.** One Low precision note on the semaphore release path. This is the diminishing-returns gate.

Grounded in the actual reused code (`render.ts`, `theme.ts`, `blob-store.ts`, `supabase-blob-store.ts`), re-verified this round rather than trusted from prior rounds.

---

## (A) Round-2 fixes — genuine, not reworded

1. **Single-flight/semaphore FAILURE cleanup (Codex B-1 High / Claude B-N1 Medium) — GENUINE.**
   §3 step 6 now carries a dedicated paragraph: "Both guards MUST clean up in `finally` … On *any*
   settle — success, error, or timeout — the semaphore slot is released **and** the single-flight
   `Map` entry is deleted (`inFlight.delete(cacheKey)`)." It names both poison modes (permanently-busy
   key from a leaked map entry; capacity bleed-to-zero from a leaked slot) and specifies
   **waiter-on-failed-leader → receives the leader's error (503), NOT a poisoned/cached failure — entry
   gone, next request retries cleanly.** §11 adds the "poison-prevention test" (leader errors/times out →
   map entry deleted + slot released + subsequent request retries + repeated failures don't bleed the cap;
   same-key waiters get 503, not a poisoned entry). Matches exactly what Codex B-1 and Claude B-N1
   mandated. (One residual precision nit on the *saturation* path — see B, non-blocking.)

2. **mdKey validation ORDERING (Codex B-2 Medium) — GENUINE.**
   §3 step 2 now runs `assertCloudSummaryMdKey(mdKey)` **immediately after selecting `mdKey`, BEFORE the
   blob read and before deriving `base`** (explicit words in the spec), enforcing single path component +
   `.md` suffix + non-empty base + no `/ \ .. NUL`, → **409** on failure, so `nested/foo.md` never reaches
   `blobStore.get` and can never produce nested `models/…`/`pdfs/…` keys. The validator file is specified:
   new `lib/html-doc/assert-cloud-summary-md-key.ts` (§4 row), and §4's `serve-summary-core.ts` row states
   `loadSummaryForServe` "calls `assertCloudSummaryMdKey(mdKey)` **before** the blob read." §11 has the
   dedicated test. **Independently confirmed load-bearing:** `assertLogicalKey` (`blob-store.ts:21-24`)
   only rejects leading `/`, `..`, NUL — it *passes* embedded-slash `nested/foo.md` — so the timing fix +
   dedicated single-component validator is exactly the right correction, not a reworded no-op.

3. **Lows — all GENUINE:**
   - **503-after-charge not a double charge (Claude B-N2):** §3 step 6 "*Charge note (round-2 Low)*" states
     a saturation-503 can occur after Stage 2 already materialized/charged the model, and that this is the
     pre-existing on-view materialization (§3 money invariant), not a new/double charge; the retry finds the
     model cached and renders free. Present and correct.
   - **Stray `format`/`download` ignored (Claude B-N3):** §3 step 1 "Any stray `format`/`download` query
     params are **ignored**" + §7 note "No `format`/`download` params in this slice; `download=1` is the
     deferred download-to-disk hook." Explicit decision, not an omission.
   - **"never stale" softened (Codex B-4):** §2 Decision B now says "**collision-negligible**" with the
     64-bit/16-hex truncation caveat ("astronomically unlikely but not mathematically impossible … Use the
     full digest if the absolute guarantee is ever required"). Softened as requested.
   - **ADR key example (Codex B-3):** `0003…:45` now reads
     `pdfs/{base}.r{PDF_RENDER_VERSION}.{sha256(htmlNonceFree).slice(0,16)}.pdf` (r-salt present, nonce-free
     input named). Matches §2/§3 exactly.

**Independent determinism re-check (the load-bearing B1 assumption):** re-confirmed the nonce is the only
per-request variance in the hashed HTML — `render.ts` has no `Date`/`Math.random`/`crypto`, `GENERATOR_VERSION`
is a constant import, and `nonceAttr(undefined) === ''` (`theme.ts:79-81`). The `{nonce: undefined}` render is
a pure function of `(parsed, model, opts)`. The cache-hit design still holds.

---

## (B) Final sweep — new defects from the v3 edits

**No new Blocking. No new High.** One Low and confirmation the invariants did not regress.

### B-N6 — LOW (precision) — "on any settle the slot is released" is imprecise for the saturation-503 path
**Where:** §3 step 6 finally-cleanup paragraph.
The mandated ordering is correct: single-flight registration must precede the semaphore acquire (the spec
lists single-flight first and has waiters await the in-flight promise — required, else N same-key requests
each consume a slot and single-flight is defeated). Under that ordering the failure paths are sound:
- **Render error/timeout** (slot *was* acquired): finally deletes the map entry and releases the slot →
  clean; waiters on the rejected leader promise get 503. Correct.
- **Saturation-503** (slot *never* acquired): the leader's promise rejects, its map entry is deleted, waiters
  get 503, next request retries. Also clean — **provided the slot is released only if it was acquired.**

The imprecision: the blanket phrase "On *any* settle … the semaphore slot **is released**" reads as
unconditional. If an implementer wires a single finally that releases the slot even on the acquire-threw
path, that **over-releases** the counting semaphore — inflating available permits and eventually admitting
**more** than `PDF_MAX_CONCURRENCY` concurrent Chromium, the exact OOM the cap exists to prevent. The
idiomatic pattern (`const slot = await sem.acquire()` throwing *before* the slot-releasing try/finally is
armed, or a semaphore that hands back a release fn only on success) avoids this naturally, so it is a Low,
not a defect that ships a broken design.
**Fix (one clause):** "release the semaphore slot in `finally` **only if it was acquired** (a saturation-503
never acquired a slot, so nothing is released); the map entry is deleted unconditionally on settle." No new
test needed beyond the existing poison-prevention test, which could add one assertion: *a saturation-503 does
not raise the effective concurrency cap on the next request.*

### Internal consistency — CLEAN
Step numbering (§3 steps 1–7), helper names (`loadSummaryForServe`/`resolveAndParse`/`assertCloudSummaryMdKey`/
`pdfCacheKey`), the two distinct validators (`assertCloudSummaryMdKey` on `mdKey` in step 2 vs `assertLogicalKey`
on the final PDF key in step 5 — no overlap, no contradiction), the key format across §2/§3/§4/ADR, and the
new §4 rows are all internally consistent. No duplicated or re-contradicting claims introduced by the v3 edits.

### Money / isolation / local-untouched invariants — NO regression
- **Money:** §3 money invariant + "Precise invariant (round-1 B3)" unchanged; the new charge-note in step 6
  reinforces (not weakens) it — a saturation-503 is the pre-existing on-view model materialization, no new line.
- **Isolation:** §3 owner-isolation paragraph (session client, `auth.uid()` first segment) intact; the new
  `assertCloudSummaryMdKey` *strengthens* isolation by blocking a corrupt cross-owner/nested key before any
  storage op.
- **Local untouched:** §13 + §4 (`generateDocPdf` backward-compatible, launch-arg change gated behind the
  cloud/backend check, GET route cloud-only) unchanged.

---

## Convergence call
Round 3 returns **no new Blocking and no new High** — only one Low precision clause (B-N6, conditional slot
release on the saturation path) on the same concurrency machinery round 2 elevated. Per `docs/dev-process.md`
this is the diminishing-returns gate: **CONVERGED.** Fold B-N6's one clause into §3 step 6 during
implementation (it is a wording tightening, not a redesign) and take the spec to human approval.
