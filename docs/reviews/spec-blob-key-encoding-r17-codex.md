# Round 17 Codex review: cloud blob key encoding v19

## Findings

### Low: old adopt-placement references survived the caller move

Evidence:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:786`

```md
3. **The adopt path keeps its call site above `ensureReceiverSlot`** (`sync-run.ts:236-238`) — **and it
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:860`

```md
> **THE GUARD GOES IN THE CALLER, at `sync-run.ts:624-627`, on the `to = cloudSide` arm only.**
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:921`

```md
| `copyAdditiveVideo` — **receiver is the CLOUD** (`copyToCloud`) | **the adopt guard**, above `ensureReceiverSlot` (`sync-run.ts:236-238`) | **nothing** | Video stays one-sided. Throw → caught per-video at `:812` → `report.errors`, **no `writeVideoBaseline`** → re-fires identically every run **until a human renames the vault file** — which exists, and is the thing to rename. ✅ intended |
```

Code evidence:

`lib/cloud-sync/sync-run.ts:221`

```ts
async function copyAdditiveVideo(
```

`lib/cloud-sync/sync-run.ts:624`

```ts
const from: Side = presentIsLocal ? localSide : cloudSide;
const to: Side = presentIsLocal ? cloudSide : localSide;
const body = await readMdBody(from.blob, from.p, present);
await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
```

Failure scenario:

An implementer following line 786 or the §3.5.2 table literally puts the adopt guard back inside `copyAdditiveVideo` at the existing pre-`ensureReceiverSlot` check. That recreates the round-16 B1 shape: the function has no side discriminant, so the guard either applies in both directions or sniffs implementation type. In the both-directions version, cloud→local hydration of an existing unservable cloud key is refused, leaving a paid artifact unrecoverable through sync after serve/share/download are closed.

This does not invalidate the mechanism because the same section later states the correct placement at `sync-run.ts:624-627`, and §3.5.1b row 4 names the two additive branches and scopes the guard to the cloud receiver. It is still a stale cross-reference from the v19 move.

Proposed fix:

Change the surviving old-placement references to the caller placement. In §3.5.2, the `copyToCloud` row should say the refusal lands in the additive caller before entering `copyAdditiveVideo`, before `ensureReceiverSlot` can run, at `sync-run.ts:624-627` on the `presentIsLocal` / `to = cloudSide` arm.

Classification: `stale cross-reference`

Caused by v19 fixes: yes

## Branch-table check

§3.5.1b holds under independent verification.

Rows 1, 2, 3 and 6 are genuinely one-branch placements:

```ts
// lib/storage/supabase/supabase-metadata-store.ts:119, :143, :160
.update({ data: stripComputed(video) })
p_fields: stripComputed(fields)
p_patches: patches.map((x) => ({ video_id: x.videoId, fields: stripComputed(x.fields) }))
```

```ts
// scripts/cloud-sync.ts:62-67
local: localMetadataStore,
cloud: new SupabaseMetadataStore(client),
localBlob: localBlobStore,
cloudBlob: new SupabaseBlobStore(client, ARTIFACTS_BUCKET),
```

```ts
// lib/cloud-sync/sync-run.ts:730-733
? await reconcileCloudBase({
    cloud: cloudSide, cloudIndex: cloudSnapshot, localVideo: lv, cloudVideo: cv,
    inFlightJob: deps.inFlightJob,
  })
```

```ts
// app/s/[token]/route.ts:41
const ctx = await getShareServeContext(svc, token);
```

Rows 4 and 5 correctly name two branches:

```ts
// lib/cloud-sync/sync-run.ts:624-627
const from: Side = presentIsLocal ? localSide : cloudSide;
const to: Side = presentIsLocal ? cloudSide : localSide;
const body = await readMdBody(from.blob, from.p, present);
await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
```

```ts
// lib/cloud-sync/sync-run.ts:780-793
if (decision.action === 'copyToCloud') {
  winnerSide = localSide; loserSide = cloudSide; winnerVideo = lv; winnerSignals = la;
  winnerMdHash = (await transferClassA(localSide, cloudSide, lv, id)).mdHash;
...
} else if (decision.action === 'copyToLocal') {
  winnerSide = cloudSide; loserSide = localSide; winnerVideo = cv; winnerSignals = ca;
  winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
```

Row 7 correctly binds all production envelope writers through `serialize`, including the local generate path:

```ts
// lib/html-doc/model-store.ts:34-36
function serialize(envelope: ModelEnvelope): Buffer {
  ModelEnvelopeSchema.parse(envelope); // fail loud on an invalid model
  return Buffer.from(`${JSON.stringify(envelope, null, 2)}\n`, 'utf-8');
}
```

```ts
// lib/html-doc/generate.ts:11-12
export async function runHtmlDoc(
  videoId: string,
```

```ts
// lib/html-doc/generate.ts:50
await writeModelEnvelope(principal, base, {
```

```ts
// lib/html-doc/serve-doc.ts:174
await writeModelEnvelopeWithin(SERVE_PUT_TIMEOUT_MS, principal, base, {
```

```ts
// lib/cloud-sync/sync-run.ts:464
await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);
```

Implementation-cost note: requiring `videoId` on the write schema will force many test fixtures and helper envelope literals to change. I found current test call sites without `videoId` in `tests/lib/html-doc/rerender.test.ts`, `tests/lib/html-doc/model-store.test.ts`, `tests/lib/model-store-cloud.test.ts`, `tests/integration/share-route.test.ts`, `tests/e2e/cloud.setup.ts`, and others. That is real planning cost, but not a mechanism defect: the spec states the production sources for `videoId` and the write-schema mechanism that makes omissions compile/runtime failures.

## Other checks

The caller-level adopt move is coherent. The direction is genuinely known where `presentIsLocal` chooses `to`, and refusing before `copyAdditiveVideo` is entered is earlier than `ensureReceiverSlot`, the WB-H1 unreadable-body guard, staging, `upsertVideo`, the per-video catch, and baseline write.

The `unservable-base` explicit-branch design no longer contradicts the old "no change to the caller" claim. The working tree code still has the generic throw today:

```ts
// lib/cloud-sync/sync-run.ts:754-756
throw new Error(rec.reason === 'target-occupied'
  ? `serial collision: ${id} needs serial ${rec.want} on cloud, already held by ${rec.heldBy}`
  : `base reconciliation failed for ${id}: ${rec.reason}${'key' in rec ? ` at ${rec.key}` : ''}`);
```

That is expected in Phase 1; the spec now instructs implementation to add the explicit branch.

Behaviors 26e, 26f, and 18j7 are writable as tests. 26f can observe the negative by instrumenting the receiver metadata store's `setPlaylistMeta` / `readIndex` / `claimVideoSlot` path or by asserting no receiver row and no receiver blob after the refusal; 18j7 can seed a model with `videoId`, run `reconcileCloudBase`, and read the copied JSON.

Character sweep: the spec contains zero `Cc`/`Cf` characters excluding normal newlines/tabs/carriage returns. It does contain literal escape spellings such as `\u`, `\x`, and `\0`; those appear in quoted examples and regex source, not as invisible control characters.

## Falsifier

The armed falsifier did not fire. I did not find a third instance where a placement is stated for only one branch/direction of the path it sits on. §3.5.1b's placement × branch table holds; the only defect found is stale old-location prose from v19's adopt-guard move.

CONVERGED
