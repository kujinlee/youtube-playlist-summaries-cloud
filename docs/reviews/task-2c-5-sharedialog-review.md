# Claude Task Review — Stage 2c Task 5 (ShareDialog)

**Reviewer:** Claude (independent subagent). **Diff:** `d25d435..6fc6191` (R1) + fix `0952d60` (R2). **Date:** 2026-07-11.
**Verdict: Spec ✅ · Quality Approved** (after the ref-gated-dismissal fix).

## Mock-vacuity check (the adversarial ask) — NON-VACUOUS
`beforeEach` only `mockReset()`s both mocks (no shared default return). Each of the 16 (→18) tests sets its own `mockResolvedValue`/`mockRejectedValue`/`mockReturnValue(neverResolving)` before asserting. The switch from `jest.spyOn(realModule, fn)` (throws `Cannot redefine property` under this repo's SWC-compiled non-configurable getters — confirmed, matches `new-playlist-modal.test.tsx` precedent) to a `jest.mock` factory is legitimate and preserves per-test control. `UnauthorizedError` defined inside the same factory → `err instanceof UnauthorizedError` matches the mocked module identity. Both reviewers independently confirmed OK.

## Behavior/spec (all verified)
TTL 7/30(default)/never → `createShare(pid,vid,ttl)` per selection; create success holds `{id,url}`, URL = `window.location.origin+result.url`, Copy/Revoke enabled, dialog stays open; Copy → `clipboard.writeText` → transient "Copied ✓" in a **permanently-mounted** `aria-live="polite"` region (correct — AT announces changes to a present region), reject → `inputRef.select()` no throw; Revoke clears held share on ANY resolve incl `{revoked:false}`, only thrown error → alert; 401 → `router.replace('/login')` both paths; other errors → `role="alert"` stays open. Dismissal ✕/Escape/backdrop all via `guardedClose`, all tested (with `cleanup()` between renders). a11y `role=dialog`+`aria-modal`; trap handler byte-copies NewPlaylistModal's selector; a11y test focuses LAST → Tab → asserts FIRST (non-vacuous). **Self-restore correctly DROPPED** (only initial-focus effect, no unmount `.focus()` cleanup) — Task 7 owns restore, no race. Tokens: only real ones (`--surface-base/-overlay`, `--border`, `--text-primary/-muted`, `--accent`, `--danger`, `rgba(0,0,0,.4)`). Diff scoped to the 2 new files, no service_role/DB.

## Important finding (both reviewers) — FIXED
`guardedClose` gated on `busy` state, not the synchronous `inFlightRef` — the brief required the ref to gate backdrop+Escape (sub-frame window). **Fix `0952d60`:** `guardedClose = () => { if (!inFlightRef.current && !busy) onClose(); }`. Codex re-review CONFIRMED-FIXED; 18/18 pass.

## Lows — FIXED in 0952d60
- (Codex) revoke error paths untested → added revoke-401→login + revoke-generic→alert tests (each own reject mock, non-vacuous).
- (Claude) initial focus on first radio (7d) not default 30d → `ttlGroupRef` moved to the 30d radio.

⚠️ Cannot verify from diff: Task 7's consumption of `onClose` for focus restore (out of scope; T7 owns it).

**Round 2 (fix `0952d60`) CONVERGED** — Codex confirmed all 3 fixes genuine, no new defect. share-dialog 18/18, full suite 1985, tsc 0.
