# Codex Adversarial Review — Clickable Section Timestamps (final, code)

**Date:** 2026-06-18
**Tool:** `codex:rescue --fresh` (Codex available; the owed pass per `docs/plugins.md`).
**Range:** `f21af8f..HEAD` on `feat/section-timestamps`.
**Verdict (as received):** MUST FIX BEFORE MERGE — malformed Gemini tokens can leak into saved summaries as raw text, violating the all-or-nothing degradation contract.

---

## HIGH — malformed non-digit tokens leak raw (MUST FIX)
`lib/transcript-timestamps.ts` — `OWN_LINE_TOKEN = /^\s*\[\[TS:(\d+)\]\]\s*$/` and the final scrub
`ANY_TOKEN = /\[\[TS:\d+\]\]/g` both match **digits only**. A token like `[[TS:-1]]`, `[[TS:1.5]]`, or
`[[TS:abc]]` on its own line is therefore (a) not collected → does NOT trigger degradation (other
valid tokens still resolve), and (b) not scrubbed → remains raw in the saved `.md` and the rendered
HTML. Violates spec §8 ("no raw `[[TS:…]]` ever reaches the reader") and the all-or-nothing contract.
**Fix:** broaden both token regexes to match any `[[TS:<payload>]]`; let the existing integer
validation (`Number.isInteger(n) && 0 <= n < len`) reject the bad payload → degrade all; scrub any
remaining `[[TS:…]]` outside fences.

## MEDIUM — resolved-range monotonicity not enforced
`lib/transcript-timestamps.ts` — index monotonicity is validated, but resolved start/end seconds are
not. If transcript offsets were out of order (or two indices floor to the same second), a range could
be `end <= start`. Low real risk (youtube-transcript returns chronologically ordered segments) but the
resolver doesn't enforce the invariant it relies on.
**Fix:** also require resolved start/end to be finite and strictly increasing, else degrade.

## MEDIUM — transcript segment shape trusted at runtime
`lib/youtube.ts` — `fetchTranscriptSegments` maps `s.offset/1000`, `s.duration/1000` without checking
they are finite. A malformed library response feeds `NaN` into `buildIndexedTranscript`/`timestampLine`.
**Fix:** validate/repair each segment; keep only rows with finite numeric `offset`/`duration` and a
string `text`.

## LOW — malformed leading `▶` prose consumed
`lib/html-doc/parse.ts` — `extractTimeRange` consumes the first non-blank line if it starts with `▶`,
even when it isn't a valid timestamp line; a hand-authored section legitimately starting with `▶`
loses that prose. **This is the spec §8 documented behavior** ("malformed `▶` line → consume but
null"). Left as-is by decision.

## Handled correctly (Codex confirmed)
off-by-one end-time + `tokenK` advancement; single-token end=duration; fenced tokens incl. lang info
strings + unterminated fences (resolver↔parser consistent); blank lines before the `▶` line; magazine
model persistence + offline rerender repopulation; title drift guard; detectLanguage equivalence;
render escaping + `rel="noopener noreferrer"`; `fetchTranscriptSegments` error wrapping.

## Resolution
- HIGH + both MEDIUMs: fixed (see follow-up commit) with TDD.
- LOW: accepted (spec §8 behavior).
