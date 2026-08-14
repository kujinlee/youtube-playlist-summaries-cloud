<!-- codex-review: model=gpt-5.5 -->

**Blocking 1 — Fourth Write Entrance Is Missing: Base Reconciliation Can Publish An Unservable Cloud Key**

Evidence: [docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:264) says:

```md
**Where the check runs — every write entrance, and there are three.**
```

and lists only:

```md
| Worker mint | `summary-handler.ts:96`, immediately after `baseName` |
| Sync — additive create | `sync-run.ts:263` (`copyAdditiveVideo` → `putStaged`) |
| Sync — **Class-A transfer** | `sync-run.ts:379-399` ... |
```

But [lib/cloud-sync/reconcile-serial.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:282) is a fourth cloud write entrance:

```ts
const res = await cloud.blob.copy(cloud.p, from, to);
```

and then patches the cloud row to the remapped summary key at [lib/cloud-sync/reconcile-serial.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:293):

```ts
const patch: Record<string, unknown> = {
  serialNumber: localVideo.serialNumber,
  summaryMd: `${newBase}.md`,
  artifacts: { summaryMd: { key: `${newBase}.md`, status: 'promoted' } },
```

The `newBase` comes from the local replica at [lib/cloud-sync/reconcile-serial.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:151):

```ts
const to = localVideo.summaryMd
  ? baseOf(localVideo.summaryMd)
  : baseOf(applySerial(cloudVideo.summaryMd, localVideo.serialNumber));
```

Failure scenario: local has `summaryMd: "003_my summary.md"` or `"003_x🙂.md"` from an adopted vault file; cloud has the same video at a prior servable key, so `describeDivergence()` runs. After this slice, `copyBlob()` writes the remapped key through the encoded Supabase seam, and `updateVideoFields()` advertises it as promoted. Serve then rejects it at [lib/html-doc/serve-summary-core.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-summary-core.ts:60):

```ts
assertCloudSummaryMdKey(mdKey);
```

returning:

```ts
return { ok: false, status: 409, error: 'corrupt summary key' };
```

This also answers the fallback question: the mint fallback is not stable against later sync to a replica whose key was minted from the slug. Local-authoritative `reconcileCloudBase()` can move cloud from `${padSerial(serial)}_${videoId}.md` back to the local slug key and recreate the exact unservable promoted cloud row v6 was trying to prevent.

Proposed fix: add `reconcileCloudBase` to §2.6/§3.5 as a fourth write entrance. Before the copy plan or metadata patch, validate the candidate `${newBase}.md` with the widened `assertCloudSummaryMdKey`. For sync, refuse per-video before any copy, with no baseline advanced. Add a behavior covering base reconciliation from a local unservable key.

**Medium 1 — Additive Collision Guard Still Does Not Pin Ordering**

Evidence: v6 gives the guard at [docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:202):

```ts
const occupied = await to.blob.tryGet(toP, key);
if (occupied.ok) throw new Error(`key collision: ${key} already held`);
if (!occupied.ok && occupied.reason === 'unreadable') throw occupied.cause;  // never treat as free
```

But the actual additive flow currently claims the row before the blob write at [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:240):

```ts
const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
```

then writes at [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:263):

```ts
const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
```

Failure scenario: if the new `tryGet` guard is implemented after `ensureReceiverSlot`, an APFS alias or unreadable receiver check throws after a bare receiver row exists. That is the same partial-state shape previous rounds already killed: the next run can classify the video as two-sided instead of additive and avoid the intended pre-write refusal.

Proposed fix: specify the exact insertion point: after `video.summaryMd && mdBody != null` validation, before `ensureReceiverSlot(...)`. Use the existing `toBlob` parameter, not an implied `to.blob`.

**Medium 2 — Prefix Rule Still Contradicts Behavior 12**

Evidence: [docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:152) says:

```md
**A prefix must end on a segment boundary.** `list`/`deletePrefix` throw otherwise
```

but behavior 12 at [docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:355) says:

```md
| 12 | `list(p, 'dig/{base}/')` and `list(p, 'dig/{base}')` return the same set | unit |
```

Failure scenario: an implementation that satisfies the prose rejects `dig/{base}`; an implementation that satisfies behavior 12 permits it. The production callers all use `dig/${base}/`, so this is bounded, but the spec is internally inconsistent.

Proposed fix: restore the enforceable predicate: `prefix === '' || prefix.endsWith('/')`. Delete or rewrite behavior 12.

**Checked, No Finding**

`utf16le` fixes the round-5 concrete surrogate collision. I measured:

```text
"003_x\ud840.md" utf8 3030335f78efbfbd2e6d64 utf16le 3000300033005f00780040d82e006d006400
"003_x\ud850.md" utf8 3030335f78efbfbd2e6d64 utf16le 3000300033005f00780050d82e006d006400
```

I found no shipped source hashing blob keys with SHA-256/UTF-8 that would need to agree with the new physical-key encoder. Existing `mdHash()` hashes Markdown bodies, not filenames.

Behaviors 19 and 22 are constructible: `slugify` uses `.slice(0, 60)`, and a title of 59 ASCII chars plus `U+20000` leaves a lone high surrogate. Behavior 21 is constructible by adoption from local index/blob fixtures. It fails v5 for Class-A because v5 missed `transferClassA`; v6 fixed that part but still misses `reconcileCloudBase`.

NOT CONVERGED.
