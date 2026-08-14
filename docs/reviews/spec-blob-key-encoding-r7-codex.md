<!-- codex-review: model=gpt-5.5 -->

**Blocking — v7 does not name the branded seam, and the current write seams still accept bare `string`**

Evidence: [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:287) says:

```md
The summary write path takes `CloudSummaryKey`, not `string`.
```

but does not name the signature. The existing blob seam cannot simply be branded, because it writes non-summary artifacts too. [BlobStore](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/blob-store.ts:68) is generic:

```ts
put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void>;
```

and:

```ts
putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef>;
```

[copy](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/blob-store.ts:45) is also generic:

```ts
copy(p: Principal, from: string, to: string): Promise<CopyResult>;
```

That is necessary for models, PDFs, slides, HTML, and dig blobs. But if the brand is not placed somewhere narrower, a fifth summary writer still compiles. The exported `writeArtifact` helper is already exactly that latent fifth entrance. [consistency.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/consistency.ts:17) accepts:

```ts
kind: ArtifactKind;
key: string;
```

then writes:

```ts
const ref = await opts.blob.putStaged(opts.principal, opts.key, opts.bytes, opts.contentType);
```

and advertises:

```ts
artifacts: { [opts.kind]: { key: opts.key, status: 'promoted' } },
```

Metadata writes also still accept bare strings through [MetadataStore.updateVideoFields](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/metadata-store.ts:46):

```ts
updateVideoFields(p: Principal, id: string, fields: Partial<Video>): Promise<void>;
```

while [Video.summaryMd](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/types/index.ts:56) is:

```ts
summaryMd: z.string().nullable(),
```

I ran a TypeScript probe. `putSummary(key: CloudSummaryKey)` rejects a bare `string`; `putStagedGeneric(key: string)` and `updateVideoFields({ summaryMd: bare })` compile. The brand works only at signatures that explicitly require it.

Failure scenario: a future summary write calls `writeArtifact({ kind: 'summaryMd', key: video.summaryMd, ... })` with an adopted unservable key such as `003_my summary.md`. `tsc` accepts it today if `key` remains `string`; the blob is written through the encoded seam and metadata advertises `promoted`. Serve then rejects the key at [serve-summary-core.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-summary-core.ts:61):

```ts
assertCloudSummaryMdKey(mdKey);
```

Proposed fix: do not brand `BlobStore.put` globally. Add a summary-specific seam and name it in the spec:

```ts
putSummaryMd(..., key: CloudSummaryKey, ...): Promise<void>
putStagedSummaryMd(..., key: CloudSummaryKey, ...): Promise<StagedRef>
writePromotedSummaryMetadata(..., key: CloudSummaryKey): Promise<void>
```

or split/overload `writeArtifact` so `kind: 'summaryMd'` requires `CloudSummaryKey` and other artifact kinds keep `string`. Also require `reconcileCloudBase` to mint/adopt the branded summary target before the plan, then pass the branded value into both the MD copy and the metadata patch.

**Medium — entrance 4 is “adopt/refuse”, but v7 still understates the permanent-sync subclass**

Evidence: [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:296) says:

```md
| 4 | Base reconciliation | `reconcile-serial.ts:282`, `:293` | `baseOf(localVideo.summaryMd)` | illegal — refuse |
```

That is the right context. It is not minting; it is remapping cloud to local’s already-chosen key. [reconcile-serial.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:151) derives:

```ts
const to = localVideo.summaryMd
  ? baseOf(localVideo.summaryMd)
  : baseOf(applySerial(cloudVideo.summaryMd, localVideo.serialNumber));
```

and later advertises:

```ts
summaryMd: `${newBase}.md`,
artifacts: { summaryMd: { key: `${newBase}.md`, status: 'promoted' } },
```

But [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:304) also says:

```md
There an unservable key is a genuine refusal — `NonRetryableError`, a per-video entry in `report.errors`, no baseline advanced — which is the loud failure master already produces, preserved deliberately.
```

That is false for keys Storage already accepts but serve rejects: spaces, `(`, `)`, `+`, `=`, and over-128 guard failures. v7 itself notes Storage accepts those at [spec §4](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:345):

```md
Storage accepts space, `(`, `)`, `+` and `=`, which `SAFE` excludes.
```

