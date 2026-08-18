# Round 12 adversarial review — cloud blob key encoding v13

Subject: `docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md` in the working tree, v13.

Phase 1 review only. No production Supabase writes were made. Predicate checks were pure Node string probes; APFS/Supabase mutation was not needed for the findings below.

## Findings

### Medium — caused by the v13 `promoteIfAbsent` fix: §3.6.3 still states the rejected global `promote` contract

Evidence:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:560-563`:

````md
**R1 — a NEW primitive, `promoteIfAbsent`. `promote` itself is not touched.**

```
promoteIfAbsent(ref): 'created' | 'already-exists'
```
````

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:723-726`:

```ts
Declined, because it **wraps a credential that §3.6.0 measures to be stale by construction**. Making
the stale answer a first-class capability propagates it to every adapter and every future caller.
R1–R4 satisfy the same "don't reach through the seam" objection differently: the seam gets a stronger
**uniform contract** (`promote` is create-if-absent everywhere) rather than a new question.
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:891`:

```ts
| 18d4 | `promote` is **unchanged** — its existing callers' behaviour is byte-identical before and after this slice | contract |
```

The design now has two incompatible implementation instructions. The behavior table and R1 say to add `promoteIfAbsent` and keep `promote` byte-identical; §3.6.3 still says the seam change is "`promote` is create-if-absent everywhere", which is exactly the round-11 failure mode this version is supposed to retire.

Failure scenario:

An implementer following §3.6.3 changes `LocalFsBlobStore.promote` from overwrite to create-if-absent. Existing `promote` callers then no longer have byte-identical behavior. The current local adapter is:

`lib/storage/local/local-blob-store.ts:58-62`:

```ts
async promote(ref: StagedRef): Promise<void> {
  const from = this.abs(ref.principal, ref.tempKey); const to = this.abs(ref.principal, ref.finalKey);
  if (!fs.existsSync(from) && fs.existsSync(to)) return;   // idempotent: already promoted
  fs.mkdirSync(path.dirname(to), { recursive: true }); fs.renameSync(from, to);
}
```

That `renameSync` overwrite is still the behavior guarded by spec row 18d4. If it is changed anyway, the spec can reintroduce the stale paid-artifact behavior round 11 already found: a same-key regeneration can advertise a promoted/current artifact while the old bytes remain.

Proposed fix:

Replace the §3.6.3 sentence with the actual adopted seam contract, e.g. "the seam gets a stronger uniform primitive, `promoteIfAbsent`, while `promote` remains byte-identical for existing callers." Keep behavior 18d4 as the tripwire.

### Low — caused by the v13 `promoteIfAbsent` fix: the required-method rollout names only the three concrete adapters, but existing `BlobStore` decorators and object fakes also implement the interface

