<!-- codex-review: model=gpt-5.5 -->

**Blocking**

None.

**High**

1. Structural safety claim is false / overstated.  
[model-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/model-store.ts:15) leaves `ModelEnvelopeSchema` non-strict, and [types.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/types.ts:40) only makes the top-level `MagazineModelSchema` strict. `MagazineSectionSchema` and `BulletSchema` are not strict, so nested new fields are accepted and stripped. A real version bump that adds `section.pullQuote`, `section.intent`, `bullet.kind`, or changes the meaning of existing string fields would pass current zod and render with old semantics. B8c only proves one narrow incompatible change: `bullets: []`.

2. `sameTitles` is not a complete positional-coherence gate.  
[read-model.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/read-model.ts:16) checks ordered title equality, so reordered distinct titles and count drift in `sourceSections` are caught. But duplicate titles defeat identity: two sections both parsed as `Intro` can be reordered while the title sequence remains `['Intro', 'Intro']`, causing stale leads/bullets to attach to the wrong prose. Also, `sourceSections.length === parsed.sections.length` says nothing about `model.sections.length`. [render.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/render.ts:84) silently returns `''` when `model.sections[i]` is missing, so a schema-valid envelope with two `sourceSections` and one model section renders a 200 with a dropped section. Current generation checks count after Gemini, but persisted/cross-version/raw envelopes are not schema-barred from this state.

**Medium**

1. Owner/share split creates deliberate content divergence and the docs/comments do not state the product cost plainly enough.  
Share now serves a skewed title-stable model at [route.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/s/[token]/route.ts:96). Owner serve still calls `readFreshMagazineModel` and regenerates on version skew at [serve-doc.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-doc.ts:67). Failure scenario: anonymous viewer sees old prose indefinitely; owner opens same document and pays to heal; subsequent anonymous viewers see different content. That may be acceptable, but it is not “same link, same content.”

2. Current specs/comments still assert the old 503-on-skew behavior.  
Missed live docs/tests:
- [1F-b spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:48) still says the leaf exports `readFreshMagazineModel`; [line 89](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:89) still says share calls `readFreshMagazineModel` and stale means 503.
- [1F-c downloads spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:23), [line 35](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:35), and [line 120](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md:120) still encode fresh-only / stale-503 for share HTML.
- [cloud-sync e2e test comment](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/cloud-sync/e2e.int.test.ts:812) and [companion unit test comment](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/cloud-sync/companion.test.ts:40) still say downgrade flips share to 503.
- [client api comment](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/client/api.ts:258) still frames warmup around “share still 503s.”

3. `companion.ts` comments/code names now have stale semantics, though not a live 503 branch.  
I do not see code in [companion.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/companion.ts:113) that literally branches on the old share-503 assumption. The guard can still be justified by avoiding owner re-serve spend. But [line 142](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/companion.ts:142) still defines `shareNeedsOwnerServe` as “may not render until you re-serve,” which is no longer generally true. It is now closer to “may need owner serve to heal/freshen,” not “may need owner serve to render.”

**Low**

None.

**Checks**

B8c is genuinely invalid today: `bullets: []` violates `MagazineSectionSchema` `.min(3)` at [types.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/types.ts:42).

B8’s `'LEAD-FROM-SKEWED-MODEL'` assertion is a sufficient silent-regeneration guard in this test file: [share-route.test.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/share-route.test.ts:11) mocks Gemini to throw, and [line 214](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/share-route.test.ts:214) proves the cached skewed model was rendered.

Anonymous-route never-charge import graph still looks clean from source inspection/grep: no live imports/calls into Gemini, `serve-doc`, reserve RPCs, or `.rpc(` in the share sources.
