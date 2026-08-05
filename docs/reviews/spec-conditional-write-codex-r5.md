<!-- codex-review: model=gpt-5.5 -->

**Verdict: NOT CONVERGED.**

I found new Blocking defects in v5’s new protocol. I could not live-measure the DB: Docker socket is denied and direct `127.0.0.1:54321` access is blocked from this sandbox, and `psql` is not installed. Source reads were enough to break the design.

**Blocking**

1. [docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:292](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:292) says `committedPayload := video WITHOUT docVersion`, and [spec:320](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:320) claims this “breaks the skip’s second conjunct.” It does not reliably do that.

`persist_summary` preserves existing fields first, then only reapplies provided summary-owned fields: [0021_cloud_sync_signals.sql:116](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0021_cloud_sync_signals.sql:116) and [0021_cloud_sync_signals.sql:120](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0021_cloud_sync_signals.sql:120). Omitting `docVersion` preserves the row’s current `docVersion`; it does not remove or stale it. The status rule can still preserve `promoted` on same-key committed writes at [0021_cloud_sync_signals.sql:142](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0021_cloud_sync_signals.sql:142).

Concrete failure:
- W1 generated current-version bytes for key `007_alpha.md`.
- W2 finishes first and writes `docVersion = CURRENT`, `status = promoted`, blob = W2.
- W1 gets `PS003`, adopts `(7, "007_alpha.md")`, then does committed persist without `docVersion`.
- The row keeps W2’s current `docVersion`, keeps `promoted`, but now has W1’s `tldr`/ratings/takeaways.
- Fault before `publish`.
- Retry hits the idempotency skip at [summary-handler.ts:86](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/summary-handler.ts:86): `promoted && current docVersion`.

So the boundedness argument is still false for the two-worker same-address path. The mutation test in §8 only restores `docVersion` into the payload; it will miss the preserved-existing-current case.

2. [docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:487](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:487) makes the two-worker case only a test requirement, not a design decision. The design still says `publish(ref, key): put(key, stagedBytes)` at [spec:351](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:351), which is unconditional overwrite. `SupabaseBlobStore.put` is upsert: [supabase-blob-store.ts:22](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:22).

A test that “states the outcome the slice accepts” is not sufficient unless §6 specifies that accepted outcome. The right accepted outcome should be: identical bytes are idempotent; different bytes at a destination that changed since observation must not be silently overwritten by a stale worker. Today v5 accepts last writer wins while the guard cannot see it because the address never moved.

3. [docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:259](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:259) still sources `observedSummaryMd` from `existing?.summaryMd`, but consumers prefer `artifacts.summaryMd.key`: serve path [serve-summary-core.ts:53](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-summary-core.ts:53), dig path [resolve-summary-key.ts:3](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/dig/cloud/resolve-summary-key.ts:3), share path [serve.ts:44](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/share/serve.ts:44).

Concrete failure if one of the recorded 23 divergent rows is `summaryMd="007_old.md"` and `artifacts.summaryMd.key="003_new.md"`:
- Serve/dig read `003_new.md`.
- Worker guard/adopt reads `007_old.md`.
- Expected `(serial, "007_old.md")` matches the top-level field.
- `persist_summary` writes payload `summaryMd="007_old.md"` and `artifacts.summaryMd.key` becomes payload-wins via [0021_cloud_sync_signals.sql:137](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0021_cloud_sync_signals.sql:137).
- Consumers are moved from the authoritative promoted key back to the stale top-level key; paid digs keyed under `003_new` go dark.

§8 only says to assert both pointers after success at [spec:475](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:475). That does not fix the input-source asymmetry.

**High**

- Abort cleanup is still incomplete. [spec:298](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:298) discards temp before the committed persist, but [spec:302](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:302) throws `AbortError` between committed and publish without deleting `ref.tempKey`. That contradicts the “every discard path deletes its own temp” requirement and the no-sweeper fact at [spec:368](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:368).

- v5 intentionally breaks Class-A scalar coherence during the committed window. `persist_summary` normally writes `docVersion`, `tldr`, ratings, takeaways, `mdGeneratedAt`, etc. as one summary-owned tuple: [0021_cloud_sync_signals.sql:120](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0021_cloud_sync_signals.sql:120). v5 withholds only `docVersion`, leaving new scalars beside old/preserved version. `deriveClassASignals` reads `docVersionMajor` independently from body hash and timestamps at [backfill.ts:7](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/backfill.ts:7), and quick-view serves `tldr` without checking promoted/current body coherence at [quick-view/route.ts:81](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/api/videos/[id]/quick-view/route.ts:81). The spec names the skip benefit but does not specify who may observe this split-brain tuple or what they should do.

- [spec:435](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:435) still says “A leaked staging object is inert and swept,” directly contradicting [spec:368](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:368), which correctly says there is no staging sweeper. This is not harmless stale prose; it appears in the cleanup subsection and will mislead implementers about failure paths.

**Round-4 Fix Status**

- B-R4-1 residual unbounded: **PARTIALLY.** v5 adds the docVersion split at [spec:292](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:292), but because omission preserves an existing current `docVersion`, it does not close the two-worker same-address freeze.
- B-R4-2 stale same-address worker destructive overwrite: **NOT FIXED.** [spec:487](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:487) asks for a test; [spec:351](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:351) still overwrites.
- B-R4-3 `get` versus `tryGet`: **FIXED.** [spec:353](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:353) uses `tryGet`; [spec:361](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:361) forbids `get`.
- H-R4-2 `summaryMd` vs `artifacts.summaryMd.key`: **NOT FIXED.** The guard still uses top-level `summaryMd`; consumers prefer artifact key.
- H-R4-4 no staging sweeper: **PARTIALLY.** Good explicit deletes at [spec:307](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:307) and [spec:358](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:358), but stale false cleanup prose remains and abort-after-committed leaks temp.
- H-R4-5 abort span: **PARTIALLY.** Checks added at [spec:298](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:298) and [spec:302](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:302), but the second path omits temp cleanup.
- M-R4-3 inert `promoteSemantics`: **FIXED.** v5 drops it at [spec:477](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:477).
- H-R3-1 / M-R4-5 adopt changed re-summarize addressing: **NOT FIXED.** [spec:277](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:277) still adopts whenever `observedSummaryMd` is non-null, while [spec:536](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:536) still describes non-concurrent title-change orphaning as live/out of scope.
- Codex R4 adopt validation: **FIXED.** [spec:278](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:278) names `assertCloudSummaryMdKey`, and [spec:282](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:282) specifies `PS002`.
- Codex R4 publish mismatch under `get`: **FIXED for unreadable classification, not for same-address destructive overwrite.**

**Existing Mechanism Sweep**

- `docVersion` split is worse than it looks because the existing `persist_summary` merge preserves omitted fields. If the design needs “not current,” omission is the wrong primitive.
- `publish` still hand-rolls what `copyBlob` already models: `tryGet`, classified destination state, write, verify. v5 imports `tryGet` but not the destination-exists protection.
- Summary-key resolution already exists as `resolveSummaryMdKey` and prefers `artifacts.summaryMd.key`; v5 uses the weaker top-level field for the guard.
- `writeArtifact` already owns staged-write sequencing, but v5 again adds a single-call-site protocol instead of moving the seam.

I tried to break the predicate itself only enough to confirm it was not the issue. The failures are still in protocol: payload field omission semantics, publish overwrite semantics, key-source asymmetry, abort cleanup, and tests that name hazards without specifying accepted behavior.
