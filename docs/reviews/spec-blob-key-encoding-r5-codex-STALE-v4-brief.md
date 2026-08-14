<!-- codex-review: model=gpt-5.5 -->

**Blocking Finding 1: v4 guards indexed key aliases, but APFS overwrites unindexed vault files**

Evidence:

`docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md@20acdb7:434-440`
```ts
`LocalFsBlobStore` sets it `true`; `SupabaseBlobStore` and `InMemoryBlobStore` leave it absent. The
additive collision guard asks the **receiver's** store, so the check matches the filesystem it is about
to write to:

const sameKey = (a: string, b: string) =>
  to.blob.aliasesUnicodeNormalization ? a.normalize('NFC') === b.normalize('NFC') : a === b;
```

Current guard shape is row-based:

[lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:203)
```ts
if (video.serialNumber != null || video.summaryMd) {
  const holder = idx.videos.find((v) =>
    (video.serialNumber != null && v.serialNumber === video.serialNumber) ||
    (video.summaryMd != null && v.summaryMd === video.summaryMd));
```

The destructive write is filesystem-level:

[lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:263)
```ts
const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
```

[lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:268)
```ts
await toBlob.promote(ref);
```

[lib/storage/local/local-blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/local/local-blob-store.ts:58)
```ts
async promote(ref: StagedRef): Promise<void> {
  const from = this.abs(ref.principal, ref.tempKey); const to = this.abs(ref.principal, ref.finalKey);
  if (!fs.existsSync(from) && fs.existsSync(to)) return;   // idempotent: already promoted
  fs.mkdirSync(path.dirname(to), { recursive: true }); fs.renameSync(from, to);
}
```

And unindexed vault files are a real supported recovery subject:

[lib/pipeline.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/pipeline.ts:137)
```ts
files = fs.readdirSync(outputFolder).filter(
```

[lib/pipeline.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/pipeline.ts:151)
```ts
const video = reconstructVideo(content, file, mdPath);
```

Failure scenario: an APFS vault contains a paid but currently unindexed `003_cafe\u0301.md`; `recoverOrphanedVideos` would be able to adopt it later. Cloud has a cloud-only video with `summaryMd = "003_café.md"` NFC, now possible after the encoder. During cloud→local additive sync, the row scan finds no holder because there is no receiver row. `promote()` renames the staged NFC path onto the final NFC path; APFS resolves that path to the existing NFD file and overwrites its bytes. The paid vault file is destroyed before recovery can adopt it.

I probed this on the real filesystem: creating NFD, then `renameSync(staged NFC, final NFC)` left one NFD directory entry and changed its body to the incoming cloud body.

Proposed fix: the receiver-local additive guard must ask the filesystem, not only the index. Before claiming/writing, if `toBlob.aliasesUnicodeNormalization` and `video.summaryMd`, call `await toBlob.exists(toP, video.summaryMd)` and refuse as `serial collision` when it is true and no same-video receiver row owns that alias. This also covers the “real vault file with no index row” case v4 currently misses.

**Verified**

Round-3 B2 reproduces. Against local Supabase at `http://127.0.0.1:54321`, with the v4 raw-hash encoder transcribed, NFC and NFD `003_café.md` encode to different physical keys. Uploading the NFD physical key succeeds, downloading through the same NFD logical key returns `NFD-BODY`, and downloading through the NFC logical key returns `404`. Cleanup left zero probe objects.

`CLOUD_SUMMARY_MD_KEY` widening to `\p{M}` looks safe for the stated single-component purpose. I scanned all 2,501 `\p{M}` code points in Node v22: none normalize under NFC/NFD/NFKC/NFKD to `/`, `\`, `%`, whitespace, control, or `.`. ZWJ is not `\p{M}`; VS16 and U+0338 are `\p{M}`, but they remained ordinary filename code points in an APFS temp dir and did not create path components.

`NOT CONVERGED`

---

## ⚠ ADJUDICATION — THIS REVIEW DOES NOT APPLY TO v5

**Kept as evidence, not as a finding.** The coordinator dispatched this run with the ROUND-4 brief,
which names "v4, commit 20acdb7". Codex followed it exactly and reviewed the spec **at that commit** —
see its own citation, `design.md@20acdb7:434-440`. The working tree was already v5 (`6e331d5`).

Its Blocking — "the additive collision guard is row-based, so an unindexed vault file at an aliasing
name is overwritten" — is **correct about v4 and already fixed in v5 §3.4**, which replaced the
row scan with `toBlob.exists`.

Two things worth keeping:

1. **Independent confirmation.** Codex found the same defect from scratch that round-4 Claude's H1
   found, and v5 had already acted on it. That the fix was the right one is now corroborated by two
   reviewers who reached it independently.
2. **A process defect, and it is the session's own recurring lesson.** The coordinator checked what
   the reviewer *said* and nearly counted a v4 finding against v5. The subject of the measurement was
   wrong — this time because the coordinator chose the wrong subject when writing the brief. A review
   brief that pins a commit will be obeyed literally; pin the commit you actually want reviewed, or
   pin none.

Round 5's Codex half was re-run against v5 with the correct brief → `spec-blob-key-encoding-r5-codex.md`.
