# Dig Deeper: Code/Config Slides as Images (not transcribed fences)

**Date:** 2026-06-26
**Status:** Design — awaiting user review
**Supersedes the code-handling half of:** `2026-06-25-dig-slide-selectivity-design.md` (PR #28)

---

## Problem

PR #28 (dig-slide-selectivity) instructed Gemini to **transcribe** any slide showing a
command, terminal/CLI, code, or config into a fenced code block instead of screenshotting it,
on the theory that transcribed code is "sharper, copyable, and themed."

In practice the first real code slide (the OKF section of video `P_E29-87THI`, section 149)
rendered as a thin, incomplete fragment:

```
---
type: metric
```

This reads as neither a proper code block nor an image — a bare `---` with no closing fence —
and the user perceived it as a broken image. Investigation confirmed:

- The companion `.md` and the server render are **correct** — it is a real `<pre><code>` block
  with **zero** `<img>` tags. There is no rendering bug.
- Across **all** dig docs there is exactly **one** transcribed code block (n=1), so the
  transcription path has essentially no track record.
- Transcription reliability is unprovable at n=1, and Gemini samples video coarsely (~1 fps,
  reduced resolution), so dense on-screen code can be under-read.

**Decision:** when a slide's value is the on-screen code/config itself, show the **captured
slide image** (authoritative, 720p) rather than a verbatim transcription that may be wrong or
incomplete. Visual fidelity wins for this content class.

---

## Why the image is additive, not redundant (prose-grounds-meaning / image-preserves-fidelity)

The dig request sends Gemini the **actual video clip** (`file_uri` + `video_metadata` temporal
clip, `mime_type: video/mp4`) **together with** the indexed transcript, and instructs it to
elaborate "grounded in the transcript and video content provided." So:

- **The prose already carries the slide's *meaning*.** Gemini watches the slide and explains it
  in words (e.g., the OKF prose already describes the required `type` frontmatter field — read
  off the slide). The explanation does not depend on a transcription block.
- **The `[[SLIDE:]]` token is not a second understanding pass.** It only marks a timestamp; the
  screenshot is grabbed separately by ffmpeg at 720p. The image is a faithful picture of the
  same slide Gemini already understood.
- **The image preserves *fidelity* the prose can't guarantee.** Because Gemini samples video
  coarsely while the ffmpeg grab is a sharp 720p frame, the screenshot can preserve fine detail
  (every line of a config block, exact symbols) that Gemini's coarse sampling may under-read and
  therefore omit from prose. Gemini also elaborates *salient* content, not exhaustively.

Net: prose explains, image preserves fidelity, and we drop the unreliable middle layer
(verbatim transcription). The two are complementary by construction — the reader gets Gemini's
interpretation in words plus the ground-truth pixels to check it against.

---

## Scope of change

The change is almost entirely in the **generation prompt** (`lib/dig/generate.ts`). The capture
pipeline (`lib/dig/slides.ts`, yt-dlp + ffmpeg), token parsing (`lib/dig/slide-tokens.ts`),
companion storage (`lib/dig/companion-doc.ts`), and rendering (`lib/html-doc/render-dig-deeper.ts`,
base64 inline + missing-slide placeholder) **already handle images and need no change.**

### Policy (new prompt wording)

1. **Remove** the rule: *"If the clip shows a command, terminal/CLI, code, or config, transcribe
   it into a fenced code block … do not screenshot it."*
2. **Extend** the `[[SLIDE:]]` trigger list to include **code / terminal / CLI / config slides
   whose on-screen text carries meaning** — treated like any other genuine visual.
3. **Still excluded** (unchanged): title cards, bullet lists, quotes, tips, speaker-on-camera.
4. **No fabrication:** emit `[[SLIDE:]]` only when the code/config is **actually shown on a
   slide**. If code is merely spoken or described with no on-screen slide, it stays as plain
   prose — no fence, no image.
5. **Caption** for a code/config slide is a short human-readable description (e.g.,
   *"OKF frontmatter: the required type field"*), not a verbatim transcription.
   **Caption character constraint (review H2):** captions must be plain English phrases and
   **must not contain `[`, `]`, `(`, `)`, or `|`** — `sanitizeCaption` (`lib/dig/slide-tokens.ts:118`)
   strips those characters, and `|`/`]` are token delimiters in the `[[SLIDE:sec|caption]]`
   grammar, so a caption containing them is silently mangled or truncated. The prompt must
   instruct Gemini explicitly to avoid those characters (no raw code/YAML/shell punctuation in
   the caption — describe the slide in words).
6. The existing **≤3 `[[SLIDE:]]` per section** cap is unchanged; code/config slides count
   toward the same shared budget (review M2: 2 diagrams + 2 code slides → still only 3 emitted).
   "Most sections need zero slides" guidance stays.

### Result

No code-fence transcription path remains in dig output. What was the `type: metric` fence
becomes the actual slide screenshot for the OKF section after re-dig.

---

## Versioning & migration

- **Bump `DIG_GENERATOR_VERSION` 2 → 3** (`lib/dig/generate.ts:13`). This is the entire migration
  trigger.
- Every existing dug section (stamped `genVersion: 2`) immediately computes `isStale` against the
  new constant and renders the PR #28 `↻ outdated` `.dig-refresh` control.
- Re-dig is **lazy / on-demand**: the user clicks `↻ outdated` (or "expand all", which PR #28
  wired to refresh stale sections); the section regenerates under the new prompt and the
  code/config slide returns as a screenshot. **No bulk regeneration, no Gemini calls on page
  load.**
- The OKF doc specifically: one re-dig of section 149 → the `P_E29-87THI` clip is captured → the
  `type: metric` fence is replaced by the slide image.
- **No data migration script, no file rewrites** — the version bump plus the existing
  stale-refresh UI does it all.
- **Prose-only sections (review L3):** a v2 section that legitimately had no slides re-digs to a
  v2-equivalent prose-only section under v3 — a functional no-op costing one Gemini call per
  click. Acceptable; the staleness UI does not distinguish "had a code fence" from "had nothing".

---

## Testing

### CI-automated (jest, written first / RED)

| Layer | Exact change |
|---|---|
| **Prompt content** | `tests/lib/dig/generate.test.ts` — the test *"instructs transcribing code/commands into fenced code blocks"* (asserts `/transcribe[^.]*code block/i`, ~line 197–198) must be **inverted**: assert the prompt does **not** instruct transcribing code. **Add** a positive assertion that the prompt lists code/config/terminal among the `[[SLIDE:]]` triggers, and an assertion of the caption character constraint (H2 — prompt tells Gemini to avoid `[ ] ( ) |` in captions). |
| **Version constant** | `tests/lib/dig/generate.test.ts` — the assertion `expect(DIG_GENERATOR_VERSION).toBe(2)` (~line 188) → `toBe(3)` (review L1). |
| **Selectivity tests** | `tests/lib/dig/slide-tokens.test.ts`, `tests/lib/dig/companion-doc.test.ts` — update any fixtures/assertions that encoded "code → fence" to reflect "code → slide". |
| **Staleness** | Adjust/add a test so a `genVersion: 2` section computes `isStale` against `3` (the existing route-stamps-`DIG_GENERATOR_VERSION` test stays green). |
| **Budget (review M2)** | Add explicit rows: 2 diagrams + 1 code slide → 3 emitted; 2 diagrams + 2 code slides → still only 3 (parser-enforced cap). |
| **Capture / render** | Unchanged — `slides.ts` and `render-dig-deeper.ts` already handle images; existing tests cover them. |

### Manual-once (real Gemini call — not CI; review L2)

- **Acceptance:** re-dig the OKF section (`P_E29-87THI`, section 149) and confirm the slide image
  appears in place of the `type: metric` fence.

**Honest limit:** the policy is enforced by *prompt wording*. Gemini is probabilistic, so
"code slide → screenshot" is a strong instruction, not a guarantee. CI tests verify the *prompt*
says the right thing; they cannot verify Gemini always obeys — hence the manual acceptance check.

---

## Known limitations / edge cases

- **Capture failure (review M3):** if yt-dlp or ffmpeg fails for a code/config `[[SLIDE:]]` token,
  `slides.ts` silently strips the token — leaving prose with **no image and no fence** for that
  point. This is the existing PR #28 behavior (per-frame ffmpeg failure → drop token; yt-dlp
  ENOENT → strip all). Accepted as-is: the prose still explains the slide's meaning, so a dropped
  code slide degrades to prose-only, not to a broken artifact. Logged as `[dig-slide-miss]`.
