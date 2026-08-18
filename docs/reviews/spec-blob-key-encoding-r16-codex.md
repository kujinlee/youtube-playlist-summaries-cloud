# Adversarial review — cloud blob key encoding spec v18 — round 16 — Codex

Subject: working tree `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` v18.

## Blocking 1 — `serialize()` does not dominate writes to `models/<base>.json`

Evidence:

```ts
// docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1301-1310
**THE FIX — attach the requirement to the point that DOMINATES the writers, not to a writer.** Both
writers already funnel through one private function, and nothing else calls it (**enumerated over the
whole repo**: `lib/dig/companion-doc.ts:123` defines an unrelated `serialize` for a different type):

// lib/html-doc/model-store.ts:34 — the only path from an envelope to bytes
function serialize(envelope: ModelEnvelope): Buffer
// :52  writeModelEnvelope        → blobStore.put(…, serialize(envelope), …)
// :73  writeModelEnvelopeWithin  → const bytes = serialize(envelope)
```

```ts
// docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1316-1317
| **read** — `readModelEnvelope` | `ModelEnvelopeSchema` (unchanged) | `optional()` | The 7 legacy prod envelopes must still parse; §3.6.4's table has a legacy row for them |
| **write** — the parameter type of both writers, validated inside `serialize` | `ModelEnvelopeWriteSchema = ModelEnvelopeSchema.extend({ videoId: z.string().min(1) })` | **required** | No writer, present or future, can produce bytes without it |
```

But `reconcileCloudBase` writes `models/<newBase>.json` without `serialize()`:

```ts
// lib/cloud-sync/reconcile-serial.ts:95-99
async function paidKeysUnder(
  blob: BlobStore, p: Principal, video: Video, base: string,
): Promise<string[]> {
  const keys = [`${base}.md`, MODEL_KEY(base)];
```

```ts
// lib/cloud-sync/reconcile-serial.ts:116-118
function remap(key: string, oldBase: string, newBase: string): string | null {
  if (key === `${oldBase}.md`) return `${newBase}.md`;
  if (key === MODEL_KEY(oldBase)) return MODEL_KEY(newBase);
```

```ts
// lib/cloud-sync/reconcile-serial.ts:280-282
let copied = 0;
for (const { from, to } of plan) {
  const res = await cloud.blob.copy(cloud.p, from, to);
```

```ts
// lib/storage/blob-store.ts:155-156
try {
  await store.put(p, to, src.bytes, contentTypeForKey(to));
```

Failure scenario: a cloud row with `summaryMd = "007_old.md"` is base-reconciled to local `"003_new.md"`. The existing `models/007_old.json` is one of the seven legacy envelopes with no `videoId`, which v18 deliberately allows to read. `reconcileCloudBase` copies those raw bytes to `models/003_new.json` through `copyBlob` and `store.put`, never through `serialize()` and never through `ModelEnvelopeWriteSchema`. The new durable object therefore has no `videoId` after a write path that v18 says cannot produce one. A later `companionTransfer` sees the relocated legacy envelope as the `no videoId` branch and cannot enforce the paid-artifact ownership check the `videoId` credential was added for.

This also leaves the mutation plan under-specified:

```ts
// docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1506-1509
| Stop writing `videoId` in any one writer | 18j5 | PROVISIONAL |
| Route the serve path through a writer that bypasses `serialize` | **18j5** — the round-15 Blocking, reproduced as a mutation | PROVISIONAL |
| Make the sync ship copy the sender's envelope verbatim | **18j6** — the erasure | PROVISIONAL |
| Relax `ModelEnvelopeWriteSchema`'s `videoId` to `.optional()` | 18j5 — one edit, one place, and it must go red for **both** writers (v17's row named a parameter on one function, so it could not express this) | PROVISIONAL |
```

None of those mutations hits the raw relocation copy. `18j5` can go green while `copyBlob` still creates a `models/<base>.json` object without `videoId`.

Proposed fix: treat model relocation as a third model-write path, not as generic bytes. Either remove `MODEL_KEY(base)` from the generic `paidKeysUnder`/`copyBlob` path and add a model-specific relocation that `readModelEnvelope`s, stamps the cloud row's `videoId`, validates `ModelEnvelopeWriteSchema`, and writes through `serialize()`; or explicitly redesign the ownership credential so byte-copy remains valid. Add a behavior/mutation for "base relocation of a legacy no-`videoId` model rewrites the destination envelope with the row video id" or for the deliberately chosen alternative.

Classification: mechanism. Quote the repaired test: "Can a redesign remove it?" Yes. A shape where model ownership is enforced at every producer of a model object, or where the credential survives raw byte relocation by construction, dissolves this. The current shape still chooses a named serialization point that does not dominate the durable state.