Failure scenario: a vault-adopted local video has `summaryMd = "003_my summary.md"`. Base reconciliation must refuse, because repairing to `${padSerial}_${videoId}.md` would make local and cloud disagree. But this is not “same loud failure master already produces”; master can store that object and then serve fails later. v7 turns it into a permanent per-video sync refusal until the user renames the vault file.

Proposed fix: keep adopt/refuse for entrance 4, but state the remediation explicitly: the sync report must identify the local filename and say the vault file must be renamed to a servable summary key. Do not claim this preserves master behavior for the space/overlength subclass.

**Medium — the escape-hatch script does not close the actual TypeScript escape hatches**

Evidence: [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:314) says:

```md
`scripts/check-key-brand.py` FAILS IF a cast to `CloudSummaryKey` appears outside
`toCloudSummaryKey`'s own module.
```

That only catches the literal cast. It does not catch `any`, `unknown` double-casts, `JSON.parse` typed as branded, a zod schema returning `CloudSummaryKey`, or a DB read wrapper declared to return branded keys. This repo already uses `any` around summary metadata. [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:299):

```ts
const art = (rec as any).artifacts?.summaryMd;
```

and [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:432):

```ts
await loser.store.updateVideoFields(loser.p, videoId, completeTuple as Partial<Video>);
```

Failure scenario: a DB helper returns `any`, and a new writer calls `putSummaryMd(row.data.summaryMd, ...)`. If the expression is `any`, TypeScript accepts it as `CloudSummaryKey` without an `as CloudSummaryKey` token, so `check-key-brand.py` passes.

Proposed fix: keep the cast check, but do not describe it as closing the hatch. Add a type test with `any`/`unknown` inputs for the approved summary seams, and add a grep/check rule for value-producing `CloudSummaryKey` annotations outside the factory. Legitimate external uses should be parameter types only, not parsed/read values.

**Medium — Round-6 M1 still stands: collision guard ordering is not pinned**

Evidence: [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:205) gives only:

```ts
const occupied = await to.blob.tryGet(toP, key);
if (occupied.ok) throw new Error(`key collision: ${key} already held`);
if (!occupied.ok && occupied.reason === 'unreadable') throw occupied.cause;
```

The current additive flow claims the receiver slot at [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:240):

```ts
const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
```

before the blob write at [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:263):

```ts
const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
```

Failure scenario: if the new `tryGet` collision guard is implemented after `ensureReceiverSlot`, a local APFS alias or unreadable receiver blob throws after a bare receiver row exists. The next run can classify the video as two-sided and bypass the intended additive pre-write refusal.

Proposed fix: specify the exact insertion point: after the `video.summaryMd && mdBody == null` guard and before `ensureReceiverSlot(...)`. Also fix the mutation text at [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:433), which says:

```md
The additive guard consults index rows instead of `toBlob.exists`
```

It should be `toBlob.tryGet`, not `exists`.

**Medium — Round-6 M2 still stands: prefix rule contradicts behavior 12**

Evidence: [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:155) says:

```md
**A prefix must end on a segment boundary.** `list`/`deletePrefix` throw otherwise
```

but [behavior 12](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:438) still expects the no-slash form to work through the “encode empty segments” mutation:

```md
Encode empty segments | 11 and 12
```

Round 6 quoted the explicit behavior as:

```md
`list(p, 'dig/{base}/')` and `list(p, 'dig/{base}')` return the same set
```

The contradiction remains in substance: a rule that requires a segment boundary should reject `dig/{base}` unless the implementable predicate treats a complete final segment as a boundary. The production callers use `dig/${base}/`, so this is bounded, but the spec still gives two incompatible implementation targets.

Proposed fix: choose one rule. The simplest enforceable rule is `prefix === '' || prefix.endsWith('/')`; then delete the no-slash equivalence behavior.

**Checked**

The brand itself is a real nominal constraint when the signature is explicit. My `tsc --strict --noEmit` probe rejected a bare `string` passed to `putSummary(key: CloudSummaryKey)` and accepted the same bare string through generic `string` seams. So the mechanism is viable; v7 has not yet specified the load-bearing seam tightly enough.

NOT CONVERGED.
