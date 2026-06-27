# Adversarial Spec Review — Dig Code/Config Slides as Images

**Date:** 2026-06-26
**Spec:** `docs/superpowers/specs/2026-06-26-dig-code-slide-as-image-design.md`
**Reviewer:** Claude adversarial subagent (Codex at usage limit per `docs/plugins.md` fallback rule; Codex-specific pass should be re-attempted before merge).
**Prior spec:** `2026-06-25-dig-slide-selectivity-design.md` (PR #28 — already merged).

---

## Summary verdict

**No Blocking.** Two HIGH findings that require spec clarification or an extra test row before the plan is written. Three MEDIUM findings that should be addressed in the spec or implementation plan. Three LOW findings that can be fixed during implementation.

---

## Confirmed-correct (verified against code)

- `DIG_GENERATOR_VERSION = 2` is at `lib/dig/generate.ts:13`. The spec's "bump 2→3" is the correct mutation site.
- `genVersion` in `DugSection` is already implemented and propagated through `companion-doc.ts`, `dig-merge.ts`, and `render-dig-deeper.ts` (PR #28). The isStale / `↻ outdated` control already works. No pipeline change is needed for staleness — the spec's reuse claim is accurate.
- `parseSlideTokens` (`slide-tokens.ts`) only acts on tokens Gemini emits — fewer tokens automatically means fewer captures. No parser change needed for this policy flip.
- `resolveSlideTokens` (`slides.ts`) already handles code/config images identically to diagram images — the capture, containment, base64 render, and missing-slide placeholder paths are content-type-agnostic. The claim "capture pipeline needs no change" is accurate.
- `render-dig-deeper.ts` markdown-it `image` rule inlines any `assets/` JPEG as a base64 data URI with a `<span class="missing-slide">` fallback on ENOENT. Works for code-slide images as well as any other image.
- Existing generate.test.ts line 197-198 asserts `transcribe[^.]*code block` — this test **must fail (RED)** after the prompt change and must be rewritten to assert the inverse. The spec mentions this but does not make the required test update explicit enough.
- The PR #28 spec had a `↻ outdated` expand-all follow-up task (§4.5 in the prior spec). That wiring (`nav.ts`) selects `.dig-refresh` sections for expand-all. This spec's version bump will mark all `genVersion: 2` sections stale, exercising exactly that path. No contradiction.

---

## Findings

### HIGH

**H1 — Existing generate.test.ts test actively asserts the old policy and will pass on the unmodified codebase (wrong RED baseline)**

`tests/lib/dig/generate.test.ts:197-198` contains:
```
it('instructs transcribing code/commands into fenced code blocks', () => {
  expect(p()).toMatch(/transcribe[^.]*code block/i);
});
```
And line 211-212:
```
it('no longer invites a "code screen" screenshot', () => {
  expect(p()).not.toMatch(/code screen/i);
```

After the prompt flip, the first assertion must become a RED test (`expect(p()).not.toMatch(/transcribe[^.]*code block/i)` or equivalent). The second may stay green. The spec's Testing table (row 7) says "Update any fixtures/assertions that encoded 'code → fence'", but the wording is vague — it does not name `tests/lib/dig/generate.test.ts:197-198` or the exact rewrite. The plan must name this file and line explicitly to avoid a subtle error: an implementer who runs the suite before touching the test will get a false-red that looks like a real failure, or worse, will mark the old assertion as passing after changing the prompt and not notice the semantic inversion.

**Fix:** Add a concrete row to the Enumerated Behaviors table (or spec Testing section) that names `tests/lib/dig/generate.test.ts:197-198` and states: "rewrite to assert that the prompt does NOT contain a transcribe-code instruction; and DOES include code/config in the SLIDE trigger list." Also add a positive assertion: `expect(p()).toMatch(/code.*config.*SLIDE|SLIDE.*code.*config/is)` or similar.

---

**H2 — Caption policy for code/config slides is underspecified in a way that creates Gemini-adversarial risk**

The spec (§ "Policy", point 5) says the caption for a code/config slide is "a short human-readable description (e.g., 'OKF frontmatter: the required `type` field')". Behavior table row 1 says "prompt yields a `[[SLIDE:]]` token (no fence); capture → image." Neither the spec nor the prompt wording (which the spec says to add) specifies:

1. Whether the caption must use backtick inline code (as in the example) or plain prose.
2. Whether Gemini should include the specific value/symbol it sees, or just the conceptual label.
3. How to handle a code slide whose content spans multiple concepts (e.g. a full YAML block with five keys).

This matters because `sanitizeCaption` (`slide-tokens.ts`) strips backticks? Let me check: `sanitizeCaption` strips `] [ ( ) |` and control characters but does NOT strip backticks. So backtick captions are safe to emit. But Gemini may use pipes (stripped) or brackets (stripped) in a caption if the code contains YAML or shell syntax, silently truncating the caption to empty. The spec's example `"OKF frontmatter: the required \`type\` field"` would survive sanitization correctly. But a Gemini-emitted caption like `"Config: field=value|other=val"` would be stripped to `"Config: field=valueother=val"` — lossily. A caption like `"[required] type field"` would become `" required  type field"`.

The spec should instruct Gemini to use plain English phrases free of `|`, `[`, `]` in captions — the same injection-risk characters `sanitizeCaption` removes. This is a prompt-wording constraint, not a parser change.

**Fix:** Add to the spec prompt policy (point 5): "Caption must be a plain English phrase with no `|`, `[`, `]`, `(`, `)` characters, since these are stripped by the token parser." Add a Behavior table row: "Code slide with YAML/shell syntax in content — Gemini caption uses plain prose, not verbatim syntax" → expected: sanitizeCaption output is non-empty and semantically meaningful. This is testable with a `buildDigPrompt` unit test that asserts the caption guidance is present in the prompt string.

---

### MEDIUM

**M1 — Behavior table row 2 ("no fabricated slide") has no corresponding prompt wording constraint**

Row 2: "code only spoken/described, not on a slide → plain prose, no fence, no SLIDE token." The spec adds code/config to the `[[SLIDE:]]` trigger list but does not say how Gemini is to know whether code was "on a slide" vs. "spoken." The existing prompt says "Emit `[[SLIDE:…]]` ONLY when a genuine visual … **cannot be conveyed in words**." Adding code/config slides to the emit-list without a guard creates ambiguity: Gemini may emit a `[[SLIDE:]]` for a speaker saying "run `git commit -m 'fix'`" even though no slide was shown. The prior policy (transcribe → fence) was actually safe here because transcription of spoken commands is still prose.

The spec says "No fabrication: emit `[[SLIDE:]]` only when the code/config is **actually shown on a slide**" — but this constraint must be in the prompt, not just in the spec document. The current draft (§ "Policy, point 4") says to include this in the prompt. This is the right call — but the spec should also note that the acceptance test for this behavior is the OKF section itself (post re-dig, no spurious slides in prose-only sections). The Behavior table should include this as a test row with a testable fixture expectation rather than just a principle.

**Fix:** Spec is structurally correct — just confirm the plan task includes prompt text that says explicitly "only when the code or config is **visibly shown on a slide or screen capture in the clip**; if code is only spoken or in the transcript but not shown on screen, do not emit a [[SLIDE:]] token." Also add an E2E acceptance step: after re-digging the OKF section, verify no other sections in the same video acquired spurious slide tokens.

---

**M2 — The ≤3 slide budget is now jointly competed by code slides and graphic slides, but the spec does not enumerate the mixed-section budget edge case**

Behavior row 5 says "≤3 `[[SLIDE:]]` total" and the spec says "The existing ≤3 cap is unchanged; code/config slides count toward the same budget." This is the right policy. But there is no behavior row or test case for the edge case where a section has 2 genuine diagrams and 1 code slide — all three should be emitted. Nor for a section with 4+ code slides — only the first 3 should appear. The prior spec's Behavior table row 6 (from 2026-06-25 spec) covered "Gemini emits zero slides" but not the mixed-budget case.

This matters because `parseSlideTokens` enforces the cap at parse time, not at generation time. If Gemini emits 4 `[[SLIDE:]]` tokens, only the first 3 survive. The spec should acknowledge that the behavior is already correctly enforced by the existing parser and add a test row making the mixed budget explicit.

**Fix:** Add Behavior row: "Section with 2 graphic slides + 1 code slide → all 3 are emitted, 0 dropped" and "Section with 2 graphic slides + 2 code slides → only 3 emitted (4th dropped by parseSlideTokens regardless of content type)." These are already testable via `parseSlideTokens` directly — no Gemini mock needed.

---

**M3 — Capture-failure path for code/config slides is underspecified relative to the existing graphic-slide failure path**

For existing graphic slides, when yt-dlp fails, `resolveSlideTokens` strips all tokens and returns text-only markdown — the user sees the `[[SLIDE:…]]` removed entirely (no placeholder, no fence). When ffmpeg fails per-token, that token is removed individually. The spec says "code shown but capture fails" is an edge case to consider, and the out-of-scope section defers to the existing `stripAllTokens` path.

The issue is user-facing: a code/config slide that fails to capture leaves **nothing visible** (the strip path removes the token entirely), whereas a code/config slide that was previously a fence would have left a partial-but-visible transcription. The spec explicitly chose "image-only, transcription dropped" (Out of Scope §4). But it does not say what the user should see on capture failure: a `<span class="missing-slide">…</span>` placeholder (the per-token ffmpeg success path that writes the markdown image reference → `render-dig-deeper.ts` shows the placeholder when the JPEG is absent from disk) — or nothing.

Actually tracing the code: on yt-dlp failure, `stripAllTokens` removes the raw token text → no `![caption](…)` → no `<span class="missing-slide">`. On ffmpeg failure per-token, the token is also removed → same result. So on any capture failure for a code slide, the user sees nothing — no image, no placeholder, no fence. For graphic diagrams this was acceptable. For code/config slides it may be more surprising because the prose may reference "as shown in the config" but the visual is absent.

The spec should acknowledge this explicitly: "On capture failure, code/config slides are treated identically to graphic slides — stripped silently. The prose Gemini writes should be self-contained enough that the absence of the image is not fatal." This is a known limitation, not a bug, but it should be documented.

**Fix:** Add this to "Out of Scope" or Edge Cases section. No code change needed. The behavior table should note it: row 1 expected column should say "capture → image; on capture failure → silently stripped (same as graphic slide, prose self-contained)."

---

### LOW

**L1 — The spec does not call out that `generate.test.ts:159` ("DIG_GENERATOR_VERSION is the integer 2") must be updated to assert 3**

`tests/lib/dig/generate.test.ts:159-161`:
```ts
describe('DIG_GENERATOR_VERSION', () => {
  it('is the integer 2', () => {
    expect(DIG_GENERATOR_VERSION).toBe(2);
  });
});
```

After bumping to 3, this test fails with a clear message ("expected 2, received 3"), so it will not be silently missed — it is a straightforward update. But the spec's Testing section does not mention it. The plan should list it.

**Fix:** Add to Testing table: "Update `generate.test.ts:159` — assert `DIG_GENERATOR_VERSION` is `3`." Trivial but should be explicit.

---

**L2 — The "capture → image" outcome for code slides is testable only via prompt-string assertions, not via any mock-Gemini fixture — spec should acknowledge this honestly**

The spec's "Honest limit" paragraph notes that tests verify the prompt says the right thing but cannot verify Gemini obeys. This is correct. However, the spec also says "Acceptance is verified by re-digging the OKF section and confirming the slide image appears." This is an informal verification step with no corresponding E2E test fixture. The existing E2E dig tests use a stub POST→SSE path (per the prior review); they cannot assert Gemini actually emitted a `[[SLIDE:]]` for a code slide.

There is no adversarial risk here (the spec is already honest about it), but the implementation plan should distinguish clearly between: (a) unit tests asserting prompt policy (automatable, required for CI), and (b) manual acceptance with the real video (required once before merge, not in CI).

**Fix:** Add a note to the plan's acceptance criteria: "Manual acceptance test: re-dig OKF section `P_E29-87THI` section 149, confirm `[[SLIDE:]]` token emitted and image rendered in HTML doc. Not in CI." This makes the two verification modes unambiguous.

---

**L3 — Docs with `genVersion: 2` but zero slides are marked stale, pay one re-dig, then stay fresh — spec should confirm this is intentional and the cost is acceptable**

The version bump marks ALL existing dug sections stale regardless of whether they ever emitted any `[[SLIDE:]]` tokens. A section that was pure prose under v2 (no fence, no slide) will also show `↻ outdated`, re-dig, and come back as pure prose under v3 — functionally identical but at the cost of one Gemini call. The spec says "lazy / on-demand" which is correct — no cost unless the user clicks. But if a user has 50 dug sections (all prose, no code), they will see 50 `↻ outdated` badges and trigger 50 re-digs to change nothing.

This is a policy decision, not a bug. The alternative (per-content-type versioning) is complex and explicitly out of scope. The spec should explicitly acknowledge this tradeoff: "All existing dug sections become stale regardless of content. Prose-only sections re-dig cheaply (no slide capture). The cost is proportional to the number of sections the user deliberately refreshes."

**Fix:** Add a one-sentence acknowledgment in the Migration section: "Sections that were already prose-only (no [[SLIDE:]] under v2) become stale and re-dig as prose-only under v3 — no semantic change, one Gemini call per refresh. This is acceptable given the lazy / on-demand model."

---

## What was looked for but not found (genuine non-issues)

- **PR #28 regressions:** the existing `isStale` / `↻ outdated` / expand-all wiring is unaffected. The spec's policy flip only changes what the v3 prompt asks Gemini to do; all downstream code already handles whatever tokens Gemini emits.
- **Token parser changes needed:** none. `parseSlideTokens` is content-type-agnostic and handles code-slide timestamps identically to graphic-slide timestamps.
- **Rendering changes needed:** none. `render-dig-deeper.ts` builds the same `![caption](assets/…)` reference regardless of what the slide depicts.
- **Companion-doc format changes:** none. `genVersion` already serialized/parsed per-section (PR #28).
- **Migration script risk:** none needed — version bump + lazy re-dig is the correct and safe pattern. Existing dug sections remain readable; only their genVersion triggers the badge.
- **Korean-language path:** unchanged. The prompt change is content-policy only; the Korean instruction block is independent.
- **Mixed code+graphic prompt ambiguity:** the prompt already uses "ONLY when" and lists specific approved categories. Adding code/config to the approved list does not create ambiguity about graphics. The exclusion list (title cards, bullets, quotes, tips, speaker) is unchanged.

---

## Bottom line

Architecture is sound. This is a minimal, well-scoped change — one prompt rewrite + one version bump. The staleness cascade is correctly handled by existing infrastructure. Two HIGH findings require explicit test-naming (H1) and prompt-wording guidance for caption safety (H2) before the plan is written. Address H1 and H2 in the spec before handing off to implementation. M1-M3 can be addressed in the plan's behaviors table. L1-L3 are cosmetic/documentation and can be fixed during task execution.

**Pre-plan actions required:**
1. (H1) Name `tests/lib/dig/generate.test.ts:197-198` explicitly as a test to invert; add a positive assertion for `code/config` in the SLIDE trigger list.
2. (H2) Add caption guidance to the prompt policy: no `|`, `[`, `]`, `(`, `)` characters in captions; plain English description only.