- **Caption mangling:** mitigated by the prompt caption constraint (Policy §5); residual risk if
  Gemini ignores it is a stripped/empty caption, never a broken token (`sanitizeCaption` is total).

## Out of scope

- Reliability *detection* / model self-confidence (the chosen approach — image-first — removes the
  need for it).
- Keeping transcription as a secondary copyable element (explicitly rejected: image-only).
- Per-content-type slide budgets (keep the unified ≤3 cap).
- Bulk regeneration of all existing dug sections (lazy re-dig only).

---

## Enumerated Behaviors (for the implementation plan)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Code/config slide → image | clip shows on-screen code/config whose text carries meaning | prompt yields a `[[SLIDE:]]` token (no fence); capture → image |
| 2 | No fabricated slide | code only spoken/described, not on a slide | plain prose, no fence, no `[[SLIDE:]]` |
| 3 | Genuine graphic → image | diagram/chart/architecture/UI | unchanged — `[[SLIDE:]]` |
| 4 | Non-visual text excluded | title card, bullet list, quote, tip, speaker | no `[[SLIDE:]]`, no fence |
| 5 | Slide budget — shared cap | 2 diagrams + 2 code slides in one section | only 3 `[[SLIDE:]]` emitted (parser cap) |
| 6 | Existing dug section stale | `genVersion: 2` section loaded after bump | renders `↻ outdated`; re-dig regenerates under v3 |
| 7 | Prompt no longer transcribes code | build prompt | string excludes "transcribe … do not screenshot"; includes code/config in `[[SLIDE:]]` list |
| 8 | Caption constraint in prompt | build prompt | prompt instructs captions avoid `[ ] ( ) \|` (plain English) |
| 9 | Code only spoken, not on a slide | clip has no on-screen code | prose only — no `[[SLIDE:]]`, no fence |
| 10 | Code slide capture fails | yt-dlp/ffmpeg error on a code `[[SLIDE:]]` | token stripped → prose-only at that point; `[dig-slide-miss]` logged |
| 11 | Version constant | read `DIG_GENERATOR_VERSION` | equals `3` |
