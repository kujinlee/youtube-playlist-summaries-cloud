<!-- codex-review: model=gpt-5.5 -->

**Findings**

Blocking — Task 8 — [plan line 1711](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1711)

Plan test code:

```ts
await seedEnvelope(cloud, base, undefined as unknown as string,
  { sourceMd: 'wrong.md', sourceMdHash: 'stale' });
```

But the same plan makes writer-side `videoId` required:

```ts
export const ModelEnvelopeWriteSchema = ModelEnvelopeSchema.extend({ videoId: z.string().min(1) });
function serialize(envelope: ModelEnvelopeWrite): Buffer {
  ModelEnvelopeWriteSchema.parse(envelope);
```

Failure scenario: after Task 7, this “legacy envelope” cannot be seeded through `writeModelEnvelope`; Zod rejects `videoId: undefined` before writing. An engineer pasting the Task 8 file gets a failing setup, not behavior 18j4.

Proposed fix: seed the legacy receiver envelope as raw JSON bytes through `side.blob.put(side.p, MODEL_KEY(base), Buffer.from(...), 'application/json')`, omitting the `videoId` property entirely. Keep `writeModelEnvelope` for non-legacy envelopes.

Blocking — Task 12 — [plan line 2649](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:2649)

Plan says the integration test file is new:

```md
`tests/integration/cloud-sync/adopt-guard.int.test.ts` — INTEGRATION
```

but the provided block is only:

```ts
it('behavior 26d2 — the SKIP is visible on run 1 AND run 2, and copyToLocal hydrates the paid summary', async () => {
  await prepareSyncCtx(ctx);
  await seedLocalVideoFull(ctx, { position: 3, summaryMd: null });
  await seedCloudVideo(ctx, { position: 7, summaryMd: EVIL, mdBody: '# paid\n' });
  const first = await runSync(ctx.syncDeps(), { playlistKey: ctx.playlistKey });
  const second = await runSync(ctx.syncDeps(), { playlistKey: ctx.playlistKey });
  ...
  expect(await localBlobBytes(ctx, EVIL)).not.toBeNull();
});
```

`tests/integration/cloud-sync/adopt-guard.int.test.ts` does not exist, and this block does not declare or import `ctx`, `EVIL`, `prepareSyncCtx`, `seedLocalVideoFull`, `seedCloudVideo`, `runSync`, or `localBlobBytes`.

Failure scenario: an engineer creates the named file and pastes the block; TypeScript/Jest fails before executing the behavior.

Proposed fix: provide the whole file, including imports from `@/tests/integration/helpers/cloud`, `runSync`, `makeOwnerContext`, cleanup, `const EVIL = ...`, and `const ctx = await makeOwnerContext()` inside the test.

Medium — Task 7 rollout count — [plan line 1401](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:1401)

Plan states:

```md
| total call sites | 41 | 43 | **42** |
| test | 38 | 39 | **39** |
```

Under the stated rule:

```md
matching `writeModelEnvelope(` / `writeModelEnvelopeWithin(`, skipping comment and import lines, and
subtracting the two declarations
```

I count **41** total: 3 production + 38 test/e2e. The false extra is the known test-title shape, not a call.

Proposed fix: change line 1401 to `41`, line 1403 to `38`, and line 1409 “42” to “41”. The review matrix later says the correct thing at line 3325.

Low — Task 4 sweep noun still repeated — [plan line 3326](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:3326)

The main Task 4 wording is fixed:

```md
4,448,256 loop iterations → 3,479,131 NON-EMPTY SLUG ASSERTIONS
```

but the wrong noun still appears later:

```md
T4's behavior 27 is now **stride 1** (3,479,131 iterations, executed)
```

and again at line 3359:

```md
FIXED — stride 1, executed, 3,479,131 iterations
```

Proposed fix: replace both with `3,479,131 non-empty slug assertions`.

Task 0 line reference is corrected: `tests/integration/helpers/cloud.ts:131` is the `syncDeps(...)` declaration.

Task 10 and Task 13’s full test blocks have resolving import paths and bound free identifiers under their stated prerequisite tasks, and their assertions bite the intended mutations.

NOT CONVERGED
