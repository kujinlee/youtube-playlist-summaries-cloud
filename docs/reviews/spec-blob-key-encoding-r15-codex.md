# Round 15 Codex review — cloud blob key encoding v17

Subject: live working tree `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` v17.

## Findings

### Blocking — `writeModelEnvelope` is not the model-write seam; serve uses `writeModelEnvelopeWithin`

Evidence:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1120-1124`

```md
**`writeModelEnvelope` requires `videoId`** — not the schema field (optional, for legacy reads) but
the **writer's parameter**. Then no writer can omit it, and the count stops mattering. `generate.ts`
has the video in scope; `serve-doc.ts` has it as an explicit param; the sync ship must **stamp the
receiver's `videoId`** rather than copy the sender's envelope verbatim
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1228`

```md
| 18j5 | **Every** envelope writer writes `videoId` — `serve-doc.ts`, `generate.ts`, and the sync ship — because `writeModelEnvelope` **requires** the parameter (round-14 H1 / Codex M1) | unit |
```

But the serve writer is not `writeModelEnvelope`; it is the bounded writer:

`lib/html-doc/model-store.ts:46-52`

```ts
export async function writeModelEnvelope(
  principal: Principal,
  base: string,
  envelope: ModelEnvelope,
  blobStore: BlobStore = localBlobStore,
): Promise<void> {
  await blobStore.put(principal, MODEL_KEY(base), serialize(envelope), 'application/json');
}
```

`lib/html-doc/model-store.ts:66-73`

```ts
export async function writeModelEnvelopeWithin(
  timeoutMs: PutBudget,
  principal: Principal,
  base: string,
  envelope: ModelEnvelope,
  blobStore: BlobStore = localBlobStore,
): Promise<void> {
  const bytes = serialize(envelope);          // validates first — fail loud before any write
```

`lib/html-doc/serve-doc.ts:174-182`

```ts
await writeModelEnvelopeWithin(SERVE_PUT_TIMEOUT_MS, principal, base, {
  sourceMd: parsed.sourceMd ?? `${base}.md`,
  generatedAt: new Date().toISOString(),
  sourceSections: titles,
  generatorVersion: GENERATOR_VERSION,
  model,
  // Hash the MD BODY, not the key — see the `mdBody` param doc above (§4.2).
  ...(mdBody !== undefined ? { sourceMdHash: mdHash(mdBody) } : {}),
}, blobStore);
```

Concrete failure scenario: implement v17 literally by making only `writeModelEnvelope(...)` require a `videoId`. The owner serve path keeps writing new cloud envelopes without `videoId`, so v17's self-healing claim is false: a re-serve does not close the legacy branch. Later, `companionTransfer` sees the receiver envelope as `no videoId` and proceeds under the legacy rule instead of detecting ownership. That can overwrite or delete a paid model envelope that should have been protected by the new credential.

Proposed fix: put the requirement below both public write helpers, not on one helper name. Either make `serialize`/a new `writeModelEnvelopeBytes` require `videoId`, or give both `writeModelEnvelope` and `writeModelEnvelopeWithin` a required `videoId` parameter and stamp it before serialization. Behavior 18j5 must assert the bounded serve writer too.

Classification: `mechanism`; caused by v17's own fix.

Test discriminator: a redesign can remove this by making model-envelope writes have one lower seam; the current derivation names a function that is not the full seam.

### Medium — the Supabase adapter seam excludes `bulkUpdateVideoFields`

Evidence:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:620-622`

```md
**In the Supabase adapter, refuse any patch that sets `summaryMd` or `artifacts.summaryMd.status =
'promoted'` to a key failing `isServableSummaryKey`.** Then **the entrance count stops mattering** —
which is the only property that has ever survived contact with this codebase.
```

`lib/storage/metadata-store.ts:45-47`

```ts
upsertVideo(p: Principal, video: Video): Promise<void>;
updateVideoFields(p: Principal, id: string, fields: Partial<Video>): Promise<void>;
bulkUpdateVideoFields(p: Principal, patches: { videoId: string; fields: Partial<Video> }[]): Promise<void>;
```

`lib/storage/supabase/supabase-metadata-store.ts:153-162`

```ts
async bulkUpdateVideoFields(
  p: Principal,
  patches: { videoId: string; fields: Partial<Video> }[],
): Promise<void> {
  const id = await this.requirePlaylistId(p);
  const { error } = await this.client.rpc('merge_video_data_bulk', {
    p_playlist_id: id,
    p_patches: patches.map((x) => ({ video_id: x.videoId, fields: stripComputed(x.fields) })),
  });
  if (error) throw error;
}
```

Current production callers are benign:

`lib/pipeline.ts:332-339`

```ts
fields: {
  playlistIndex: positionMap.get(v.id) ?? v.playlistIndex,
  videoPublishedAt: v.videoPublishedAt ?? publishedMap.get(v.id),
  addedToPlaylistAt: v.addedToPlaylistAt ?? addedMap.get(v.id),
},
}));
await store.bulkUpdateVideoFields(principal, patches);
```

`lib/serial-migrate-exec.ts:14-17`

```ts
await store.bulkUpdateVideoFields(
  principal,
  assignments.map((a) => ({ videoId: a.id, fields: { serialNumber: a.serial } })),
);
```

Concrete failure scenario: the next metadata batch writer uses the existing `MetadataStore.bulkUpdateVideoFields` method to patch `{ summaryMd, artifacts: { summaryMd: { key, status: 'promoted' } } }`. That write reaches `merge_video_data_bulk` without the adapter refusal if v17 only guards `upsertVideo` and `updateVideoFields`. The design's core claim, "the entrance count stops mattering", is false for an already exposed adapter method.

Proposed fix: define the seam as "every Supabase adapter method that writes `videos.data`", and require the same refusal in `bulkUpdateVideoFields` for every patch entry. Add a behavior or mutation row that fails if `bulkUpdateVideoFields` can advertise an unservable promoted summary.

Classification: `mechanism`; caused by v17's own fix.

Test discriminator: a redesign can remove this by moving validation to a single lower merge path or SQL domain check; adapter methods are still enumerated.

### Medium — metadata refusal outcomes are still underspecified for the three asserted callers

Evidence:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:1253`

```md
| 26c | **The Supabase adapter refuses** any patch setting `summaryMd` / `status:'promoted'` to a non-servable key — asserted through **each** of `copyAdditiveVideo`, `transferClassA` and `reconcileCloudBase`, and stated with **no claim about how many entrances exist** | integration |
```

`lib/cloud-sync/sync-run.ts:263-286`

```ts
const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
...
await toBlob.promote(ref);
...
sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
...
await to.upsertVideo(toP, sanitized as Video);
```

`lib/cloud-sync/sync-run.ts:394-432`

```ts
await loser.blob.put(loser.p, key, staged, 'text/markdown');
...
summaryMd: key,
...
artifacts: { summaryMd: { key, status: 'promoted' } },
};
await loser.store.updateVideoFields(loser.p, videoId, completeTuple as Partial<Video>);
```

`lib/cloud-sync/sync-run.ts:811-813`

```ts
await writeVideoBaseline(dataRoot, key, id, buildBaseline(winnerSignals, winnerMdHash, merges, base));
} catch (e: any) {
  report.errors.push({ videoId: id, message: e?.message ?? String(e) }); // Behaviors #11/#13
}
```

`lib/cloud-sync/reconcile-serial.ts:324-329`

```ts
await cloud.store.updateVideoFields(cloud.p, cloudVideo.id, patch as Partial<Video>);
} catch (cause) {
  // The copies are durable and harmless — the row still points at the old base, which is still
  // intact. A re-run resumes via the identical-bytes path rather than deadlocking.
  return { ok: false, reason: 'metadata-failed', cause };
}
```

Concrete failure scenario: if the new adapter refusal fires in `transferClassA`, the loser blob has already been overwritten at `key`, then `updateVideoFields` throws, the per-video catch records an error, and `writeVideoBaseline` is skipped. For `copyAdditiveVideo`, the promoted blob and claimed receiver slot may already exist before `upsertVideo` refuses; the caller catches and skips baseline. For `reconcileCloudBase`, the current function would return `metadata-failed` after copies, not the in-memory refusal promised by 26d, unless the separate in-memory guard catches it earlier. v17 says "refuse" but only names the `companionTransfer` refusal outcome; 26c does not say what each caller leaves behind or whether the next run retries cleanly.

Proposed fix: add an outcome table for the three 26c callers. It should state, for each caller, whether baseline advances, what durable blob/row state may already exist, and whether the next run re-enters the same refusal or a different branch. Tests should assert the post-run state, not just that an error was reported.

Classification: `branch-coverage`; caused by v17's own fix.

Test discriminator: a redesign cannot remove the need to state the branches of a throwing refusal after earlier durable writes; it can only choose a different lower mechanism with its own outcomes.

### Low — the Bidi fix still enumerates while the text claims a property derivation

Evidence:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:272-274`