Caused by v18's own fixes: yes. v18 moved the rule from `writeModelEnvelope` to `serialize()` and asserted dominance; the missed writer is `reconcileCloudBase`'s byte-copy path.

Armed falsifier: fires to REDESIGN. This is another fix-induced finding of the exact form "the derivation does not reach writer/method/caller N": `serialize()` does not reach `reconcileCloudBase`/`copyBlob`. Round 15 already had two instances of this shape. The honest conclusion is that this document is still choosing enforcement points by name instead of dominance, and a wider redesign is owed rather than a fourth repair.

## Medium 1 — `unservable-base` says "no caller change", but behavior 26d requires a manual-repair message

Evidence:

```md
<!-- docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:727-733 -->
> **`{ ok: false; reason: 'unservable-base'; key: string }`** — `key` matters, because the caller's
> generic tail already interpolates it (`sync-run.ts:735-757`: `` `…${rec.reason}${'key' in rec ? ` at ${rec.key}` : ''}` ``),
> so a variant carrying `key` produces a usable message with **no change to the caller**. Verified
> that a new variant works mechanically: generic throw → caught per-video at `:812` → no baseline →
> re-fires cleanly, not stuck.
```

```md
<!-- docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:735-738 -->
> **And it must name the manual repair, which behavior 26d did not require.** Behavior 26 demands
> that of the *adopt* error; this is the case an operator is **least** able to diagnose, because the
> offending name is a **local vault filename** while the error is reported against a **cloud** video.
> Give 26d the same clause.
```

```md
<!-- docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1468 -->
| 26d | **A base relocation onto an unservable vault name is refused IN MEMORY**: no blob is copied, the old base is **intact**, nothing is deleted, the result is `{ ok:false, reason:'unservable-base', key }`, **and the message names the manual repair** — the offending name is a *local vault filename* while the error is reported against a *cloud* video (round-14 B1, round-15 M3) | integration |
```

The current caller tail cannot satisfy that:

```ts
// lib/cloud-sync/sync-run.ts:754-756
throw new Error(rec.reason === 'target-occupied'
  ? `serial collision: ${id} needs serial ${rec.want} on cloud, already held by ${rec.heldBy}`
  : `base reconciliation failed for ${id}: ${rec.reason}${'key' in rec ? ` at ${rec.key}` : ''}`);
```

Failure scenario: `reconcileCloudBase` returns `{ ok:false, reason:'unservable-base', key:'003_bad.md' }`. The operator sees `base reconciliation failed for <id>: unservable-base at 003_bad.md`. That names the key, but it does not say this is a local vault filename or what manual repair is needed. Behavior 26d can only pass if either the caller dispatches this variant specially or `reconcileCloudBase` carries a full message, which contradicts "no change to the caller."

Proposed fix: choose one instruction. Prefer a special `unservable-base` branch in `sync-run.ts` that says the cloud video is blocked by the local vault filename and that the local file must be renamed to a servable single component before sync can relocate the base. Then keep 26d as written and delete the "no change to the caller" claim.

Classification: stale cross-reference. Quote the repaired test: "Can a redesign remove it?" No. The variant can be correct; the stale sentence is the claim that generic interpolation is enough after v18 added the manual-repair message requirement.

Caused by v18's own fixes: yes. v18 added the `unservable-base` variant and strengthened 26d's message requirement while retaining the older "generic tail, no caller change" text.

## Holds under attack

`videoDataPayload()` dominates the three Supabase adapter data-writing methods in the current module shape:

```ts
// lib/storage/supabase/supabase-metadata-store.ts:115-121
async upsertVideo(p: Principal, video: Video): Promise<void> {
  const id = await this.requirePlaylistId(p);
  const { error } = await this.client
    .from('videos')
    .update({ data: stripComputed(video) })
```

```ts
// lib/storage/supabase/supabase-metadata-store.ts:140-144
const { error } = await this.client.rpc('merge_video_data', {
  p_playlist_id: id,
  p_video_id: videoId,
  p_fields: stripComputed(fields),
```

```ts
// lib/storage/supabase/supabase-metadata-store.ts:158-160
const { error } = await this.client.rpc('merge_video_data_bulk', {
  p_playlist_id: id,
  p_patches: patches.map((x) => ({ video_id: x.videoId, fields: stripComputed(x.fields) })),
```

The generic `<T extends object>` signature does not prevent a runtime implementation from inspecting `summaryMd` and `artifacts` on all three payload shapes; it just means the implementation must cast or use an indexed view. I found no fourth SupabaseMetadataStore method writing arbitrary `videos.data`. The worker `persist_summary` RPC is outside the adapter, but v18 already keeps the mint guard outside the seam for the no-money-before-refusal placement.

CONVERGED status: no. The model-envelope dominance falsifier fired.

NOT CONVERGED
