<!-- codex-review: model=gpt-5.5 -->

**Blocking Finding 1: NFC aliasing can delete the newly advertised paid blob**

Evidence:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:181-186`
```ts
n = s.normalize('NFC')
...
return `${head}=h${base64url(sha256(utf8(n))).slice(0, 22)}${ext}`
```

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:351-352`
```md
| 3 | NFC and NFD forms of one title encode to the **same** physical key | unit |
| 4 | Two different logical keys never share a physical key | property |
```

Those two assertions conflict. Today logical equality is not NFC-normalized:

`lib/storage/blob-store.ts:96-98`
```ts
export function normalizeLogicalKey(key: string): string {
  return key.split('/').filter((seg) => seg !== '' && seg !== '.').join('/');
}
```

The dangerous delete path is in serial reconciliation:

`lib/cloud-sync/reconcile-serial.ts:117-120`
```ts
if (key === `${oldBase}.md`) return `${newBase}.md`;
if (key === MODEL_KEY(oldBase)) return MODEL_KEY(newBase);
const digPrefix = `dig/${oldBase}/`;
if (key.startsWith(digPrefix)) return `dig/${newBase}/${key.slice(digPrefix.length)}`;
```

`lib/cloud-sync/reconcile-serial.ts:282-289`
```ts
const res = await cloud.blob.copy(cloud.p, from, to);
if (res.ok) { if (!res.already) copied += 1; continue; }
...
if (res.reason === 'source-absent' && from !== `${oldBase}.md`) continue;
return { ok: false, reason: 'copy-failed', key: to, detail: res };
```

`lib/cloud-sync/reconcile-serial.ts:351-360`
```ts
if (after?.summaryMd !== `${newBase}.md`) {
  return { ok: false, reason: 'metadata-unverified', found: after?.summaryMd ?? null };
}
...
for (const { from, to } of plan) {
  if (to === from) continue;
  try { await cloud.blob.delete(cloud.p, from); } catch { cleanupFailures += 1; }
```

Failure scenario: cloud row has `summaryMd = "003_cafe\u0301.md"` and local authoritative row has `summaryMd = "003_café.md"`. They are distinct byte strings, so `from !== to`; reconciliation copies old to new, advances metadata to the NFC key, then deletes `from`. Under the proposed Supabase adapter, `from` and `to` encode to the same physical object, so cleanup deletes the object the row now points at. That is paid summary/dig/model loss.

Proposed fix: do not normalize inside the physical encoder unless the logical seam also becomes NFC-canonical everywhere. The smaller safe fix is: make the encoder injective over the original logical segment bytes, and add a separate pre-storage/key-generation NFC canonicalization policy only if all metadata comparisons, copy planning, and delete decisions are updated to the same canonical equality. At minimum, add a fail-fast test for `copy -> metadata advance -> cleanup` where old/new differ only by Unicode normalization.

**Medium Finding 2: `list(p, '')` stops satisfying the BlobStore contract**

Evidence:

`lib/storage/blob-store.ts:78-79`
```ts
/** List logical keys (relative to the owner root) under a prefix. Absent prefix → []. */
list(p: Principal, prefix: string): Promise<string[]>;
```

Existing shared test expectations include empty prefix:

`tests/lib/storage/in-memory-blob-store.test.ts:147-149`
```ts
expect((await s.list(p, '')).sort()).toEqual(
  ['dig/base/1000.r9.md', 'dig/base/65.r9.md', 'other.md'],
);
```

`tests/lib/storage/in-memory-blob-store.test.ts:182`
```ts
expect(await s.list(p, '')).toEqual(['a.md']);
```