```ts
if (/[\x00-\x1f\x7f-\x9f]/.test(s)) return false;         // C0 + DEL + C1 (round-12 L1)
if (/%2f|%5c/i.test(s)) return false;                    // percent-encoded separators
if (/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/.test(s)) return false;  // all 12 Bidi_Control
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:372-375`

```md
> **⚠ Round-14 L1 — v9's class covered 9 of the 12 `Bidi_Control` code points.** `U+061C`
> (ARABIC LETTER MARK), `U+200E` (LRM) and `U+200F` (RLM) passed. The class is now the full property,
> not a hand-picked range — the same *"enumerate vs derive"* lesson as the homoglyph denylist, arriving
> in the fix that replaced it.
```

Measured on Node v22.14.0:

```text
/\p{Bidi_Control}/u 12 061c 200e 200f 202a 202b 202c 202d 202e 2066 2067 2068 2069
/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]/u 12 061c 200e 200f 202a 202b 202c 202d 202e 2066 2067 2068 2069
```

Concrete failure scenario: the current literal list happens to equal today's property in Node 22, so this is not a present data-loss path. The failure is that v17 advertises the exact derivation it does not write down. A future reader can preserve the hand list while believing the spec has removed the enumeration class.

Proposed fix: either write the predicate as `/\p{Bidi_Control}/u` and add a unit/property test over the property, or retract the "not a hand-picked range" sentence and keep the explicit list as a deliberate enumeration. Behavior 17 should include at least one of the three round-14 misses, not only a bidi override.

Classification: `stale cross-reference`; caused by v17's own fix.

Test discriminator: the current test/mutation text would catch deleting all bidi rejection, not the stale claim that this is property-derived.

## Conclusion

v17 did make the right structural move for the `summaryMd` metadata path, but two new "seams" are not actually seams: the model envelope seam misses `writeModelEnvelopeWithin`, and the metadata seam misses `bulkUpdateVideoFields`. Those are mechanism defects caused by v17's own fixes. Given the round-11 through round-14 history and another fix-induced mechanism defect here, the honest conclusion is that the shape is still not stable enough to approve without a wider seam redesign.

NOT CONVERGED
