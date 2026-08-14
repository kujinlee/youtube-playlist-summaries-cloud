<!-- codex-review: model=gpt-5.5 -->

**Blocking Finding 1: `transferClassA` can write the blob under raw NFD while advertising the canonical NFC key**

Evidence:

[docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:381](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:381)
```md
1. **Worker persist** — `lib/job-queue/summary-handler.ts:96` mints `baseName` from `slugify(title)`,
```

[docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:383](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:383)
```md
2. **Sync, sender → cloud record** — `sanitizeAdditiveVideo` and `transferClassA`
   (`sync-run.ts:263`, `:279`, `:399`, `:430`) carry the sender's key into cloud rows and blobs.
```

But `transferClassA` writes the blob before the named metadata fields:

[lib/cloud-sync/sync-run.ts:379](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:379)
```ts
const key = winnerVideo.summaryMd;
```

[lib/cloud-sync/sync-run.ts:381](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:381)
```ts
const ref = await loser.blob.putStaged(loser.p, key, Buffer.from(body, 'utf8'), 'text/markdown');
```

[lib/cloud-sync/sync-run.ts:394](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:394)
```ts
await loser.blob.put(loser.p, key, staged, 'text/markdown');
```

[lib/cloud-sync/sync-run.ts:399](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:399)
```ts
summaryMd: key,
```

[lib/cloud-sync/sync-run.ts:430](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:430)
```ts
artifacts: { summaryMd: { key, status: 'promoted' } },
```

Failure scenario: local is the Class-A winner with `summaryMd = "003_cafe\u0301.md"` and newer MD body; cloud has the same video at canonical `"003_café.md"` with an older promoted blob. v3 says `describeDivergence` canonicalizes the local key, so base relocation is skipped. If the implementation follows the named ingress sites and canonicalizes `:399/:430` but not `:379/:381/:394`, the new body is written to the raw-NFD physical address while the cloud row advertises NFC. Serve then reads the old NFC blob, while sync reports the Class-A copy succeeded and can advance the baseline.

Proposed fix: canonicalize once at `transferClassA` entry, before both blob writes and metadata tuple construction, e.g. derive `const key = canonicalCloudKey(winnerVideo.summaryMd)`. Add an integration behavior for local→cloud Class-A where the winner key is NFD, the loser row is NFC, body hashes differ, and the post-sync cloud serve returns the winner bytes.

**Medium Finding 2: §6 still requires the old v2 encoder equivalence that v3 explicitly removed**

Evidence:

[docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:218](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:218)
```md
return `${head}=h${base64url(sha256(utf8(s))).slice(0, 22)}${ext}`
```

[docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:221](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:221)
```md
> ⚠ **v3: the encoder hashes the RAW segment. v2 hashed `NFC(s)`, and that was the root of five
```

[docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:276](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:276)
```md
#### 3.2.2 The encoder is injective, full stop — because canonicalization happens upstream
```

[docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:505](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:505)
```md
| 3 | NFC and NFD forms of one segment encode to the **same** physical key | unit |
```

Measured with the v3 pseudocode: `encode("003_café.md")` and `encode("003_cafe\u0301.md")` produce different hashes; `encode("003_K.md")` hashes while `encode("003_K.md")` is identity. That is correct only if inputs have already passed the ingress canonicalizer.

Failure scenario: a developer implements the raw-hash encoder correctly, then behavior 3 fails. The tempting “fix” is to hash `NFC(s)` again, which reopens round-2 M1’s U+212A raw-vs-normalized split.

Proposed fix: rewrite behavior 3 as “the ingress canonicalizer maps NFD to NFC before encoding, so `encode(canonicalizeKey(NFD)) === encode(NFC)`.” Also update line 250/506 residue from “injective over NFC-normalized logical keys” to the v3 contract: encoder injective on raw input; cloud key space canonicalized before encode.

**Checked**

APFS note: verified on this machine. A file created as `003_cafe\u0301.md` is visible through the NFC path, and `wx` creation of the NFC name returns `EEXIST`.

Existing-row issue: I did not find a stronger normalization-only prod-row migration defect than §4.1’s existing storage gate. Pre-v3 Supabase Storage rejected the non-ASCII raw keys that would be needed for a paid NFD blob through normal paths. The remaining existing-row risk is accepted/non-`SAFE` ASCII object names, and §4’s gate covers that if it can actually run.

Behavior 16: non-vacuous for additive sync. It would fail if only the validator belt were added or if additive writes stored raw NFD while DB advertised NFC. It does not cover the `transferClassA` two-sided path above.

Verdict: `NOT CONVERGED`
