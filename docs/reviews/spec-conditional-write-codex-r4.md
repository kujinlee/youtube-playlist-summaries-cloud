<!-- codex-review: model=gpt-5.5 -->

**Verdict: NOT CONVERGED.**

I found new Blocking protocol defects. I also could not run fresh live probes because this sandbox cannot access the Docker socket (`permission denied`), so the live-stack claims below rely on prior recorded probes plus deterministic source reads.

**Blocking**
1. [docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:277](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:277) — `adoptBase(observedSummaryMd) # VALIDATED — see below` does not actually specify validation.

The “see below” never defines accepted shape, rejection class, or caller behavior. The repo already has the validator: [assert-cloud-summary-md-key.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/assert-cloud-summary-md-key.ts:16), and consumers reject corrupt/nested summary keys: [serve-summary-core.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-summary-core.ts:60), [resolve-summary-key.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/dig/cloud/resolve-summary-key.ts:16).

Concrete failure: row has `summaryMd = "nested/foo.md"` or `"raw/275_google-okf.md"`. v4 adopts it, writes paid summary bytes there, persists `promoted`, then serve rejects the key as corrupt/unsupported. This should be specified as fail-closed, likely `PS002`/non-retryable repair-needed, before publication.

2. [docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:325](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:325) — publish mismatch handling is under-specified and can freeze row/body mismatch.

v4 says `put`, `readBack := get(key)`, compare `mdHash`, throw before `promoted`. Worst interleaving on same key:

- Row starts `serial=3`, `summaryMd="003_alpha.md"`, status `promoted`.
- W2 does committed persist with W2 scalars; inherited status remains `promoted`.
- W1 then does committed persist with W1 scalars; inherited status remains `promoted`.
- W1 `put`s W1 bytes.
- W2 `put`s W2 bytes, then crashes before final promoted persist.
- W1 read-back sees W2 bytes, mdHash mismatch, throws.
- Row is still `promoted` with W1 scalars, blob has W2 body. Retry can hit the idempotency skip at [summary-handler.ts:86](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/summary-handler.ts:86) and freeze it.

`mdHash` is the right byte comparison, but mismatch cannot just “throw” while the row may already be `promoted` due key-scoped inheritance. The spec needs behavior for “different valid summary” and should use `tryGet`, not `get`, because [BlobStore](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/blob-store.ts:46) explicitly says `get` collapses unreadable and absent.

**High**
- [docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:379](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:379) still says staging leaks are “swept.” I found `_staging` writers and `deletePrefix`, but no sweeper. A `PS003` loop can leak up to `N * max_attempts = 15` staging objects per job unless every discard path explicitly deletes temp.
- [docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:256](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:256) only checks abort at attempt top. The irreversible span is `persist(committed)` → `publish` → `persist(promoted)`. Current code already checks immediately before writes for this reason: [summary-handler.ts:166](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/summary-handler.ts:166). v4 should require checks immediately before committed and before publish.
- Codex R2/R3 H4 is still not fixed: v4 argues no deadlock at [spec:242](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:242), but §8 still has no concurrent-session test for `reserve_video_slot` / `claim_video_slot` / `persist_summary` under the new `FOR UPDATE`.

**Round-3 Fix Status**
- B-R3-1 observedSerial provenance: **FIXED.** v4 states attempt 1 uses `reserveVideoSlot` for serial and `:84` read for key, and explicitly admits the torn read at [spec:259](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:259).
- B-R3-2 `p_artifact_is_new`: **FIXED as removal, not fixed as product behavior.** The unsafe boolean is gone at [spec:150](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:150); promoted inheritance is knowingly scoped to #22 at [spec:347](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:347).
- B-R3-3 publish discards verification: **PARTIALLY.** v4 adds verify-after-write at [spec:322](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:322), but uses `get`, leaves mismatch behavior unsafe, and does not specify temp cleanup on throw.
- Codex R3 B1: **FIXED** by removing the flag.
- Codex R3 B2: **PARTIALLY / SCOPED.** Same-key new-artifact inheritance is acknowledged at [spec:357](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:357), but §9 titles #22 only as “on a re-address.”
- Codex R3 B3: **PARTIALLY** as above.
- Codex R3 B4: **NOT FIXED.** Validation is asserted, not specified.

**Torn Read**
Worst interleaving: `:84` reads `summaryMd="007_alpha.md"`, A3 relocates to `(3,"003_alpha.md")`, then `reserveVideoSlot` returns `3`. Attempt 1 expected tuple `(3,"007_alpha.md")` never existed and is rejected with `PS003`. Attempt 2 uses `PS003.detail` and should converge.

I could not make this reject a true brand-new/no-row first summary: with no `summaryMd`, A3 has nothing to relocate. It burns one attempt for existing-row relocation. The 154 serial-less rows do not interact with the torn tuple; `reserve_video_slot` raises on them before the normal Gemini spend path.

**Existing Mechanisms**
v4 still reinvents weaker versions of existing mechanisms:

- `copyBlob` already uses `tryGet` and verify-after-write with classified failure: [blob-store.ts:126](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/blob-store.ts:126). v4’s `publish` should copy that shape.
- Summary key validation already exists: [assert-cloud-summary-md-key.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/assert-cloud-summary-md-key.ts:16). v4’s `adoptBase` must use it.
- `transferClassA` already documents the `promote` vs `put` trap, but still lacks final verify after `put`: [sync-run.ts:386](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:386). v4 correctly spots that, but then only partially imports the safer `copyBlob` discipline.
