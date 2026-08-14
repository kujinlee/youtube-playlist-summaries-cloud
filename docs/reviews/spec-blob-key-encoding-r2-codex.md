<!-- codex-review: model=gpt-5.5 -->

**Blocking Finding 1: §3.5 misses the target-occupied guard, so relocation can create two promoted rows that alias one physical summary**

Evidence:

[docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:320](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:320)
```md
**Fix — make NFC canonical at the logical seam too, so "physically the same object" and "logically
the same key" are one equivalence relation.** Four sites:
```

[docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:327](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:327)
```md
3. `describeDivergence` (`reconcile-serial.ts:151-155`) compares NFC-normalized bases, so a
   normalization-only difference is `agreed` and no relocation is attempted at all.
4. The relocation plan's collision check (`reconcile-serial.ts:262-276`) holds **NFC-normalized**
   destinations in its Set, so two sources aliasing onto one destination is `ambiguous-mapping`
   rather than silently sequenced.
```

But the same relocation path has another base-equality guard:

[lib/cloud-sync/reconcile-serial.ts:193](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:193)
```ts
const holder = cloudIndex.find((v) =>
  v.id !== cloudVideo.id &&
  (v.serialNumber === localVideo.serialNumber ||
    (v.summaryMd != null && baseOf(v.summaryMd) === newBase)));
```

Failure scenario:

- Cloud video A: `summaryMd = "007_alpha.md"`, blob exists.
- Local authoritative A: `summaryMd = "003_café.md"`.
- Other cloud video B: `summaryMd = "003_cafe\u0301.md"`, `serialNumber` is stale/null/not `3`, blob exists at the same NFC-equivalent physical key v2 will use for A.
- A relocation runs. The holder check misses B because `baseOf(v.summaryMd) === newBase` is byte-exact.
- If B’s object bytes equal A’s copied bytes, `copyBlob` can report `already: true`; metadata then advertises A at `003_café.md`.
- Now A and B are two promoted rows whose logical keys are different bytes but the v2 seam maps them to one physical object. A later write/regeneration to either key overwrites the other video’s paid artifact.

Proposed fix: include the target-occupied guard in §3.5. Compare target bases with the same canonical equality as the encoder, e.g. `normalizeLogicalKey(baseOf(v.summaryMd)) === normalizeLogicalKey(newBase)`, or compare normalized full summary keys. Add a test with another cloud row occupying the target base only by NFC equivalence.

**Round-1 Fix Audit**

- B1: Mostly fixed, but incomplete. The four named sites address the direct self-delete case; the target-occupied guard above is the missed same-equivalence seam.
- H1/H2: Fixed. `LIMIT = 255` matches the measured per-segment ceiling; I re-probed local Supabase: 255-char segment OK, 256-char segment `500`, 4x250 segments OK.
- H3: Fixed. v2 preserves empty segments, and current Supabase `.replace(/\/$/, '')` behavior is compatible with `''`, `dig/base`, and `dig/base/`.
- M1: Fixed in the spec: marker guard is now every segment, not only leaf.
- M2: Fixed: injectivity is scoped to NFC-normalized logical keys.
- M3: Fixed as far as the spec goes: gate is explicitly unrunnable until storage grants exist, and it skips owner/playlist segments, which matches `objectKey`.
- L1: Fixed by measuring `=`-leading cases.
- L2: Fixed by narrowing shared list contract.

I also checked `normalizeLogicalKey` callers: today only `copyBlob` calls it, and all real adapters delegate `copy()` through `copyBlob`. That means the NFC change affects local/in-memory copy semantics too, but I found no production local copy caller beyond cloud-base reconciliation’s cloud-side `copy`.

Behavior 16 would catch v1’s direct B1 self-delete. It would not catch the missed occupied-target case unless it includes a second cloud row with a canonically equivalent target base.

Verdict: `NOT CONVERGED`
