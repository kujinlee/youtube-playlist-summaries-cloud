<!-- codex-review: model=gpt-5.5 -->

**High**

1. [lib/cloud-sync/reconcile-serial.ts:261](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:261) + [lib/job-queue/summary-handler.ts:95](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/summary-handler.ts:95) race can re-diverge the row after A3 cleanup, orphaning paid dig/model blobs.

Concrete scenario:

Cloud row starts as `vidA: serialNumber=7, summaryMd="007_alpha.md"`, with paid `dig/007_alpha/120.r3.md` and `models/007_alpha.json`. Local has the same `vidA` as a bare slot/stub: `serialNumber=3`, no `summaryMd`.

A cloud worker already called `reserveVideoSlot` and computed `baseName="007_alpha"` from serial `7` at `summary-handler.ts:95-97`, but has not persisted yet. A3 then runs, `describeDivergence` synthesizes target `003_alpha` from the local serial, copies `007_alpha.*` and `dig/007_alpha/*` to `003_alpha.*`, updates cloud metadata to `serialNumber=3, summaryMd="003_alpha.md"`, verifies, and deletes the old `007_alpha` sources at [reconcile-serial.ts:296](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:296).

Then the worker continues with the stale `video` object containing `serialNumber: 7, summaryMd: "007_alpha.md"` at [summary-handler.ts:156](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/summary-handler.ts:156). `persist_summary` preserves the existing row’s `serialNumber` but re-applies the payload `summaryMd` (`supabase/migrations/0021_cloud_sync_signals.sql:116-137`). The final row becomes `serialNumber=3` beside `summaryMd/artifacts.summaryMd.key="007_alpha.md"`.

Actual loss: the paid dig/model blobs A3 preserved under `003_alpha` are now unreachable again, while cleanup has removed the original `dig/007_alpha/*` and `models/007_alpha.json`. If the worker crashes after the committed persist and before promote, the row also points at `007_alpha.md` with no final promoted blob.

Fix direction: A3 needs to fence against an in-flight summary writer or the worker persist must be conditional on the serial/base it reserved. At minimum, the pre-write check should compare more than `summaryMd`; it needs to detect `serialNumber` changes and stale worker writes must not be allowed to reapply an old `summaryMd` after A3 moved the base.

**Medium**

None found.

**Low**

None found.

**Checks Performed**

I re-read all four prior review docs, then checked the Round 5 changes around `claimVideoSlot`, `ensureReceiverSlot`, `describeDivergence`, `remap`, the plan-before-copy path, snapshot refresh, and the worker persist path.

A6a’s `findIndex` to `find` change does not appear to change behavior for a row present with `serialNumber: null`: both old and new shapes reach the legacy-fill branch and merge in a new serial instead of treating null as persisted.

`remap()` now fails closed for the reviewed key families, validates source and destination before copy, and rejects duplicate destinations before writing. I did not find a new unmapped real key shape or a new two-source-to-one-destination case beyond the covered tests.

I do not think M-R2-2’s local-serial/no-summary relocation is intrinsically wrong when the cloud row is quiescent: the subsequent copy hydrates local and both rows agree on the serial-encoded key. The High above is the missing concurrency condition: a bare local stub plus an in-flight cloud worker makes that relocation unsafe.
