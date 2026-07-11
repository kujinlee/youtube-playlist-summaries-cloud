# Whole-Branch Dual Review — Stage 2b (Cloud Ingest, Frontend)

**Branch:** feat/stage-2b-cloud-ingest. **Diff:** merge-base `4c0109b`..`642c2e6` (25 commits). **Date:** 2026-07-11.
**Reviewers:** Codex (gpt-5.5) + Claude (opus, independent). **Gate:** final, before auto-merge.

## Cross-cutting checks (both PASS)
- **Local app untouched:** diff over `components/local/*`, `app/api/ingest/*` empty. ✓
- **Session-client discipline:** no service_role in `lib/client/` or `components/cloud/`; createIngest/getJobStatus are plain fetches; `npm run check:confinement` passes. ✓
- **Shared primitive:** zero pre-existing prod callers of `pollUntilTerminal` (grep-confirmed); old-vs-new loop semantically identical when new options undefined; `abortableSleep(…, undefined)` returns `sleep(ms)` directly. ✓
- **Design tokens:** real tokens only (modal `bg-[rgba(0,0,0,.4)]` scrim matches existing modal convention, no token defined). ✓
- **Consistency:** 401→UnauthorizedError→/login uniform across all 5 call sites; IngestError→ingestErrorMessage identical in modal + refresh. ✓
- **Wrong-playlist Refresh:** protected by id-tagged derived playlistUrl (correct by construction) + reqSeq. ✓

## NEW finding — severity split, controller adjudicated
**Refresh (`CloudApp.onRefresh`) has no synchronous double-submit mutex** — relies on async `refreshing` state, unlike NewPlaylistModal's `submittingRef`. Two rapid entries could both call `createIngest(playlistUrl)` (spend path: producer preflight + YouTube fetch + enqueue/join).
- **Codex: BLOCKING** for a money-gate — "same class as the modal bug; would not merge without a refreshingRef + test."
- **Claude: LOW/READY** — React flushes discrete clicks so button disables before a 2nd click; a double-fire POSTs the SAME id-derived URL which the backend dedups (`joined`) → no double-charge, no wrong-playlist. Defense-in-depth, safe to ship.

**Controller decision: FIX (mirror the modal's `submittingRef`).** Rationale: (1) T6 precedent — spend-path re-entrancy gets a synchronous mutex regardless of "no realistic path"; (2) modal-hardened/Refresh-not is the exact asymmetry that hid this from per-task review; (3) auto-merge grant requires a CLEAN whole-branch review — a 3-line fix beats overriding a Blocking on a money path. Fix + focused re-review before merge. → `refreshingRef` mutex in onRefresh + double-refresh guard test.

## Deferred items — both confirm genuinely non-blocking
(a) abortableSleep stray timer (browser no-op, settled-guarded); (b) onProgress-aborts-signal→done (not a banner path); (c) banner lacks role=status/aria-live (a11y follow-up); (d) stale-listVideos→A's video list (display-only, spend path protected by derivation); (e) onRefresh result not null-checked (fails safe via id-match gate). Plus new Low: banner refetch can race a just-clicked sort → new-sort response dropped (display-only, no spend).

## Verdict
Claude: READY. Codex: 1 Blocking (Refresh mutex). **Controller: fix the Refresh mutex → re-review to clean → then merge.** Everything else ready.

## Resolution — CLEAN (merge-ready)
Refresh mutex fixed in `bb13c84` — `refreshingRef` synchronous check at the top of `onRefresh` (before the createIngest await) + reset in `finally` (repeatable, no deadlock; finally runs even on the 401 early return). Both spend paths (modal submit + Refresh) now have parity synchronous mutexes. Codex focused re-review (`642c2e6..bb13c84`): **CONVERGED / MERGE-READY** — Blocking resolved, no ref/state desync, derived playlistUrl + reqSeq + wiring untouched, no new findings. Final suite at `bb13c84`: tsc 0, unit 1955/1955, integration 331 pass/2 skip. **Whole-branch gate CLEAN → auto-merge authorized (standing grant).**

Deferred to post-merge follow-up (all confirmed non-blocking by both reviewers): abortableSleep clearTimeout; banner role=status/aria-live a11y; onProgress-aborts-signal edge; display-only stale-list/sort races.
