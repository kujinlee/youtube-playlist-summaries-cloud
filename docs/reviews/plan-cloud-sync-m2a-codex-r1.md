# Plan Review: Stage 3 Cloud Sync M2a

## Blocking

### Task 5 / Task 12: Class-A `mdHash` is computed from the `summaryMd` filename, not the MD body

Failure scenario: local has `summaryMd: "001_title.md"` containing body `# A\n`, cloud has `summaryMd: "001_title.md"` containing body `# B\n`. Task 5's proposed `deriveClassASignals(video)` returns `mdHash(video.summaryMd)` (plan: `docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:784-792`), so both replicas hash the string `"001_title.md"` and Class A falsely skips or treats stale/current decisions against a filename digest. The spec contract says `mdHash` is MD-body-only bytes normalized and hashed, not metadata or human fields (`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:137-141`). Current code confirms `summaryMd` is a blob/file key, not markdown content: ingestion writes MD bytes to the blob at `baseName.md` and stores only the filename on the video record (`lib/pipeline.ts:56-57`, `lib/pipeline.ts:264-266`); the model generator also treats it as provenance filename (`lib/html-doc/generate.ts:48-51`).

Specific fix: do not let `deriveClassASignals(video)` compute `mdHash` from `Video` alone. Change the plan so Task 5 derives only record-level signals, and Task 12 reads the MD blob via `BlobStore.get(principal, video.summaryMd)` and computes `mdHash(mdBytes.toString('utf8'))`, then passes that into Class A. Add a unit/integration test where local and cloud use the same `summaryMd` key with different MD bodies and assert Class A does not skip.

### Task 4: Regenerate applies corrections but never stamps `mdGeneratedAt` / `mdCorrectionsHash`

Failure scenario: user enters corrections, the regenerate route saves `corrections`, calls Gemini to apply them, writes the corrected MD file, and updates only `tldr`, `takeaways`, and `summaryHtml`. The corrected MD still carries the old or absent `mdCorrectionsHash`, so a later sync classifies the corrected MD as stale versus the reconciled corrections and may keep/report the wrong Class-A state. The plan explicitly leaves this conditional: "If `pipeline.ts` has no `corrections` in scope... The regenerate route... wire that in the same task if the route builds the persisted record, else leave..." (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:666-677`). Current source shows the route does not build a full persisted record; it directly writes the corrected MD and then calls `updateVideoFields` without `mdGeneratedAt` or `mdCorrectionsHash` (`app/api/videos/[id]/regenerate/route.ts:51-71`). The spec requires MD generation/fix paths to stamp `mdGeneratedAt` and `mdCorrectionsHash` (`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:127-135`, `docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:227-229`).

Specific fix: Task 4 must explicitly modify `app/api/videos/[id]/regenerate/route.ts`. After a successful corrected MD write, update the video with `mdGeneratedAt: new Date().toISOString()`, `mdCorrectionsHash: mdHash(trimmedCorrections ?? '')`, and any current `docVersion` policy in the same metadata update as `tldr` / `takeaways` / `summaryHtml: null`. Add a test that posts corrections, reads the video, and verifies the hash equals `mdHash(corrections)`.

### Task 7: `mdHash` equality still bypasses corrections-currency and format rows

Failure scenario 1: local and cloud MD bodies are byte-identical, local has `mdCorrectionsHash: OLD`, cloud has `mdCorrectionsHash: CUR`, and reconciled corrections hash is `CUR`. The plan's implementation computes `lCur`/`cCur`, then immediately returns `skip` when `local.mdHash === cloud.mdHash` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1072-1078`). That leaves local with stale Class-A currency metadata. The spec says corrections-currency is evaluated first and "one MD corrections-current, the other corrections-stale" means the current side wins (`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:150-155`).

Failure scenario 2: local and cloud MD bodies are byte-identical and both stale, but local `docVersionMajor` is 2 and cloud is 3. The plan skips before checking format (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1075-1089`), even though the spec only allows the equal-hash skip for both current, or both stale-and-format-equal (`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:154-158`).

Specific fix: reorder the Task 7 algorithm and tests. After presence checks, evaluate one-current-vs-stale before any equal-hash skip. For equal MD hashes, skip only when both current, or both stale and `docVersionMajor` is equal; otherwise copy the winning complete Class-A tuple/signals so metadata converges, and still set `needsRegen` when both stale.

## High

### Task 3: Adding defaulted RPC parameters with `create or replace` leaves old RPC overloads in place

Failure scenario: migration 0021 creates `update_video_annotations(uuid,text,jsonb,text[],timestamptz default now())` and `merge_video_data(uuid,text,jsonb,timestamptz default now())` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:422-465`). Current deployed signatures are four-arg `update_video_annotations` (`supabase/migrations/0016_update_video_annotations.sql:13-15`) and three-arg `merge_video_data` (`supabase/migrations/0007_storage_and_rpcs.sql:81-82`). In Postgres, changing input arguments creates a new overload, not a replacement of the old signature. Existing app calls or store calls that omit/serialize-away `p_edited_at` can continue hitting the old function, which still drops `corrections` and stamps no `annotationsEditedAt` (`supabase/migrations/0016_update_video_annotations.sql:17-25`).

