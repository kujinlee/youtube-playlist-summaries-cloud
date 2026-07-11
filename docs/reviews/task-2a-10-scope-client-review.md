# Dual Review — Stage 2a Task 10 (scope-aware API client + ScopeProvider)

**Date:** 2026-07-11 · **Diff:** `f568f45..eec9cfe`

## Codex (gpt-5.5) — Spec PASS · Approved · 0 findings (any severity)
Exhaustive route-parity: listPlaylists→GET /api/playlists; listVideos→`?playlist`/`?outputFolder`+sort; getQuickView→`?playlist`; saveAnnotation→POST `/review?playlist=` body {score/note} (playlist in QUERY, not body); setArchived→POST `/archive?playlist=` body {action}. Confirmed playlist never body-only. Tests assert exact full URLs + init objects; throw-before-fetch `not.toHaveBeenCalled`; 401→UnauthorizedError.

## Claude (opus/sonnet) — Spec PASS · Approved · 0 Critical/Important
Full parity TABLE for all 5 routes × both modes — every URL+method+body matches exactly (cloud query-param playlist; local body outputFolder; client correctly omits/rejects the wrong-mode param). `handle()` maps 401→UnauthorizedError + non-2xx→Error{message}. Scope union/ScopeProvider/useScope (incl. missing-provider throw) correct. Tests use exact strings/objects (no substring false-greens).
- **Minor (test-coverage, deferred → whole-branch):** (1) asymmetric throw-before-fetch coverage (each fn tests one mode; impl correct for both); (2) no direct ScopeProvider/useScope test (T15 will exercise it); (3) listPlaylists no dedicated 401 test (shared `handle()` path, tested elsewhere).

## Note: spec §9 body-vs-query
Spec §9 URL Contracts wrote "body {playlist}" for review/archive POSTs, but T7/T8 implemented `?playlist=` uniformly across ALL cloud routes (controller-confirmed: review:112, archive:62). The client correctly matches the ROUTES (query param). Self-consistent; spec §9 wording superseded by the uniform implementation. Not a defect.

**Disposition:** clean — both passes PASS/Approved, 0 Critical/Important/Blocking/High. Client/route parity verified exhaustively. Task 10 complete. Test-coverage Minors → whole-branch. 21/21 new, full suite 1841, tsc 0.
