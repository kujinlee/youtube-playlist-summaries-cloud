<!-- codex-review: model=gpt-5.5 -->

**Verdict: NOT CONVERGED.**

I tried to break v3 by reading the spec, prior Codex rounds, current `persist_summary`, both blob stores, `summary-handler`, A3 relocation, and the summary-key validators. I can still break the write/recovery protocol.

**Round-2 Findings**

B1, `promote()` create-if-absent publishes stale bytes: **FIXED for that exact bug.** v3 replaces re-address promotion with `publish(ref, key)` defined as verified staged bytes → `put()` overwrite at [spec:286](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:286). New problem below: the final `put()` is not itself verified.

B2, `p_expected_summary_md` semantics unclear / fail-closed if sourced from payload: **FIXED.** v3 explicitly rebuilds payload each attempt and uses `(observedSerial, observedSummaryMd)` for committed, then `(observedSerial, key)` for promoted at [spec:260](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:260) and [spec:267](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:267).

H3, no test for bytes after re-address: **FIXED.** v3 requires `get(<newBase>.md)` to equal newly generated MD under create-if-absent semantics at [spec:357](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:357).

H4, no contention test for new lock: **NOT FIXED.** v3 argues no deadlock at [spec:237](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:237), but §8 does not require concurrent `reserve_video_slot` / `claim_video_slot` / `persist_summary` coverage.

**Blocking**

1. [spec:303](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:303) - `p_artifact_is_new` lets a stale or buggy caller disable the stale-caller defense.

Current monotonic rule preserves `promoted` for same-key `committed` writes at [0021:142](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0021_cloud_sync_signals.sql:142). v3 makes that suppressible by a caller assertion at [spec:306](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:306).

Concrete interleaving:

- Row: `serialNumber=7`, `summaryMd="007_alpha.md"`, `artifacts.summaryMd.status="promoted"`, blob=`GOOD`.
- Stale/buggy caller generated `STALE` earlier, but address still matches.
- It calls committed persist with expected `(7, "007_alpha.md")`, payload `summaryMd="007_alpha.md"`, status=`committed`, `artifactIsNew=true`.
- Predicate passes because address did not move.
- Monotonic preservation is bypassed. Row is downgraded to `committed`; if the worker dies, a genuinely promoted artifact is hidden behind 503.
- If it continues, `publish()` overwrites `007_alpha.md` with stale bytes, then marks promoted.

So the defense is no longer a defense against a stale caller. The row cannot verify “new artifact”; the caller can lie.

2. [spec:307](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:307) - same-key re-summarize is also a new artifact, but v3 only passes `artifactIsNew` on re-address.

Case: doc-version bump, same title.

- Existing row: `serialNumber=7`, `summaryMd="007_alpha.md"`, `status="promoted"`, old docVersion.
- Worker generates new current-version MD at the same key.
- `isReAddress=false`, so committed persist uses `artifactIsNew=false`.
- Key-scoped monotonic rule preserves `promoted` before the new blob is published.
- If the process dies before `publish()`, row now has current-version scalars/docVersion but old blob. On retry, idempotency skip at [summary-handler.ts:86](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/summary-handler.ts:86) sees promoted + current docVersion and can freeze the mismatch.

This is the same crash window v3 says `committed` is supposed to make non-serving.

3. [spec:286](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:286) - `putStaged → verify staged → put final` does not verify the bytes that become final.

`SupabaseBlobStore.put()` is just upload with `upsert: true` at [supabase-blob-store.ts:22](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:22). v3 asserts “atomic upsert” at [spec:291](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:291), but the `BlobStore` contract does not state that, and no final read/compare is required.

The established safe property is: verify staged bytes, then finalization uses that verified object. With `put()`, final publication is a second write. The staged verify no longer proves the final object contains those bytes. Before the final promoted persist, v3 needs a `tryGet(key)` byte-compare like `copyBlob()` does at [blob-store.ts:161](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/blob-store.ts:161).

4. [spec:253](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:253) - `baseOf(observedSummaryMd)` adopts malformed keys instead of failing closed.

Current `baseOf` is only `.replace(/\.md$/, '')` at [reconcile-serial.ts:83](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:83). The codebase already has a stricter cloud summary key allowlist at [assert-cloud-summary-md-key.ts:14](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/assert-cloud-summary-md-key.ts:14), and `resolveSummaryMdKey` rejects nested keys at [resolve-summary-key.ts:15](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/dig/cloud/resolve-summary-key.ts:15).

Concrete bad adoptions:

- `observedSummaryMd=""` → `baseName=""`, `key=".md"`.
- `observedSummaryMd="nested/foo.md"` → `baseName="nested/foo"`, `key="nested/foo.md"`.
- `observedSummaryMd="raw/275_google-okf.md"` → keeps a nested/raw key that downstream summary-key guards reject.

All are worse than re-deriving `007_<slug>.md`, and worse than failing with `PS002`/non-retryable repair-needed.

**Expected-Key Walk**

First summary, bare row: passes. `expected=(serial,null)` on committed, then `(serial,key)` on promoted.

Re-summarize same title: predicate passes, but status handling is broken as Blocking #2.

Re-summarize changed title: v3 adopts observed key, so it does not move to the new slug. Predicate passes. That is coherent, but it means v3 has implicitly chosen slug-stable re-summarize despite listing non-concurrent title-change orphaning as out of scope.

Re-address after serial race: passes on retry with observed `(3,"003_alpha.md")`.

Re-address after slug race: passes on retry with observed `(7,"007_beta.md")`.

I did not find an expected-key reject/accept bug in those paths; the defects are in status truth, publication verification, and malformed address adoption.

**Coverage Gaps**

Missing from §8: contention/deadlock test for the new `FOR UPDATE`; lying/buggy `artifactIsNew=true`; same-key re-summarize with docVersion bump and crash before publish; final-byte verification after `put()`; malformed `observedSummaryMd`; and cleanup/behavior after `publish()` succeeds but promoted persist gets `PS003`.
