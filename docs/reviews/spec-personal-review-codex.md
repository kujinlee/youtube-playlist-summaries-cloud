# Codex Adversarial Review — Personal Review Spec

**Date:** 2026-05-28
**Spec:** `docs/superpowers/specs/2026-05-28-personal-annotations-design.md`
**Phase:** Phase 1 (spec review)

---

## Findings

**P0**

- Severity: P0
  Section: `API Route`, lines 54, 57; `Backward Compatibility`, line 190
  Finding: The spec claims an "atomic index write" but does not specify a concurrency control model for read-modify-write updates.
  Impact: Concurrent score/note saves, ingestion, archive, or deep-dive updates can lose fields if each request reads an old `playlist-index.json` and writes it back later.
  Resolution: Documented as accepted trade-off — single-user local app, same pattern used throughout all write routes. Added to Out of Scope section.

**P1**

- Severity: P1
  Section: `API Route`, lines 41-55
  Finding: The write API has no authorization, origin, or CSRF contract beyond `outputFolder` and `videoId` guards.
  Resolution: Documented explicit threat model — local-only app, no auth consistent with all other routes.

- Severity: P1
  Section: `API Route`, lines 43-55; `Testing`, lines 252-254
  Finding: The route contract specifies only `{ ok: true }` and omits error response bodies/statuses.
  Resolution: Added full response table (200/400/404/500) to spec.

- Severity: P1
  Section: `Data Model`, lines 19-20; `API Route`, lines 46-47
  Finding: `personalNote` is unconstrained free text with no max length.
  Resolution: Added 500-character max; 400 response for oversized notes.

- Severity: P1
  Section: `FilterState`, line 28; `app/page.tsx changes`; `Filtering` table
  Finding: `minPersonalScore` described as "minimum required" but unscored videos still pass — contradicts the label.
  Resolution: Renamed semantics to "dim unscored while filtering" — spec now explicitly documents intent that unscored videos are shown dimmed, not hidden.

- Severity: P1
  Section: `Sorting`, lines 147-152
  Finding: Sort comparator returns `1` when both `a.personalScore` and `b.personalScore` are `undefined` — violates antisymmetry.
  Resolution: Added `if (both undefined) return 0` guard to comparator.

- Severity: P1
  Section: `StarRating`, lines 65-67
  Finding: Optimistic update failure/rollback behaviour undefined.
  Resolution: Added rollback spec — `onChange(previousScore)` called on API failure; stars disabled during in-flight save.

- Severity: P1
  Section: `NoteCell`, lines 88, 167
  Finding: Save closes popover immediately, no loading or error state.
  Resolution: Spec now says popover stays open during save, Save/Cancel disabled; closes only on success; shows error inline on failure.

- Severity: P1
  Section: Props / data flow
  Finding: Optimistic update flow from cell components back to Page's `videos` array not specified.
  Resolution: Added explicit `onAnnotationChange(videoId, patch)` ownership at Page level with full code snippet.

**P2 (presented to user for decision)**

- P2: `NoteCell` focus management → non-modal (Tab moves freely), accepted
- P2: Popover placement flip → flip to stay within viewport, accepted
- P2: Re-sync regression test → added to test table
- P2: `onChange` callback should be `(note: string | undefined) => void` → fixed in spec
- P2: Interaction between archived and unscored opacity → resolved with single `cellDim` computed value (archived takes precedence)
- P2: Dismissal while saving → spec now says dismiss is disabled while save is in flight
- P2: `My Score` first-click direction → specified as descending (highest first)
- P2: API test coverage gaps → expanded test table
- P2: Empty-string notes in manually-edited indexes → Zod `.optional()` accepts them; API normalises going forward (accepted)

**P3 (accepted as-is)**

- P3: Note truncation by UTF-16 vs grapheme — accepted (short notes, acceptable trade-off); later changed to 25 chars during grill-with-docs
- P3: Popover viewport anchoring — noted, deferred to implementation
- P3: `My Score` first-click direction — resolved (descending)
- P3: Component tests for async failure — added to test table

---

## Verdict

**Not ready for implementation as originally written.** All P0/P1 findings were addressed in the spec before proceeding to Phase 2.