Specific fix: in migration 0021, explicitly `drop function update_video_annotations(uuid, text, jsonb, text[])` and `drop function merge_video_data(uuid, text, jsonb)` before creating the new defaulted signatures, then grant only the new signatures. Add an integration test that calls each RPC without `p_edited_at` and verifies the new defaulted function stamps correctly.

### Task 8 / missing writer task: `sourceMdHash` is never written into new model envelopes

Failure scenario: sync transfers a freshly generated MD with a freshly generated model companion. Because no task updates `writeModelEnvelope` callers to include `sourceMdHash`, `decideCompanion` sees the sender envelope as legacy and deletes the receiver's model blob. The next owner serve has to regenerate the model, which is the charged path the spec intended to avoid when a valid companion exists. The plan adds the optional schema field in Task 2 (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:229-244`) and compares it in Task 8 (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1121-1178`), but no task stamps it. Current model writers omit it (`lib/html-doc/generate.ts:49-55`; the same pattern exists in serve-time generation found by `writeModelEnvelope` call sites).

Specific fix: add a Task 4 or Task 8 step to compute `sourceMdHash: mdHash(md)` in every summary-model writer after reading the source MD body. Add tests that `runHtmlDoc` / owner serve write an envelope whose `sourceMdHash` equals the MD-body hash, and that sync ships that companion instead of deleting it.

### Task 10: File token store does not implement the promised parent-directory fail-closed checks

Failure scenario: `~/.config/youtube-playlist-summaries` is group/world writable, or owned by another user. The planned implementation writes and reads a mode-600 token file but never stats the parent directory (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1426-1444`), despite the interface promising a "parent-dir + broad-perms check" (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1341-1348`). A local attacker with directory write permission can replace or remove the token file and capture the refresh token lifecycle. The spec requires file fallback to fail closed on broad parent permissions (`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:231-235`).

Specific fix: before every read and write, `stat(path.dirname(file))`, require it is owned by the current uid where available, and reject group/other writable modes. Create the directory with restrictive mode and chmod it to `0700`. Add tests for broad parent directory permissions, not just broad token-file permissions.

## Medium

### Task 12: Core orchestration is a placeholder where the plan needs executable detail

Failure scenario: a fresh engineer implements the skeleton literally enough to pass the three Task 12 tests but misses baseline-aware deletes, complete Class-A tuple verification, or companion deletion/reporting. The task body says "`skeleton — implementer fills the transfer/atomic details`" and leaves union enumeration, per-video writes, `atomicTransfer`, and baseline construction as comments (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1677-1728`). It then says "Fill in" the money-safe additive branch and atomic transfer (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1734-1735`). The spec's crash-safety contract is precise: stage, verify, promote, finalize the complete tuple, and only then advance the manifest (`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:231-247`). Current storage plumbing has a two-step metadata status update around promotion (`lib/storage/supabase/consistency.ts:15-41`) and worker persistence has a separate `persist_summary` RPC wrapper (`lib/storage/worker-persistence.ts:16-27`), so the plan must say exactly how sync combines blob promotion with the complete Class-A record write.

Specific fix: replace the Task 12 skeleton with concrete helper contracts: `readMdBody`, `copyAdditiveVideo`, `transferClassA`, `verifyReceiverTuple`, `buildBaselineAfterWrites`, and exact metadata fields written for local vs cloud. Include the baseline-aware delete decision before additive create, and add Task 12 tests for no manifest advance unless `mdHash`, `mdCorrectionsHash`, `docVersion`, artifact status, and carried scalars all verify.

### Task 3: `archived`-only writes create an empty `annotationsEditedAt` object

Failure scenario: a user toggles Archive only. The spec says `archived` is replica-local and "an `archived`-only write restamps nothing" (`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:218-223`). The proposed SQL always wraps the row in `jsonb_set(..., '{annotationsEditedAt}', coalesce(...) || v_stamp, true)` even when `v_stamp = '{}'` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:448-454`). That mutates the row by adding `annotationsEditedAt: {}` for an archive-only write, which is not a timestamp stamp but is still unnecessary sync-signal churn.

Specific fix: make the update conditional: if `v_stamp = '{}'::jsonb`, use `(data || v_set) - v_clear` with no `jsonb_set`; otherwise set/merge `annotationsEditedAt`. Add an archived-only assertion that `row.annotationsEditedAt` remains absent.

## Low

### Task 2: `mdHash` appears in the Task 12 atomic tuple but is not part of `VideoSchema`

Failure scenario: an implementer follows Task 12 and writes `mdHash` into the receiver record as part of the "complete tuple" (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1734`), but Task 2 does not add `mdHash` to `VideoSchema` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:213-227`) and the current schema has no such field (`types/index.ts:47-86`). Depending on parse/write paths, this can either be stripped, retained as an undocumented JSON key, or confuse manifest-vs-record responsibilities.

Specific fix: clarify that `mdHash` is computed from the MD body and stored in the manifest baseline only, unless the spec intentionally wants a persisted video field. If persisted, add it explicitly to `VideoSchema`, `persist_summary`, and local writers; otherwise remove `mdHash` from the Task 12 record-write tuple and keep it in verification/baseline only.

## Verdict

NOT CONVERGED
