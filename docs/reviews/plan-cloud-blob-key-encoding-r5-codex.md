<!-- codex-review: model=gpt-5.5 -->

**Findings**

Blocking — T11 — [docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:2510](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:2510)

Plan T6 adds a new required `BlobStore` member:

```ts
// lib/storage/blob-store.ts — on the BlobStore interface, beside `promote` at :73
  promoteIfAbsent(ref: StagedRef): Promise<void>;
```

But the new T11 decorator says it implements that post-T6 interface and omits the member:

```ts
class RecordingBlobStore implements BlobStore {
  ...
  promote(ref: StagedRef): Promise<void> { return this.inner.promote(ref); }
  deletePrefix(p: Principal, prefix: string) { return this.inner.deletePrefix(p, prefix); }
  list(p: Principal, prefix: string) { return this.inner.list(p, prefix); }
  copy(p: Principal, from: string, to: string): Promise<CopyResult> { return copyBlob(this, p, from, to); }
}
```

Failure scenario: execute tasks literally. T6 lands first and makes `BlobStore.promoteIfAbsent` required. Then T11 creates `adopt-guard.int.test.ts`; `npx tsc --noEmit` fails because `RecordingBlobStore` incorrectly implements `BlobStore`.

Proposed fix: add full delegation:

```ts
promoteIfAbsent(ref: StagedRef): Promise<void> { return this.inner.promoteIfAbsent(ref); }
```

Recording `tryGet` is not the problem for 26f: the guard is above `readMdBody`, so neither `get` nor `tryGet` should fire on the sender store.

High — T2 — [docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:731](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:731)

The plan’s prod guard is string-regex based:

```ts
if (!/^https?:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(url)) {
  throw new Error(`refusing to run against a non-local stack: ${url}`);
}
```

A valid non-local URL can pass it via URL userinfo:

```text
https://localhost:54321@project.supabase.co
```

Measured with Node 22.14.0: the regex returns `true`, but `new URL(...).hostname` is `project.supabase.co`.

The repo already has the safer host-exact helper:

```ts
const host = new URL(url).hostname;
return host === 'localhost' || host === '127.0.0.1';
```

at [lib/supabase/is-local-url.ts:7](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/supabase/is-local-url.ts:7).

Failure scenario: a malformed or userinfo-bearing Supabase URL points at a hosted project while beginning with `https://localhost:54321@...`; the guard passes and the integration test can delete/list using that configured backend.

Proposed fix: import and use `isLocalSupabaseUrl(url)`, or parse with `new URL(url).hostname` directly. Keep the absent-env throw.

Low — T0 — [docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:301](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-15-cloud-blob-key-encoding.md:301)

The elision count is wrong:

```ts
localBlob: localBlobStore,
// …5 lines elided (:141-145): `cloudBlob,`, a 2-line comment, `inFlightJob:`,
```

Actual code is:

```ts
local: localMetadataStore,
cloud,
localBlob: localBlobStore,
cloudBlob,
// The REAL probe...
// (status filtering...)
inFlightJob: supabaseInFlightJobProbe(userClient, ctx.userId),
dataRoots: [ctx.tempDataRoot],
ownerId: userId,
```

at [tests/integration/helpers/cloud.ts:136](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/helpers/cloud.ts:136). After `localBlob`, the omitted block is six lines, `:140-145`, not five lines `:141-145`. The claim that `localBlob` is the third key is correct.

Failure scenario: not a compile failure, but the quote is explicitly there to prevent another mistaken append/substitution; the inaccurate count reintroduces the “verbatim-but-not” class this fix was meant to close.

Proposed fix: change it to:

```ts
// …6 lines elided (:140-145): `cloudBlob,`, a 2-line comment, `inFlightJob:`,
//   `dataRoots: [ctx.tempDataRoot],` and `ownerId: userId,`
```

NOT CONVERGED
