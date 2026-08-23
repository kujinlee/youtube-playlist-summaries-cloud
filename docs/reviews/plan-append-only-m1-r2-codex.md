<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Blocking** — [docs/superpowers/plans/2026-08-22-m1-honest-card.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-22-m1-honest-card.md:92): the Consequences table says “Bytes DID land, no corrections anywhere” is “as before”, and Task 1 Step 7 says any Class-A/sync failure means the table is wrong. The table is already wrong.
Scenario: local has `mdCorrectionsHash = mdHash('')`, older `mdGeneratedAt`, body `LOCAL`; cloud worker publishes body `WORKER`, same doc major, no corrections. Before M1 cloud has `mdCorrectionsHash = null`, so `reconcileClassA` takes `lCur && !cCur` at [reconcile-class-a.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-class-a.ts:39) and returns `copyToCloud`. After M1 cloud has `mdCorrectionsHash = mdHash('')`, so both are current and the recency tiebreak at [reconcile-class-a.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-class-a.ts:49) can return `copyToLocal`.
Suggested fix: explicitly list this changed outcome, decide whether it is intended, add a focused `reconcileClassA` test for old-vs-new cloud signals, and remove/rewrite the Step 7 “no Class-A outcome changes” stop rule.

**Blocking** — [docs/superpowers/plans/2026-08-22-m1-honest-card.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-22-m1-honest-card.md:303): the read-back proves only a momentary blob state, not that the row being persisted will describe the final live body.
Scenario: worker promotes `WORKER`; read-back returns `WORKER`, so `published = true`; before the subsequent `persistSummary(..., 'promoted')`, sync `transferClassA` writes a different `LOCAL` body with `BlobStore.put` and updates the row. The worker’s final promoted persist then stamps `mdGeneratedAt`/`mdCorrectionsHash` for `WORKER` over a row whose live blob is now `LOCAL`. The row lock inside `persist_summary` cannot protect the prior blob read.
Suggested fix: either scope M1 honestly as a best-effort reduction that does not close concurrent writer races, or add a real fence/identity check tied to the row update. At minimum, add a test that interposes a blob+row writer between read-back and promoted persist.

**High** — [docs/superpowers/plans/2026-08-22-m1-honest-card.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-22-m1-honest-card.md:304): `mdHash(live) === mdHash(core.mdContent)` does not prove “its bytes became the live body.” `mdHash` canonicalizes CRLF/LF, trailing blank lines, and Unicode NFC at [content-hash.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/content-hash.ts:9).
Scenario: final key already contains `WORKER body\r\n`; worker stages `WORKER body\n`. `promote` discards the staged object under Supabase semantics, but `published` is true and the worker stamps a body it did not publish.
Suggested fix: if byte publication is the contract, compare `Buffer.equals(Buffer.from(core.mdContent, 'utf8'))`. If canonical equivalence is acceptable, change the goal/tests/comments from “bytes” to “canonical MD body” and account for the provenance lie explicitly.

**Medium** — [docs/superpowers/plans/2026-08-22-m1-honest-card.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-22-m1-honest-card.md:390): the read-back failure test can pass with half-broken stamping.
Scenario: implementation accidentally sets `mdCorrectionsHash: mdHash('')` on read-back failure but omits `mdGeneratedAt`. The Task 2 test only asserts `mdGeneratedAt` is absent at lines 396-398, so it passes while still corrupting the card’s corrections currency.
Suggested fix: assert both keys are absent in the read-back failure case, as the occupied-key test already does.

**Medium** — [docs/superpowers/plans/2026-08-22-m1-honest-card.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-22-m1-honest-card.md:303): `.catch(() => null)` makes the new storage read silently fail closed with no observable fault.
Scenario: Supabase `download` throws or returns an error for RLS/5xx/timeout; [SupabaseBlobStore.get](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:34) collapses returned errors to `null`, and the added catch collapses thrown errors too. The job completes promoted but unstamped, with no log/report/metric that the proof step failed.
Suggested fix: use `tryGet` or an explicit helper that records `absent` vs `unreadable` where possible; at least log/report read-back failure while still omitting stamps if that is the chosen behavior.

**Low** — [docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md:34): the measured `generation_id` command does not reproduce the stated value.
Ran command exactly: `grep -rli "generation_id" --exclude-dir=node_modules --exclude-dir=docs .`
Observed 8 paths, including `.remember/*`, `.next/*`, `.git/COMMIT_EDITMSG`, `.superpowers/*`, and two scripts. The row says zero references with “2 ratchet scripts + 1 contract test only.”
Suggested fix: either narrow the command to shipped source, or update the value to match the command.

**Checks**

Verified good:
- Schema line count command reproduced `4108 total`.
- Highest migration command reproduced `0025_settle_is_observable.sql`.
- Blob-addressing file-count command reproduced `40`.
- `video_summary_current` ranking is total as claimed: corrections currency, doc major, card `mdGeneratedAt`, `produced_at`, then unique `generation_id` at [04_artifacts.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:704).
- r17 really says the next test is migration, not round 18.
- `DEPENDS`/`ROOTS` cannot express “root gated by item”; the prose workaround should not break `depends_errors`.
- Task 3 append does not collide with existing `S()`/`CUR`.
- The Task 2 `readVideo → null` plus pre-seeded blob interleaving is reachable given [summary-handler.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/summary-handler.ts:84) reads before reserve/write.
- `InMemoryBlobStore.get` can reject on a real path when `failReads` is armed and `provesAbsence` is true at [in-memory-blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/testing/in-memory-blob-store.ts:109).

NOT VERIFIED:
- Full unit suite command in roadmap.
- Fly production release command.
- Proposed new Jest file, because it is not present as code yet.

NOT CONVERGED
