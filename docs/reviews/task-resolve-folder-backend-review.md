# Claude Code Review — resolve-folder backend (auto-derive output folder)

**Date:** 2026-06-08 · **Reviewer:** general-purpose senior reviewer
**Scope:** `lib/output-folder.ts`, `app/api/resolve-folder/route.ts`, `lib/youtube.ts` (fetchPlaylistTitle) + tests

## Strengths
- ID-based matching runs `URL.searchParams.get('list')` on both input and stored URLs → `&si=`/order normalized away on both sides.
- Both layouts handled: candidate order `[<dir>/raw, <dir>]` returns nested `<dir>/raw` (agentic) and flat `<dir>` (cs146s).
- Scan is crash-safe: missing root guard, readdir try/catch, per-index try/catch (one corrupt index skips, doesn't abort).
- Path traversal neutralized at the slug boundary (`slugify` keeps only letters/digits); write-boundary still enforced downstream by `assertOutputFolder` in `/api/ingest`.

## Issues
**Critical:** none.

**Important**
1. `normalizeToRoot` has no production consumer yet (only `resolveOutputFolder` is wired). → Consumed by the Header wiring task (Task 17). Noted; not orphaned.
2. Root-that-looks-like-a-flat-playlist ambiguity: a flat playlist folder is structurally indistinguishable from a root-with-one-flat-playlist; `normalizeToRoot` could over-climb. → Mitigated by showing the derived target in the header (UX plan) + documented assumption.

**Minor**
3. Route `baseOutputFolder ?? outputFolder` relies on `readSettings` returning `undefined` (not `''`). Works today; add a comment.
4. No test for corrupt-index skip in `resolveOutputFolder`.
5. No `fetchPlaylistTitle` error-path test; a failed title fetch currently propagates.
6. Scan is sync I/O per request, uncached — fine at this scale.

## Assessment
**Ready to merge: With fixes** — resolve the title-fetch failure behavior and add the cheap test gaps.

## Disposition
Applied: title-fetch wrapped in try/catch → falls back to id slug (also fixes empty-slug); `normalizeToRoot` only strips `/raw` for a real playlist raw dir + empty guard; route maps invalid-URL → 400, unexpected → 500 generic (no leak); added tests for corrupt-index skip, title-fetch failure, normalize edge cases. `normalizeToRoot` consumer lands in Task 17.
