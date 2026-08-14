<!-- codex-review: model=gpt-5.5 -->

**High Finding 1: v4 deletes Unicode equivalence in the thesis, but still instructs canonicalization in the encoder section**

Evidence:

[docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:246)
```md
> segment (`SAFE.test(s)`) but *hashed* the normalized one, so the two equivalence relations §3.5
> claimed to have merged still differed, with exactly one counterexample in all of Unicode (U+212A
> KELVIN SIGN, whose NFC form is ASCII `K`). The deeper problem is §3.5. Normalization is now handled
> at ingress, so **everything reaching this function is already canonical** and the encoder needs no
> opinion about Unicode at all.
```

[docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:301)
```md
#### 3.2.2 The encoder is injective, full stop — because canonicalization happens upstream

v2 said the encoder was "injective on NFC-normalized logical keys", which is a property of a function
composed with something the caller might not have applied. v3 makes it unconditional: **the encoder is
injective on its input**, and §3.5 guarantees every input is already canonical.
```

These contradict the v4 deletion claim:

[docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md:399)
```md
**v4 introduces NO equivalence at all.** Keys are byte strings, as they have always been. Every one of
the eight comparison sites is correct *as written*, unmodified, because two different byte strings are
two different keys — which is what the whole system already assumed. There is no ingress list, no
canonicalizer, no `normalizeLogicalKey` change, and no check script for any of it.
```

Concrete failure scenario: implementation follows §3.2.2 and adds ingress canonicalization, or scopes tests to “already canonical” inputs. That reintroduces the equivalence v4 is meant to delete. The already-demonstrated failure then becomes reachable again: byte-exact cleanup in [reconcile-serial.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:358) sees `to !== from` and deletes the source even when the physical layer has made the source and destination the same object.

Proposed fix: delete the stale v3 sentences. State the encoder contract as “injective on raw input bytes/JS strings,” and make behavior 4 quantify over all valid logical segments, not NFC-normalized inputs. Add a mutation/check that any ingress canonicalizer or `sha256(NFC(s))` implementation fails.

**Checked**

I independently re-probed round-3 B2 against local Supabase at `http://127.0.0.1:54321`, with URL refusal for non-local hosts and cleanup. Raw NFD direct upload is still rejected `400 Invalid key`; raw-hash encoded NFD uploads and downloads with the right bytes. NFC and NFD encode to different physical keys.

I also probed APFS: NFC/NFD aliases (`wx` got `EEXIST`; rename overwrote the existing file), while variation selector and combining grapheme joiner variants stayed distinct files. A full `\p{M}` sweep found no mark that normalizes under NFC/NFD/NFKC/NFKD into `/`, `\`, `%`, whitespace, controls, or `.`; ZWJ is not admitted by the proposed regex.

NOT CONVERGED.
