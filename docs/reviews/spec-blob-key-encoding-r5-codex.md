<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Blocking — `encodeSegment` is specified as injective, but the design is a truncated hash**
Evidence: [spec:107](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:107)

```text
return `${head}=h${base64url(sha256(utf8(s))).slice(0, 22)}${ext}`
```

and [spec:114](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:114):

```text
`encodeSegment` is **injective over all valid logical segments as raw JS strings**
```

Failure scenario: two different non-`SAFE` logical segments with the same 32-char safe head, same extension, and same first 132 bits of SHA-256 encode to the same physical segment. The second write can make the first paid artifact unreachable or return the wrong bytes for a different video. The collision is cryptographically unlikely, but the spec states a stronger property than the mechanism can provide, and behavior 4 cannot prove it as a property test over arbitrary logical segments.

Proposed fix: either use a reversible encoding if strict injectivity is required, or change the contract to “collision-resistant, with structurally disjoint identity/hash branches,” and make the accepted collision risk explicit. Behavior 4 should stop claiming arbitrary injectivity; keep only the crafted `SAFE`/`=` branch-collision test.

**Medium — Behavior 19’s worker-side falsifier is vacuous for the current mint path**
Evidence: [spec:201](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:201)

```text
a title yielding a key with a space, `~`, or an emoji is enqueued
```

but the minted key comes from [summary-handler.ts:96](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/summary-handler.ts:96):

```ts
const baseName = `${padSerial(serial)}_${slugify(payload.title)}`;
```

and [slugify.ts:4](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/slugify.ts:4):

```ts
.replace(/[^\p{L}\p{N}]+/gu, '-')
```

Failure scenario: a test using a normal title with spaces, `~`, or emoji will not exercise the new precondition because `slugify` removes/maps those characters before `assertCloudSummaryMdKey` would see the key. After widening to `\p{M}`, the worker mint path appears to have no current real title that fails the guard. The sync/adoption path does: it writes the sender key verbatim at [sync-run.ts:263](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:263).

Proposed fix: split the falsifier. For worker minting, place the assertion immediately after `baseName` is computed and before `summaryCore`/`generateSummary`; test it with an injected or future-broken key constructor, not a normal title. For sync, behavior 19 should use an adopted `summaryMd` containing a space, `~`, emoji, slash-like corruption, or overlong component and assert refusal before `putStaged`.

Also specify cleanup/classification: the worker currently reserves a row before `baseName` exists at [summary-handler.ts:95](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/summary-handler.ts:95). If the new assertion throws there, it should be non-retryable and should remove a newly-created bare reservation, the same way the permanent transcript path does.

**Medium — v5 keeps the known non-byte-exact `copyBlob` equivalence as “unreachable”**
Evidence: [blob-store.ts:134](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/blob-store.ts:134)

```ts
if (normalizeLogicalKey(from) === normalizeLogicalKey(to)) return { ok: true, already: true };
```

v5 records the defect but keeps it unchanged at [spec:211](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:211):

```text
`copy()` needs no change
```

and [spec:212](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:212):

```text
Its same-key short-circuit **is** wrong on an aliasing backend
```

Failure scenario: if any future local `.copy()` caller appears, `copyBlob` can return `{ok:true, already:true}` without proving the source exists or the destination has bytes. This is exactly the “safe because unreachable” class the Phase 6 review calls out. I verified current reachability: `.copy(` has one non-test caller, [reconcile-serial.ts:282](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:282), and it is `cloud.blob.copy`.

Proposed fix: delete `normalizeLogicalKey` and the short-circuit. Let `copyBlob` read source and destination through `tryGet`. If the bytes match, it will still return `{ok:true, already:true}` with proof.

**Checked / Verified**

§3.3’s marker boundary is correct: v5 scopes the marker check to the physical remainder only, not the caller prefix, which fixes the round-4 `=` stranding case.

§3.4’s local direction is correct: [local-blob-store.ts:36](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/local/local-blob-store.ts:36) uses `fs.statSync`, so APFS itself answers the aliasing question for an orphaned vault file.

Supabase direction needs care but I do not have a concrete failure: [supabase-blob-store.ts:78](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:78) is `get() !== null`, and [blob-store.ts:57](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/blob-store.ts:57) says false does not prove absence. The additive guard may use `exists()` as a fail-closed positive check, but must not treat `false` on Supabase as proof that overwriting is safe.

The Phase 6 “do not add shared `sameKey()`” conclusion is right. The remaining problem is the opposite: one old equivalence helper still exists and should be deleted, not generalized.

NOT CONVERGED.
