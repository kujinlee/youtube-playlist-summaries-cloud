# Plan review round 3 — Codex — cloud blob key encoding (backlog #36)

Subject: `docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md` **v3** (commit `c8b5031`).
Model: gpt-5.5 via `scripts/codex-review.py --prompt-file`.

**Findings**

**Blocking, executable-blocker — Task 10 — the money guard test is knowingly impossible as written.**  
Plan evidence: [plan:1928](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1928) says:

```ts
const videoId = randomUUID();
// A title whose slug exceeds the 131-code-point servability bound is NOT reachable — slugify
// caps at 60 ...
await expect(handler(makeJob({ ... payload: makePayload({ title: 'x'.repeat(400) }) }), mockCtx))
  .rejects.toThrow(/servable/);
```

The same step then contradicts it at [plan:1943](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1943): “no `slugify` output can reach this branch” and “the implementer must construct a `baseName` the predicate rejects”.

Code evidence: [summary-handler.ts:96](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/summary-handler.ts:96) builds the only key from the title:

```ts
const baseName = `${padSerial(serial)}_${slugify(payload.title)}`;
```

Failure scenario: an engineer implements the guard literally, runs the stated integration test, and it still does not reject on `title: 'x'.repeat(400)` because `slugify` caps the slug at 60. They either cannot make Task 10 pass or they “fix” it by changing unrelated production seams. This is directly in the no-money-before-refusal path.

Proposed fix: replace the Step 1 snippet with one concrete executable test: either a unit test over `isServableSummaryKey(`${padSerial(n)}_${slugify(t)}.md`)`, or add an explicit test-only way to drive an unservable `baseName`. Do not leave both a fake test and a prose escape hatch.

**Blocking, executable-blocker — Task 12 — the four-cell unit tests still contain placeholder calls.**  
Plan evidence: [plan:2152](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:2152) through [plan:2173](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:2173) has all four arms as non-executable placeholders:

```ts
await reconcileCloudBase({ /* old: servable, new: unservable */ });
await reconcileCloudBase({ /* cloud: 128 ASCII + .md, local serial widens it */ });
await reconcileCloudBase({ /* old: unservable, new: servable */ });
await reconcileCloudBase({ /* local: serial but NO summaryMd; cloud: unservable */ });
```

Code evidence: [reconcile-serial.ts:166](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:166) requires a real five-field argument object:

```ts
export async function reconcileCloudBase(args: {
  cloud: CloudReplica;
  cloudIndex: Video[];
  localVideo: Video;
  cloudVideo: Video;
  inFlightJob: InFlightJobProbe;
}): Promise<SerialReconcileResult> {
```

Failure scenario: the engineer pastes the tests and gets type/runtime fixture failures, not the intended red test for missing variants. This repeats the prior “elided fixtures” class.

Proposed fix: replace the four placeholder calls with concrete `InMemoryBlobStore` + mocked `MetadataStore` fixtures for each row in the table. If 26d3 is unconstructible, choose the fallback fixture in the code block itself.

**Blocking, executable-blocker — Task 13 — additive protocol tests still contain comment-only calls on the paid-artifact path.**  
Plan evidence: [plan:2432](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:2432) through [plan:2450](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:2450):

```ts
await expect(copyAdditiveVideo(/* …same shape, mdBody 'newcomer' … */))
await expect(copyAdditiveVideo(/* …toBlob: absentOnReadBack(store)… */))
await expect(copyAdditiveVideo(/* …toBlob: store… */)).rejects.toThrow(/could not confirm/);
```

Code evidence: [sync-run.ts:221](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:221) takes six required runtime inputs:

```ts
async function copyAdditiveVideo(
  to: MetadataStore, toP: Principal, toBlob: BlobStore, playlistMeta: PlaylistMetadata,
  video: Video, mdBody: string | null,
```

Failure scenario: the “different bytes”, “absent read-back”, and “unreadable” tests do not execute the intended behavior. An engineer can complete Task 13 with the overwrite/refusal protocol under-tested, exactly where a wrong implementation can overwrite or orphan a paid summary.

Proposed fix: provide the full fixture builder and decorators in the snippet, or replace the snippet with quoted current code plus exact changes. No `/* … */` call sites in this section.

**High, executable-blocker — Task 8 — the integration fixture block is not pasteable despite claiming no argument-less calls.**  
Plan evidence: [plan:1529](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1529) imports from the wrong relative path for a file under `tests/integration/cloud-sync/`:

```ts
import { makeOwnerContext, prepareSyncCtx, seedCloudVideo, seedLocalVideoFull,
         type Ctx } from './helpers/cloud';
```

The helper actually lives at [cloud.ts:1](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/helpers/cloud.ts:1), so the import should be `../helpers/cloud`. The same block uses undeclared symbols including `SupabaseMetadataStore`, `SupabaseBlobStore`, `ARTIFACTS_BUCKET`, `ModelEnvelopeWrite`, `MODEL_FIXTURE`, `localVideoRecord`, `winner`, `loser`, `lv`, `cloudSide`, and `localSide`.

Failure scenario: implementing Task 8 literally fails before reaching the intended `videoId` ownership assertion. This is not polish; it is the r2 placeholder problem in a different form.

Proposed fix: make the Step 1 snippet a complete test file skeleton with imports, `beforeEach`, `ctx`, side builders, and `lv` setup, or downgrade it to quoted-current-code plus precise change text.

**Medium, would-be-nice — Task 4 — the executed full-sweep count is mislabeled.**  
Plan evidence: [plan:929](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:929) says “all four title forms — 3,479,131 iterations”. I reran the loop under Node 22.14.0: total loop iterations are 4,448,256; non-empty slug assertions are 3,479,131; skipped empty slugs are 969,125. The predicate had 0 violations.

Failure scenario: future reviewers chase a false count. It does not invalidate the behavior.

Proposed fix: change “iterations” to “non-empty slug assertions” and state the total loop count separately.

**Low, would-be-nice — Task 0 — one quoted-current line number is off by one.**  
Plan evidence: [plan:245](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:245) says `tests/integration/helpers/cloud.ts:132` is:

```ts
syncDeps(opts: { failCloudPromote?: boolean; failCloudModelPut?: boolean } = {}): SyncDeps {
```

Code evidence: that line is actually [cloud.ts:131](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/helpers/cloud.ts:131); [cloud.ts:132](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/helpers/cloud.ts:132) is:

```ts
const cloud = new SupabaseMetadataStore(userClient);
```

Proposed fix: change the reference to `:131`.

Checks I reran: `canonicallyEqualName` 4/4 passed; `isServableSummaryKey` listed cases, Bidi sweep, and full slug cross-derivation passed; local/in-memory `promoteIfAbsent` transcription passed fresh-temp contract cases; runner split has 0 `npx jest tests/integration/...` occurrences. No tracked files modified.

NOT CONVERGED