Evidence:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:575-579`:

```ts
| Adapter | Implementation |
|---|---|
| `LocalFsBlobStore` | `mkdirSync(dirname)` — **keep it**, `promote` already does it (`:61`) and nested `dig/<base>/<n>.r<V>.md` keys need it — then `link` + `unlink` + `rmdir` |
| `SupabaseBlobStore` | its existing `promote` body already is this (`:112-116`) |
| `InMemoryBlobStore` | its `create-if-absent` semantics, unconditionally |
```

There are other concrete implementers/decorators of `BlobStore` in the working tree:

`tests/integration/helpers/cloud.ts:168-184`:

```ts
class FailPromoteBlobStore implements BlobStore {
  constructor(private inner: BlobStore) {}
  /** Forward the wrapped backend's absence-proving capability — the sync path reads it to decide
   *  whether "no bytes" may be treated as a semantic fact (B1/H1/H2 guards). */
  get provesAbsence(): boolean | undefined { return this.inner.provesAbsence; }
  put(p: Principal, key: string, bytes: Buffer, ct: string) { return this.inner.put(p, key, bytes, ct); }
  get(p: Principal, key: string) { return this.inner.get(p, key); }
  tryGet(p: Principal, key: string) { return this.inner.tryGet(p, key); }
  exists(p: Principal, key: string) { return this.inner.exists(p, key); }
  delete(p: Principal, key: string) { return this.inner.delete(p, key); }
  putStaged(p: Principal, key: string, bytes: Buffer, ct: string) { return this.inner.putStaged(p, key, bytes, ct); }
  async promote(_ref: StagedRef): Promise<void> { throw new Error('injected cloud promote failure'); }
  deletePrefix(p: Principal, prefix: string) { return this.inner.deletePrefix(p, prefix); }
  list(p: Principal, prefix: string) { return this.inner.list(p, prefix); }
  /** `copyBlob(this, …)` — routed through the DECORATOR, not `inner`, so any injected fault on
   *  this wrapper's primitives is observed by `copy` exactly as it would be in production. */
  copy(p: Principal, from: string, to: string): Promise<CopyResult> { return copyBlob(this, p, from, to); }
}
```

`tests/integration/serve-model-unreadable.test.ts:57-79`:

```ts
class UnreadableModelBlobStore implements BlobStore {
  constructor(private inner: BlobStore) {}
  get provesAbsence(): boolean | undefined { return this.inner.provesAbsence; }
  async get(p: Principal, key: string) {
    if (key.includes('models/')) return null; // transient failure, indistinguishable from absent
    return this.inner.get(p, key);
  }
  async tryGet(p: Principal, key: string): Promise<BlobRead> {
    // The honest answer for a transient 5xx / timeout / RLS denial: we could NOT read it, and that
    // is NOT proof the object is gone. This is what the money guard must key off.
    if (key.includes('models/')) return { ok: false, reason: 'unreadable', cause: new Error('simulated transient storage failure') };
    return this.inner.tryGet(p, key);
  }
  put(p: Principal, key: string, bytes: Buffer, ct: string) { return this.inner.put(p, key, bytes, ct); }
  exists(p: Principal, key: string) { return this.inner.exists(p, key); }
  delete(p: Principal, key: string) { return this.inner.delete(p, key); }
  putStaged(p: Principal, key: string, bytes: Buffer, ct: string) { return this.inner.putStaged(p, key, bytes, ct); }
  promote(ref: Parameters<BlobStore['promote']>[0]) { return this.inner.promote(ref); }
  deletePrefix(p: Principal, prefix: string) { return this.inner.deletePrefix(p, prefix); }
  list(p: Principal, prefix: string) { return this.inner.list(p, prefix); }
  /** Routed through the decorator, so a copy involving a model key correctly reports
   *  `*-unreadable` rather than inheriting the `get`-returns-null lie this class simulates. */
  copy(p: Principal, from: string, to: string) { return copyBlob(this, p, from, to); }
}
```

`tests/lib/storage/consistency.test.ts:38-59`:

```ts
const blob: BlobStore = {
  async put() {},
  async get() { return null; },
  async tryGet() { return { ok: false as const, reason: 'absent' as const }; },
  async exists(_p, key) {
    order.push(`exists(${key})`);
    // Return true for the temp key to simulate successful staging
    return opts.tempExists !== false;
  },
  async delete() {},
  async deletePrefix() {},
  async list() { return []; },
  async copy() { return { ok: true as const, already: false }; },
  async putStaged(principal, key, _bytes, _contentType) {
    order.push('putStaged');
    stagedRef = { principal, tempKey: `_staging/${key}`, finalKey: key };
    return stagedRef;
  },
  async promote(ref) {
    order.push(`promote(${ref.finalKey})`);
  },
};
```

Failure scenario:

The implementation follows the spec literally and updates only `LocalFsBlobStore`, `SupabaseBlobStore`, and `InMemoryBlobStore`. TypeScript then fails on the decorators/object fake, or a decorator is patched ad hoc in a test without preserving the wrapper's fault semantics. This is not a production data-loss path, but it is a predictable implementation interruption caused by the new required method.

Proposed fix:

Add an implementation note or behavior under 18d2/18d4: every class/object that `implements BlobStore` or is typed as `BlobStore` must either implement `promoteIfAbsent` directly or forward it through the decorator, with fault-injection wrappers deciding explicitly whether the injected `promote` fault also applies to `promoteIfAbsent`.

## Checked Non-Findings

The v13 predicate held on the targeted cases I reproduced. The probe used the spec predicate exactly: it accepts `003_lesson-\u2488.md`, rejects `001_a\uff0e\uff0eb.md`, rejects `/`, `\`, `%2f`, C0/DEL, bidi overrides/isolates, and keeps the 131-code-point bound. A full U+0000-10FFFF slugify survivability sweep found `badSlugCount 0`; the expected 21 NFKC trailing-dot numerals were `U+2488`-`U+249B` and `U+1F100`.

The §3.6.4 dissolved residual held against the cited current code. Produced summaries write `video_id` unconditionally:

`lib/ingestion/summary-core.ts:101-108`:

```ts
const frontmatterLines = [
  '---', 'tags:', ...allTags.map((t) => `  - ${t}`),
  `video_id: "${videoId}"`,
  ...(channel ? [`channel: "${channel}"`] : []),
  `lang: ${language.toUpperCase()}`,
  ...(videoType ? [`type: ${videoType}`] : []),
  ...(audience ? [`audience: ${audience}`] : []),
  `score: ${overallScore}`, '---',
];
```

Adoption refuses a file without that field:

`lib/pipeline.ts:147-149`:

```ts
const content = fs.readFileSync(mdPath, 'utf-8');
const videoId = parseFrontmatterField(content, 'video_id');
if (!videoId || indexedIds.has(videoId)) continue;
```

`ensureReceiverSlot` runs before the additive blob write:

`lib/cloud-sync/sync-run.ts:240-263`:

```ts
const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
...
const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
```

The current corrections route edits the existing MD body and writes it back; it does not currently create a new vault `.md` that omits frontmatter. The spec is still right to record backlog #23 as the live falsifier to watch.

Writer 3's new `sourceMd` credential is available in valid envelopes:

`lib/html-doc/model-store.ts:15-23`:

```ts
export const ModelEnvelopeSchema = z
  .object({
    sourceMd: z.string().min(1),
    generatedAt: z.string().min(1),
    sourceSections: z.array(z.string()),
    generatorVersion: z.string().min(1).optional(),
    model: MagazineModelSchema,
    // Stage 3 (§4.2): MD-body-only digest of the MD this model was generated from.
    sourceMdHash: z.string().optional(),
  });
```

Missing/unreadable/schema-invalid envelopes flow through `readModelEnvelope` as `null`, so the design can refuse destructive companion operations when no `sourceMd` credential is present rather than inventing ownership.

CONVERGED