The spec knowingly makes Supabase unable to name some listed keys:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:240-244`
```md
If a returned leaf itself carries the `=h` marker, the adapter cannot name it
and **throws**. ... No production path can reach this today (only tests call `list(p, '')`)
```

Failure scenario: after a Korean summary is stored, `list(p, '')` enumerates the owner root and sees a hashed top-level summary leaf like `003_=h....md`. The adapter cannot invert it and throws, even though `BlobStore.list` promises logical keys under any prefix and existing contract tests treat empty prefix as valid.

Proposed fix: either narrow the seam contract explicitly so `list()` is only supported for caller-owned prefixes whose remaining leaves are reversible ASCII, or choose a reversible listing design for root/non-ASCII leaves. If narrowing, add a distinct method or documented precondition and update all shared contract tests so Supabase is not silently violating `BlobStore`.

**Low Finding 3: The no-migration proof overstates the accepted/rejected boundary, but the proposed gate is the right shape**

The spec says:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:276-278`
```md
**The set of keys the encoding changes is exactly the set Storage would have rejected.** A key made
only of `SAFE` characters and within `LIMIT` is emitted byte-identically; a key outside that set was
refused at upload and therefore **is not in the bucket**.
```

But the same spec records accepted keys outside `SAFE`:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:280-282`
```md
Storage accepts space,
`(`, `)`, `+`, `=` (§2.1), which `SAFE` excludes, so such a key would be re-addressed and orphaned.
```

Failure scenario: an existing object named `003_a+b=c.md` is accepted by Storage but would be hashed by the proposed encoder, so future reads by logical key miss the existing physical object.

Proposed fix: rewrite §4 as “no migration is conditional on a prod bucket scan proving no existing segment falls outside `SAFE` or over `LIMIT`.” The gate itself is falsifiable and covers the counterexample:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:286-288`
```md
FAILS IF ... any row having a path segment that either does not match
`^[A-Za-z0-9._-]+$` **or exceeds `LIMIT` (96) characters**.
```

Also keep §4.1 blocking deployment until the gate can actually run:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:315-316`
```md
Until then §4 is **unverified**, and this slice must not be deployed to prod
```

**Verified Points**

No production path reaches Supabase Storage outside the adapter. In `app`, `lib`, and `scripts`, direct storage calls are only here:

`lib/storage/supabase/supabase-blob-store.ts:20-23`
```ts
private b() { return this.client.storage.from(this.bucket); }
const { error } = await this.b().upload(this.objectKey(p, key), bytes, { contentType, upsert: true });
```

Production construction goes through the adapter:

`lib/storage/resolve.ts:57-60`
```ts
metadataStore: new SupabaseMetadataStore(ctx.supabaseClient),
blobStore: new SupabaseBlobStore(ctx.supabaseClient, ARTIFACTS_BUCKET),
jobQueue: new SupabaseJobQueue(ctx.supabaseClient),
```

`lib/storage/resolve.ts:81-83`
```ts
blobStore: new SupabaseBlobStore(serviceClient, ARTIFACTS_BUCKET),
principal: { id: ownerId, indexKey: data.playlist_key },
```

`蔵/scripts/cloud-sync.ts:62-67`
```ts
cloud: new SupabaseMetadataStore(client),
localBlob: localBlobStore,
cloudBlob: new SupabaseBlobStore(client, ARTIFACTS_BUCKET),
```

The production `list()` callers do match the spec’s prefix claim:

`lib/cloud-sync/reconcile-serial.ts:102`
```ts
keys.push(...await blob.list(p, `dig/${base}/`));
```

`lib/dig/cloud/load-dig-for-serve.ts:32-34`
```ts
const prefix = `dig/${load.base}/`;
const suffix = `.r${DIG_GENERATOR_VERSION}.md`;
const keys = (await load.bundle.blobStore.list(load.principal, prefix)).filter((k) => k.endsWith(suffix));
```

`app/api/videos/[id]/dig-state/route.ts:47-50`
```ts
const keys = await load.bundle.blobStore.list(load.principal, `dig/${load.base}/`);
const sectionIds = keys
  .filter((k) => k.endsWith(suffix))
  .map((k) => k.match(/\/(\d+)\.r\d+\.md$/))
```

Verdict: `NOT CONVERGED`
